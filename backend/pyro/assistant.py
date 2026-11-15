"""Respuestas acotadas compartidas por la web y el bot; no es un modelo de IA."""
from __future__ import annotations

import unicodedata

from . import nrt
from .alerts import build_alert
from .config import Config
from .store import Dataset


def _normalize(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))


def answer_question(text: str, cfg: Config, ds: Dataset, bbox, zone_name: str, recent_selector=None) -> str:
    question = _normalize(text.strip())
    if any(word in question for word in ('viento', 'ruta', 'carretera', 'propagacion', 'vivienda', 'agua', 'hidrante')):
        return ('No tengo viento puntual, rutas ni cercanía a viviendas o agua. Consulta fuentes operativas '
                'y verifica en campo; no puedo indicar una ruta segura ni cómo se propagará el fuego.')
    if any(word in question for word in ('temporada', 'semaforo', 'estacional', 'historico', 'historia', 'calendario')):
        alert = build_alert(cfg, ds, bbox, zone_name, recent_selector=recent_selector)
        if not alert.get('available', True):
            return f"{zone_name}: no hay historial suficiente para este cálculo. No es un pronóstico de incendios."
        return (f"{zone_name}: {alert.get('label', 'sin información')}. "
                f"{alert.get('reasons', [''])[1] if len(alert.get('reasons', [])) > 1 else ''} "
                "Es una referencia histórica, no indica focos activos ni predice incendios. "
                "Las cifras armonizadas están en revisión.")
    if any(word in question for word in ('foco', 'incendio', 'fuego', 'calor', 'punto', 'ocurriendo', 'pasando', 'actual', 'reciente', 'alerta', 'hay algo')):
        recent = nrt.stats(cfg, bbox, selector=recent_selector) if recent_selector else nrt.stats(cfg, bbox)
        info = recent.get('meta') or {}
        fetched = info.get('fetched_at') or 'fecha de descarga desconocida'
        if not recent.get('available'):
            return (f"{zone_name}: no hay datos recientes cargados. No significa que no haya focos. "
                    "Las alertas dependen de una descarga FIRMS correcta y del bot en ejecución.")
        try:
            w, s, e, n = info['bbox']
            covered = w <= bbox[0] and s <= bbox[1] and e >= bbox[2] and n >= bbox[3]
        except (KeyError, TypeError, ValueError):
            covered = False
        coverage_note = '' if covered else ' La descarga no tiene cobertura completa verificada de esta zona.'
        proximity_note = ' No conozco tu ubicación en esta consulta y no puedo calcular cercanía.' if 'cerca' in question else ''
        return (f"{zone_name}: {recent.get('total', 0)} detecciones en el archivo reciente guardado. "
                f"Última descarga: {fetched}; última fecha de detección: {recent.get('last_day') or info.get('last_day') or 'desconocida'}. "
                f"{coverage_note}{proximity_note} Puede estar desactualizado y no equivale a incendios confirmados. Verifica la fecha y confirma en campo.")
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
