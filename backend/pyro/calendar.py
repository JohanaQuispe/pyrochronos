"""Ensambla la respuesta completa: calendario, tarjetas, serie del ano y metadatos."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from . import anomalies as anom
from . import grid
from .config import Config
from .harmonize import Calibration, calibrate, harmonize
from .summary import MONTHS, build_summary, month_name, n
from .store import Dataset


def _nan_to_none(values) -> list:
    return [None if (v is None or (isinstance(v, float) and not np.isfinite(v))) else int(round(float(v))) for v in values]


def _series_for_chart(ser: pd.DataFrame, year: int, periods: list[int]) -> dict:
    others = ser[ser["period_year"] != year]
    med, p25, p75 = [], [], []
    for pid in periods:
        block = others.loc[others["period_index"] == pid, "value"].dropna()
        if block.empty:
            med.append(None); p25.append(None); p75.append(None)
        else:
            med.append(float(block.median()))
            p25.append(float(np.percentile(block, 25)))
            p75.append(float(np.percentile(block, 75)))
    row = ser[ser["period_year"] == year].set_index("period_index")
    values = [float(row.loc[pid, "value"]) if pid in row.index and np.isfinite(row.loc[pid, "value"]) else None
              for pid in periods]
    modis = [float(row.loc[pid, "modis"]) if pid in row.index else None for pid in periods]
    viirs = [float(row.loc[pid, "viirs"]) if pid in row.index else None for pid in periods]
    return {"year": year, "labels": periods, "value": values, "median": med, "p25": p25, "p75": p75,
            "modis": modis, "viirs": viirs}


def build_calendar(
    cfg: Config,
    ds: Dataset,
    bbox: tuple[float, float, float, float],
    start: date,
    end: date,
    granularity: str = "month",
    measure: str | None = None,
    sources: str = "both",
    zone_name: str | None = None,
    selected_year: int | None = None,
) -> dict:
    measure = measure or cfg.default_measure
    if measure not in cfg.measures:
        raise ValueError(f"medida no soportada: {measure}")
    if granularity not in ("month", "week"):
        raise ValueError("granularidad debe ser 'month' o 'week'")
    if sources not in ("both", "modis", "viirs"):
        raise ValueError("sources debe ser 'both', 'modis' o 'viirs'")
    if start > end:
        raise ValueError("la fecha inicial no puede ser posterior a la final")

    daily = grid.daily_counts(ds.cells, ds.df, bbox, cfg.cell_deg)
    if sources == "modis":
        for col in ("viirs_cd", "viirs_det"):
            daily[col] = 0
        daily["union_cd"] = daily["modis_cd"]
        daily["union_det"] = daily["modis_det"]
    elif sources == "viirs":
        for col in ("modis_cd", "modis_det"):
            daily[col] = 0
        daily["union_cd"] = daily["viirs_cd"]
        daily["union_det"] = daily["viirs_det"]
    else:
        # la union real (celdas sin duplicar entre satelites) viene de daily_counts
        pass

    agg_all = grid.aggregate_periods(daily, granularity)
    months_agg = grid.aggregate_periods(daily, "month") if granularity != "month" else agg_all

    cal: Calibration = calibrate(
        agg_all,
        measure,
        cfg.overlap_start.year,
        cfg.overlap_end.year,
        int(cfg.harmonization["shrink_min_years"]),
        float(cfg.harmonization["min_periods_for_factor"]),
    )
    ser_all = harmonize(agg_all, cal)
    ser_all = anom.classify(ser_all, granularity, cfg.anomalies)

    # serie mensual armonizada (para tarjetas, siempre en meses)
    cal_m = calibrate(months_agg, measure, cfg.overlap_start.year, cfg.overlap_end.year,
                      int(cfg.harmonization["shrink_min_years"]),
                      float(cfg.harmonization["min_periods_for_factor"])) if granularity != "month" else cal
    if granularity != "month":
        ser_month = anom.classify(harmonize(months_agg, cal_m), "month", cfg.anomalies)
    else:
        ser_month = ser_all

    in_range = (ser_all["period_year"] >= start.year) & (ser_all["period_year"] <= end.year)
    ser = ser_all[in_range]
    months = ser_month[(ser_month["period_year"] >= start.year) & (ser_month["period_year"] <= end.year)]

    # --- calendario (filas = anos, columnas = meses o semanas) ---------------
    periods = grid.period_bounds(granularity)
    years = list(range(start.year, end.year + 1))
    values = np.full((len(years), len(periods)), np.nan)
    estimated = np.zeros((len(years), len(periods)), dtype=bool)
    fallback = np.zeros((len(years), len(periods)), dtype=bool)
    levels = np.empty((len(years), len(periods)), dtype=object)
    levels[:] = None
    pcts = np.full((len(years), len(periods)), np.nan)
    yi = {y: i for i, y in enumerate(years)}
    pi = {p: j for j, p in enumerate(periods)}
    for row in ser.itertuples(index=False):
        i, j = yi.get(int(row.period_year)), pi.get(int(row.period_index))
        if i is None or j is None:
            continue
        values[i, j] = row.value
        estimated[i, j] = bool(row.estimated)
        fallback[i, j] = bool(row.factor_fallback)
        levels[i, j] = row.anomaly_level
        pcts[i, j] = row.anomaly_pct

    # --- "sin dato" frente a cero -------------------------------------------
    cov_start, cov_end = ds.start, ds.end
    covered = grid.day_to_period(
        pd.Series(np.arange((cov_start - date(1970, 1, 1)).days, (cov_end - date(1970, 1, 1)).days + 1)),
        granularity,
    )
    covered_keys = set(zip(covered["period_year"].tolist(), covered["period_index"].tolist()))
    for i, y in enumerate(years):
        for j, p in enumerate(periods):
            if (y, p) in covered_keys and np.isnan(values[i, j]):
                values[i, j] = 0.0          # cubierto y sin focos = cero real
            if (y, p) not in covered_keys:
                values[i, j] = np.nan       # fuera de cobertura = sin dato

    # --- tarjetas ------------------------------------------------------------
    cards: dict = {}
    if not months.empty and np.isfinite(months["value"]).any():
        by_month = months.groupby("period_index")["value"].sum(min_count=1)
        by_month = by_month.dropna()
        if not by_month.empty:
            pid = int(by_month.idxmax())
            cards["most_active_month"] = {
                "period_index": pid, "name": month_name(pid), "value": float(by_month.max()),
                "years_counted": int(months.loc[months["period_index"] == pid, "period_year"].nunique()),
            }
        by_year = months.groupby("period_year")["value"].sum(min_count=1).dropna()
        if not by_year.empty:
            yy = int(by_year.idxmax())
            card_year = {"period_year": yy, "value": float(by_year.max())}
            # honestidad: si el segundo ano cae dentro de la banda de incertidumbre del primero,
            # no podemos afirmar cual fue el mas activo. Se dice explicitamente.
            block = months[months["period_year"] == yy]
            low = float(np.nansum(block["value_low"])) if block["value_low"].notna().any() else float(by_year.max())
            card_year["low"] = low
            card_year["estimated_share"] = float(block["estimated"].mean()) if len(block) else 0.0
            others = by_year.drop(index=yy)
            if len(others):
                runner_year = int(others.idxmax())
                runner_value = float(others.max())
                card_year["runner_up"] = {"period_year": runner_year, "value": runner_value}
                card_year["tie_within_uncertainty"] = bool(runner_value >= low)
            cards["most_active_year"] = card_year

        with_data = months.dropna(subset=["value"]).sort_values(["period_year", "period_index"])
        if not with_data.empty:
            last = with_data.iloc[-1]
            hist = months.loc[
                (months["period_index"] == last["period_index"]) & (months["period_year"] != last["period_year"]),
                "value",
            ].dropna()
            item = {
                "period_year": int(last["period_year"]),
                "period_index": int(last["period_index"]),
                "name": month_name(int(last["period_index"])),
                "value": float(last["value"]),
                "median": float(hist.median()) if len(hist) else None,
                "delta_pct": None,
                "level": last["anomaly_level"],
                "level_label": anom.plain_level(last["anomaly_level"]),
            }
            if len(hist) and hist.median() > 0:
                item["delta_pct"] = float((last["value"] / hist.median() - 1) * 100)
            cards["last_month"] = item

    # --- temporada de fuego (meses por encima de la mitad del pico) ----------
    if not months.empty:
        climatology = months.groupby("period_index")["value"].mean().dropna()
        if not climatology.empty and climatology.max() > 0:
            peak = int(climatology.idxmax())
            hot = {int(m) for m, v in climatology.items() if v >= 0.33 * climatology.max()}
            best: list[int] = []
            for start_m in range(1, 13):
                run: list[int] = []
                while ((start_m + len(run) - 1) % 12) + 1 in hot and len(run) < 12:
                    run.append(((start_m + len(run) - 1) % 12) + 1)
                if len(run) > len(best):
                    best = run
            if best:
                label = (
                    f"{month_name(best[0])} a {month_name(best[-1])}"
                    if len(best) > 1
                    else month_name(best[0])
                )
                cards["season"] = {
                    "months": best,
                    "label": label,
                    "peak_month": peak,
                    "peak_name": month_name(peak),
                    "share_of_peak": round(float(climatology[best].mean() / climatology.max()), 2),
                    "criterion": "meses con al menos un tercio de la actividad del mes pico",
                }

    mask_det = ((ds.df["day"] >= (start - date(1970, 1, 1)).days) & (ds.df["day"] <= (end - date(1970, 1, 1)).days)
                & (ds.df["lat"] >= bbox[1]) & (ds.df["lat"] <= bbox[3])
                & (ds.df["lon"] >= bbox[0]) & (ds.df["lon"] <= bbox[2]))
    if sources == "modis":
        mask_det &= ds.df["source"] == 1
    elif sources == "viirs":
        mask_det &= ds.df["source"] == 2
    cards["total_detections"] = int(mask_det.sum())
    cards["total_cell_days"] = float(np.nansum(values)) if values.size else 0.0

    # --- serie del ano elegido ----------------------------------------------
    years_with_data = [int(y) for y in months.groupby("period_year")["value"].sum(min_count=1).dropna().index]
    year = int(selected_year) if selected_year else (years_with_data[-1] if years_with_data else end.year)
    if year not in years:
        year = years[-1]
    chart = _series_for_chart(ser_all, year, periods)

    months_with_data = sorted({int(m) for m in months.loc[months["value"].notna(), "period_index"]})
    coverage = ds.coverage()
    calib_dict = cal.as_dict()
    calib_dict["applicable"] = sources == "both"

    payload = {
        "meta": {
            "zone": zone_name or cfg.zone_name(),
            "bbox": list(bbox),
            "start": str(start),
            "end": str(end),
            "granularity": granularity,
            "measure": measure,
            "measure_label": "celdas-día con fuego" if measure == "cell_days" else "focos detectados",
            "sources": sources,
            "cell_deg": cfg.cell_deg,
            "periods": periods,
            "period_labels": [month_name(p) for p in periods] if granularity == "month" else [f"S{p}" for p in periods],
            "months_with_data": months_with_data,
            "generated_at": ds.generated_at,
            "data_version": ds.source_version,
            "disclaimer": cfg.disclaimer,
            "coverage": coverage,
        },
        "calendar": {
            "years": years,
            "values": [[None if np.isnan(v) else float(v) for v in row] for row in values],
            "estimated": estimated.tolist(),
            "factor_fallback": fallback.tolist(),
            "levels": [[None if v is None else str(v) for v in row] for row in levels],
            "anomaly_pct": [[None if np.isnan(v) else round(float(v), 1) for v in row] for row in pcts],
            "max_value": float(np.nanmax(values)) if np.isfinite(values).any() else 0.0,
        },
        "cards": cards,
        "chart": chart,
        "calibration": calib_dict,
        "summary": build_summary(cards, coverage, calib_dict, granularity, zone_name or cfg.zone_name()),
        "thresholds": {
            "high": float(cfg.anomalies["high"]),
            "extreme": float(cfg.anomalies["extreme"]),
            "min_value": float(cfg.anomalies["min_value"]),
            "min_history_years": int(cfg.anomalies["min_history_years"]),
        },
        "quality": {
            "min_conf_modis": cfg.min_conf_modis,
            "min_conf_viirs": cfg.min_conf_viirs,
            "cell_deg": cfg.cell_deg,
        },
    }
    payload["cards"]["total_detections_label"] = n(cards["total_detections"])
    return payload


def hotspots_geojson(ds: Dataset, bbox, start: date, end: date, sources: str, limit: int, conf_min: int = 0) -> dict:
    d0 = (start - date(1970, 1, 1)).days
    d1 = (end - date(1970, 1, 1)).days
    df = ds.df
    mask = ((df["day"] >= d0) & (df["day"] <= d1)
            & (df["lat"] >= bbox[1]) & (df["lat"] <= bbox[3])
            & (df["lon"] >= bbox[0]) & (df["lon"] <= bbox[2]))
    if sources == "modis":
        mask &= df["source"] == 1
    elif sources == "viirs":
        mask &= df["source"] == 2
    mask &= df["conf_level"] >= conf_min
    sub = df.loc[mask]
    total = int(len(sub))
    sampled = False
    if total > limit:
        sub = sub.sample(n=limit, random_state=7).sort_values("day")
        sampled = True
    feats = []
    for row in sub.itertuples(index=False):
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(float(row.lon), 4), round(float(row.lat), 4)]},
            "properties": {
                "day": str(date(1970, 1, 1) + pd.Timedelta(days=int(row.day))),
                "source": "MODIS" if int(row.source) == 1 else "VIIRS",
                "conf": int(row.conf_level),
                "frp": None if not np.isfinite(row.frp) else round(float(row.frp), 2),
            },
        })
    return {
        "type": "FeatureCollection",
        "features": feats,
        "meta": {"total": total, "shown": len(feats), "sampled": sampled},
    }
