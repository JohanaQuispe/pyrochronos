from types import SimpleNamespace

from pyro import notify


def test_bulletin_warns_of_provisional_harmonization(monkeypatch):
    cfg = SimpleNamespace(default_zone='peru', default_measure='cell_days',
                          zone_bbox=lambda _: [0, 0, 1, 1], zone_name=lambda _: 'Perú')
    ds = SimpleNamespace(start='2000-01-01', end='2026-01-01')
    payload = {
        'meta': {'zone': 'Perú', 'coverage': {'end': '2026-01-01'}},
        'cards': {'total_detections': 10, 'most_active_year': {'period_year': 2026}},
        'calendar': {'years': [], 'levels': [], 'values': []},
    }
    monkeypatch.setattr(notify, 'build_calendar', lambda *args, **kwargs: payload)
    message = notify.build_bulletin(cfg, ds)
    assert 'histórico, no tiempo real' in message
    assert 'Cifras armonizadas provisionales' in message
    assert 'No usar el ranking anual como definitivo' in message
