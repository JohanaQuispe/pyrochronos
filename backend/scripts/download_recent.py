#!/usr/bin/env python3
"""Descarga los focos de las ultimas horas/dias (NRT) para una zona.

    export FIRMS_MAP_KEY=...
    python backend/scripts/download_recent.py --zone peru --days 3
    python backend/scripts/download_recent.py --bbox -70.6,-13.4,-68.6,-11 --days 5

Los datos se guardan en data/derived/recent.parquet (aparte de la serie historica).
Latencia tipica de las fuentes NRT: ~3 horas desde el paso del satelite.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyro import nrt  # noqa: E402
from pyro.config import env, load_config  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone", default=None)
    ap.add_argument("--bbox", default=None, help="oeste,sur,este,norte")
    ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--sources", default=",".join(nrt.NRT_SOURCES))
    args = ap.parse_args()

    cfg = load_config()
    if not env("FIRMS_MAP_KEY"):
        print("ERROR: falta FIRMS_MAP_KEY en el entorno (ver .env.example)", file=sys.stderr)
        return 2
    if args.bbox:
        bbox = tuple(float(x) for x in args.bbox.split(","))
    else:
        bbox = cfg.zone_bbox(args.zone)
    sources = tuple(s.strip() for s in args.sources.split(",") if s.strip())

    print(f"Descargando {args.days} dia(s) para {bbox} desde {sources} ...")
    df = nrt.fetch_recent(cfg, bbox, days=args.days, sources=sources)
    if df.empty:
        print("Sin detecciones nuevas (o la API no respondio). No se sobrescriben datos previos.")
        return 1
    meta = nrt.save_recent(cfg, df, sources, args.days)
    print(f"Guardado {meta['rows']} detecciones ({meta['first_day']} .. {meta['last_day']}) en {nrt.recent_path(cfg)}")
    print("La web ya puede mostrarlas: /api/recent y el semaforo de temporada las usan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
