"""Pruebas de los endpoints de la capa de campo y del alias historical-grid."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from api.main import app

    return TestClient(app)


@pytest.fixture()
def field_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PYRO_FIELD_DIR", str(tmp_path))
    return tmp_path


def test_historical_grid_matches_calendar(client):
    grid = client.get("/api/historical-grid", params={"zone": "madrededios", "granularity": "week"})
    assert grid.status_code == 200
    body = grid.json()
    cal = client.get("/api/calendar", params={"zone": "madrededios", "granularity": "week"}).json()
    assert body["meta"]["zone"] == cal["meta"]["zone"]
    assert body["calendar"]["values"] == cal["calendar"]["values"]
    assert body["meta"]["granularity"] == "week"


def test_register_geofence_and_list(client, field_dir):
    r = client.post("/api/register-geofence", json={"telegram_id": 42, "lat": -12.59, "lon": -69.18})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["geofence"]["radius_km"] == 10.0
    assert isinstance(body["nearby_critical_hotspots"], list)
    listed = client.get("/api/geofences").json()
    assert listed["count"] == 1
    assert listed["items"][0]["telegram_id"] == "42"


def test_register_geofence_validates_coordinates(client, field_dir):
    assert client.post("/api/register-geofence", json={"telegram_id": 1, "lat": 999, "lon": 0}).status_code == 422
    assert client.post("/api/register-geofence", json={"telegram_id": 1, "lat": 0, "lon": 0,
                                                      "radius_km": 500}).status_code == 422


def test_register_geofence_requires_setup_key_when_configured(client, field_dir, monkeypatch):
    monkeypatch.setenv("PYRO_SETUP_KEY", "secreto")
    r = client.post("/api/register-geofence", json={"telegram_id": 7, "lat": -12.0, "lon": -69.0})
    assert r.status_code == 401
    ok = client.post("/api/register-geofence", json={"telegram_id": 7, "lat": -12.0, "lon": -69.0},
                     headers={"X-Setup-Key": "secreto"})
    assert ok.status_code == 200


def test_groundtruth_roundtrip(client, field_dir):
    r = client.post("/api/groundtruth", json={"hotspot_id": "nrt-1", "verdict": "quema_agricola"})
    assert r.status_code == 200
    assert r.json()["summary"]["counts"]["quema_agricola"] == 1
    got = client.get("/api/groundtruth").json()
    assert got["summary"]["total"] == 1
    assert got["items"][0]["label"].startswith("🌾")
    bad = client.post("/api/groundtruth", json={"hotspot_id": "x", "verdict": "inventado"})
    assert bad.status_code == 422
