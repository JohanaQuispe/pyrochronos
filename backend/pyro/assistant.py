"""Respuestas acotadas compartidas por la web y el bot; no es un modelo de IA."""
from __future__ import annotations

import unicodedata
from datetime import date, datetime, timedelta, timezone

from . import nrt
from .alerts import build_alert
from .config import Config
from .store import Dataset


def _normalize(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))


def _download_time(value, now=None):
    """Fecha legible en hora de Perú; la frescura solo se confirma con zona horaria explícita."""
    try:
        stamp = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            raise ValueError('falta zona horaria')
        stamp = stamp.astimezone(timezone.utc)
        local = stamp.astimezone(timezone(timedelta(hours=-5)))
        current = now or datetime.now(timezone.utc)
        age = current - stamp
        fresh = timedelta(0) <= age <= timedelta(hours=6)
        return local.strftime('%d/%m/%Y a las %H:%M') + ' (hora de Perú)', fresh
    except (TypeError, ValueError, OverflowError):
        return 'fecha desconocida', False


def _utc_day(value):
    try:
        return date.fromisoformat(str(value)).strftime('%d/%m/%Y') + ' (fecha UTC)'
    except (TypeError, ValueError):
        return 'no disponible para esta zona'


def answer_question(text: str, cfg: Config, ds: Dataset, bbox, zone_name: str, recent_selector=None, language: str = 'es') -> str:
    question = _normalize(text.strip())
    if language == 'en':
        return _answer_english(question, cfg, ds, bbox, zone_name, recent_selector)
    if any(word in question for word in ('viento', 'ruta', 'carretera', 'propagacion', 'vivienda', 'agua', 'hidrante')):
        return ('No tengo viento puntual, rutas ni cercanía a viviendas o agua. Consulta fuentes operativas '
                'y verifica en campo; no puedo indicar una ruta segura ni cómo se propagará el fuego.')
    if any(word in question for word in ('temporada', 'semaforo', 'estacional', 'historico', 'historia', 'calendario')):
        alert = build_alert(cfg, ds, bbox, zone_name, recent_selector=recent_selector)
        if not alert.get('available', True):
            return f"{zone_name}: no hay historial suficiente para este cálculo. No es un pronóstico de incendios."
        return (f"{zone_name}: {alert.get('label', 'sin información')}. "
                f"{alert.get('reasons', [''])[1] if len(alert.get('reasons', [])) > 1 else ''} "
                "El indicador también incorpora detecciones recientes si están disponibles; no confirma incendios activos ni los predice. "
                "Las cifras armonizadas están en revisión.")
    if any(word in question for word in ('foco', 'incendio', 'fuego', 'calor', 'punto', 'ocurriendo', 'pasando', 'actual', 'reciente', 'alerta', 'hay algo')):
        recent = nrt.stats(cfg, bbox, selector=recent_selector) if recent_selector else nrt.stats(cfg, bbox)
        info = recent.get('meta') or {}
        if not recent.get('available'):
            return (f"📍 Zona: {zone_name}\n\n"
                    "No hay datos recientes cargados. Esto no significa que no haya focos de calor.\n"
                    "Comprueba que el bot esté encendido y pueda descargar datos de NASA FIRMS.")
        try:
            w, s, e, n = (float(x) for x in info['bbox'])
            covered = w <= bbox[0] and s <= bbox[1] and e >= bbox[2] and n >= bbox[3]
        except (KeyError, TypeError, ValueError, OverflowError):
            covered = False
        downloaded, fresh = _download_time(info.get('fetched_at'))
        count = f"{int(recent.get('total') or 0):,}".replace(',', ' ')
        days = info.get('days')
        period = f" de los últimos {days} días solicitados" if isinstance(days, int) and not isinstance(days, bool) and 1 <= days <= 10 else ''
        lines = [f"📍 Zona consultada: {zone_name}",
                 f"🛰️ La última descarga guardada contiene {count} detecciones de calor en esta zona{period}.",
                 f"📥 Descarga: {downloaded}.",
                 f"📅 Fecha de la detección más reciente en esta zona: {_utc_day(recent.get('last_day'))}."]
        if not covered:
            lines.append('⚠️ No se ha comprobado que la descarga cubra toda esta zona.')
        if not fresh:
            lines.append('⚠️ La descarga puede estar desactualizada; comprueba la conexión y actualiza los datos.')
        if 'cerca' in question:
            lines.append('Esta consulta resume la zona; no calcula qué tan cerca están de tu ubicación.')
        lines.append('Una detección de calor no confirma un incendio y no indica que siga activo. Verifica en campo y con fuentes oficiales.')
        return '\n'.join(lines)
    if any(word in question for word in ('telegram', 'aviso', 'bot', 'notifica', 'notificacion')):
        return ('Para recibir avisos en Telegram, abre el bot, comparte tu ubicación y elige la distancia. '
                'El bot debe estar ejecutándose y los datos FIRMS deben actualizarse. Solo avisa focos '
                'dentro del radio que superan el umbral de FRP, no todos los incendios.')
    if any(word in question for word in ('modis', 'viirs', 'satelite', 'datos', 'sensores')):
        return (f"Datos históricos disponibles: {ds.start} a {ds.end}; {len(ds.df):,} detecciones MODIS y VIIRS. "
                "Son focos de calor, no incendios confirmados. Las cifras armonizadas están en revisión.")
    return ('Puedo responder preguntas concretas sobre focos recientes, temporada histórica, satélites '
            'y cómo funcionan los avisos. No soy una IA de conversación ni puedo confirmar incendios. '
            'Prueba: ¿Hay focos recientes?')


