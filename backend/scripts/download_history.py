#!/usr/bin/env python3
"""Descarga el historial completo de un pais desde NASA FIRMS.

Usa los archivos anuales por pais (sin MAP_KEY, procesamiento estandar):
    https://firms.modaps.eosdis.nasa.gov/data/country/{producto}/{anio}/{producto}_{anio}_{Pais}.csv

Es reanudable: si el archivo ya existe y no esta vacio, no se vuelve a pedir.
Un 404 significa "ese anio todavia no esta publicado" y se informa sin romper.

Uso:
    python backend/scripts/download_history.py --country Peru --years 2000-2025
    python backend/scripts/download_history.py --country Peru --products modis
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import requests

BASE = "https://firms.modaps.eosdis.nasa.gov/data/country"
PRODUCTS = {
    "modis": {"slug": "modis", "first_year": 2000},
    "viirs-snpp": {"slug": "viirs-snpp", "first_year": 2012},
}


def download(url: str, dest: Path, retries: int = 3) -> str:
    """Devuelve 'ok', 'existe', 'no-publicado' o el error."""
    if dest.exists() and dest.stat().st_size > 500:
        return "existe"
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, timeout=180)
            if r.status_code == 404:
                return "no-publicado"
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            if b"latitude" not in r.content[:200]:
                raise RuntimeError("el archivo no parece un CSV de FIRMS")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.content)
            return "ok"
        except Exception as exc:  # reintento con espera creciente
            if attempt == retries:
                return f"error: {exc}"
            time.sleep(2 * attempt)
    return "error"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--country", default="Peru", help="nombre en ingles como lo escribe FIRMS")
    ap.add_argument("--years", default="2000-2025")
    ap.add_argument("--products", default="modis,viirs-snpp")
    ap.add_argument("--out", default="data/raw")
    args = ap.parse_args()

    a, _, b = args.years.partition("-")
    years = list(range(int(a), int(b or a) + 1))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    for product in [p.strip() for p in args.products.split(",") if p.strip()]:
        info = PRODUCTS[product]
        for year in years:
            if year < info["first_year"]:
                continue
            name = f"{info['slug']}_{year}_{args.country}.csv"
            dest = out / name
            url = f"{BASE}/{info['slug']}/{year}/{name}"
            status = download(url, dest)
            if status == "ok":
                blob = dest.read_bytes()
                manifest[name] = {
                    "url": url,
                    "bytes": len(blob),
                    "sha256": hashlib.sha256(blob).hexdigest(),
                    "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                print(f"  ok   {name} ({len(blob)/1e6:.1f} MB)")
            elif status == "existe":
                print(f"  ya    {name}")
            elif status == "no-publicado":
                print(f"  404   {name} (todavia no publicado)")
            else:
                print(f"  !!    {name}: {status}")
            manifest_path.write_text(json.dumps(manifest, indent=2))
            time.sleep(0.3)

    print(f"\nListo. Archivos en {out}. Manifiesto: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
