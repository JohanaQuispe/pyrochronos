"""Armonizacion MODIS + VIIRS.

Regla: la escala de referencia es la de los DOS sensores juntos (celdas-dia sin
duplicar). En los anos de solape (2012-2025) esa escala se observa. Antes de
2012 solo existe MODIS, asi que el valor se ESTIMA multiplicando por el cociente
tipico (union/MODIS) de ese mismo periodo del ano; la banda de incertidumbre sale
de la dispersion de ese cociente entre anos. Lo estimado se dibuja rayado.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

PREFIX = {"cell_days": "cd", "detections": "det"}


@dataclass
class Calibration:
    factor_by_period: dict[int, float] = field(default_factory=dict)
    ratio_p25: dict[int, float] = field(default_factory=dict)
    ratio_p75: dict[int, float] = field(default_factory=dict)
    samples_by_period: dict[int, int] = field(default_factory=dict)
    viirs_factor_by_period: dict[int, float] = field(default_factory=dict)
    viirs_p25_by_period: dict[int, float] = field(default_factory=dict)
    viirs_p75_by_period: dict[int, float] = field(default_factory=dict)
    viirs_samples_by_period: dict[int, int] = field(default_factory=dict)
    viirs_global_factor: float | None = None
    viirs_global_p25: float | None = None
    viirs_global_p75: float | None = None
    global_factor: float = 1.0
    global_p25: float = 1.0
    global_p75: float = 1.0
    agreement_r: float | None = None
    agreement_n: int = 0
    overlap_years: list[int] = field(default_factory=list)
    measure: str = "cell_days"

    def factor(self, period_index: int) -> tuple[float, float, float, bool]:
        """(factor, p25, p75, uso_factor_global)"""
        if period_index in self.factor_by_period:
            return (
                self.factor_by_period[period_index],
                self.ratio_p25[period_index],
                self.ratio_p75[period_index],
                False,
            )
        return self.global_factor, self.global_p25, self.global_p75, True

    def factor_viirs(self, period_index: int) -> tuple[float | None, float | None, float | None, bool]:
        """Factor unión/VIIRS, independiente del factor unión/MODIS."""
        if period_index in self.viirs_factor_by_period:
            return (self.viirs_factor_by_period[period_index], self.viirs_p25_by_period[period_index],
                    self.viirs_p75_by_period[period_index], False)
        return self.viirs_global_factor, self.viirs_global_p25, self.viirs_global_p75, True

    def as_dict(self) -> dict:
        return {
            "measure": self.measure,
            "global_factor": round(float(self.global_factor), 3),
            "global_p25": round(float(self.global_p25), 3),
            "global_p75": round(float(self.global_p75), 3),
            "viirs_global_factor": None if self.viirs_global_factor is None else round(self.viirs_global_factor, 3),
            "viirs_global_p25": None if self.viirs_global_p25 is None else round(self.viirs_global_p25, 3),
            "viirs_global_p75": None if self.viirs_global_p75 is None else round(self.viirs_global_p75, 3),
            "viirs_factor_by_period": {str(k): round(v, 3) for k, v in sorted(self.viirs_factor_by_period.items())},
            "viirs_samples_by_period": {str(k): int(v) for k, v in sorted(self.viirs_samples_by_period.items())},
            "agreement_r": None if self.agreement_r is None else round(float(self.agreement_r), 3),
            "agreement_n": int(self.agreement_n),
            "overlap_years": self.overlap_years,
            "factor_by_period": {str(k): round(float(v), 3) for k, v in sorted(self.factor_by_period.items())},
            "samples_by_period": {str(k): int(v) for k, v in sorted(self.samples_by_period.items())},
        }


def calibrate(
    agg: pd.DataFrame,
    measure: str,
    overlap_start_year: int,
    overlap_end_year: int,
    shrink_min_years: int,
    min_periods_for_factor: float,
) -> Calibration:
    p = PREFIX[measure]
    m = agg[f"modis_{p}"].to_numpy(float)
    v = agg[f"viirs_{p}"].to_numpy(float)
    u = agg[f"union_{p}"].to_numpy(float)

    both = (m > 0) & (v > 0)
    in_window = agg["period_year"].between(overlap_start_year, overlap_end_year).to_numpy()
    overlap = both & in_window
    cal = Calibration(measure=measure)
    cal.overlap_years = sorted(set(agg.loc[overlap, "period_year"].astype(int)))

    if not overlap.any():
        cal.global_factor = cal.global_p25 = cal.global_p75 = 1.0
        return cal

    ratio = np.where(m > 0, u / np.maximum(m, 1), np.nan)
    usable = overlap & (m >= min_periods_for_factor) & np.isfinite(ratio)
    if usable.sum() >= 3:
        cal.global_factor = float(np.median(ratio[usable]))
        cal.global_p25 = float(np.percentile(ratio[usable], 25))
        cal.global_p75 = float(np.percentile(ratio[usable], 75))
    else:  # senal muy debil: sin evidencia suficiente, no inventamos factor
        cal.global_factor = cal.global_p25 = cal.global_p75 = 1.0

    years = agg["period_year"].to_numpy()
    for pid, block in agg.groupby("period_index"):
        sel = usable & (agg["period_index"].to_numpy() == pid)
        vals = ratio[sel]
        if vals.size >= shrink_min_years:
            cal.factor_by_period[int(pid)] = float(np.median(vals))
            cal.ratio_p25[int(pid)] = float(np.percentile(vals, 25))
            cal.ratio_p75[int(pid)] = float(np.percentile(vals, 75))
            cal.samples_by_period[int(pid)] = int(vals.size)

    # VIIRS sola requiere su propio cociente unión/VIIRS; nunca usar unión/MODIS.
    viirs_ratio = np.divide(u, v, out=np.full_like(u, np.nan), where=v > 0)
    viirs_usable = overlap & (v >= min_periods_for_factor) & np.isfinite(viirs_ratio)
    if viirs_usable.sum() >= 3:
        samples = viirs_ratio[viirs_usable]
        cal.viirs_global_factor = float(np.median(samples))
        cal.viirs_global_p25 = float(np.percentile(samples, 25))
        cal.viirs_global_p75 = float(np.percentile(samples, 75))
    for pid in agg['period_index'].unique():
        sel = viirs_usable & (agg['period_index'].to_numpy() == pid)
        samples = viirs_ratio[sel]
        if len(samples) >= shrink_min_years:
            cal.viirs_factor_by_period[int(pid)] = float(np.median(samples))
            cal.viirs_p25_by_period[int(pid)] = float(np.percentile(samples, 25))
            cal.viirs_p75_by_period[int(pid)] = float(np.percentile(samples, 75))
            cal.viirs_samples_by_period[int(pid)] = int(len(samples))

    # concordancia: correlacion de las dos fuentes en el solape
    if both.sum() >= 3 and np.std(m[both]) > 0 and np.std(v[both]) > 0:
        cal.agreement_r = float(np.corrcoef(m[both], v[both])[0, 1])
        cal.agreement_n = int(both.sum())
    del years
    return cal


def harmonize(agg: pd.DataFrame, cal: Calibration, sources: str = 'both') -> pd.DataFrame:
    """Devuelve la serie armonizada con bandera de estimacion y banda de incertidumbre."""
    p = PREFIX[cal.measure]
    m = agg[f"modis_{p}"].to_numpy(float)
    v = agg[f"viirs_{p}"].to_numpy(float)
    u = agg[f"union_{p}"].to_numpy(float)

    out = agg[["period_year", "period_index"]].copy()
    value = np.full(len(agg), np.nan)
    low = np.full(len(agg), np.nan)
    high = np.full(len(agg), np.nan)
    estimated = np.zeros(len(agg), dtype=bool)
    fallback = np.zeros(len(agg), dtype=bool)
    factor_used = np.full(len(agg), np.nan)

    for i, pid in enumerate(agg["period_index"].to_numpy()):
        if sources != 'both':                 # vista de un sensor: datos observados
            value[i] = low[i] = high[i] = u[i]
        elif m[i] > 0 and v[i] > 0:            # ambos sensores: unión observada
            value[i] = low[i] = high[i] = u[i]
        elif m[i] > 0:
            f, lo, hi, is_global = cal.factor(pid)
            factor_used[i] = f
            value[i] = m[i] * f
            low[i], high[i] = m[i] * lo, m[i] * hi
            estimated[i], fallback[i] = True, is_global
        elif v[i] > 0:
            f, lo, hi, is_global = cal.factor_viirs(pid)
            if f is not None:                  # sin evidencia: valor no disponible, no cero
                factor_used[i] = f
                value[i] = v[i] * f
                low[i], high[i] = v[i] * lo, v[i] * hi
                estimated[i], fallback[i] = True, is_global

    out["value"] = value
    out["value_low"] = low
    out["value_high"] = high
    out["estimated"] = estimated
    out["factor_fallback"] = fallback
    out["factor"] = factor_used
    out["modis"] = m
    out["viirs"] = v
    out["union"] = u
    out["observed"] = np.where((m > 0) | (v > 0), u, np.nan)
    return out
