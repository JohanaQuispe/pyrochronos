"""Semaforo de temporada: aviso ANTES del pico, con la historia de la zona.

Que hace y que no hace (importante para no mentir):
  - SI: dice en que punto de su temporada historica esta la zona y cuando llega la
    ventana en la que, en los anos anteriores, se concentraron los incendios.
  - NO: no predice igniciones ni es un pronostico meteorologico. Los satelites
    detectan calor DESPUES de que el fuego empezo.

Niveles: normal / vigilancia / critico, calculados con la climatologia semanal de la
propia zona (mediana por semana del ano) y, si hay datos recientes cargados, con lo
observado en los ultimos dias.
"""
from __future__ import annotations

from datetime import date

import numpy as np

from .calendar import build_calendar
from .config import Config
from . import nrt
from .store import Dataset

LEVELS = {
    "critico": {
        "severity": 2,
        "label": "Ventana crítica",
        "short": "Actividad histórica máxima",
        "action": (
            "Activa vigilancia diaria: revisa el boletín reciente, confirma que las brigadas tengan "
            "el aviso y prioriza las zonas con mayor actividad histórica. Es la época en la que se "
            "concentran los incendios de tu zona."
        ),
    },
    "vigilancia": {
        "severity": 1,
        "label": "Vigilancia",
        "short": "Actividad en ascenso",
        "action": (
            "Revisa el calendario una vez por semana y confirma que el monitoreo esté activo. "
            "Todavía no es el pico, pero la temporada ya empezó."
        ),
    },
    "normal": {
        "severity": 0,
        "label": "Fuera de temporada",
        "short": "Actividad histórica baja",
        "action": "Mantén el monitoreo habitual: históricamente esta no es la época de incendios de tu zona.",
    },
}


def _iso_week(d: date) -> int:
    return int(d.isocalendar()[1])


def build_alert(
    cfg: Config,
    ds: Dataset,
    bbox: tuple[float, float, float, float],
    zone_name: str,
    reference_date: date | None = None,
    lookahead_weeks: int = 4,
    recent_selector=None,
) -> dict:
    ref = reference_date or date.today()
    weekly = build_calendar(cfg, ds, bbox, ds.start, ds.end, "week", cfg.default_measure, "both", zone_name)
    cal = weekly["calendar"]
    values = np.array([[np.nan if v is None else v for v in row] for row in cal["values"]], dtype=float)
    weeks = weekly["meta"]["periods"]

    with np.errstate(all="ignore"):
        clim = np.nanmedian(values, axis=0)
        p90 = np.nanpercentile(values, 90, axis=0)
    if not np.isfinite(clim).any():
        return {"level": "normal", "severity": 0, "label": LEVELS["normal"]["label"],
                "available": False, "reasons": ["No hay historial suficiente en esta zona."]}

    peak = float(np.nanmax(clim))
    peak_week = int(weeks[int(np.nanargmax(clim))])
    wk = _iso_week(ref)
    window = [((wk + i - 1) % 53) + 1 for i in range(max(1, lookahead_weeks))]

    def expected(w: int) -> float:
        idx = weeks.index(w) if w in weeks else None
        if idx is None or not np.isfinite(clim[idx]):
            return float("nan")
        return float(clim[idx])

    ratios = [(w, expected(w) / peak if peak > 0 and np.isfinite(expected(w)) else 0.0) for w in window]
    best_week, best_ratio = max(ratios, key=lambda t: t[1])
    if best_ratio >= 0.75:
        level = "critico"
    elif best_ratio >= 0.40:
        level = "vigilancia"
    else:
        level = "normal"

    reasons = [f"Referencia: semana {wk} del año ({ref.isoformat()})."]
    reasons.append(
        f"En {zone_name}, la semana de mayor actividad histórica es la {peak_week}."
    )
    if best_ratio > 0:
        reasons.append(
            f"En las próximas {len(window)} semanas, la más activa es la semana {best_week}: "
            f"se espera un {best_ratio * 100:.0f} % de la actividad del pico histórico."
        )
    else:
        reasons.append(f"Las próximas {len(window)} semanas son de baja actividad histórica en esta zona.")

    # --- actividad reciente observada (si hay NRT cargado) --------------------
    recent = nrt.stats(cfg, bbox, selector=recent_selector) if recent_selector else nrt.stats(cfg, bbox)
    recent_ratio = None
    if recent.get("available") and not recent.get("empty"):
        det = build_calendar(cfg, ds, bbox, ds.start, ds.end, "week", "detections", "both", zone_name)
        dvals = np.array([[np.nan if v is None else v for v in row] for row in det["calendar"]["values"]], dtype=float)
        with np.errstate(all="ignore"):
            dclim = np.nanmedian(dvals, axis=0)
        idx = weeks.index(wk) if wk in weeks else None
        med = float(dclim[idx]) if idx is not None and np.isfinite(dclim[idx]) else float("nan")
        obs = float(recent.get("last_7_days") or 0)
        if np.isfinite(med) and med > 0:
            recent_ratio = obs / med
            reasons.append(
                f"Actividad reciente observada: {int(obs)} focos en los últimos 7 días "
                f"({recent_ratio:.1f}× la mediana histórica de esta semana, {med:.0f} focos)."
            )
            if recent_ratio >= 1.5 and level == "normal":
                level = "vigilancia"
                reasons.append("La actividad reciente ya está por encima de lo normal: se sube a vigilancia.")
            elif recent_ratio >= 2.5:
                level = "critico"
                reasons.append("La actividad reciente duplica con holgura lo normal: se sube a ventana crítica.")

    info = LEVELS[level]
    return {
        "available": True,
        "level": level,
        "severity": info["severity"],
        "label": info["label"],
        "short": info["short"],
        "action": info["action"],
        "reasons": reasons,
        "reference_date": ref.isoformat(),
        "week": wk,
        "peak_week": peak_week,
        "peak_value": peak,
        "ratio": round(float(best_ratio), 3),
        "window": [
            {
                "week": w,
                "expected": None if not np.isfinite(expected(w)) else round(expected(w), 1),
                "ratio": round(float(r), 3),
                "in_peak": r >= 0.75,
            }
            for w, r in ratios
        ],
        "recent": recent,
        "measure": weekly["meta"]["measure"],
        "measure_label": weekly["meta"]["measure_label"],
        "disclaimer": (
            "Semaforo basado en la estacionalidad histórica de la zona y, si existen, en los focos "
            "recientes. No es un pronóstico meteorológico ni predice igniciones."
        ),
    }
