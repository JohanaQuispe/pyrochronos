"""Boletin breve para enviar por Telegram a un equipo de guardabosques.

Aviso honesto: NO es una alerta en tiempo real. Es un resumen del calendario
historico armonizado para la zona elegida, pensado para circulos de guardaparques
y brigadas. El envio usa la API de bots de Telegram con un token que vive SOLO en
el servidor (variable de entorno), nunca en el codigo ni en el navegador.
"""
from __future__ import annotations

from datetime import date

import requests

from .calendar import build_calendar
from .config import Config, env
from .store import Dataset
from .summary import month_name, n

MAX_LEN = 3800


def build_bulletin(cfg: Config, ds: Dataset, zone_key: str | None = None, years_back: int = 3) -> str:
    """Arma el texto del boletin con cifras calculadas, sin inventar nada."""
    zone_key = zone_key or cfg.default_zone
    bbox = cfg.zone_bbox(zone_key)
    payload = build_calendar(
        cfg, ds, bbox, ds.start, ds.end,
        granularity="month", measure=cfg.default_measure, sources="both",
        zone_name=cfg.zone_name(zone_key),
    )
    cards = payload["cards"]
    cal = payload["calendar"]
    lines = [f"*PyroChronos · {payload['meta']['zone']}*"]
    lines.append(f"Datos NASA FIRMS hasta {payload['meta']['coverage']['end']} (histórico, no tiempo real).")

    if cards.get("season"):
        season = cards["season"]
        lines.append(f"· Temporada de fuego: *{season['label']}* (pico en {season['peak_name']}).")
    elif cards.get("most_active_month"):
        lines.append(f"· Temporada de fuego: el mes con más actividad es *{cards['most_active_month']['name']}*.")
    if cards.get("most_active_year"):
        lines.append(f"· Año más activo del registro: *{cards['most_active_year']['period_year']}*.")

    last = cards.get("last_month")
    if last:
        delta = last.get("delta_pct")
        if delta is None:
            lines.append(f"· Último mes con datos: {last['name']} de {last['period_year']} (sin historial suficiente).")
        else:
            sign = "+" if delta > 0 else ""
            lines.append(
                f"· Último mes con datos: {last['name']} de {last['period_year']} "
                f"({sign}{delta:.0f}% frente a la mediana histórica: {last['level_label']})."
            )

    # periodos marcados como altos o extremos en los ultimos anos con datos
    years = cal["years"]
    recent_years = years[-years_back:]
    flagged = []
    for yi, y in enumerate(years):
        if y not in recent_years:
            continue
        for xi, level in enumerate(cal["levels"][yi]):
            if level in ("alto", "extremo"):
                value = cal["values"][yi][xi]
                flagged.append((y, xi + 1, level, value))
    if flagged:
        lines.append("· Periodos fuera de lo normal en los últimos años con datos:")
        for y, month, level, value in sorted(flagged, key=lambda t: (t[0], t[1]))[-6:]:
            mark = "◆" if level == "extremo" else "▲"
            lines.append(f"   {mark} {month_name(month)} de {y}: {n(value)} celdas-día")
    else:
        lines.append("· Sin periodos marcados como fuera de lo normal en los últimos años con datos.")

    lines.append("")
    lines.append(f"Focos registrados en toda la serie: {n(cards.get('total_detections'))}.")
    lines.append("_Resumen del calendario histórico armonizado MODIS+VIIRS. No sustituye un aviso oficial._")
    text = "\n".join(lines)
    return text[:MAX_LEN]


def send_telegram(
    text: str, token: str | None = None, chat_id: str | None = None, parse_mode: str | None = "Markdown"
) -> dict:
    """Envia el texto. Si Telegram rechaza el formato, reintenta en texto plano.

    Un mensaje sin negritas sigue siendo util; un mensaje que no llega, no.
    (Telegram devuelve 400 "can't parse entities" si el Markdown esta mal formado.)
    """
    token = token or env("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or env("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("faltan TELEGRAM_BOT_TOKEN y/o TELEGRAM_CHAT_ID en el entorno")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}
    if parse_mode:
        data["parse_mode"] = parse_mode
    r = requests.post(url, data=data, timeout=30)
    if r.status_code == 400 and parse_mode:
        data.pop("parse_mode", None)
        r = requests.post(url, data=data, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Telegram respondio {r.status_code}: {r.text[:200]}")
    return r.json()
