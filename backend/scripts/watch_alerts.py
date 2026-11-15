#!/usr/bin/env python3
"""Vigilancia automatica: revisa el semaforo y avisa por Telegram cuando sube de nivel.

Pensado para correr cada hora (cron o un bucle con --loop):

    export FIRMS_MAP_KEY=...            # para los focos recientes (opcional)
    export TELEGRAM_BOT_TOKEN=...
    export TELEGRAM_CHAT_ID=...
    python backend/scripts/watch_alerts.py --zone madrededios --send
    python backend/scripts/watch_alerts.py --zones peru,madrededios --loop 3600 --send

Reglas honestas:
  - Solo avisa cuando el nivel sube respecto del ultimo aviso guardado.
  - Nunca dice "incendio detectado en X minutos" si no hay datos recientes cargados.
  - Guarda estado en data/derived/alert_state.json para no repetir el mismo aviso.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyro.alerts import build_alert  # noqa: E402
from pyro.config import ROOT, env, load_config  # noqa: E402
from pyro.notify import send_telegram  # noqa: E402
from pyro.store import load_dataset  # noqa: E402

STATE = ROOT / "data" / "derived" / "alert_state.json"
ICON = {"critico": "🔴", "vigilancia": "🟠", "normal": "🟢"}


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def message(zone_name: str, alert: dict) -> str:
    lines = [
        f"{ICON.get(alert['level'], '')} *PyroChronos · {zone_name}*",
        f"Semáforo: *{alert['label']}* (semana {alert['week']}, pico histórico semana {alert['peak_week']})",
        "",
    ]
    lines += [f"· {r}" for r in alert["reasons"]]
    lines += ["", f"*Qué hacer:* {alert['action']}", "", f"_{alert['disclaimer']}_"]
    return "\n".join(lines)


def run_once(cfg, ds, zones: list[str], send: bool, force: bool) -> int:
    state = load_state()
    sent = 0
    for key in zones:
        alert = build_alert(cfg, ds, cfg.zone_bbox(key), cfg.zone_name(key))
        prev = state.get(key, {}).get("severity", -1)
        state.setdefault(key, {})
        state[key].update(
            {
                "severity": alert["severity"],
                "level": alert["level"],
                "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        )
        print(f"{key}: {alert['level']} (antes {prev}) - {alert['reasons'][-1]}")
        if alert["severity"] > prev or force:
            text = message(cfg.zone_name(key), alert)
            if send:
                try:
                    send_telegram(text)
                    sent += 1
                    print("  enviado a Telegram")
                except Exception as exc:
                    print(f"  no se pudo enviar: {exc}")
            else:
                print("  (simulacion) se enviaria:\n" + text)
    save_state(state)
    return sent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone", default=None)
    ap.add_argument("--zones", default=None, help="lista separada por comas")
    ap.add_argument("--send", dest="send", action="store_true", help="enviar de verdad")
    ap.add_argument("--force", action="store_true", help="avisar aunque el nivel no haya subido")
    ap.add_argument("--loop", type=int, default=0, help="segundos entre revisiones (0 = una vez)")
    args = ap.parse_args()

    cfg = load_config()
    ds = load_dataset(cfg)
    zones = [z.strip() for z in (args.zones or args.zone or cfg.default_zone).split(",") if z.strip()]
    if args.send and not (env("TELEGRAM_BOT_TOKEN") and env("TELEGRAM_CHAT_ID")):
        print("ERROR: para --send faltan TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID", file=sys.stderr)
        return 2

    while True:
        run_once(cfg, ds, zones, args.send, args.force)
        if not args.loop:
            return 0
        print(f"\n... esperando {args.loop} s (Ctrl+C para salir)\n")
        time.sleep(args.loop)


if __name__ == "__main__":
    raise SystemExit(main())
