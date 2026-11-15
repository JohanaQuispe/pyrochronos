#!/usr/bin/env python3
"""Precarga el contexto de NASA POWER para una zona (sin clave de API).

    python backend/scripts/download_power.py --zone madrededios --years 5

Guarda `data/derived/power_<zona>.json`. La web solo lee ese archivo: nunca llama
a NASA durante una petición, así la demo no depende de internet.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyro import power  # noqa: E402
from pyro.config import load_config  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone", default=None, help="zona de config.yaml")
    ap.add_argument("--years", type=int, default=5, help="años de historia a descargar")
    ap.add_argument("--lat", type=float, default=None, help="latitud (por defecto el centro de la zona)")
    ap.add_argument("--lon", type=float, default=None, help="longitud (por defecto el centro de la zona)")
    ap.add_argument("--dry-run", action="store_true", help="solo muestra qué pediría")
    args = ap.parse_args()

    cfg = load_config()
    zone = args.zone or cfg.default_zone
    if zone not in cfg.zones:
        print(f"zona desconocida: {zone}. Opciones: {', '.join(cfg.zones)}")
        return 2
    lat, lon = (args.lat, args.lon) if args.lat is not None and args.lon is not None else power.zone_point(cfg, zone)
    end = date.today() - timedelta(days=1)
    start = date(end.year - max(1, args.years), end.month, min(end.day, 28))

    print(f"Zona: {cfg.zone_name(zone)} · punto ({lat:.4f}, {lon:.4f})")
    print(f"Rango: {start} → {end} · parámetros: {', '.join(power.PARAMETERS)}")
    if args.dry_run:
        print("(dry-run: no se descargó nada)")
        return 0
    try:
        frame = power.fetch_daily(lat, lon, start, end)
    except Exception as exc:
        print(f"No pude descargar de NASA POWER: {exc}")
        print("Nota: este entorno no tiene salida a internet; ejecútalo en tu portátil.")
        return 1
    path = power.save_cache(cfg, zone, frame, lat, lon)
    ctx = power.climate_context(cfg, zone)
    print(f"Guardado: {path} ({len(frame)} días)")
    print(f"Ventana 30 d: lluvia {ctx['window'].get('rain_mm')} mm · "
          f"déficit {ctx['rain_deficit_pct'] if ctx['rain_deficit_pct'] is None else round(ctx['rain_deficit_pct'], 1)} % · "
          f"Tmax {ctx['window'].get('tmax_mean_c')} °C · anomalía "
          f"{ctx['tmax_anomaly_c'] if ctx['tmax_anomaly_c'] is None else round(ctx['tmax_anomaly_c'], 2)} °C")
    print(f"Nivel: {ctx['label']} (años de comparación: {ctx['history_years']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
