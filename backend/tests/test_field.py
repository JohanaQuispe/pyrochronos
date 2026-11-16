"""Pruebas de la capa de campo: geocercas, aviso, botones y validación humana."""
from __future__ import annotations

import copy

import pandas as pd
import pytest

from pyro import geofence, groundtruth
from pyro.config import Config, load_config


@pytest.fixture()
def cfg(tmp_path):
    base = load_config()
    raw = copy.deepcopy(base.raw)
    raw["api"]["data_file"] = str(tmp_path / "detections.parquet")
    return Config(raw)


def frame(rows):
    return pd.DataFrame(
        rows,
        columns=["day", "lat", "lon", "source", "conf_level", "conf_raw", "frp", "ftype"],
    )


def test_haversine_known_distance():
    # 1 grado de latitud ~ 111,2 km
    assert geofence.haversine_km(0.0, 0.0, 1.0, 0.0) == pytest.approx(111.19, abs=0.05)
    assert geofence.haversine_km(-12.0, -69.0, -12.0, -69.0) == pytest.approx(0.0, abs=1e-9)
    # 10 km al este en el ecuador ~ 0,0899 grados de longitud
    assert geofence.haversine_km(0.0, 0.0, 0.0, 0.0899) == pytest.approx(10.0, abs=0.1)


def test_bearing_and_compass():
    assert geofence.bearing_deg(0.0, 0.0, 1.0, 0.0) == pytest.approx(0.0, abs=0.5)
    assert geofence.bearing_deg(0.0, 0.0, 0.0, 1.0) == pytest.approx(90.0, abs=0.5)
    assert geofence.compass(0) == "N"
    assert geofence.compass(63) == "NE"
    assert geofence.compass(180) == "S"
    assert geofence.compass(359) == "N"


def test_mark_critical_uses_zone_history():
    history = frame([[100, -12.0, -69.0, 2, 2, 90, 10.0, 0]] * 100)
    recent = frame([[200, -12.0, -69.0, 2, 2, 95, 900.0, 0], [200, -12.1, -69.1, 2, 1, 60, 1.0, 0]])
    marked = geofence.mark_critical(recent, history=history)
    assert marked["critical"].tolist() == [True, False]
    assert marked.loc[0, "frp_p95"] == pytest.approx(10.0)


def test_mark_critical_respects_min_frp():
    history = frame([[100, -12.0, -69.0, 2, 2, 90, 1.0, 0]] * 100)
    recent = frame([[200, -12.0, -69.0, 2, 2, 95, 2.0, 0]])
    marked = geofence.mark_critical(recent, history=history, min_frp=20.0)
    assert not bool(marked.loc[0, "critical"])


def test_nearest_filters_radius_and_sorts():
    df = frame([
        [200, -12.00, -69.00, 2, 2, 95, 100.0, 0],  # 0 km
        [200, -12.05, -69.00, 2, 2, 95, 100.0, 0],  # ~5,5 km
        [200, -12.50, -69.00, 2, 2, 95, 100.0, 0],  # ~55 km
    ])
    df["critical"] = True
    df["hotspot_id"] = ["a", "b", "c"]
    near = geofence.nearest(df, -12.00, -69.00, radius_km=10)
    assert near["hotspot_id"].tolist() == ["a", "b"]
    assert near["distance_km"].is_monotonic_increasing
    assert near.loc[0, "cardinal"] == "N"


def test_nearest_ignores_non_critical_when_asked():
    df = frame([[200, -12.0, -69.0, 2, 2, 95, 100.0, 0]])
    df["critical"] = False
    df["hotspot_id"] = ["x"]
    assert geofence.nearest(df, -12.0, -69.0, 10).empty


