"""El importador de datos propios: columnas flexibles, confianza y fechas."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "import_clean.py"


@pytest.fixture(scope="module")
def imp():
    spec = importlib.util.spec_from_file_location("import_clean", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_detect_columns_in_spanish(imp):
    cols = imp.detect_columns(["Latitud", "Longitud", "Fecha", "Satelite", "Confianza", "FRP", "Tipo"])
    assert cols["lat"] == "Latitud"
    assert cols["lon"] == "Longitud"
    assert cols["date"] == "Fecha"
    assert cols["satellite"] == "Satelite"
    assert cols["confidence"] == "Confianza"


def test_detect_columns_english(imp):
    cols = imp.detect_columns(["latitude", "longitude", "acq_date", "instrument", "confidence", "frp"])
    assert cols == {"lat": "latitude", "lon": "longitude", "date": "acq_date",
                    "satellite": "instrument", "confidence": "confidence", "frp": "frp"}


def test_source_and_confidence(imp):
    assert imp.to_source("MODIS") == 1
    assert imp.to_source("VIIRS S-NPP") == 2
    assert imp.to_source("otro") is None
    assert imp.to_conf_level("h", 2) == 2
    assert imp.to_conf_level("n", 2) == 1
    assert imp.to_conf_level("l", 2) == 0
    assert imp.to_conf_level(85, 1) == 2
    assert imp.to_conf_level(50, 1) == 1
    assert imp.to_conf_level(10, 1) == 0


def test_epoch_days_accepts_two_formats(imp):
    series = pd.Series(["2024-09-15", "20240916", "no-es-fecha"])
    days = imp.to_epoch_days(series)
    assert days.iloc[0] == (pd.Timestamp("2024-09-15") - pd.Timestamp("1970-01-01")).days
    assert days.iloc[1] == (pd.Timestamp("2024-09-16") - pd.Timestamp("1970-01-01")).days
    assert pd.isna(days.iloc[2])


def test_build_frame_returns_store_schema(imp):
    df = pd.DataFrame({
        "Latitud": [-12.5, -12.5, None],
        "Longitud": [-69.2, -69.2, -69.0],
        "Fecha": ["2024-09-15", "2024-09-15", "2024-09-16"],
        "Satelite": ["VIIRS", "VIIRS", "MODIS"],
        "Confianza": ["h", "h", 90],
        "FRP": [45.0, 45.0, 12.0],
        "Tipo": [0, 0, 0],
    })
    cols = imp.detect_columns(list(df.columns))
    frame, report = imp.build_frame(df, cols)
    assert list(frame.columns) == ["day", "lat", "lon", "source", "conf_level", "conf_raw", "frp", "ftype"]
    assert report["filas_leidas"] == 3
    assert report["sin_coordenadas"] == 1
    assert frame["source"].tolist() == [2, 2]
    assert frame["conf_level"].tolist() == [2, 2]
