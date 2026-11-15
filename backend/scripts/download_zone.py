#!/usr/bin/env python3
"""Descarga una zona cualquiera (o los ultimos meses) con la API 'area' de FIRMS.

Necesita FIRMS_MAP_KEY en el entorno. Trocea el rango en bloques de 5 dias
(el maximo que acepta el servicio), guarda cada bloque y se puede reanudar.

Uso:
    export FIRMS_MAP_KEY=...
    python backend/scripts/download_zone.py --bbox -70.6,-13.4,-68.6,-11 --years 2025-2026
    python backend/scripts/download_zone.py --recent 120            # ultimos 120 dias, Peru

Cada archivo de salida sigue el formato de FIRMS, para que build_dataset.py lo lea igual.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pyro.config import env, load_config, ROOT  # noqa: E402

API = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
MAX_DAYS = 5
SOURCES = {"modis": "MODIS_SP", "viirs": "VIIRS_SNPP_SP"}


def fetch_window(key: str, source: str, bbox: str, start: date, days: int) -> tuple[requests.Response, str]:
    url = f"{API}/{key}/{source}/{bbox}/{days}/{start.isoformat()}"
    return requests.get(url, timeout=180), url


def main() -> int:
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", default=None, help="oeste,sur,este,norte (por defecto, la zona de config)")
    ap.add_argument("--zone", default=None, help="nombre de zona de config.yaml (ej. madrededios)")
    ap.add_argument("--sources", default="modis,viirs")
    ap.add_argument("--years", default=None, help="ej. 2026 o 2025-2026")
    ap.add_argument("--recent", type=int, default=0, help="ultimos N dias hasta hoy")
    ap.add_argument("--out", default="data/raw")
    ap.add_argument("--pause", type=float, default=1.2, help="segundos entre consultas")
    args = ap.parse_args()

    key = env("FIRMS_MAP_KEY")
    if not key:
        print("ERROR: falta FIRMS_MAP_KEY en el entorno (ver .env.example)", file=sys.stderr)
        return 2

    if args.bbox:
        bbox = args.bbox
    else:
        w, s, e, n = cfg.zone_bbox(args.zone)
        bbox = f"{w},{s},{e},{n}"
    area = 1.0
    w, s, e, n = (float(x) for x in bbox.split(","))
    area = (e - w) * (n - s)
    if area > cfg.max_area_deg2:
        print(f"ERROR: la zona es demasiado grande ({area:.0f} grados²).", file=sys.stderr)
        return 3

    today = date.today()
    if args.recent:
        start_all = today - timedelta(days=args.recent)
        end_all = today
    elif args.years:
        a, _, b = args.years.partition("-")
        start_all = date(int(a), 1, 1)
        end_all = date(int(b or a), 12, 31)
    else:
        start_all, end_all = cfg.overlap_start, today

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    progress_path = out / "progress_zone.json"
    progress = json.loads(progress_path.read_text()) if progress_path.exists() else {}
    tag = f"{abs(hash(bbox)) % 100000:05d}"

    total = 0
    for short in [x.strip() for x in args.sources.split(",") if x.strip()]:
        source = SOURCES[short]
        per_year: dict[int, list[str]] = {}
        cursor = start_all
        while cursor <= end_all:
            days = min(MAX_DAYS, (end_all - cursor).days + 1)
            token = f"{short}:{cursor.isoformat()}"
            if progress.get(token) == "ok":
                cursor += timedelta(days=days)
                continue
            try:
                resp, url = fetch_window(key, source, bbox, cursor, days)
                if resp.status_code == 200 and "Invalid MAP_KEY" not in resp.text[:200]:
                    lines = resp.text.strip().splitlines()
                    body = lines[1:] if lines else []
                    if body:
                        per_year.setdefault(cursor.year, []).append("\n".join(body))
                    total += len(body)
                    progress[token] = "ok"
                else:
                    progress[token] = f"error {resp.status_code}: {resp.text[:120]}"
                    print(f"  !! {cursor} -> {progress[token]}")
            except Exception as exc:
                progress[token] = f"error: {exc}"
                print(f"  !! {cursor} -> {exc}")
            progress_path.write_text(json.dumps(progress, indent=2))
            cursor += timedelta(days=days)
            time.sleep(args.pause)

        header = ("latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,"
                  "confidence,version,bright_t31,frp,daynight,type")
        head_viirs = ("latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,"
                      "confidence,version,bright_ti5,frp,daynight,type")
        for year, chunks in per_year.items():
            dest = out / f"{short if short == 'modis' else 'viirs-snpp'}_{year}_zone{tag}.csv"
            with open(dest, "w", encoding="utf-8") as fh:
                fh.write((header if short == "modis" else head_viirs) + "\n")
                fh.write("\n".join("\n".join(c) for c in chunks) + "\n")
            print(f"  escrito {dest.name}")

    print(f"\n{total} detecciones nuevas. Reconstruye la tabla con:\n  python backend/scripts/build_dataset.py --raw {out}")
    print(f"(config del proyecto: {ROOT})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
