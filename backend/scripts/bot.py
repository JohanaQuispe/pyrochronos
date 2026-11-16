#!/usr/bin/env python3
"""Bot de campo de PyroChronos: avisos de fuego cerca de ti, en lenguaje llano.

Pensado para un bombero o un guardaparque, no para un ingeniero:

  · Se usa con TRES botones, sin escribir comandos.
  · No habla de "geocercas" ni de "radios": habla de "aquí" y de "a cuántos km".
  · Cuando un foco intenso cae cerca, manda dónde está, a qué distancia y tres
    botones para decir qué era.

Funciona igual en un chat privado y en un grupo: la posición se guarda por
PERSONA y los avisos se envían al chat donde compartió la ubicación.

    python backend/scripts/bot.py --dry-run        # mensaje de ejemplo, sin red
    python backend/scripts/bot.py --send-demo      # manda ese ejemplo (marcado DEMO)
    python backend/scripts/bot.py --poll           # escucha y avisa (bucle)
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyro import assistant, geofence, groundtruth, nrt  # noqa: E402
from pyro.config import Config, env, load_config  # noqa: E402
from pyro.store import Dataset, load_dataset  # noqa: E402

API = "https://api.telegram.org/bot{token}/{method}"
POLL_TIMEOUT = 25
SOURCE_LABELS = {1: "MODIS", 2: "VIIRS", 3: "VIIRS"}
RADIUS_CHOICES = (5, 10, 20, 50)
DEFAULT_RADIUS = 10.0

WELCOME = (
    "*PyroChronos · apoyo a la brigada*\n"
    "Puedo avisar de focos de calor con FRP elevado cerca de ti si hay datos recientes cargados "
    "y estoy funcionando. Una detección no confirma un incendio.\n\n"
    "1️⃣ Pulsa *📍 Compartir mi ubicación* (una sola vez).\n"
    "2️⃣ Cuando llegue un aviso, dime qué era con los botones.\n"
    "3️⃣ Si quieres avisos más lejos o más cerca, pulsa *⚙️ Distancia de aviso*.\n\n"
    "_Es una detección de satélite, no un aviso oficial._"
)
HELP = (
    "*Cómo se usa*\n"
    "📍 *Compartir mi ubicación* — me dices dónde estás.\n"
    "⚙️ *Distancia de aviso* — a cuántos km a la redonda te aviso (5, 10, 20 o 50).\n"
    "ℹ️ *Mi estado* — dónde estás, tu distancia y cuántos fuegos vigilo.\n"
    "❓ *Ayuda* — este texto.\n\n"
    "También funcionan los comandos: /distancia 15, /estado, /ayuda.\n\n"
    "_En un grupo, todos ven la ubicación que compartas; si te importa la privacidad, "
    "compártela en el chat privado del bot._"
)


class Telegram:
    """Cliente mínimo de la Bot API. El token nunca se imprime."""

    def __init__(self, token: str):
        self.token = token

    def call(self, method: str, **params) -> dict:
        try:
            r = requests.post(API.format(token=self.token, method=method), json=params, timeout=30)
        except requests.RequestException:
            raise RuntimeError(f"Telegram {method}: error de conexión") from None
        try:
            body = r.json()
        except ValueError:
            body = {"ok": False, "description": f"HTTP {r.status_code} sin JSON"}
        if not body.get("ok"):
            description = str(body.get('description', 'error')).replace(self.token, '***')
            raise RuntimeError(f"Telegram {method}: {description}")
        return body.get("result", {})

    def text(self, chat_id, text: str, keyboard: dict | None = None) -> dict:
        params = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown",
                  "disable_web_page_preview": True}
        if keyboard:
            params["reply_markup"] = keyboard
        try:
            return self.call("sendMessage", **params)
        except RuntimeError:
            params.pop("parse_mode", None)  # reintento en texto plano
            return self.call("sendMessage", **params)

    def location(self, chat_id, lat: float, lon: float, keyboard: dict | None = None) -> dict:
        params = {"chat_id": chat_id, "latitude": float(lat), "longitude": float(lon)}
        if keyboard:
            params["reply_markup"] = keyboard
        return self.call("sendLocation", **params)


def main_keyboard(language: str = 'es') -> dict:
    """Botones grandes en el idioma elegido."""
    if language == 'en':
        return {'keyboard': [[{'text': '📍 Share my location', 'request_location': True}],
                             [{'text': '⚙️ Alert distance'}, {'text': 'ℹ️ My status'}],
                             [{'text': '❓ Help'}]], 'resize_keyboard': True, 'is_persistent': True}
    return {
        "keyboard": [
            [{"text": "📍 Compartir mi ubicación", "request_location": True}],
            [{"text": "⚙️ Distancia de aviso"}, {"text": "ℹ️ Mi estado"}],
            [{"text": "❓ Ayuda"}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def radius_keyboard(current: float | None = None) -> dict:
    row = [
        {"text": f"{km} km{' ✓' if current and abs(current - km) < 0.01 else ''}", "callback_data": f"r:{km}"}
        for km in RADIUS_CHOICES
    ]
    return {"inline_keyboard": [row]}


def normalize_command(text: str) -> str:
    """Deja el texto limpio: sin `/comando@bot`, sin caracteres invisibles."""
    clean = (text or "").replace("\u200b", "").replace("\u2060", "").strip()
    return re.sub(r"^(/\w+)@\w+", r"\1", clean)


def parse_radius(text: str) -> float | None:
    """Acepta «15», «15 km», «15km», «/distancia 15», «/radio@bot 15»."""
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:km|kms)?", normalize_command(text))
    if not match:
        return None
    try:
        value = float(match.group(1).replace(",", "."))
    except ValueError:
        return None
    return value if 1 <= value <= 100 else None


def zone_hotspots(cfg: Config, ds: Dataset, zone: str):
    """Focos históricos de la zona (sirven para el umbral de intensidad)."""
    w, s, e, n = cfg.zone_bbox(zone)
    df = ds.df
    mask = (df["lat"] >= s) & (df["lat"] <= n) & (df["lon"] >= w) & (df["lon"] <= e)
    return df.loc[mask]


def sample_alert(cfg: Config, ds: Dataset, zone: str) -> tuple[dict, list]:
    """Aviso de ejemplo con un foco histórico real (para --dry-run y --send-demo)."""
    import pandas as pd

    hist = zone_hotspots(cfg, ds, zone)
    marked = geofence.mark_critical(hist, history=hist)
    critical = marked[marked["critical"]].sort_values("day", ascending=False)
    row = (critical.iloc[0] if not critical.empty else hist.sort_values("day", ascending=False).iloc[0]).to_dict()
    row["sensor"] = SOURCE_LABELS.get(int(row.get("source", 2)), "satélite")
    row["day_label"] = str(pd.to_datetime(int(row["day"]), unit="D").date())
    row["conf_label"] = "alta" if int(row.get("conf_level", 1)) >= 2 else "nominal"
    row["distance_km"] = 6.4
    row["bearing_deg"] = 63.0
    row["cardinal"] = geofence.compass(63.0)
    row["hotspot_id"] = f"hist-{int(row['day'])}-{row['lat']:.3f}"
    return row, critical.head(3).to_dict("records")


def register_location(cfg: Config, tg: Telegram, msg: dict) -> None:
    """Guarda dónde está la persona y le confirma en lenguaje llano."""
    loc = msg["location"]
    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    user_id = (msg.get("from") or {}).get("id", chat_id)
    previous = groundtruth.load_geofences(cfg).get(str(user_id), {})
    radius = float(previous.get("radius_km", DEFAULT_RADIUS))
    rec = groundtruth.save_geofence(
        cfg, user_id, loc["latitude"], loc["longitude"], radius,
        name=(msg.get("from") or {}).get("first_name"),
        chat_id=chat_id,
    )
    is_group = chat.get("type") in ("group", "supergroup")
    language = rec.get('language', 'es')
    if language == 'en':
        text = (f"✅ *Saved*\nI can alert you about qualifying heat detections within *{rec['radius_km']:.0f} km* of this location.\n\n"
                "Tap *⚙️ Alert distance* to change it.")
        if is_group:
            text += '\n\n_Everyone in this group can see the location you shared._'
    else:
        text = (f"✅ *Listo*\nTe aviso de detecciones de calor que cumplan el criterio a menos de *{rec['radius_km']:.0f} km* de aquí.\n\n"
                "Toca *⚙️ Distancia de aviso* para cambiarlo.")
        if is_group:
            text += "\n\n_En este grupo todos ven la ubicación que compartiste._"
    tg.text(chat_id, text, main_keyboard(language))


def show_state(cfg: Config, tg: Telegram, chat_id, user_id) -> None:
    fences = groundtruth.load_geofences(cfg)
    mine = fences.get(str(user_id))
    recent, meta = nrt.load_recent(cfg)
    summary = groundtruth.verdict_summary(cfg)
    language = (mine or {}).get('language', 'es')
    if language == 'en':
        lines = ['*Your status*']
        if mine and mine.get('lat') is not None and mine.get('lon') is not None:
            lines.append(f"📍 Shared location: {mine['lat']:.4f}, {mine['lon']:.4f}")
            lines.append(f"📏 Alert distance: *{mine['radius_km']:.0f} km*")
        else:
            lines.append('📍 No location yet: tap *Share my location*.')
        if recent is None:
            lines.append('Recent data: none loaded; this does not mean there are no hotspots.')
        else:
            lines.append(f"Detections in stored NRT file: {len(recent)}; downloaded: {meta.get('fetched_at') or 'unknown'}.")
            lines.append('The file may be outdated and does not confirm fires.')
        lines.append(f"✅ Team reports saved: {summary['total']}")
        for code, count in summary['counts'].items():
            if count:
                lines.append(f"   {geofence.EN_VERDICTS[code]}: {count}")
        tg.text(chat_id, '\n'.join(lines), main_keyboard(language))
        return
    lines = ["*Tu estado*"]
    if mine and mine.get('lat') is not None and mine.get('lon') is not None:
        lines.append(f"📍 Estás en: {mine['lat']:.4f}, {mine['lon']:.4f}")
        lines.append(f"📏 Te aviso hasta *{mine['radius_km']:.0f} km* a la redonda")
    else:
        lines.append("📍 Todavía no sé dónde estás: pulsa *Compartir mi ubicación*.")
    if recent is None:
        lines.append("Focos recientes: sin datos cargados; esto no significa ausencia de focos.")
    else:
        lines.append(f"Focos en el archivo NRT: {len(recent)}; descarga: {meta.get('fetched_at') or 'fecha desconocida'}.")
        lines.append("El archivo puede estar desactualizado; no confirma incendios.")
    lines.append(f"✅ Confirmaciones registradas en el equipo: {summary['total']}")
    for code, count in summary["counts"].items():
        if count:
            lines.append(f"   {geofence.VERDICTS[code]}: {count}")
    tg.text(chat_id, "\n".join(lines), main_keyboard())


def handle_message(cfg: Config, tg: Telegram, msg: dict, dataset: Dataset, zone: str) -> None:
    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    user_id = (msg.get("from") or {}).get("id", chat_id)
    raw = msg.get("text") or ""
    text = normalize_command(raw).lower()
    if text.startswith(('/language', '/idioma')):
        parts = text.split()
        if len(parts) != 2 or parts[1] not in ('en', 'es'):
            tg.text(chat_id, 'Elige /language en o /idioma es · Choose /language en or /idioma es.')
        else:
            language = parts[1]
            groundtruth.set_language(cfg, user_id, language)
            tg.text(chat_id, 'Language set to English.' if language == 'en' else 'Idioma cambiado a español.', main_keyboard(language))
        return
    language = groundtruth.load_geofences(cfg).get(str(user_id), {}).get('language', 'es')

    if "location" in msg:
        register_location(cfg, tg, msg)
        return

    if language == 'en':
        _handle_english_message(cfg, tg, text, raw, chat_id, user_id, dataset, zone)
        return

    # Botones y sinónimos, en lenguaje llano
    if text.startswith("/start") or text.startswith("/empezar") or "ubicaci" in text:
        tg.text(chat_id, WELCOME, main_keyboard())
        return
    if text.startswith("/ayuda") or "ayuda" in text:
        tg.text(chat_id, HELP, main_keyboard())
        return
    if "distancia" in text or text.startswith("/radio") or text.startswith("/distancia"):
        current = groundtruth.load_geofences(cfg).get(str(user_id), {}).get("radius_km")
        value = parse_radius(text)
        if value is None:
            tg.text(
                chat_id,
                f"¿A cuántos km a la redonda quieres los avisos?\n"
                f"Elige un botón (ahora: *{current:.0f} km*)." if current else
                "¿A cuántos km a la redonda quieres los avisos? Elige un botón:",
                radius_keyboard(current),
            )
            return
        rec = groundtruth.set_radius(cfg, user_id, value) or {}
        if rec.get("lat") is None:
            tg.text(chat_id, f"Guardado: *{value:.0f} km*. Ahora pulsa *📍 Compartir mi ubicación* "
                             "y empiezo a avisarte.", main_keyboard())
        else:
            tg.text(chat_id, f"Listo: te aviso hasta *{value:.0f} km* a la redonda.", main_keyboard())
        return
    if text.startswith("/estado") or "estado" in text:
        show_state(cfg, tg, chat_id, user_id)
        return
    reply = assistant.answer_question(raw, cfg, dataset, cfg.zone_bbox(zone), cfg.zone_name(zone))
    tg.text(chat_id, reply, main_keyboard())


def _handle_english_message(cfg, tg, text, raw, chat_id, user_id, dataset, zone):
    keyboard = main_keyboard('en')
    if text.startswith('/start') or 'share my location' in text:
        tg.text(chat_id, '*PyroChronos · field support*\nI can alert you about nearby heat detections above an intensity threshold when the bot is running and recent data are loaded. A detection does not confirm a fire.\n\n1. Tap *📍 Share my location*.\n2. Choose an alert distance.\n3. Use the buttons to report what you found.\n\n_Not an official warning._', keyboard)
        return
    if text.startswith('/help') or 'help' in text:
        tg.text(chat_id, 'Share your location, choose an alert distance and check your status. Commands: /distance 15, /status, /language en or /idioma es. In a group everyone sees a shared location; use a private chat for privacy.', keyboard)
        return
    if 'distance' in text or text.startswith(('/distance', '/radio')):
        current = groundtruth.load_geofences(cfg).get(str(user_id), {}).get('radius_km')
        value = parse_radius(text)
        if value is None:
            tg.text(chat_id, 'How many kilometers away should alerts cover? Choose an option:', radius_keyboard(current))
            return
        rec = groundtruth.set_radius(cfg, user_id, value) or {}
        msg = f'Saved: *{value:.0f} km*. '
        msg += 'Now tap *📍 Share my location*.' if rec.get('lat') is None else 'Alerts cover this radius around your shared location.'
        tg.text(chat_id, msg, keyboard)
        return
    if text.startswith('/status') or 'my status' in text:
        show_state(cfg, tg, chat_id, user_id)
        return
    tg.text(chat_id, assistant.answer_question(raw, cfg, dataset, cfg.zone_bbox(zone), cfg.zone_name(zone), language='en'), keyboard)


def handle_callback(cfg: Config, tg: Telegram, cb: dict) -> None:
    data = str(cb.get("data") or "")
    user_id = (cb.get("from") or {}).get("id")
    chat_id = (cb.get("message") or {}).get("chat", {}).get("id")
    language = groundtruth.load_geofences(cfg).get(str(user_id), {}).get('language', 'es')

    if language == 'en':
        if data.startswith('r:'):
            try:
                value = float(data.split(':', 1)[1])
                if not 1 <= value <= 100:
                    raise ValueError('invalid radius')
            except ValueError:
                tg.call('answerCallbackQuery', callback_query_id=cb['id'], text='Invalid option.')
                return
            rec = groundtruth.set_radius(cfg, user_id, value) or {}
            tg.call('answerCallbackQuery', callback_query_id=cb['id'], text=f'Saved: {value:.0f} km')
            if chat_id:
                suffix = ' Now tap *📍 Share my location*.' if rec.get('lat') is None else ' Alerts cover this radius.'
                tg.text(chat_id, f'Saved: *{value:.0f} km*.' + suffix, main_keyboard('en'))
            return
        parsed = geofence.parse_callback(data)
        if not parsed:
            tg.call('answerCallbackQuery', callback_query_id=cb['id'], text='Unknown option.')
            return
        hotspot_id, verdict = parsed
        groundtruth.save_verdict(cfg, hotspot_id, user_id, verdict)
        label = geofence.EN_VERDICTS[verdict]
        tg.call('answerCallbackQuery', callback_query_id=cb['id'], text=f'Recorded: {label}')
        if chat_id:
            tg.text(chat_id, f"✅ Saved: *{label}*\nTeam reports: {groundtruth.verdict_summary(cfg)['total']}")
        return

    # Cambio de distancia desde los botones
    if data.startswith("r:"):
        try:
            value = float(data.split(":", 1)[1])
        except ValueError:
            tg.call("answerCallbackQuery", callback_query_id=cb["id"], text="Opción no válida.")
            return
        rec = groundtruth.set_radius(cfg, user_id, value) or {}
        if rec.get("lat") is None:
            tg.call("answerCallbackQuery", callback_query_id=cb["id"], text=f"Guardado: {value:.0f} km")
            if chat_id:
                tg.text(chat_id, f"Guardado: *{value:.0f} km*. Ahora pulsa *📍 Compartir mi ubicación*.",
                        main_keyboard())
            return
        tg.call("answerCallbackQuery", callback_query_id=cb["id"], text=f"Guardado: {value:.0f} km")
        if chat_id:
            tg.text(chat_id, f"Listo: te aviso hasta *{value:.0f} km* a la redonda.", main_keyboard())
        return

    parsed = geofence.parse_callback(data)
    if not parsed:
        tg.call("answerCallbackQuery", callback_query_id=cb["id"], text="No entendí esa opción.")
        return
    hotspot_id, verdict = parsed
    try:
        groundtruth.save_verdict(cfg, hotspot_id, user_id, verdict)
    except ValueError as exc:
        tg.call("answerCallbackQuery", callback_query_id=cb["id"], text=str(exc)[:200], show_alert=True)
        return
    label = geofence.VERDICTS[verdict]
    tg.call("answerCallbackQuery", callback_query_id=cb["id"], text=f"Registrado: {label}")
    if chat_id:
        summary = groundtruth.verdict_summary(cfg)
        tg.text(chat_id, f"✅ Guardado: *{label}*\nConfirmaciones en el equipo: {summary['total']}")


def fresh_for_zone(meta: dict, bbox, now: datetime | None = None) -> bool:
    """No enviar un archivo antiguo, sin fecha o de una zona distinta como alerta nueva."""
    now = now or datetime.now(timezone.utc)
    try:
        fetched = datetime.fromisoformat(meta['fetched_at'].replace('Z', '+00:00'))
        if fetched.tzinfo is None:
            return False
        age = now - fetched.astimezone(timezone.utc)
        w, s, e, n = (float(x) for x in meta['bbox'])
        return timedelta(0) <= age <= timedelta(hours=6) and w <= bbox[0] and s <= bbox[1] and e >= bbox[2] and n >= bbox[3]
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def refresh_recent(cfg: Config, zone: str) -> dict:
    """Solo reemplaza la descarga tras obtener todas las fuentes sin error."""
    bbox = cfg.zone_bbox(zone)
    df = nrt.fetch_recent(cfg, bbox, days=3, sources=nrt.NRT_SOURCES, strict=True)
    return nrt.save_recent(cfg, df, nrt.NRT_SOURCES, 3, bbox=bbox)


def check_alerts(cfg: Config, tg: Telegram, zone: str, dataset: Dataset) -> int:
    """Avisa solo detecciones recientes y archivos frescos con cobertura conocida."""
    recent, meta = nrt.load_recent(cfg)
    bbox = cfg.zone_bbox(zone)
    if recent is None or recent.empty or not fresh_for_zone(meta, bbox):
        return 0
    w, s, e, n = bbox
    today = datetime.now(timezone.utc).date()
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc).date()
    latest_day = (today - epoch).days
    inside = recent[(recent["lat"] >= s) & (recent["lat"] <= n) & (recent["lon"] >= w) & (recent["lon"] <= e)
                    & (recent["day"] >= latest_day - 2) & (recent["day"] <= latest_day)]
    if inside.empty:
        return 0
    hist = zone_hotspots(cfg, dataset, zone)
    marked = geofence.mark_critical(inside, history=hist).reset_index(drop=True)
    marked["hotspot_id"] = [
        f"nrt-{int(r.day)}-{r.lat:.3f}-{r.lon:.3f}-{int(r.source)}" for r in marked.itertuples()
    ]
    sent = 0
    for fence in groundtruth.active_geofences(cfg):
        if fence.get("lat") is None or fence.get("lon") is None:
            continue
        target = str(fence.get("chat_id") or fence["telegram_id"])
        hits = geofence.nearest(marked, fence["lat"], fence["lon"], fence.get("radius_km", DEFAULT_RADIUS))
        for _, hit in hits.iterrows():
            hit = hit.to_dict()
            if groundtruth.already_sent(cfg, target, hit["hotspot_id"]):
                continue
            language = fence.get('language', 'es')
            tg.text(target, geofence.alert_text(hit, fence.get("radius_km", DEFAULT_RADIUS), zone=cfg.zone_name(zone), language=language),
                    geofence.inline_keyboard(hit["hotspot_id"], language=language))
            try:
                tg.location(target, float(hit["lat"]), float(hit["lon"]))
            except RuntimeError:
                pass  # el pin es un extra: Telegram aceptó el texto, pero no confirma lectura
            groundtruth.mark_sent(cfg, target, hit["hotspot_id"])
            sent += 1
    return sent


def diagnose_live(cfg: Config, dataset: Dataset, zone: str) -> dict:
    """Solo lectura: candidatos reales según los mismos filtros, sin enviar ni alterar deduplicación."""
    recent, meta = nrt.load_recent(cfg)
    bbox = cfg.zone_bbox(zone)
    fences = groundtruth.active_geofences(cfg)
    result = {'downloaded': recent is not None, 'fresh_and_covered': fresh_for_zone(meta, bbox),
              'fetched_at': meta.get('fetched_at'), 'fences': len(fences), 'matches': 0, 'new': 0}
    if recent is None or recent.empty or not result['fresh_and_covered']:
        return result
    w, s, e, n = bbox
    latest = (datetime.now(timezone.utc).date() - datetime(1970, 1, 1, tzinfo=timezone.utc).date()).days
    inside = recent[(recent['lat'] >= s) & (recent['lat'] <= n) & (recent['lon'] >= w) & (recent['lon'] <= e)
                    & (recent['day'] >= latest - 2) & (recent['day'] <= latest)]
    if inside.empty:
        return result
    marked = geofence.mark_critical(inside, history=zone_hotspots(cfg, dataset, zone)).reset_index(drop=True)
    marked['hotspot_id'] = [f'nrt-{int(r.day)}-{r.lat:.3f}-{r.lon:.3f}-{int(r.source)}' for r in marked.itertuples()]
    seen = set()
    for fence in fences:
        target = str(fence.get('chat_id') or fence['telegram_id'])
        hits = geofence.nearest(marked, fence['lat'], fence['lon'], fence.get('radius_km', DEFAULT_RADIUS))
        for _, hit in hits.iterrows():
            key = (target, hit['hotspot_id'])
            if key in seen:
                continue
            seen.add(key)
            result['matches'] += 1
            if not groundtruth.already_sent(cfg, target, hit['hotspot_id']):
                result['new'] += 1
    return result


def poll(cfg: Config, tg: Telegram, dataset: Dataset, zone: str, interval: int, once: bool,
         auto_refresh: bool = False) -> int:
    try:
        tg.call("setMyCommands", commands=[
            {"command": "start", "description": "Empezar y compartir mi ubicación"},
            {"command": "distancia", "description": "A cuántos km me avisas (ej. /distancia 15)"},
            {"command": "estado", "description": "Dónde estoy y qué vigilo"},
            {"command": "ayuda", "description": "Cómo se usa"},
        ])
    except RuntimeError as exc:
        print(f"aviso: no pude registrar los comandos ({exc})", file=sys.stderr)
    offset = None
    print(f"Escuchando… zona={zone} intervalo={interval}s (Ctrl+C para salir)")
    last_check = 0.0
    while True:
        try:
            params = {"timeout": POLL_TIMEOUT}
            if offset:
                params["offset"] = offset
            updates = tg.call("getUpdates", **params) or []
        except RuntimeError as exc:
            print(f"error de red, reintento en 5 s: {exc}", file=sys.stderr)
            time.sleep(5)
            continue
        for upd in updates:
            offset = int(upd["update_id"]) + 1
            try:
                if "message" in upd:
                    handle_message(cfg, tg, upd["message"], dataset, zone)
                elif "callback_query" in upd:
                    handle_callback(cfg, tg, upd["callback_query"])
            except Exception as exc:  # un update malo no debe tumbar el bot
                print(f"update ignorado: {exc}", file=sys.stderr)
        if time.time() - last_check >= interval:
            try:
                if auto_refresh:
                    info = refresh_recent(cfg, zone)
                    print(f"Datos FIRMS actualizados: {info['rows']} detecciones; fecha UTC {info['fetched_at']}")
                sent = check_alerts(cfg, tg, zone, dataset)
                if sent:
                    print(f"{sent} aviso(s) enviados")
            except Exception as exc:
                print(f"No pude actualizar o revisar focos; no se envían alertas en este ciclo: {nrt.redact(str(exc))}", file=sys.stderr)
            last_check = time.time()
        if once:
            return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Bot de campo de PyroChronos (avisos de fuego cerca de ti).")
    ap.add_argument("--zone", default=None, help="zona de config.yaml (por defecto la principal)")
    ap.add_argument("--dry-run", action="store_true", help="imprime el aviso de ejemplo sin enviar nada")
    ap.add_argument("--check-live", action="store_true", help="diagnostica candidatos reales guardados sin enviar ni cambiar estado")
    ap.add_argument("--send-demo", action="store_true", help="envía el ejemplo marcado como DEMO")
    ap.add_argument("--poll", action="store_true", help="escucha mensajes y avisa")
    ap.add_argument("--once", action="store_true", help="una sola pasada y sale")
    ap.add_argument("--interval", type=int, default=900, help="segundos entre revisiones de focos (mínimo 300)")
    ap.add_argument("--auto-refresh", action="store_true", help="actualiza FIRMS antes de cada revisión; requiere FIRMS_MAP_KEY")
    args = ap.parse_args(argv)
    if args.interval < 300:
        ap.error("--interval debe ser al menos 300 segundos")
    if args.auto_refresh and not env("FIRMS_MAP_KEY"):
        print("Falta FIRMS_MAP_KEY en .env; no se puede actualizar FIRMS automáticamente.", file=sys.stderr)
        return 2

    cfg = load_config()
    ds = load_dataset(cfg)
    zone = args.zone or cfg.default_zone

    if args.check_live:
        info = diagnose_live(cfg, ds, zone)
        print(f"Zona: {cfg.zone_name(zone)} · última descarga UTC: {info['fetched_at'] or 'desconocida'}")
        print(f"Archivo cargado: {'sí' if info['downloaded'] else 'no'} · fresco y cubre la zona: {'sí' if info['fresh_and_covered'] else 'no'}")
        print(f"Ubicaciones registradas: {info['fences']} · coincidencias con el criterio: {info['matches']} · pendientes de enviar: {info['new']}")
        print('Solo diagnóstico: no envía mensajes y no altera el historial. Una coincidencia no confirma que Telegram haya entregado una alerta.')
        return 0

    if args.dry_run:
        row, top = sample_alert(cfg, ds, zone)
        print("=== Aviso de ejemplo (foco histórico, no de hoy) ===")
        print(geofence.alert_text(row, DEFAULT_RADIUS, zone=cfg.zone_name(zone)))
        print("\nBotones:", [b[0]["text"] for b in geofence.inline_keyboard(row["hotspot_id"])["inline_keyboard"]])
        print(f"\nUmbral de intensidad en {cfg.zone_name(zone)}: {row['frp_p95']:.0f} MW · ejemplo: {float(row['frp']):.0f} MW")
        return 0

    token = env("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Falta TELEGRAM_BOT_TOKEN (mira python backend/scripts/telegram_setup.py --guide).")
        return 2
    tg = Telegram(token)

    if args.send_demo:
        chat_id = env("TELEGRAM_CHAT_ID")
        if not chat_id:
            print("Falta TELEGRAM_CHAT_ID: ejecuta telegram_setup.py --chat-id y --write-env.")
            return 2
        row, _ = sample_alert(cfg, ds, zone)
        banner = ("*DEMO* — este aviso usa un foco histórico de la zona "
                  f"({row['day_label']}), no una detección de hoy.\n\n")
        tg.text(chat_id, banner + geofence.alert_text(row, DEFAULT_RADIUS, zone=cfg.zone_name(zone)),
                geofence.inline_keyboard(row["hotspot_id"]))
        tg.location(chat_id, float(row["lat"]), float(row["lon"]))
        print("Demo enviada. Pulsa un botón en Telegram y luego --poll --once para verlo guardado.")
        return 0

    return poll(cfg, tg, ds, zone, args.interval, args.once, auto_refresh=args.auto_refresh)


if __name__ == "__main__":
    raise SystemExit(main())
