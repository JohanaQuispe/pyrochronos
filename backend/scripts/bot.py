#!/usr/bin/env python3
"""Bot de campo de PyroChronos: geocercas, pines y validación humana.

Usa la Bot API de Telegram con `requests` (sin librerías extra). Hace tres cosas:

  1. /start  -> pide tu ubicación con un botón (geocerca de 10 km por defecto).
  2. Cuando un foco CRÍTICO (FRP sobre el percentil 95 de su sensor en la zona)
     cae dentro de tu radio: manda texto con distancia y rumbo, un pin
     (sendLocation, abre Waze/Google Maps) y tres botones de validación.
  3. Guarda tu veredicto (fuego real / quema agrícola / falsa alarma).

Lo que NO hace: no detecta incendios, no predice, no sustituye un aviso oficial.
Los focos salen de `recent.parquet`, que se descarga aparte con
`download_recent.py`. Si no hay datos recientes, el bot lo dice y no inventa nada.

    python backend/scripts/bot.py --dry-run        # mensaje de ejemplo, sin red
    python backend/scripts/bot.py --send-demo      # manda ese ejemplo (marcado DEMO)
    python backend/scripts/bot.py --poll           # escucha y avisa (bucle)
    python backend/scripts/bot.py --poll --once    # una pasada y sale
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyro import geofence, groundtruth, nrt  # noqa: E402
from pyro.config import Config, env, load_config  # noqa: E402
from pyro.store import Dataset, load_dataset  # noqa: E402

API = "https://api.telegram.org/bot{token}/{method}"
POLL_TIMEOUT = 25
SOURCE_LABELS = {1: "MODIS", 2: "VIIRS", 3: "VIIRS"}

WELCOME = (
    "*PyroChronos · modo campo*\n"
    "Te aviso cuando un foco de calor intenso caiga dentro de tu radio.\n\n"
    "1. Pulsa el botón de abajo y comparte tu ubicación.\n"
    "2. Cuando llegue un aviso, confirma qué es con los tres botones.\n\n"
    "_Es una detección satelital, no un aviso oficial: confirma antes de movilizar._"
)
HELP = (
    "/start — activar el aviso y compartir ubicación\n"
    "/estado — tu geocerca y cuántos focos vigilo\n"
    "/radio 15 — cambiar el radio a 15 km\n"
    "/ayuda — esta ayuda"
)


class Telegram:
    """Cliente mínimo de la Bot API. El token nunca se imprime."""

    def __init__(self, token: str):
        self.token = token

    def call(self, method: str, **params) -> dict:
        r = requests.post(API.format(token=self.token, method=method), json=params, timeout=30)
        try:
            body = r.json()
        except ValueError:
            body = {"ok": False, "description": f"HTTP {r.status_code} sin JSON"}
        if not body.get("ok"):
            raise RuntimeError(f"Telegram {method}: {body.get('description', 'error')}")
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


def location_keyboard() -> dict:
    return {
        "keyboard": [[{"text": "📍 Compartir mi ubicación", "request_location": True}]],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def zone_hotspots(cfg: Config, ds: Dataset, zone: str) -> "object":
    """Focos históricos de la zona (sirve para el umbral FRP y para el ejemplo)."""
    import pandas as pd

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


def check_alerts(cfg: Config, tg: Telegram, zone: str, dataset: Dataset) -> int:
    """Revisa focos recientes y avisa a cada geocerca. Devuelve cuántos envió."""
    recent, meta = nrt.load_recent(cfg)
    if recent is None or recent.empty:
        return 0
    w, s, e, n = cfg.zone_bbox(zone)
    inside = recent[(recent["lat"] >= s) & (recent["lat"] <= n) & (recent["lon"] >= w) & (recent["lon"] <= e)]
    if inside.empty:
        return 0
    hist = zone_hotspots(cfg, dataset, zone)
    marked = geofence.mark_critical(inside, history=hist)
    marked = marked.reset_index(drop=True)
    marked["hotspot_id"] = [
        f"nrt-{int(r.day)}-{r.lat:.3f}-{r.lon:.3f}-{int(r.source)}" for r in marked.itertuples()
    ]
    sent = 0
    for fence in groundtruth.active_geofences(cfg):
        hits = geofence.nearest(marked, fence["lat"], fence["lon"], fence.get("radius_km", 10.0))
        for _, hit in hits.iterrows():
            hit = hit.to_dict()
            if groundtruth.already_sent(cfg, fence["telegram_id"], hit["hotspot_id"]):
                continue
            text = geofence.alert_text(hit, fence.get("radius_km", 10.0), zone=cfg.zone_name(zone))
            kb = geofence.inline_keyboard(hit["hotspot_id"])
            tg.text(fence["telegram_id"], text, kb)
            try:
                tg.location(fence["telegram_id"], float(hit["lat"]), float(hit["lon"]))
            except RuntimeError:
                pass  # el pin es un extra: si falla, el texto ya llegó
            groundtruth.mark_sent(cfg, fence["telegram_id"], hit["hotspot_id"])
            sent += 1
    return sent


def handle_message(cfg: Config, tg: Telegram, msg: dict, dataset: Dataset, zone: str) -> None:
    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()
    if "location" in msg:
        loc = msg["location"]
        rec = groundtruth.save_geofence(cfg, chat_id, loc["latitude"], loc["longitude"], 10.0)
        tg.text(
            chat_id,
            f"✅ *Geocerca activada*\nRadio: {rec['radius_km']:.0f} km\n"
            f"Centro: {rec['lat']:.4f}, {rec['lon']:.4f}\n\n"
            "Te aviso cuando un foco crítico caiga dentro. Puedes cambiarlo con /radio 15.",
            {"remove_keyboard": True},
        )
        return
    if text.startswith("/start"):
        tg.text(chat_id, WELCOME, location_keyboard())
        return
    if text.startswith("/ayuda"):
        tg.text(chat_id, HELP)
        return
    if text.startswith("/radio"):
        parts = text.split()
        try:
            new_radius = float(parts[1].replace(",", "."))
            if not 1 <= new_radius <= 100:
                raise ValueError
        except (IndexError, ValueError):
            tg.text(chat_id, "Uso: /radio 15  (entre 1 y 100 km)")
            return
        fences = groundtruth.load_geofences(cfg)
        current = fences.get(str(chat_id))
        if not current:
            tg.text(chat_id, "Primero comparte tu ubicación con /start.")
            return
        groundtruth.save_geofence(cfg, chat_id, current["lat"], current["lon"], new_radius)
        tg.text(chat_id, f"Radio actualizado a {new_radius:.0f} km.")
        return
    if text.startswith("/estado"):
        fences = groundtruth.load_geofences(cfg)
        mine = fences.get(str(chat_id))
        recent, meta = nrt.load_recent(cfg)
        n_recent = 0 if recent is None else int(len(recent))
        summary = groundtruth.verdict_summary(cfg)
        lines = ["*Tu estado*"]
        if mine:
            lines.append(f"Geocerca: {mine['radius_km']:.0f} km en {mine['lat']:.4f}, {mine['lon']:.4f}")
        else:
            lines.append("Sin geocerca todavía: usa /start y comparte tu ubicación.")
        lines.append(f"Focos recientes cargados: {n_recent}")
        if recent is None:
            lines.append("_No hay datos recientes: ejecuta download_recent.py en el servidor._")
        lines.append(f"Validaciones en campo: {summary['total']}")
        for code, count in summary["counts"].items():
            lines.append(f"  · {geofence.VERDICTS[code]}: {count}")
        tg.text(chat_id, "\n".join(lines))
        return
    tg.text(chat_id, "No entiendo ese mensaje.\n\n" + HELP, location_keyboard())


def handle_callback(cfg: Config, tg: Telegram, cb: dict) -> None:
    parsed = geofence.parse_callback(cb.get("data", ""))
    if not parsed:
        tg.call("answerCallbackQuery", callback_query_id=cb["id"], text="No entendí esa opción.")
        return
    hotspot_id, verdict = parsed
    try:
        groundtruth.save_verdict(cfg, hotspot_id, cb["from"]["id"], verdict)
    except ValueError as exc:
        tg.call("answerCallbackQuery", callback_query_id=cb["id"], text=str(exc)[:200], show_alert=True)
        return
    label = geofence.VERDICTS[verdict]
    tg.call("answerCallbackQuery", callback_query_id=cb["id"], text=f"Registrado: {label}")
    chat_id = cb.get("message", {}).get("chat", {}).get("id")
    if chat_id:
        summary = groundtruth.verdict_summary(cfg)
        tg.text(chat_id, f"✅ Guardado: *{label}*\nValidaciones en este equipo: {summary['total']}")


def poll(cfg: Config, tg: Telegram, dataset: Dataset, zone: str, interval: int, once: bool) -> int:
    try:
        tg.call("setMyCommands", commands=[
            {"command": "start", "description": "Activar aviso y compartir ubicación"},
            {"command": "estado", "description": "Mi geocerca y focos vigilados"},
            {"command": "radio", "description": "Cambiar el radio (ej. /radio 15)"},
            {"command": "ayuda", "description": "Qué puedo hacer"},
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
                sent = check_alerts(cfg, tg, zone, dataset)
                if sent:
                    print(f"{sent} aviso(s) enviados")
            except Exception as exc:
                print(f"no pude revisar focos: {exc}", file=sys.stderr)
            last_check = time.time()
        if once:
            return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Bot de campo de PyroChronos (geocercas y validación).")
    ap.add_argument("--zone", default=None, help="zona de config.yaml (por defecto la principal)")
    ap.add_argument("--dry-run", action="store_true", help="imprime el aviso de ejemplo sin enviar nada")
    ap.add_argument("--send-demo", action="store_true", help="envía el ejemplo marcado como DEMO")
    ap.add_argument("--poll", action="store_true", help="escucha mensajes y avisa (por defecto si no hay otra acción)")
    ap.add_argument("--once", action="store_true", help="una sola pasada y sale")
    ap.add_argument("--interval", type=int, default=300, help="segundos entre revisiones de focos")
    args = ap.parse_args(argv)

    cfg = load_config()
    ds = load_dataset(cfg)
    zone = args.zone or cfg.default_zone

    if args.dry_run:
        row, top = sample_alert(cfg, ds, zone)
        print("=== Aviso de ejemplo (foco histórico, no de hoy) ===")
        print(geofence.alert_text(row, 10.0, zone=cfg.zone_name(zone)))
        print("\nBotones:", [b[0]["text"] for b in geofence.inline_keyboard(row["hotspot_id"])["inline_keyboard"]])
        print(f"\nUmbral FRP p95 en {cfg.zone_name(zone)}: {row['frp_p95']:.0f} MW · FRP del ejemplo: {float(row['frp']):.0f} MW")
        print(f"Otros focos críticos recientes-últimos en la zona: {len(top)}")
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
        tg.text(chat_id, banner + geofence.alert_text(row, 10.0, zone=cfg.zone_name(zone)),
                geofence.inline_keyboard(row["hotspot_id"]))
        tg.location(chat_id, float(row["lat"]), float(row["lon"]))
        print("Demo enviada. Pulsa un botón en Telegram y luego --poll --once para verlo guardado.")
        return 0

    return poll(cfg, tg, ds, zone, args.interval, args.once)


if __name__ == "__main__":
    raise SystemExit(main())
