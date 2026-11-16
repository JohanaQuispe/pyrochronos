"""Pruebas del bot en lenguaje llano: botones, comandos tolerantes y grupos."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest

from pyro import groundtruth
from pyro.config import Config, load_config

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bot.py"


@pytest.fixture(scope="module")
def bot():
    spec = importlib.util.spec_from_file_location("pyro_bot", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("PYRO_FIELD_DIR", str(tmp_path))
    base = load_config()
    raw = copy.deepcopy(base.raw)
    raw["api"]["data_file"] = str(tmp_path / "detections.parquet")
    return Config(raw)


def test_keyboard_has_three_plain_actions(bot):
    rows = bot.main_keyboard()["keyboard"]
    flat = [button["text"] for row in rows for button in row]
    assert any("ubicación" in t for t in flat)
    assert any("Distancia" in t for t in flat)
    assert any("Ayuda" in t for t in flat)
    assert rows[0][0]["request_location"] is True
    # nada de jerga delante del brigadista
    assert not any("geocerca" in t.lower() or "radio" in t.lower() for t in flat)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("/radio 15", 15.0),
        ("/radio@pyrochronos_JQ_bot 15", 15.0),
        ("/distancia 20", 20.0),
        ("15 km", 15.0),
        ("15km", 15.0),
        ("distancia 7,5", 7.5),
        ("distancia", None),
        ("/estado", None),
        ("/radio 500", None),
        ("/radio 0", None),
    ],
)
def test_parse_radius_is_tolerant(bot, text, expected):
    assert bot.parse_radius(text) == expected


def test_normalize_command_strips_bot_name(bot):
    assert bot.normalize_command("/estado@mi_bot") == "/estado"
    assert bot.normalize_command("  /start  ") == "/start"
    assert bot.normalize_command("/radio\u200b 15") == "/radio 15"


def test_radius_preference_without_location(cfg):
    rec = groundtruth.set_radius(cfg, 42, 20)
    assert rec["radius_km"] == 20
    assert rec["lat"] is None
    assert groundtruth.active_geofences(cfg) == []  # sin posición no se avisa a nadie
    saved = groundtruth.save_geofence(cfg, 42, -12.5, -69.2, 20, chat_id=-100)
    assert saved["lat"] == -12.5
    assert saved["chat_id"] == "-100"
    assert groundtruth.active_geofences(cfg)[0]["radius_km"] == 20


def test_group_keeps_person_and_chat_separate(cfg):
    groundtruth.save_geofence(cfg, 7, -12.0, -69.0, 10, chat_id=-100123)
    groundtruth.save_geofence(cfg, 8, -13.0, -70.0, 10, chat_id=-100123)
    fences = groundtruth.active_geofences(cfg)
    assert {f["telegram_id"] for f in fences} == {"7", "8"}
    assert {f["chat_id"] for f in fences} == {"-100123"}


def test_language_preference_persists_through_location_and_english_controls(bot, cfg):
    class FakeTelegram:
        def __init__(self): self.messages = []; self.callbacks = []
        def text(self, chat_id, text, keyboard=None): self.messages.append((text, keyboard))
        def call(self, method, **kwargs): self.callbacks.append((method, kwargs))
    tg = FakeTelegram()
    base = {'chat': {'id': 7, 'type': 'private'}, 'from': {'id': 7, 'first_name': 'Test'}}
    bot.handle_message(cfg, tg, {**base, 'text': '/language en'}, None, 'peru')
    assert groundtruth.load_geofences(cfg)['7']['language'] == 'en'
    assert 'English' in tg.messages[-1][0]
    bot.handle_message(cfg, tg, {**base, 'location': {'latitude': -12, 'longitude': -69}}, None, 'peru')
    assert groundtruth.load_geofences(cfg)['7']['language'] == 'en'
    assert 'heat detections' in tg.messages[-1][0]
    bot.handle_message(cfg, tg, {**base, 'text': '/distance 20'}, None, 'peru')
    assert groundtruth.load_geofences(cfg)['7']['radius_km'] == 20
    assert 'Saved' in tg.messages[-1][0]
    bot.handle_callback(cfg, tg, {'id': 'cb', 'from': {'id': 7}, 'data': 'r:5', 'message': {'chat': {'id': 7}}})
    assert groundtruth.load_geofences(cfg)['7']['radius_km'] == 5
    assert 'Saved' in tg.messages[-1][0]
    bot.handle_message(cfg, tg, {**base, 'text': '/idioma es'}, None, 'peru')
    assert groundtruth.load_geofences(cfg)['7']['language'] == 'es'
    assert groundtruth.load_geofences(cfg)['7']['lat'] == -12
