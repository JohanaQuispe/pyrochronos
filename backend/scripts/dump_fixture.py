#!/usr/bin/env python3
"""Genera un payload de calendario en JSON para las pruebas de humo del frontend.

    python backend/scripts/dump_fixture.py --zone peru --granularity month \
        --out frontend/scripts/fixtures/calendar-month.json

Así las pruebas de humo no dependen de archivos temporales ni de la red.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyro.calendar import build_calendar  # noqa: E402
from pyro.config import ROOT, load_config  # noqa: E402
from pyro.store import load_dataset  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone", default="peru")
    ap.add_argument("--granularity", default="month", choices=["month", "week"])
    ap.add_argument("--out", default=str(ROOT / "frontend" / "scripts" / "fixtures" / "calendar-month.json"))
    args = ap.parse_args()

    cfg = load_config()
    ds = load_dataset(cfg)
    payload = build_calendar(
        cfg, ds, cfg.zone_bbox(args.zone), ds.start, ds.end,
        granularity=args.granularity, measure=cfg.default_measure, sources="both",
        zone_name=cfg.zone_name(args.zone),
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{out} · {out.stat().st_size / 1024:.1f} KB · años {len(payload['calendar']['years'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
