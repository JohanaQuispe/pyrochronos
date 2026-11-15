"""Resumen en lenguaje simple. Texto generado SOLO con los numeros calculados.

No hay modelo de lenguaje aqui: son plantillas que rellenan cifras del sistema,
para que nada de lo que se afirma pueda ser inventado.
"""
from __future__ import annotations

MONTHS = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def n(value: float | int | None) -> str:
    if value is None or (isinstance(value, float) and not value == value):
        return "sin dato"
    return f"{int(round(value)):,}".replace(",", " ")


def month_name(index: int) -> str:
    return MONTHS[int(index) - 1]


def build_summary(cards: dict, coverage: dict, calibration: dict, granularity: str, zone_name: str) -> str:
    parts: list[str] = []
    start, end = coverage.get("start"), coverage.get("end")
    parts.append(
        f"En {zone_name} hay datos de {start} a {end} y {n(cards.get('total_detections'))} focos de calor "
        "detectados por satelite en el rango elegido."
    )

    if cards.get("season"):
        season = cards["season"]
        parts.append(
            f"La temporada de fuego va de {season['label']}, con el máximo en {season['peak_name']}."
            if len(season["months"]) > 1
            else f"La actividad se concentra en {season['label']}."
        )
    if cards.get("most_active_month") and not cards.get("season"):
        c = cards["most_active_month"]
        parts.append(f"El mes con mas actividad en toda la serie es {month_name(c['period_index'])}.")
    if cards.get("most_active_year"):
        c = cards["most_active_year"]
        parts.append(f"El ano con mas actividad es {c['period_year']}.")

    last = cards.get("last_month")
    if last:
        direction = "por encima" if (last.get("delta_pct") or 0) > 0 else "por debajo"
        if last.get("delta_pct") is None:
            parts.append(
                f"El ultimo mes con datos es {month_name(last['period_index'])} de {last['period_year']}, "
                "pero no hay historial suficiente para compararlo."
            )
        else:
            parts.append(
                f"El ultimo mes con datos es {month_name(last['period_index'])} de {last['period_year']}: "
                f"quedo {abs(last['delta_pct']):.0f}% {direction} de la mediana historica de ese mes "
                f"({last['level_label']})."
            )
    if calibration.get("agreement_r") is not None:
        r = calibration["agreement_r"]
        quality = "alta" if r >= 0.9 else "media" if r >= 0.7 else "baja"
        parts.append(
            f"En los anos en que MODIS y VIIRS coinciden, sus series se parecen mucho "
            f"(correlacion {r:.2f}, concordancia {quality})."
        )
    parts.append(
        "El calendario es historico: sirve para ver patrones y periodos criticos, no para detectar "
        "incendios en el momento."
    )
    return " ".join(parts)