def test_alert_text_has_distance_disclaimer_and_pin_data():
    row = {
        "distance_km": 6.4, "cardinal": "NE", "frp": 52.0, "frp_p95": 43.0,
        "day_label": "2025-11-22", "time_utc": "14:20", "sensor": "VIIRS", "conf_label": "nominal",
        "lat": -12.5, "lon": -69.2,
    }
    text = geofence.alert_text(row, 10.0, zone="Madre de Dios")
    assert "6.4 km al NE" in text
    assert "52 MW" in text and "43 MW" in text
    assert "ni un aviso oficial" in text
    assert "distancia en línea recta" in text
    assert "no es un incendio confirmado" in text.lower()
    assert "Madre de Dios" in text


def test_keyboard_and_callback_roundtrip():
    kb = geofence.inline_keyboard("nrt-200--12.0-69.0-2")
    data = kb["inline_keyboard"][0][0]["callback_data"]
    assert len(data.encode()) <= 64
    assert [row[0]["text"] for row in kb["inline_keyboard"]] == list(geofence.VERDICTS.values())
    assert geofence.parse_callback(data) == ("nrt-200--12.0-69.0-2", "fuego_real")
    assert geofence.parse_callback("gt:1:inventado") is None
    assert geofence.parse_callback("basura") is None


def test_geofence_store_roundtrip(cfg):
    assert groundtruth.active_geofences(cfg) == []
    rec = groundtruth.save_geofence(cfg, 42, -12.59, -69.18, 15)
    assert rec["radius_km"] == 15.0
    groundtruth.save_geofence(cfg, 42, -12.60, -69.19, 15)  # actualiza, no duplica
    fences = groundtruth.active_geofences(cfg)
    assert len(fences) == 1
    assert fences[0]["lat"] == pytest.approx(-12.60)


def test_verdict_store_and_summary(cfg):
    groundtruth.save_verdict(cfg, "h1", 42, "fuego_real")
    groundtruth.save_verdict(cfg, "h1", 42, "quema_agricola")
    groundtruth.save_verdict(cfg, "h2", 7, "falsa_alarma")
    summary = groundtruth.verdict_summary(cfg)
    assert summary["counts"] == {"fuego_real": 0, "quema_agricola": 1, "falsa_alarma": 1}
    assert summary["total"] == 2
    assert len(groundtruth.load_verdicts(cfg)[0]["history"]) == 2
    with pytest.raises(ValueError):
        groundtruth.save_verdict(cfg, "h3", 1, "no_existe")


def test_sent_dedupe(cfg):
    assert not groundtruth.already_sent(cfg, 42, "h1")
    groundtruth.mark_sent(cfg, 42, "h1")
    assert groundtruth.already_sent(cfg, 42, "h1")
    assert not groundtruth.already_sent(cfg, 7, "h1")


def test_alert_text_for_actual_normalized_nrt_row():
    row = {'day': 20000, 'source': 2, 'conf_level': 2, 'lat': -12.5, 'lon': -69.2,
           'distance_km': 6.4, 'cardinal': 'NE', 'frp': 52, 'frp_p95': 43}
    text = geofence.alert_text(row, zone='Madre de Dios')
    assert '2024-10-04' in text and 'VIIRS' in text and 'confianza alta' in text
    assert '`-12.5000, -69.2000`' in text
    assert 'https://www.google.com/maps/search/?api=1&query=-12.5000,-69.2000' in text
    assert 'Hora de detección no disponible' in text
    assert 'no mide cercanía a viviendas' in text


def test_english_alert_has_limits_and_english_actions():
    row = {'day': 20000, 'source': 2, 'conf_level': 2, 'lat': -12.5, 'lon': -69.2,
           'distance_km': 6.4, 'cardinal': 'SO', 'frp': 52, 'frp_p95': 43}
    text = geofence.alert_text(row, zone='Perú', language='en')
    assert '6.4 km SW' in text
    assert '2024-10-04' in text and 'UTC' in text and 'confidence high' in text
    assert 'not a confirmed fire' in text.lower() and 'official warning' in text
    keyboard = geofence.inline_keyboard('abc', language='en')
    assert keyboard['inline_keyboard'][0][0]['text'] == '🔥 Real fire'
    assert geofence.parse_callback(keyboard['inline_keyboard'][0][0]['callback_data']) == ('abc', 'fuego_real')
