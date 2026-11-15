"""Anomalias: percentil de cada semana/mes frente al historial de la MISMA zona.

Detalles que importan:
- comparacion contra el mismo periodo del ano, con ventana +-1 semana/mes;
- leave-one-out: el ano evaluado NO entra en su propio historial;
- se exige un minimo de anos de historial y un valor minimo, para no marcar
  como "extremo" un periodo con dos focos.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MODULUS = {"week": 53, "month": 12}


def _distance(index: np.ndarray, target: int, modulus: int) -> np.ndarray:
    d = np.abs(index - target)
    return np.minimum(d, modulus - d)


def classify(series: pd.DataFrame, granularity: str, cfg: dict) -> pd.DataFrame:
    """Agrega columnas anomaly_pct y anomaly_level a la serie harmonizada."""
    out = series.copy()
    mod = MODULUS[granularity]
    window = int(cfg["window_periods"])
    min_years = int(cfg["min_history_years"])
    min_value = float(cfg["min_value"])

    pct_out = np.full(len(out), np.nan)
    level_out = np.empty(len(out), dtype=object)
    level_out[:] = None
    n_years_out = np.zeros(len(out), dtype=int)

    idx = out["period_index"].to_numpy()
    yrs = out["period_year"].to_numpy()
    val = out["value"].to_numpy(float)

    finite = np.isfinite(val)
    for i in range(len(out)):
        if not finite[i] or val[i] < min_value:
            continue
        near = _distance(idx, int(idx[i]), mod) <= window
        hist_mask = finite & near & (yrs != yrs[i])
        hist = val[hist_mask]
        if hist.size == 0:
            continue
        years_in_hist = len(set(yrs[hist_mask].tolist()))
        n_years_out[i] = years_in_hist
        if years_in_hist < min_years:
            continue
        below = float(np.sum(hist < val[i]))
        equal = float(np.sum(hist == val[i]))
        pct = 100.0 * (below + 0.5 * equal) / hist.size
        pct_out[i] = pct
        if pct >= float(cfg["extreme"]):
            level_out[i] = "extremo"
        elif pct >= float(cfg["high"]):
            level_out[i] = "alto"
        else:
            level_out[i] = "normal"

    out["anomaly_pct"] = pct_out
    out["anomaly_level"] = level_out
    out["history_years"] = n_years_out
    return out


def plain_level(level: str | None) -> str:
    return {
        "extremo": "muy por encima de lo normal",
        "alto": "por encima de lo normal",
        "normal": "dentro de lo normal",
        None: "sin historial suficiente",
    }[level if level else None]
