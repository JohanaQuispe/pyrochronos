#!/usr/bin/env python3
"""Imprime el semaforo de temporada de una zona (y opcionalmente lo envia por Telegram)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyro.alerts import build_alert  # noqa: E402
from pyro.config import load_config  # noqa: E402
from pyro.store import load_dataset  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone", default=None)
    ap.add_argument("--weeks", type=int, default=4)
    args = ap.parse_args()
    cfg = load_config()
    ds = load_dataset(cfg)
    key = args.zone or cfg.default_zone
    alert = build_alert(cfg, ds, cfg.zone_bbox(key), cfg.zone_name(key), lookahead_weeks=args.weeks)
    print(f"[{alert['label'].upper()}] {cfg.zone_name(key)}")
    for reason in alert["reasons"]:
        print("  -", reason)
    print("\nQué hacer:", alert["action"])
    print("\n" + alert["disclaimer"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
