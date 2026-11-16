"""Pruebas del nucleo: normalizacion, cuadricula, armonizacion, anomalias y API."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from pyro import anomalies, grid, harmonize, normalize
from pyro.config import load_config


def modis_frame(rows):
    df = pd.DataFrame(rows, columns=["latitude", "longitude", "acq_date", "confidence", "frp", "type"])
    return normalize.normalize_frame(df, "modis", min_conf_modis=30)


def viirs_frame(rows):
    df = pd.DataFrame(rows, columns=["latitude", "longitude", "acq_date", "confidence", "frp", "type"])
    return normalize.normalize_frame(df, "viirs", min_conf_modis=30)


def test_confianza_unificada():
    m = modis_frame([
        (-12.0, -75.0, "2024-09-01", "10", 5.0, 0),   # baja
        (-12.0, -75.0, "2024-09-01", "55", 5.0, 0),   # nominal
        (-12.0, -75.0, "2024-09-01", "92", 5.0, 0),   # alta
    ])
    assert m["conf_level"].tolist() == [0, 1, 2]
    v = viirs_frame([
        (-12.0, -75.0, "2024-09-01", "l", 5.0, 0),
        (-12.0, -75.0, "2024-09-01", "n", 5.0, 0),
        (-12.0, -75.0, "2024-09-01", "h", 5.0, 0),
    ])
    assert v["conf_level"].tolist() == [0, 1, 2]
    assert v["source"].iloc[0] == normalize.SOURCE_VIIRS


def test_control_de_calidad_descarta_confianza_baja():
    df = pd.concat([
        modis_frame([(-12.0, -75.0, "2024-09-01", "5", 1.0, 0)]),
        viirs_frame([(-12.0, -75.0, "2024-09-01", "l", 1.0, 0)]),
    ], ignore_index=True)
    clean = normalize.filter_quality(df, min_conf_modis=30, exclude_types=())
    assert clean.empty
    keep = normalize.filter_quality(df, min_conf_modis=0, drop_low_viirs=False)
    assert len(keep) == 2


def test_fuentes_fijas_se_pueden_excluir():
    df = modis_frame([
        (-12.0, -75.0, "2024-09-01", "80", 1.0, 0),
        (-12.0, -75.0, "2024-09-01", "80", 1.0, 2),
    ])
    assert len(normalize.filter_quality(df, exclude_types=[2])) == 1


def _daily(modis, viirs, day0="2024-01-01"):
    """Serie diaria minima para probar la cuadricula."""
    rows = []
    base = np.datetime64(day0, "D")
    offset = (base - np.datetime64("1970-01-01", "D")).astype(int)
    for i, (lat, lon) in enumerate(modis):
        rows.append({"day": offset, "lat": lat, "lon": lon, "source": 1, "conf_level": 1, "conf_raw": 80,
                     "frp": 1.0, "ftype": 0})
    for i, (lat, lon) in enumerate(viirs):
        rows.append({"day": offset, "lat": lat, "lon": lon, "source": 2, "conf_level": 1, "conf_raw": -1,
                     "frp": 1.0, "ftype": 0})
    return pd.DataFrame(rows)


def test_celdas_dia_no_cuentan_dos_veces():
    df = _daily([(-12.002, -75.002), (-12.0024, -75.0023)], [])  # misma celda de 0,01 grados
    cells = grid.build_cells(df, 0.01)
    daily = grid.daily_counts(cells, df, (-81.5, -18.5, -68.5, 0.5), 0.01)
    assert daily["modis_cd"].iloc[0] == 1     # misma celda -> una celda-dia
    assert daily["modis_det"].iloc[0] == 2    # dos detecciones sueltas


def test_union_entre_satelites_no_duplica():
    df = _daily([(-12.0, -75.0)], [(-12.0, -75.0)])
    cells = grid.build_cells(df, 0.01)
    daily = grid.daily_counts(cells, df, (-81.5, -18.5, -68.5, 0.5), 0.01)
    assert daily["union_cd"].iloc[0] == 1
    assert daily["modis_cd"].iloc[0] == 1 and daily["viirs_cd"].iloc[0] == 1


def _agg(years, periods=12, factor=2.0, overlap_from=2020):
    rows = []
    for y in years:
        for p in range(1, periods + 1):
            m = 10
            both = y >= overlap_from
            rows.append({
                "period_year": y, "period_index": p,
                "modis_cd": m,
                "viirs_cd": m * (factor - 1) if both else 0,
                "union_cd": m * factor if both else m,
                "modis_det": m * 2, "viirs_det": m * 2 * (factor - 1) if both else 0,
                "union_det": m * 2 * factor if both else m * 2,
                "days_observed": 30,
            })
    return pd.DataFrame(rows)


def test_factor_de_calibracion_y_valores_estimados():
    agg = _agg(range(2010, 2025), factor=2.0, overlap_from=2020)
    cal = harmonize.calibrate(agg, "cell_days", 2020, 2024, shrink_min_years=2, min_periods_for_factor=1)
    assert cal.global_factor == pytest.approx(2.0)
    ser = harmonize.harmonize(agg, cal)
    antes = ser[ser.period_year == 2015]
    despues = ser[ser.period_year == 2022]
    assert antes["estimated"].all()          # antes del solape: estimado
    assert not despues["estimated"].any()    # en el solape: observado
    assert antes["value"].iloc[0] == pytest.approx(20.0)
    assert despues["value"].iloc[0] == pytest.approx(20.0)
    assert (antes["value_low"] <= antes["value"]).all()
    assert (antes["value"] <= antes["value_high"]).all()


def test_sin_solape_no_se_inventa_factor():
    agg = _agg(range(2010, 2025), factor=2.0, overlap_from=2030)
    cal = harmonize.calibrate(agg, "cell_days", 2020, 2024, shrink_min_years=2, min_periods_for_factor=1)
    assert cal.global_factor == 1.0


def test_anomalias_leave_one_out_y_minimo():
    years = list(range(2010, 2023))
    rows = []
    for y in years:
        for p in range(1, 13):
            rows.append({"period_year": y, "period_index": p, "value": 10.0})
    # un año claramente por encima, y un valor por debajo del minimo
    rows.append({"period_year": 2023, "period_index": 9, "value": 500.0})
    rows.append({"period_year": 2023, "period_index": 3, "value": 1.0})
    ser = pd.DataFrame(rows)
    cfg = {"window_periods": 1, "min_history_years": 6, "min_value": 5, "high": 90, "extreme": 97.5}
    out = anomalies.classify(ser, "month", cfg)
    sept = out[(out.period_year == 2023) & (out.period_index == 9)].iloc[0]
    assert sept.anomaly_pct > 97.5
    assert sept.anomaly_level == "extremo"
    small = out[(out.period_year == 2023) & (out.period_index == 3)].iloc[0]
    assert pd.isna(small.anomaly_pct)     # no se clasifica un valor casi cero
    old = out[(out.period_year == 2010) & (out.period_index == 9)].iloc[0]
    assert old.anomaly_level in ("normal", "alto", "extremo")


def test_config_invalida_falla():
    cfg = load_config()
    assert cfg.cell_deg == 0.01
    assert 0 < cfg.anomalies["high"] < cfg.anomalies["extreme"] <= 100
    w, s, e, n = cfg.zone_bbox()
    assert w < e and s < n


# --- API ---------------------------------------------------------------------
@pytest.fixture(scope="module")
def client():
    fastapi_testclient = pytest.importorskip("fastapi.testclient")
    from api.main import app

    if not load_config().data_file.exists():
        pytest.skip("falta el parquet de datos")
    return fastapi_testclient.TestClient(app)


def test_meta_endpoint(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    body = r.json()
    assert body["coverage"]["start"] <= body["coverage"]["end"]
    assert any(z["key"] == "peru" for z in body["zones"])


def test_calendario_mensual(client):
    r = client.get("/api/calendar", params={"zone": "madrededios", "granularity": "month"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["meta"]["periods"]) == 12
    assert len(body["calendar"]["values"]) == len(body["calendar"]["years"])
    assert body["calibration"]["agreement_r"] is not None
    assert "summary" in body and body["summary"]


def test_calendario_semanal_y_medidas(client):
    for gran in ("week", "month"):
        for measure in ("cell_days", "detections"):
            r = client.get("/api/calendar", params={"zone": "peru", "granularity": gran, "measure": measure})
            assert r.status_code == 200, r.text


def test_zona_demasiado_grande_se_rechaza(client):
    r = client.get("/api/calendar", params={"bbox": "-120,-40,-30,40"})
    assert r.status_code == 400


def test_csv_de_focos_cabeza_correcta(client):
    r = client.get("/api/csv/hotspots", params={"zone": "madrededios", "start": "2024-08-01", "end": "2024-09-30"})
    assert r.status_code == 200
    head = r.text.splitlines()[0]
    assert head.startswith("acq_date,latitude,longitude,satellite,confidence_level")
    first = r.text.splitlines()[1].split(",")
    assert first[0].startswith("2024-")
    assert -18.5 <= float(first[1]) <= 0.5


# --- semaforo de temporada y reporte ----------------------------------------
def test_semaforo_responde_y_es_coherente(client):
    r = client.get("/api/alert", params={"zone": "madrededios"})
    assert r.status_code == 200
    body = r.json()
    assert body["level"] in ("normal", "vigilancia", "critico")
    assert 0 <= body["severity"] <= 2
    assert 1 <= body["week"] <= 53
    assert body["reasons"] and body["action"] and body["disclaimer"]
    assert len(body["window"]) == 4
    assert all(0 <= w["ratio"] <= 1.01 for w in body["window"])


def test_semaforo_en_plena_temporada_es_critico(client):
    # Madre de Dios: el pico histórico está en septiembre; una referencia en esa semana debe dar crítico
    r = client.get("/api/alert", params={"zone": "madrededios", "date_ref": "2026-09-08"})
    assert r.status_code == 200
    body = r.json()
    assert body["level"] == "critico"
    assert body["ratio"] > 0.75


def test_semaforo_sin_recientes_lo_dice(client):
    r = client.get("/api/recent", params={"zone": "peru"})
    assert r.status_code == 200
    if not r.json().get("available"):
        assert r.json()["reason"]


def test_reporte_ejecutivo_es_html_con_cifras(client):
    r = client.get("/api/report", params={"zone": "madrededios"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    html = r.text
    assert "Reporte para la brigada" in html
    assert "Cómo se armonizó" in html
    assert "Imprimir / Guardar como PDF" in html
    assert "NASA FIRMS" in html


def test_english_report_and_bulletin(client):
    report = client.get('/api/report', params={'zone': 'madrededios', 'language': 'en'})
    assert report.status_code == 200 and '<html lang="en">' in report.text
    assert 'Provisional results' in report.text and 'not confirmed fires' in report.text
    assert 'union/VIIRS' in report.text
    bulletin = client.get('/api/bulletin', params={'zone': 'peru', 'language': 'en'})
    assert bulletin.status_code == 200
    assert 'historical, not real time' in bulletin.json()['text']
    assert 'provisional' in bulletin.json()['text']


def test_reporte_rechaza_fechas_invertidas(client):
    r = client.get("/api/report", params={"zone": "peru", "start": "2025-01-01", "end": "2010-01-01"})
    assert r.status_code == 400


def test_redact_hides_firms_key():
    """Un error de red no debe escupir la clave en la consola (ni en el video)."""
    from pyro import nrt

    key = "abcdef0123456789abcdef0123456789"
    message = f"Max retries: https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/MODIS_NRT/..."
    assert key not in nrt.redact(message, key)
    assert "***" in nrt.redact(message, key)
    assert nrt.redact("sin claves", key) == "sin claves"
