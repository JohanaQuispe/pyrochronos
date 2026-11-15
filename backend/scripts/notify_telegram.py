#!/usr/bin/env python3
"""Envia (o simula) el boletin de una zona a un chat de Telegram.

    export TELEGRAM_BOT_TOKEN=...   # solo en tu maquina o en el servidor
    export TELEGRAM_CHAT_ID=...
    python backend/scripts/notify_telegram.py --zone madrededios --dry-run
    python backend/scripts/notify_telegram.py --zone madrededios --send
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyro.config import load_config  # noqa: E402
from pyro.notify import build_bulletin, send_telegram  # noqa: E402
from pyro.store import load_dataset  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone", default=None)
    ap.add_argument("--years-back", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true", default=True, help="solo imprime el mensaje (por defecto)")
    ap.add_argument("--send", dest="dry_run", action="store_false", help="envia de verdad")
    args = ap.parse_args()

    cfg = load_config()
    ds = load_dataset(cfg)
    text = build_bulletin(cfg, ds, args.zone, args.years_back)
    print(text)
    if args.dry_run:
        print("\n(modo simulacion: no se envio nada. Usa --send para enviar de verdad)")
        return 0
    send_telegram(text)
    print("\nEnviado a Telegram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
