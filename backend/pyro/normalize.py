"""Normalizacion: CSV crudos de FIRMS -> un unico esquema comun.

Esquema de salida (una fila = una deteccion):
    day        int32   dias desde 1970-01-01
    lat, lon   float32 grados
    source     int8    1 = MODIS, 2 = VIIRS
    conf_level int8    0 = baja, 1 = nominal, 2 = alta
    conf_raw   int8    MODIS 0-100 ; VIIRS -1 (no aplica)
    frp        float32 MW
    ftype      int8    0 vegetacion, 1 volcan, 2 fuente fija, 3 costa/otro
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

SOURCE_MODIS = 1
SOURCE_VIIRS = 2

STORE_COLUMNS = ["day", "lat", "lon", "source", "conf_level", "conf_raw", "frp", "ftype"]
EPOCH = np.datetime64("1970-01-01", "D")

_CONF_LEVEL_NAMES = {0: "baja", 1: "nominal", 2: "alta"}

_FILE_RE = re.compile(r"^(?P<product>modis|viirs-snpp|viirs-jpss1|viirs-noaa20|viirs-noaa21)[_-](?P<year>\d{4})", re.I)


def _detect_product(path: Path) -> str:
    m = _FILE_RE.match(path.name)
    if not m:
        raise ValueError(f"no reconozco el producto en el nombre del archivo: {path.name}")
    prod = m.group("product").lower().replace("-", "")
    return {"modis": "modis", "viirssnpp": "viirs", "viirsjpss1": "viirs",
            "viirsnoaa20": "viirs", "viirsnoaa21": "viirs"}.get(prod, prod)


def _confidence_level(values: pd.Series, is_modis: bool, min_conf_modis: int) -> pd.Series:
    """MODIS trae confianza 0-100 y VIIRS categorias l/n/h. Los unificamos a 0/1/2."""
    raw = values.astype("string").str.strip().str.lower()
    if is_modis:
        num = pd.to_numeric(raw, errors="coerce")
        level = pd.Series(1, index=values.index, dtype="int8")  # nominal por defecto
        level[num >= 80] = 2
        level[num < min_conf_modis] = 0
        level[num.isna()] = 0
        return level.astype("int8")
    mapping = pd.Series({"l": 0, "n": 1, "h": 2}, dtype="int8")
    return raw.map(mapping).fillna(0).astype("int8")


def normalize_frame(
    df: pd.DataFrame,
    product: str,
    min_conf_modis: int = 30,
    bbox: tuple[float, float, float, float] | None = None,
) -> pd.DataFrame:
    """Convierte un DataFrame crudo de FIRMS al esquema comun."""
    is_modis = product == "modis"
    out = pd.DataFrame(index=df.index)
    out["lat"] = pd.to_numeric(df["latitude"], errors="coerce").astype("float32")
    out["lon"] = pd.to_numeric(df["longitude"], errors="coerce").astype("float32")
    dates = pd.to_datetime(df["acq_date"], errors="coerce")
    out["day"] = (dates.values.astype("datetime64[D]") - EPOCH).astype("int32")
    out["source"] = np.int8(SOURCE_MODIS if is_modis else SOURCE_VIIRS)
    out["conf_level"] = _confidence_level(df["confidence"], is_modis, min_conf_modis)
    if is_modis:
        out["conf_raw"] = pd.to_numeric(df["confidence"], errors="coerce").fillna(0).clip(0, 100).astype("int8")
    else:
        out["conf_raw"] = np.int8(-1)
    out["frp"] = pd.to_numeric(df.get("frp"), errors="coerce").astype("float32")
    if "type" in df.columns:
        out["ftype"] = pd.to_numeric(df["type"], errors="coerce").fillna(0).clip(0, 9).astype("int8")
    else:
        out["ftype"] = np.int8(0)

    # limpieza minima: coordenadas y fecha validas
    mask = out["day"].notna() & out["lat"].between(-90, 90) & out["lon"].between(-180, 180)
    if bbox is not None:
        w, s, e, n = bbox
        mask &= out["lat"].between(s, n) & out["lon"].between(w, e)
    out = out.loc[mask, STORE_COLUMNS].copy()
    out["day"] = out["day"].astype("int32")
    return out.reset_index(drop=True)


def read_raw_csv(path: Path, min_conf_modis: int = 30, bbox=None) -> pd.DataFrame:
    """Lee un CSV crudo (uno por producto y ano) y lo normaliza."""
    product = _detect_product(Path(path))
    df = pd.read_csv(path, dtype={"confidence": "string"}, low_memory=False)
    return normalize_frame(df, product, min_conf_modis, bbox)


def load_raw_directory(
    raw_dir: Path,
    pattern: str = "*",
    min_conf_modis: int = 30,
    bbox=None,
) -> pd.DataFrame:
    """Normaliza todos los CSV de una carpeta (reanudable: ignora lo ilegible)."""
    files = sorted(p for p in Path(raw_dir).glob(f"{pattern}*.csv"))
    if not files:
        raise FileNotFoundError(f"no hay CSV en {raw_dir} con patron '{pattern}'")
    frames = []
    for f in files:
        try:
            frames.append(read_raw_csv(f, min_conf_modis, bbox))
        except ValueError as exc:  # nombre desconocido: se informa y se sigue
            print(f"  aviso: {exc}")
    out = pd.concat(frames, ignore_index=True)
    out = out.sort_values(["day", "source"], kind="stable").reset_index(drop=True)
    return out


def filter_quality(
    df: pd.DataFrame, min_conf_modis: int = 30, exclude_types=(), drop_low_viirs: bool = True
) -> pd.DataFrame:
    """Aplica el umbral de confianza y los tipos excluidos (configurable)."""
    mask = pd.Series(True, index=df.index)
    is_modis = df["source"] == SOURCE_MODIS
    if min_conf_modis > 0:
        mask &= ~is_modis | (df["conf_level"] >= 1)
    if drop_low_viirs:
        mask &= is_modis | (df["conf_level"] >= 1)
    if exclude_types:
        mask &= ~df["ftype"].isin(list(exclude_types))
    return df.loc[mask].reset_index(drop=True)


def decode_source(values) -> pd.Series:
    return pd.Series(values).map({SOURCE_MODIS: "MODIS", SOURCE_VIIRS: "VIIRS"})


def conf_level_name(level: int) -> str:
    return _CONF_LEVEL_NAMES.get(int(level), "desconocida")
