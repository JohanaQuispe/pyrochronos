#!/usr/bin/env python3
"""Construye la tabla de detecciones a partir de los CSV crudos de FIRMS.

Uso:
    python backend/scripts/build_dataset.py --raw /ruta/a/los/csv
    python backend/scripts/build_dataset.py --raw data/raw --pattern modis

Los CSV crudos se descargan con download_history.py (archivos anuales por pais)
o download_zone.py (cualquier zona, con MAP_KEY).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from pyro.config import ROOT, load_config  # noqa: E402
from pyro import normalize  # noqa: E402
from pyro.store import write_dataset  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Normaliza los CSV de FIRMS y guarda un parquet")
    ap.add_argument("--raw", default=str(ROOT / "data/raw"), help="carpeta con los CSV crudos")
    ap.add_argument("--pattern", default="", help="filtro de nombre, ej. 'modis' o 'viirs'")
    ap.add_argument("--out", default=None, help="ruta del parquet de salida")
    ap.add_argument("--device", action="store_true", help="solo diagnostico: no escribe nada")
    args = ap.parse_args()

    cfg = load_config()
    raw = Path(args.raw)
    if not raw.exists():
        print(f"ERROR: no existe la carpeta {raw}", file=sys.stderr)
        return 2

    print(f"Leyendo CSV de {raw} (patron '{args.pattern or '*'}', zona {cfg.zone_name()})...")
    df = normalize.load_raw_directory(
        raw, pattern=args.pattern, min_conf_modis=cfg.min_conf_modis, bbox=cfg.zone_bbox()
    )
    before = len(df)
    df = normalize.filter_quality(
        df, min_conf_modis=cfg.min_conf_modis, exclude_types=cfg.exclude_types, drop_low_viirs=True
    )
    print(f"  detecciones leidas: {before:,}  tras control de calidad: {len(df):,}")
    if df.empty:
        print("ERROR: no quedo ninguna deteccion. Revisa el patron y la configuracion.", file=sys.stderr)
        return 3

    days = df["day"].to_numpy()
    d0 = pd.Timestamp("1970-01-01") + pd.to_timedelta(int(days.min()), unit="D")
    d1 = pd.Timestamp("1970-01-01") + pd.to_timedelta(int(days.max()), unit="D")
    per_source = df.groupby("source").size().to_dict()
    print(f"  rango: {d0.date()} .. {d1.date()}   por satelite: {per_source}")

    if args.device:
        print("Modo diagnostico: no se escribio nada.")
        return 0

    out = Path(args.out) if args.out else cfg.data_file
    info = write_dataset(
        df,
        out,
        meta={
            "zone": cfg.zone_name(),
            "bbox": list(cfg.zone_bbox()),
            "cell_deg": cfg.cell_deg,
            "source_version": f"{d0.date()}_{d1.date()}",
            "quality": {
                "min_conf_modis": cfg.min_conf_modis,
                "min_conf_viirs": cfg.min_conf_viirs,
                "exclude_types": cfg.exclude_types,
            },
        },
    )
    print(f"Guardado {out} ({out.stat().st_size/1e6:.1f} MB, {info['rows']:,} filas, sha {info['sha256']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
