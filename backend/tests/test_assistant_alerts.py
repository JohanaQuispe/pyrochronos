"""Consultas compartidas y seguridad de los avisos NRT sin red real."""
from datetime import datetime, timedelta, timezone
import copy
import importlib.util
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from pyro import assistant, nrt, groundtruth
from pyro.config import Config, load_config
from pyro.store import Dataset


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv('PYRO_FIELD_DIR', str(tmp_path))
    raw = copy.deepcopy(load_config().raw)
    raw['api']['data_file'] = str(tmp_path / 'detections.parquet')
    return Config(raw)


@pytest.fixture
def bot():
    path = Path(__file__).resolve().parents[1] / 'scripts' / 'bot.py'
    spec = importlib.util.spec_from_file_location('bot_assistant_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def ds():
    rows = [[20000, -12.0, -69.0, 2, 2, -1, 10., 0]] * 10
    return Dataset(pd.DataFrame(rows, columns=['day','lat','lon','source','conf_level','conf_raw','frp','ftype']), '', '')


def test_questions_missing_recent_and_unknown(cfg, ds):
    bbox = cfg.zone_bbox('peru')
    reply = assistant.answer_question('¿Hay focos recientes?', cfg, ds, bbox, 'Perú')
    assert 'no hay datos recientes' in reply.lower()
    assert 'no significa' in reply.lower()
    assert 'No soy una IA' in assistant.answer_question('¿Qué debería cocinar?', cfg, ds, bbox, 'Perú')
    assert 'no puedo indicar una ruta segura' in assistant.answer_question('¿Qué ruta debo tomar?', cfg, ds, bbox, 'Perú')


def test_recent_message_explains_count_date_and_uncertainty(cfg, ds, monkeypatch):
    bbox = cfg.zone_bbox('peru')
    monkeypatch.setattr(nrt, 'stats', lambda *_a, **_kw: {
        'available': True, 'total': 856, 'last_day': '2026-11-15',
        'meta': {'fetched_at': '2026-11-15T22:23:46+00:00', 'days': 3, 'bbox': list(bbox)},
    })
    answer = assistant.answer_question('¿Hay focos recientes?', cfg, ds, bbox, 'Perú')
    assert '856 detecciones de calor' in answer
    assert 'últimos 3 días solicitados' in answer
    assert '15/11/2026 a las 17:23 (hora de Perú)' in answer
    assert '15/11/2026 (fecha UTC)' in answer
    assert 'no confirma un incendio' in answer and 'no indica que siga activo' in answer
    assert 'cubra toda esta zona' not in answer


def test_recent_message_warns_of_unknown_coverage_and_does_not_use_global_date(cfg, ds, monkeypatch):
    bbox = cfg.zone_bbox('peru')
    monkeypatch.setattr(nrt, 'stats', lambda *_a, **_kw: {
        'available': True, 'empty': True, 'total': 0,
        'meta': {'fetched_at': 'sin fecha', 'last_day': '2026-11-15'},
    })
    answer = assistant.answer_question('¿Hay focos cerca?', cfg, ds, bbox, 'Perú')
    assert '0 detecciones' in answer and 'no disponible para esta zona' in answer
    assert '15/11/2026' not in answer
    assert 'puede estar desactualizada' in answer and 'no se ha comprobado' in answer.lower()
    assert 'no calcula qué tan cerca' in answer


def test_download_time_requires_timezone_and_detects_staleness():
    now = datetime(2026, 11, 16, 4, tzinfo=timezone.utc)
    assert assistant._download_time('2026-11-15T22:23:46Z', now) == ('15/11/2026 a las 17:23 (hora de Perú)', True)
    assert assistant._download_time('2026-11-15T22:23:46', now) == ('fecha desconocida', False)
    assert not assistant._download_time('2026-11-15T20:00:00Z', now)[1]
    assert not assistant._download_time('2026-11-16T05:00:00Z', now)[1]


def test_chat_endpoint(cfg, monkeypatch, ds):
    import api.main as main
    monkeypatch.setattr(main, 'cfg', cfg)
    monkeypatch.setattr(main, 'dataset', lambda: ds)
    client = TestClient(main.app)
    response = client.post('/api/assistant', json={'question': '¿Hay focos recientes?', 'zone': 'peru'})
    assert response.status_code == 200
    assert 'no hay datos recientes' in response.json()['answer'].lower()
    assert client.post('/api/assistant', json={'question': 'x' * 501}).status_code == 422
    assert client.post('/api/assistant', json={'question': ' ', 'zone': 'peru'}).status_code == 400


def test_english_assistant_endpoint(cfg, monkeypatch, ds):
    import api.main as main
    monkeypatch.setattr(main, 'cfg', cfg)
    monkeypatch.setattr(main, 'dataset', lambda: ds)
    client = TestClient(main.app)
    response = client.post('/api/assistant', json={'question': 'Are there recent hotspots?', 'zone': 'peru', 'language': 'en'})
    assert response.status_code == 200
    assert 'no recent data are loaded' in response.json()['answer'].lower()
    reply = assistant.answer_question('How do I receive alerts?', cfg, ds, cfg.zone_bbox('peru'), 'Perú', language='en')
    assert 'share your location' in reply and 'not for every fire' in reply
    assert client.post('/api/assistant', json={'question': 'hello', 'language': 'xx'}).status_code == 422


def test_bot_uses_same_answer(bot, cfg, ds):
    class FakeTelegram:
        def text(self, chat_id, text, keyboard=None): self.answer = text
    tg = FakeTelegram()
    bot.handle_message(cfg, tg, {'chat': {'id': 7}, 'from': {'id': 7}, 'text': '¿Hay focos recientes?'}, ds, 'peru')
    assert 'no hay datos recientes' in tg.answer.lower()


def test_freshness_requires_full_coverage(bot, cfg):
    now = datetime.now(timezone.utc)
    bb = cfg.zone_bbox('peru')
    meta = {'fetched_at': now.isoformat(), 'bbox': list(bb)}
    assert bot.fresh_for_zone(meta, bb, now)
    assert not bot.fresh_for_zone({**meta, 'fetched_at': (now - timedelta(hours=7)).isoformat()}, bb, now)
    assert not bot.fresh_for_zone({**meta, 'fetched_at': (now + timedelta(minutes=1)).isoformat()}, bb, now)
    assert not bot.fresh_for_zone({'fetched_at': now.isoformat()}, bb, now)
    assert not bot.fresh_for_zone({**meta, 'bbox': [bb[0]+1, bb[1], bb[2], bb[3]]}, bb, now)


def test_alert_fresh_only_and_no_duplicates(bot, cfg, ds):
    now = datetime.now(timezone.utc)
    day = (now.date() - datetime(1970, 1, 1, tzinfo=timezone.utc).date()).days
    cols = ['day','lat','lon','source','conf_level','conf_raw','frp','ftype']
    rows = pd.DataFrame([[day, -12., -69., 2, 2, -1, 100., 0],
                         [day-10, -12.01, -69., 2, 2, -1, 100., 0]], columns=cols)
    bbox = cfg.zone_bbox('peru')
    nrt.save_recent(cfg, rows, nrt.NRT_SOURCES, 3, bbox=bbox)
    groundtruth.save_geofence(cfg, 7, -12.0, -69.0, 10, chat_id=7)
    class FakeTelegram:
        def __init__(self): self.messages=[]; self.locations=[]
        def text(self, target, message, keyboard=None): self.messages.append(message)
        def location(self, target, lat, lon): self.locations.append((lat, lon))
    tg = FakeTelegram()
    diagnostic = bot.diagnose_live(cfg, ds, 'peru')
    assert diagnostic['fresh_and_covered'] and diagnostic['matches'] == 1 and diagnostic['new'] == 1
    assert not groundtruth.load_sent(cfg)  # diagnosis must not record or send anything
    assert bot.check_alerts(cfg, tg, 'peru', ds) == 1
    assert len(tg.messages) == 1 and len(tg.locations) == 1
    assert 'ni un aviso oficial' in tg.messages[0]
    assert bot.check_alerts(cfg, tg, 'peru', ds) == 0
    assert bot.diagnose_live(cfg, ds, 'peru')['new'] == 0


def test_refresh_failure_does_not_overwrite(bot, cfg, monkeypatch):
    cols = ['day','lat','lon','source','conf_level','conf_raw','frp','ftype']
    old = pd.DataFrame([[20000,-12.,-69.,2,2,-1,50.,0]], columns=cols)
    nrt.save_recent(cfg, old, nrt.NRT_SOURCES, 3, bbox=cfg.zone_bbox('peru'))
    def fail(*args, **kwargs):
        assert kwargs['strict'] is True
        raise RuntimeError('FIRMS no disponible')
    monkeypatch.setattr(nrt, 'fetch_recent', fail)
    with pytest.raises(RuntimeError): bot.refresh_recent(cfg, 'peru')
    assert len(nrt.load_recent(cfg)[0]) == 1


def test_strict_download_rejects_http_failure_and_invalid_csv(cfg, monkeypatch):
    monkeypatch.setenv('FIRMS_MAP_KEY', 'secret-value')
    class Response:
        status_code = 500
        text = 'secret-value'
    monkeypatch.setattr(nrt.requests, 'get', lambda *a, **kw: Response())
    with pytest.raises(RuntimeError) as error:
        nrt.fetch_recent(cfg, cfg.zone_bbox('peru'), sources=('MODIS_NRT',), strict=True)
    assert 'secret-value' not in str(error.value)
    Response.status_code = 200
    Response.text = 'error'
    with pytest.raises(RuntimeError, match='cabecera CSV'):
        nrt.fetch_recent(cfg, cfg.zone_bbox('peru'), sources=('MODIS_NRT',), strict=True)


def test_poll_refresh_failure_never_sends(bot, cfg, ds, monkeypatch):
    class Telegram:
        def call(self, method, **kwargs): return []
    def fail(*args): raise RuntimeError('fuente no disponible')
    monkeypatch.setattr(bot, 'refresh_recent', fail)
    monkeypatch.setattr(bot, 'check_alerts', lambda *args: pytest.fail('no debe enviar en un ciclo fallido'))
    assert bot.poll(cfg, Telegram(), ds, 'peru', 900, True, auto_refresh=True) == 0


def test_telegram_connection_error_does_not_expose_token(bot, monkeypatch):
    def fail(*args, **kwargs): raise bot.requests.ConnectionError('https://api.telegram.org/botSECRET/sendMessage')
    monkeypatch.setattr(bot.requests, 'post', fail)
    with pytest.raises(RuntimeError) as error:
        bot.Telegram('SECRET').call('sendMessage')
    assert 'SECRET' not in str(error.value)


def test_live_alert_filters_and_send_failure_retry(bot, cfg, ds):
    now = datetime.now(timezone.utc)
    day = (now.date() - datetime(1970, 1, 1, tzinfo=timezone.utc).date()).days
    cols = ['day','lat','lon','source','conf_level','conf_raw','frp','ftype']
    rows = pd.DataFrame([
        [day, -12., -69., 2, 2, -1, 100., 0],     # eligible
        [day, -12.01, -69., 2, 2, -1, 1., 0],      # below threshold
        [day, -13., -69., 2, 2, -1, 100., 0],      # outside radius
        [day-3, -12.02, -69., 2, 2, -1, 100., 0],  # too old
        [day+1, -12.03, -69., 2, 2, -1, 100., 0],  # future
    ], columns=cols)
    bbox = cfg.zone_bbox('peru')
    groundtruth.save_geofence(cfg, 7, -12., -69., 10, chat_id=7)
    groundtruth.set_language(cfg, 7, 'en')
    nrt.save_recent(cfg, rows, nrt.NRT_SOURCES, 3, bbox=bbox)
    class Telegram:
        def __init__(self): self.fail = True; self.messages = []
        def text(self, target, message, keyboard=None):
            if self.fail: raise RuntimeError('send failed')
            self.messages.append((message, keyboard))
        def location(self, *args): pass
    tg = Telegram()
    assert bot.diagnose_live(cfg, ds, 'peru')['new'] == 1
    with pytest.raises(RuntimeError): bot.check_alerts(cfg, tg, 'peru', ds)
    assert not groundtruth.load_sent(cfg)
    tg.fail = False
    assert bot.check_alerts(cfg, tg, 'peru', ds) == 1
    assert 'not a confirmed fire' in tg.messages[0][0].lower()
    assert tg.messages[0][1]['inline_keyboard'][0][0]['text'] == '🔥 Real fire'
    assert bot.check_alerts(cfg, tg, 'peru', ds) == 0
    nrt.save_recent(cfg, rows, nrt.NRT_SOURCES, 3, bbox=[bbox[0]+1, bbox[1], bbox[2], bbox[3]])
    assert bot.check_alerts(cfg, tg, 'peru', ds) == 0
    assert not bot.diagnose_live(cfg, ds, 'peru')['fresh_and_covered']


def test_heartbeat_success_failure_private_only(bot, cfg, ds, monkeypatch):
    groundtruth.save_geofence(cfg, 7, -12., -69., 10, chat_id=7)
    groundtruth.save_geofence(cfg, 8, -12., -69., 10, chat_id=-100)
    groundtruth.save_geofence(cfg, 9, -12., -69., 10, chat_id=9)
    groundtruth.set_language(cfg, 9, 'en')
    class FakeTelegram:
        def __init__(self): self.messages = []
        def call(self, method, **kwargs): return []
        def text(self, target, text, keyboard=None): self.messages.append((target, text))
    tg = FakeTelegram()
    stamp = datetime.now(timezone.utc).isoformat()
    info = {'rows': 5, 'fetched_at': stamp, 'bbox': list(cfg.zone_bbox('peru'))}
    monkeypatch.setattr(bot, 'refresh_recent', lambda *a: info)
    monkeypatch.setattr(nrt, 'load_recent', lambda *a: (pd.DataFrame(), info))
    monkeypatch.setattr(bot, 'check_alerts', lambda *a: 0)
    assert bot.poll(cfg, tg, ds, 'peru', 900, True, auto_refresh=True, heartbeat=True) == 0
    assert {target for target, _ in tg.messages} == {'7', '9'}
    assert 'Revisión de vigilancia completada' in tg.messages[0][1]
    assert 'no significa que no haya incendios' in tg.messages[0][1]
    assert stamp in tg.messages[0][1]
    assert 'Monitoring cycle completed' in tg.messages[1][1]
    tg.messages.clear()
    def fail(*a): raise RuntimeError('connection failed')
    monkeypatch.setattr(bot, 'refresh_recent', fail)
    assert bot.poll(cfg, tg, ds, 'peru', 900, True, auto_refresh=True, heartbeat=True) == 0
    assert len(tg.messages) == 2 and 'No se pudo completar' in tg.messages[0][1]
    assert not any('completada' in text.lower() for _, text in tg.messages)
    with pytest.raises(ValueError): bot.poll(cfg, tg, ds, 'peru', 900, True, heartbeat=True)


def test_heartbeat_never_reports_success_for_bad_coverage_or_alert_failure(bot, cfg, ds, monkeypatch):
    groundtruth.save_geofence(cfg, 7, -12., -69., 10, chat_id=7)
    class Telegram:
        def __init__(self): self.messages = []
        def call(self, *args, **kwargs): return []
        def text(self, target, text, keyboard=None): self.messages.append(text)
    tg = Telegram()
    info = {'rows': 1, 'fetched_at': datetime.now(timezone.utc).isoformat(), 'bbox': [0, 0, 1, 1]}
    monkeypatch.setattr(bot, 'refresh_recent', lambda *a: info)
    monkeypatch.setattr(nrt, 'load_recent', lambda *a: (pd.DataFrame(), info))
    monkeypatch.setattr(bot, 'check_alerts', lambda *a: pytest.fail('bad coverage must not be checked'))
    bot.poll(cfg, tg, ds, 'peru', 900, True, auto_refresh=True, heartbeat=True)
    assert len(tg.messages) == 1 and 'No se pudo completar' in tg.messages[0]
    info['bbox'] = list(cfg.zone_bbox('peru'))
    def fail(*a): raise RuntimeError('Telegram error')
    monkeypatch.setattr(bot, 'check_alerts', fail)
    tg.messages.clear()
    bot.poll(cfg, tg, ds, 'peru', 900, True, auto_refresh=True, heartbeat=True)
    assert len(tg.messages) == 1 and 'No se pudo completar' in tg.messages[0]


def test_heartbeat_off_by_default(bot, cfg, ds, monkeypatch):
    groundtruth.save_geofence(cfg, 7, -12., -69., 10, chat_id=7)
    class Telegram:
        def call(self, *args, **kwargs): return []
        def text(self, *args, **kwargs): pytest.fail('default must not send heartbeat')
    monkeypatch.setattr(bot, 'check_alerts', lambda *a: 0)
    assert bot.poll(cfg, Telegram(), ds, 'peru', 900, True) == 0
