"""Contexto meteorológico con NASA POWER (sin clave de API).

Para qué sirve: el calendario dice *cuándo* hay fuego; POWER añade *cómo está el
combustible*. Un déficit de lluvia y una temperatura máxima por encima de lo normal
en los últimos 30 días describen un bosque más seco de lo habitual.

Reglas de honestidad:
- POWER es reanálisis/datos asimilados, no una estación en el sitio.
- Es una ventana de 30 días comparada con los mismos 30 días de los años anteriores
  del propio caché. Si no hay caché, NO se inventa nada: `available: false`.
- La web nunca llama a NASA en la petición: se precarga con `download_power.py`.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .config import Config

POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETERS = ("T2M_MAX", "PRECTOTCORR", "RH2M")
MISSING = -999.0
WINDOW_DAYS = 30


def cache_path(cfg: Config, zone: str) -> Path:
    """Caché por zona (carpeta configurable con PYRO_POWER_DIR, útil en pruebas)."""
    override = os.environ.get("PYRO_POWER_DIR")
    base = Path(override) if override else cfg.data_file.parent
    return base / f"power_{zone}.json"


def zone_point(cfg: Config, zone: str) -> tuple[float, float]:
    """Centro del BBox de la zona (POWER es puntual)."""
    w, s, e, n = cfg.zone_bbox(zone)
    return ((s + n) / 2, (w + e) / 2)


def fetch_daily(
    lat: float,
    lon: float,
    start: date,
    end: date,
    parameters: tuple[str, ...] = PARAMETERS,
    timeout: int = 60,
) -> pd.DataFrame:
    """Descarga la serie diaria de POWER. Solo lo usan los scripts, nunca la API."""
    params = {
        "parameters": ",".join(parameters),
        "community": "AG",
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }
    r = requests.get(POWER_URL, params=params, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"POWER respondió {r.status_code}: {r.text[:200]}")
    body = r.json()
    series = body.get("properties", {}).get("parameter", {})
    if not series:
        raise RuntimeError("POWER no devolvió parámetros (revisa lat/lon/fechas)")
    frame = pd.DataFrame(series)
    frame.index = pd.to_datetime(frame.index, format="%Y%m%d")
    frame = frame.replace(MISSING, np.nan).sort_index()
    return frame


def save_cache(cfg: Config, zone: str, frame: pd.DataFrame, lat: float, lon: float) -> Path:
    path = cache_path(cfg, zone)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "zone": zone,
        "zone_name": cfg.zone_name(zone),
        "lat": lat,
        "lon": lon,
        "source": "NASA POWER (api/temporal/daily/point, community=AG)",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "parameters": list(frame.columns),
        "daily": {
            idx.date().isoformat(): {k: (None if pd.isna(v) else float(v)) for k, v in row.items()}
            for idx, row in frame.iterrows()
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def load_cache(cfg: Config, zone: str) -> tuple[pd.DataFrame | None, dict]:
    path = cache_path(cfg, zone)
    if not path.exists():
        return None, {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    daily = raw.get("daily") or {}
    if not daily:
        return None, raw
    frame = pd.DataFrame.from_dict(daily, orient="index")
    frame.index = pd.to_datetime(frame.index)
    return frame.sort_index(), raw


def _window_stats(frame: pd.DataFrame, end: date, days: int = WINDOW_DAYS) -> dict:
    start = end - timedelta(days=days - 1)
    win = frame.loc[(frame.index.date >= start) & (frame.index.date <= end)]
    out: dict = {"start": start.isoformat(), "end": end.isoformat(), "days": int(len(win))}
    if "PRECTOTCORR" in win:
        rain = pd.to_numeric(win["PRECTOTCORR"], errors="coerce")
        out["rain_mm"] = float(rain.sum()) if rain.notna().any() else None
        out["dry_days"] = int((rain < 1.0).sum()) if rain.notna().any() else None
    if "T2M_MAX" in win:
        t = pd.to_numeric(win["T2M_MAX"], errors="coerce")
        out["tmax_mean_c"] = float(t.mean()) if t.notna().any() else None
    if "RH2M" in win:
        rh = pd.to_numeric(win["RH2M"], errors="coerce")
        out["rh_mean_pct"] = float(rh.mean()) if rh.notna().any() else None
    return out


def _same_window_previous_years(frame: pd.DataFrame, end: date, days: int = WINDOW_DAYS) -> list[dict]:
    current_start = end - timedelta(days=days - 1)
    stats = []
    year = current_start.year - 1
    while True:
        try:
            s = current_start.replace(year=year)
            e = end.replace(year=year) if not (end.month == 2 and end.day == 29) else date(year, 2, 28)
        except ValueError:
            break
        win = frame.loc[(frame.index.date >= s) & (frame.index.date <= e)]
        if win.empty:
            year -= 1
            if year < current_start.year - 20:
                break
            continue
        stats.append({
            "year": year,
            "rain_mm": float(pd.to_numeric(win["PRECTOTCORR"], errors="coerce").sum()) if "PRECTOTCORR" in win else None,
            "tmax_mean_c": float(pd.to_numeric(win["T2M_MAX"], errors="coerce").mean()) if "T2M_MAX" in win else None,
        })
        year -= 1
        if year < current_start.year - 15:
            break
    return stats


def climate_context(cfg: Config, zone: str, ref_date: date | None = None, days: int = WINDOW_DAYS) -> dict:
    """Contexto de sequía/calor de la zona, calculado solo con el caché local."""
    frame, raw = load_cache(cfg, zone)
    if frame is None or frame.empty:
        return {
            "available": False,
            "zone": cfg.zone_name(zone),
            "reason": "No hay datos de NASA POWER precargados para esta zona.",
            "how_to": f"python backend/scripts/download_power.py --zone {zone} --years 5",
            "source": "NASA POWER",
        }
    end = ref_date or frame.index[-1].date()
    end = min(end, frame.index[-1].date())
    current = _window_stats(frame, end, days)
    history = _same_window_previous_years(frame, end, days)
    rain_hist = [h["rain_mm"] for h in history if h.get("rain_mm") is not None]
    tmax_hist = [h["tmax_mean_c"] for h in history if h.get("tmax_mean_c") is not None]
    deficit = None
    if current.get("rain_mm") is not None and rain_hist and float(np.mean(rain_hist)) > 0:
        deficit = (current["rain_mm"] - float(np.mean(rain_hist))) / float(np.mean(rain_hist)) * 100
    tmax_anom = None
    if current.get("tmax_mean_c") is not None and tmax_hist:
        tmax_anom = current["tmax_mean_c"] - float(np.mean(tmax_hist))

    level = "sin_datos"
    if deficit is not None or tmax_anom is not None:
        if (deficit is not None and deficit <= -30) or (tmax_anom is not None and tmax_anom >= 1.5):
            level = "seco"
        elif (deficit is not None and deficit >= 30) or (tmax_anom is not None and tmax_anom <= -1.0):
            level = "humedo"
        else:
            level = "normal"

    return {
        "available": True,
        "zone": cfg.zone_name(zone),
        "source": "NASA POWER",
        "point": {"lat": raw.get("lat"), "lon": raw.get("lon")},
        "fetched_at": raw.get("fetched_at"),
        "window": current,
        "history_years": len(history),
        "rain_climatology_mm": float(np.mean(rain_hist)) if rain_hist else None,
        "rain_deficit_pct": deficit,
        "tmax_anomaly_c": tmax_anom,
        "level": level,
        "label": {"seco": "más seco de lo normal", "humedo": "más húmedo de lo normal",
                  "normal": "dentro de lo normal", "sin_datos": "sin datos suficientes"}[level],
        "note": ("Reanálisis NASA POWER en un punto central de la zona, no una estación local. "
                 "Compara 30 días con los mismos 30 días de los años anteriores disponibles."),
    }