def _answer_english(question, cfg, ds, bbox, zone_name, recent_selector=None):
    """Limited English templates; no claim to be a conversational AI."""
    if any(word in question for word in ('wind', 'route', 'road', 'spread', 'house', 'water', 'hydrant')):
        return ('I do not have local wind, routes, or distance to homes or water. Consult operational sources '
                'and verify in the field; I cannot recommend a safe route or predict fire spread.')
    if any(word in question for word in ('season', 'histor', 'calendar', 'temporada', 'historico', 'calendario')):
        alert = build_alert(cfg, ds, bbox, zone_name, recent_selector=recent_selector)
        if not alert.get('available', True):
            return f'{zone_name}: there is not enough historical data. This is not a fire forecast.'
        label = {'critico': 'Critical seasonal window', 'vigilancia': 'Seasonal watch', 'normal': 'Outside peak season'}.get(alert.get('level'), 'No information')
        return (f"{zone_name}: {label}. The historical peak is in week {alert.get('peak_week', 'unknown')}. "
                'The indicator also incorporates recent detections when available; it is not a forecast or confirmation of active fires. Harmonized results remain provisional.')
    if any(word in question for word in ('telegram', 'bot', 'notif', 'avis', 'receive')):
        return ('To receive Telegram alerts, share your location with the bot and choose a distance. '
                'The bot must be running and FIRMS data must be updated. Alerts are sent only for nearby '
                'detections above the thermal intensity threshold, not for every fire.')
    if any(word in question for word in ('hotspot', 'fire', 'heat', 'recent', 'current', 'alert', 'foco', 'incendio', 'fuego', 'reciente', 'alerta')):
        recent = nrt.stats(cfg, bbox, selector=recent_selector) if recent_selector else nrt.stats(cfg, bbox)
        info = recent.get('meta') or {}
        if not recent.get('available'):
            return (f'{zone_name}: no recent data are loaded. This does not mean there are no hotspots. '
                    'Check that the bot is running and can download NASA FIRMS data.')
        try:
            w, s, e, n = (float(x) for x in info['bbox'])
            covered = w <= bbox[0] and s <= bbox[1] and e >= bbox[2] and n >= bbox[3]
        except (KeyError, TypeError, ValueError, OverflowError):
            covered = False
        try:
            stamp = datetime.fromisoformat(str(info.get('fetched_at')).replace('Z', '+00:00'))
            if stamp.tzinfo is None:
                raise ValueError('timezone missing')
            local = stamp.astimezone(timezone(timedelta(hours=-5)))
            downloaded = local.strftime('%d/%m/%Y %H:%M') + ' (Peru time)'
        except (TypeError, ValueError, OverflowError):
            downloaded = 'unknown'
        _, fresh = _download_time(info.get('fetched_at'))
        days = info.get('days')
        period = f' in the requested last {days} days' if isinstance(days, int) and not isinstance(days, bool) and 1 <= days <= 10 else ''
        lines = [f'📍 Area: {zone_name}',
                 f"🛰️ The stored download contains {int(recent.get('total') or 0):,} heat detections in this area{period}.",
                 f'📥 Downloaded: {downloaded}.',
                 f"📅 Latest detection date in this area: {recent.get('last_day') or 'unavailable'} (UTC date)."]
        if not covered:
            lines.append('⚠️ Full coverage of this area has not been verified.')
        if not fresh:
            lines.append('⚠️ Data may be outdated; check the connection and refresh.')
        if 'near' in question or 'cerca' in question:
            lines.append('This summary covers the area; it does not calculate distance from your location.')
        lines.append('A heat detection is not a confirmed fire and may no longer be active. Verify in the field and with official sources.')
        return '\n'.join(lines)
    if any(word in question for word in ('modis', 'viirs', 'satellite', 'data', 'sensor', 'datos', 'satelite')):
        return (f'Historical data: {ds.start} to {ds.end}; {len(ds.df):,} MODIS and VIIRS detections. '
                'These are heat detections, not confirmed fires. Harmonized results remain provisional.')
    return ('I can answer specific questions about recent hotspots, historical seasons, satellites and alerts. '
            'I am not a conversational AI and cannot confirm fires. Try: Are there recent hotspots?')
