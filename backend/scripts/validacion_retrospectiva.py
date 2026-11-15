#!/usr/bin/env python3
"""Validación retrospectiva mensual de la estimación desde MODIS (solo lectura).

    python backend/scripts/validacion_retrospectiva.py
    python backend/scripts/validacion_retrospectiva.py --zone madrededios

Cada año del solape se retira por completo de la calibración. Sus 12 meses MODIS
se transforman con los factores entrenados en los demás años y la suma anual se
compara contra la unión observada MODIS+VIIRS del mismo año. No modifica datos.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from pyro import grid, store  # noqa: E402
from pyro.config import load_config  # noqa: E402
from pyro.harmonize import calibrate  # noqa: E402


def validate(agg: pd.DataFrame, cfg, coverage_start: date, coverage_end: date) -> dict:
    """Leave-one-year-out: evalúa años completos con MODIS y VIIRS en los 12 meses.

    El conjunto de entrenamiento usa la configuración y los filtros de calibrate(),
    sin ningún periodo del año evaluado. Se excluyen años sin los doce meses con
    detecciones de ambos sensores: no se infiere cobertura a partir de ceros.
    """
    first, last = cfg.overlap_start.year, cfg.overlap_end.year
    records, skipped = [], []
    months = set(range(1, 13))
    for year in range(first, last + 1):
        start, end = date(year, 1, 1), date(year, 12, 31)
        if start < coverage_start or end > coverage_end or start < cfg.overlap_start or end > cfg.overlap_end:
            skipped.append((year, 'fuera de la cobertura completa del archivo o solape'))
            continue
        held = agg[agg['period_year'] == year].sort_values('period_index')
        if len(held) != 12 or set(held['period_index'].astype(int)) != months:
            skipped.append((year, 'no hay 12 meses de detecciones'))
            continue
        if (not np.isfinite(held[['modis_cd', 'viirs_cd', 'union_cd']].to_numpy(float)).all()
                or (held['modis_cd'] <= 0).any() or (held['viirs_cd'] <= 0).any()
                or (held['union_cd'] <= 0).any()):
            skipped.append((year, 'hay meses sin detecciones válidas de ambos sensores'))
            continue
        train = agg[(agg['period_year'] != year) & agg['period_year'].between(first, last)]
        usable = ((train['modis_cd'] >= float(cfg.harmonization['min_periods_for_factor']))
                  & (train['modis_cd'] > 0) & (train['viirs_cd'] > 0)
                  & np.isfinite(train['union_cd'] / train['modis_cd'].replace(0, np.nan)))
        if int(usable.sum()) < 3:
            skipped.append((year, 'menos de 3 periodos útiles para calibrar sin ese año'))
            continue
        cal = calibrate(train, 'cell_days', first, last,
                        int(cfg.harmonization['shrink_min_years']),
                        float(cfg.harmonization['min_periods_for_factor']))
        factors = [cal.factor(int(month)) for month in held['period_index']]
        predicted = float(sum(float(m) * factor[0] for m, factor in zip(held['modis_cd'], factors)))
        observed = float(held['union_cd'].sum())
        if observed <= 0:
            skipped.append((year, 'unión anual sin valor positivo'))
            continue
        relative = (predicted - observed) / observed * 100.0
        records.append({'year': year, 'observed': observed, 'estimated': predicted,
                        'signed_error_pct': relative, 'absolute_error_pct': abs(relative),
                        'fallback_months': sum(int(factor[3]) for factor in factors)})
    if not records:
        return {'years': [], 'skipped': skipped, 'median_ape': None, 'mean_ape': None,
                'wape': None, 'median_bias_pct': None}
    return {
        'years': records,
        'skipped': skipped,
        'median_ape': float(np.median([r['absolute_error_pct'] for r in records])),
        'mean_ape': float(np.mean([r['absolute_error_pct'] for r in records])),
        'wape': float(sum(abs(r['estimated'] - r['observed']) for r in records)
                      / sum(r['observed'] for r in records) * 100),
        'median_bias_pct': float(np.median([r['signed_error_pct'] for r in records])),
    }


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Validación retrospectiva por año, con la zona y el parquet locales.')
    parser.add_argument('--zone', default=None, help='zona de config.yaml (por defecto Perú)')
    args = parser.parse_args(argv)
    cfg = load_config()
    zone = args.zone or cfg.default_zone
    if zone not in cfg.zones:
        parser.error('zona no disponible en config.yaml')
    ds = store.load_dataset(cfg)
    print('VALIDACIÓN RETROSPECTIVA · celdas-día · mensual · deja un año fuera')
    print(f"Archivo: {cfg.data_file.name} · SHA256: {file_sha256(cfg.data_file)}")
    print(f"Zona: {cfg.zone_name(zone)} (recuadro configurado) · filas totales: {len(ds.df):,}")
    print(f"Cobertura del archivo: {ds.start} a {ds.end} · solape configurado: {cfg.overlap_start} a {cfg.overlap_end}")
    print('Calculando…')
    daily = grid.daily_counts(ds.cells, ds.df, cfg.zone_bbox(zone), cfg.cell_deg)
    agg = grid.aggregate_periods(daily, 'month')
    result = validate(agg, cfg, ds.start, ds.end)
    print('\nAño | unión observada | estimación desde MODIS | error firmado | error absoluto | meses con factor global')
    for row in result['years']:
        print(f"{row['year']} | {row['observed']:,.0f} | {row['estimated']:,.0f} | "
              f"{row['signed_error_pct']:+.2f}% | {row['absolute_error_pct']:.2f}% | {row['fallback_months']}")
    print(f"\nAños evaluados: {len(result['years'])}")
    for year, reason in result['skipped']:
        print(f"  Excluido {year}: {reason}")
    if not result['years']:
        print('No hay evidencia suficiente para calcular un error anual.')
        return 1
    print(f"Mediana del error absoluto porcentual anual: {result['median_ape']:.2f}%")
    print(f"Promedio del error absoluto porcentual anual (MAPE): {result['mean_ape']:.2f}%")
    print(f"Error absoluto ponderado por volumen (WAPE): {result['wape']:.2f}%")
    print(f"Mediana del error porcentual firmado: {result['median_bias_pct']:+.2f}%")
    print('\nSolo evalúa la estimación MODIS→unión en el solape y años elegibles;')
    print('la unión satelital no es verdad de campo, y no valida 2000–2011 ni la estimación desde VIIRS sola.')
    print('Los meses con detecciones de ambos sensores no garantizan cobertura completa.')
    print('Copia este resultado completo al chat.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
