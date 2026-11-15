"""Pruebas del contexto NASA POWER: matemática del déficit, sin red."""
from __future__ import annotations

import copy
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from pyro import power
from pyro.config import Config, load_config


@pytest.fixture()
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("PYRO_POWER_DIR", str(tmp_path))
    base = load_config()
    raw = copy.deepcopy(base.raw)
    raw["api"]["data_file"] = str(tmp_path / "detections.parquet")
    return Config(raw)


def synthetic_frame(years=4, rainy_recent=False, tmax_recent=32.0):
    """Serie diaria sintética: misma lluvia cada año salvo el último tramo."""
    end = date(2026, 11, 14)
    start = date(end.year - years, 1, 1)
    idx = pd.date_range(start, end, freq="D")
    df = pd.DataFrame(index=idx)
    df["PRECTOTCORR"] = 5.0
    df["T2M_MAX"] = 30.0
    df["RH2M"] = 70.0
    if rainy_recent:
        df.loc[date(2026, 10, 16):, "PRECTOTCORR"] = 2.0
        df.loc[date(2026, 10, 16):, "T2M_MAX"] = tmax_recent
    return df


def test_zone_point_is_bbox_center(cfg):
    lat, lon = power.zone_point(cfg, "madrededios")
    assert lat == pytest.approx(-12.2) and lon == pytest.approx(-69.6)


def test_missing_cache_is_honest(cfg):
    ctx = power.climate_context(cfg, "madrededios")
    assert ctx["available"] is False
    assert "download_power.py" in ctx["how_to"]


def test_cache_roundtrip(cfg):
    frame = synthetic_frame()
    path = power.save_cache(cfg, "madrededios", frame, -12.2, -69.6)
    assert path.exists()
    loaded, meta = power.load_cache(cfg, "madrededios")
    assert len(loaded) == len(frame)
    assert meta["source"].startswith("NASA POWER")


def test_dry_window_is_flagged(cfg):
    frame = synthetic_frame(rainy_recent=True)
    power.save_cache(cfg, "madrededios", frame, -12.2, -69.6)
    ctx = power.climate_context(cfg, "madrededios", ref_date=date(2026, 11, 14))
    assert ctx["available"] is True
    assert ctx["window"]["rain_mm"] == pytest.approx(2.0 * 30, abs=0.5)
    assert ctx["rain_deficit_pct"] == pytest.approx(-60.0, abs=1.0)
    assert ctx["tmax_anomaly_c"] == pytest.approx(2.0, abs=0.05)
    assert ctx["level"] == "seco"
    assert ctx["label"] == "más seco de lo normal"


def test_normal_window_is_normal(cfg):
    frame = synthetic_frame(rainy_recent=False)
    power.save_cache(cfg, "madrededios", frame, -12.2, -69.6)
    ctx = power.climate_context(cfg, "madrededios", ref_date=date(2026, 11, 14))
    assert ctx["rain_deficit_pct"] == pytest.approx(0.0, abs=0.5)
    assert ctx["tmax_anomaly_c"] == pytest.approx(0.0, abs=0.05)
    assert ctx["level"] == "normal"


def test_endpoint_without_cache(cfg, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from api.main import app

    monkeypatch.setenv("PYRO_POWER_DIR", str(tmp_path))  # sin caché en esta carpeta
    client = TestClient(app)
    r = client.get("/api/climate-context", params={"zone": "madrededios"})
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is False
    assert "download_power.py" in body["how_to"]
    assert client.get("/api/climate-context", params={"zone": "narnia"}).status_code == 404


def test_endpoint_with_cache(cfg, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from api.main import app

    monkeypatch.setenv("PYRO_POWER_DIR", str(tmp_path))
    power.save_cache(cfg, "madrededios", synthetic_frame(rainy_recent=True), -12.2, -69.6)
    client = TestClient(app)
    body = client.get("/api/climate-context", params={"zone": "madrededios"}).json()
    assert body["available"] is True
    assert body["level"] in ("seco", "normal", "humedo")
    assert body["source"] == "NASA POWER"
