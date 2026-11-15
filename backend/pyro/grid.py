"""Cuadricula comun y conteo de CELDAS-DIA con fuego.

Por que celdas-dia y no detecciones: VIIRS tiene ~375 m y MODIS ~1 km, y VIIRS
hace mas observaciones por dia. Contar detecciones sueltas inflaria los anos
recientes. Contar una celda una vez por dia y satelite reduce ese sesgo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .normalize import EPOCH, SOURCE_MODIS, SOURCE_VIIRS


def add_cells(df: pd.DataFrame, cell_deg: float) -> pd.DataFrame:
    """Agrega indices de cuadricula (cx, cy) a las detecciones."""
    out = df.copy()
    out["cx"] = np.floor((out["lon"].to_numpy(np.float64) + 180.0) / cell_deg).astype(np.int32)
    out["cy"] = np.floor((out["lat"].to_numpy(np.float64) + 90.0) / cell_deg).astype(np.int32)
    return out


def build_cells(df: pd.DataFrame, cell_deg: float) -> pd.DataFrame:
    """Celdas unicas por (dia, celda, satelite). Base de la medida principal."""
    con = add_cells(df, cell_deg)
    cells = con.drop_duplicates(subset=["day", "cx", "cy", "source"])[["day", "cx", "cy", "source", "ftype"]]
    return cells.reset_index(drop=True)


def bbox_to_cells(bbox: tuple[float, float, float, float], cell_deg: float) -> tuple[int, int, int, int]:
    w, s, e, n = bbox
    cx0 = int(np.floor((w + 180.0) / cell_deg))
    cx1 = int(np.floor((e + 180.0) / cell_deg))
    cy0 = int(np.floor((s + 90.0) / cell_deg))
    cy1 = int(np.floor((n + 90.0) / cell_deg))
    return cx0, cx1, cy0, cy1


def daily_counts(
    cells: pd.DataFrame, detections: pd.DataFrame, bbox, cell_deg: float
) -> pd.DataFrame:
    """Serie diaria por fuente: celdas-dia y detecciones, y su union."""
    cx0, cx1, cy0, cy1 = bbox_to_cells(bbox, cell_deg)
    c = cells[(cells["cx"] >= cx0) & (cells["cx"] <= cx1) & (cells["cy"] >= cy0) & (cells["cy"] <= cy1)]
    d = detections[(detections["lat"] >= bbox[1]) & (detections["lat"] <= bbox[3])
                   & (detections["lon"] >= bbox[0]) & (detections["lon"] <= bbox[2])]

    cd = (c.groupby(["day", "source"]).size().unstack("source").reindex(columns=[SOURCE_MODIS, SOURCE_VIIRS]))
    de = (d.groupby(["day", "source"]).size().unstack("source").reindex(columns=[SOURCE_MODIS, SOURCE_VIIRS]))
    union_cd = c.drop_duplicates(subset=["day", "cx", "cy"]).groupby("day").size()
    union_de = d.groupby("day").size()

    out = pd.DataFrame(index=sorted(set(cd.index) | set(de.index)))
    out["modis_cd"] = cd[SOURCE_MODIS].reindex(out.index).fillna(0)
    out["viirs_cd"] = cd[SOURCE_VIIRS].reindex(out.index).fillna(0)
    out["union_cd"] = union_cd.reindex(out.index).fillna(0)
    out["modis_det"] = de[SOURCE_MODIS].reindex(out.index).fillna(0)
    out["viirs_det"] = de[SOURCE_VIIRS].reindex(out.index).fillna(0)
    out["union_det"] = union_de.reindex(out.index).fillna(0)
    out.index.name = "day"
    return out.astype("int64").reset_index()


def day_to_period(days: pd.Series, granularity: str) -> pd.DataFrame:
    """Dia -> (ano del periodo, indice del periodo). week = ISO 1..53, month = 1..12."""
    dates = pd.to_datetime(days.astype("int64"), unit="D")  # dias desde 1970-01-01
    if granularity == "month":
        return pd.DataFrame({"period_year": dates.dt.year.to_numpy(), "period_index": dates.dt.month.to_numpy()})
    if granularity == "week":
        iso = dates.dt.isocalendar()
        return pd.DataFrame({"period_year": iso["year"].to_numpy(), "period_index": iso["week"].to_numpy()})
    raise ValueError(f"granularidad no soportada: {granularity}")


def aggregate_periods(daily: pd.DataFrame, granularity: str) -> pd.DataFrame:
    """Suma la serie diaria a semanas o meses."""
    periods = day_to_period(daily["day"], granularity)
    frame = pd.concat([daily.drop(columns=["day"]), periods], axis=1)
    agg = frame.groupby(["period_year", "period_index"], as_index=False).sum(numeric_only=True)
    agg["days_observed"] = frame.groupby(["period_year", "period_index"]).size().to_numpy()
    return agg.sort_values(["period_year", "period_index"]).reset_index(drop=True)


def period_bounds(granularity: str) -> list[int]:
    return list(range(1, 13)) if granularity == "month" else list(range(1, 54))


def day_label(day: int) -> str:
    return str((EPOCH + np.timedelta64(int(day), "D")).astype("datetime64[D]"))
