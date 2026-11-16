"""Geocercas: matematica de distancia y armado del aviso tactico.

Aqui NO hay red ni Telegram: solo funciones puras (distancia, rumbo, filtro de
focos criticos y texto del mensaje) para poder probarlas sin conexion.

Honestidad: un "foco critico" es una deteccion con FRP alto comparada con el
propio historico de la zona. Sigue siendo una deteccion satelital: el mensaje
pide confirmar en campo antes de movilizar a nadie.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

EARTH_R_KM = 6371.0088
DEFAULT_RADIUS_KM = 10.0

# Veredictos de validacion humana ("ground truth") que viajan en callback_data
VERDICTS: dict[str, str] = {
    "fuego_real": "🔥 Fuego real",
    "quema_agricola": "🌾 Quema agrícola",
    "falsa_alarma": "❌ Falsa alarma",
}

_COMPASS = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en km sobre la esfera (formula del semiverseno)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R_KM * math.asin(min(1.0, math.sqrt(a)))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Rumbo inicial en grados (0 = norte, 90 = este)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def compass(deg: float) -> str:
    """Convierte un rumbo en punto cardinal en espanol."""
    return _COMPASS[int((deg % 360) / 45 + 0.5) % 8]


def critical_threshold(df: pd.DataFrame, quantile: float = 0.95, by: str | None = "source") -> float:
    """Umbral de FRP a partir del propio historico (cuantil del FRP observado)."""
    if df is None or df.empty or "frp" not in df:
        return float("nan")
    frp = pd.to_numeric(df["frp"], errors="coerce").dropna()
    if frp.empty:
        return float("nan")
    return float(np.quantile(frp.to_numpy(), quantile))


def mark_critical(
    df: pd.DataFrame,
    history: pd.DataFrame | None = None,
    quantile: float = 0.95,
    min_frp: float = 20.0,
) -> pd.DataFrame:
    """Marca focos con FRP por encima del cuantil del historico de la zona.

    `history` es la serie armonizada (o los focos historicos) de la misma zona;
    si no se pasa, el umbral se calcula con la propia tabla.
    Devuelve una copia con `critical` (bool) y `frp_p95` (float).
    """
    if df is None or df.empty:
        out = df.copy() if df is not None else pd.DataFrame()
        if not out.empty:
            out["critical"] = pd.Series(dtype=bool)
            out["frp_p95"] = float("nan")
        return out
    ref = history if history is not None and not history.empty else df
    out = df.copy()
    out["frp_p95"] = np.nan
    if "source" in out.columns and "source" in ref.columns:
        for source, group in out.groupby("source"):
            thr = critical_threshold(ref[ref["source"] == source], quantile)
            out.loc[group.index, "frp_p95"] = thr
    else:
        out["frp_p95"] = critical_threshold(ref, quantile)
    frp = pd.to_numeric(out["frp"], errors="coerce")
    out["critical"] = (frp >= out["frp_p95"]) & (frp >= float(min_frp))
    return out


def nearest(
    df: pd.DataFrame,
    lat: float,
    lon: float,
    radius_km: float = DEFAULT_RADIUS_KM,
    only_critical: bool = True,
    limit: int = 5,
) -> pd.DataFrame:
    """Focos dentro del radio, ordenados por distancia, con rumbo y cardinal."""
    if df is None or df.empty:
        cols = list(df.columns) + ["distance_km", "bearing_deg", "cardinal"] if df is not None else []
        return pd.DataFrame(columns=cols)
    work = df[df["critical"]] if only_critical and "critical" in df.columns else df
    if work.empty:
        return work.head(0)
    work = work.copy()
    work["distance_km"] = [
        haversine_km(lat, lon, float(r.lat), float(r.lon)) for r in work.itertuples()
    ]
    work = work[work["distance_km"] <= float(radius_km)].copy()
    if work.empty:
        return work.head(0)
    work["bearing_deg"] = [
        bearing_deg(lat, lon, float(r.lat), float(r.lon)) for r in work.itertuples()
    ]
    work["cardinal"] = work["bearing_deg"].map(compass)
    return work.sort_values("distance_km").head(limit).reset_index(drop=True)


def alert_text(row: dict | pd.Series, radius_km: float = DEFAULT_RADIUS_KM, zone: str | None = None, language: str = 'es') -> str:
    """Texto del aviso: cifras reales, sin adjetivos de mas."""
    if language == 'en':
        return _alert_text_english(row, zone)
    get = row.get if isinstance(row, dict) else (lambda k, d=None: row[k] if k in row else d)
    dist = float(get("distance_km", float("nan")))
    card = get("cardinal", "")
    frp = float(get("frp", float("nan")))
    p95 = float(get("frp_p95", float("nan")))
    day = get("day_label", "")
    if not day:
        raw_day = get("day")
        try:
            day = str(pd.to_datetime(int(raw_day), unit="D", utc=True).date())
        except (TypeError, ValueError, OverflowError):
            day = "fecha no disponible"
    time_utc = get("time_utc", "")
    sensor = get("sensor") or {1: "MODIS", 2: "VIIRS"}.get(get("source"), "satélite")
    conf = get("conf_label") or {0: "baja", 1: "nominal", 2: "alta"}.get(get("conf_level"), "no disponible")
    lines = ["🚨 *Aviso: detección de calor cercana*", "Un satélite detectó una señal de calor que cumple el criterio de intensidad del bot."]
    if zone:
        lines.append(f"Zona vigilada: {zone}")
    if math.isfinite(dist):
        lines.append(f"📍 A {dist:.1f} km al {card} de la ubicación que compartiste (distancia en línea recta).")
    try:
        lat, lon = float(get("lat")), float(get("lon"))
        if math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180:
            coords = f"{lat:.4f},{lon:.4f}"
            lines.append(f"Coordenadas: `{lat:.4f}, {lon:.4f}`")
            lines.append(f"Mapa: https://www.google.com/maps/search/?api=1&query={coords}")
    except (TypeError, ValueError):
        pass
    when = " ".join(str(x) for x in (day, time_utc) if x)
    lines.append(f"🛰️ Detectado: {when} (UTC) · {sensor} · confianza {conf}")
    if not time_utc:
        lines.append("Hora de detección no disponible; fecha UTC.")
    if math.isfinite(frp):
        frp_txt = f"Intensidad térmica (FRP): {frp:.0f} MW"
        if math.isfinite(p95):
            frp_txt += f"; umbral histórico de este sensor: {p95:.0f} MW"
        lines.append(frp_txt)
    lines.append("Este aviso se basa en intensidad térmica y distancia; no mide cercanía a viviendas ni riesgo de propagación.")
    lines.append("No tenemos datos de viento ni acceso. Consulta fuentes operativas antes de actuar.")
    lines.append("")
    lines.append("_No es un incendio confirmado ni un aviso oficial. Confirma en campo antes de movilizar._")
    return "\n".join(lines)


def _alert_text_english(row, zone=None):
    get = row.get
    lines = ['🚨 *Alert: nearby heat detection*', 'A satellite detected a heat signal that meets the bot’s intensity threshold.']
    if zone:
        lines.append(f'Monitored area: {zone}')
    try:
        distance = float(get('distance_km', float('nan')))
        if math.isfinite(distance):
            cardinal = get('cardinal', '')
            cardinal = {'O': 'W', 'SO': 'SW', 'NO': 'NW'}.get(cardinal, cardinal)
            lines.append(f"📍 {distance:.1f} km {cardinal} of your shared location (straight-line distance).")
    except (TypeError, ValueError):
        pass
    try:
        lat, lon = float(get('lat')), float(get('lon'))
        if math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180:
            lines.append(f'Coordinates: `{lat:.4f}, {lon:.4f}`')
            lines.append(f'Map: https://www.google.com/maps/search/?api=1&query={lat:.4f},{lon:.4f}')
    except (TypeError, ValueError):
        pass
    day = get('day_label')
    if not day:
        try:
            day = str(pd.to_datetime(int(get('day')), unit='D', utc=True).date())
        except (TypeError, ValueError, OverflowError):
            day = 'date unavailable'
    time_utc = get('time_utc') or ''
    sensor = get('sensor') or {1: 'MODIS', 2: 'VIIRS'}.get(get('source'), 'satellite')
    conf = {0: 'low', 1: 'nominal', 2: 'high'}.get(get('conf_level'), 'unavailable')
    lines.append(f'🛰️ Detected: {day} {time_utc} (UTC) · {sensor} · confidence {conf}')
    if not time_utc:
        lines.append('Detection time unavailable; date is UTC.')
    try:
        frp, threshold = float(get('frp', float('nan'))), float(get('frp_p95', float('nan')))
        if math.isfinite(frp):
            lines.append(f'Thermal intensity (FRP): {frp:.0f} MW' + (f'; sensor historical threshold: {threshold:.0f} MW' if math.isfinite(threshold) else ''))
    except (TypeError, ValueError):
        pass
    lines.append('This alert is based on thermal intensity and distance; it does not measure proximity to homes or risk of spread.')
    lines.append('Wind and access information are unavailable. Consult operational sources before acting.')
    lines.append('_Not a confirmed fire or official warning. Verify in the field before dispatching._')
    return '\n'.join(lines)


EN_VERDICTS = {'fuego_real': '🔥 Real fire', 'quema_agricola': '🌾 Agricultural burn', 'falsa_alarma': '❌ False alarm'}


def inline_keyboard(hotspot_id: int | str, language: str = 'es') -> dict:
    """Tres botones de validación en campo (callback_data corto: límite 64 bytes)."""
    labels = EN_VERDICTS if language == 'en' else VERDICTS
    return {
        "inline_keyboard": [
            [{"text": label, "callback_data": f"gt:{hotspot_id}:{code}"}]
            for code, label in labels.items()
        ]
    }


def parse_callback(data: str) -> tuple[str, str] | None:
    """Devuelve (hotspot_id, veredicto) o None si el dato no es válido."""
    parts = str(data or "").split(":")
    if len(parts) != 3 or parts[0] != "gt":
        return None
    hot_id, verdict = parts[1], parts[2]
    if verdict not in VERDICTS or not hot_id:
        return None
    return hot_id, verdict
