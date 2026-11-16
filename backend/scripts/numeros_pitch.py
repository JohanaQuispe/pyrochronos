#!/usr/bin/env python3
"""Recalcula las cifras que aparecen en docs/pitch.md con el dataset vigente.

    python backend/scripts/numeros_pitch.py

Imprime factor de armonización, banda, concordancia, totales y años más activos,
para que las cifras de la presentación coincidan con los datos que se muestran.
No escribe nada.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from pyro import grid, store  # noqa: E402
from pyro.config import load_config  # noqa: E402
from pyro.harmonize import calibrate, harmonize  # noqa: E402


def bloque(daily: pd.DataFrame, cfg, granularity: str, measure: str) -> dict:
    agg = grid.aggregate_periods(daily, granularity)
    cal = calibrate(
        agg, measure,
        cfg.overlap_start.year, cfg.overlap_end.year,
        int(cfg.harmonization["shrink_min_years"]),
        float(cfg.harmonization["min_periods_for_factor"]),
    )
    ser = harmonize(agg, cal)
    por_anio = ser.groupby("period_year")["value"].sum(min_count=1).dropna()
    top = por_anio.sort_values(ascending=False).head(5)
    return {
        "factor_global": round(float(cal.global_factor), 3),
        "factor_union_viirs": None if cal.viirs_global_factor is None else round(cal.viirs_global_factor, 3),
        "periodos_sin_estimacion": int(ser['value'].isna().sum()),
        "banda": [round(float(cal.global_p25), 3), round(float(cal.global_p75), 3)],
        "concordancia_r": None if cal.agreement_r is None else round(float(cal.agreement_r), 3),
        "pares_solape": int(cal.agreement_n),
        "factor_por_periodo": {str(k): round(float(v), 2) for k, v in sorted(cal.factor_by_period.items())},
        "total_armonizado": None if ser['value'].isna().any() else float(round(por_anio.sum(), 0)),
        "anios_mas_activos": None if ser['value'].isna().any() else {int(k): float(round(v, 0)) for k, v in top.items()},
        "desde": int(ser["period_year"].min()),
        "hasta": int(ser["period_year"].max()),
    }


def main() -> int:
    cfg = load_config()
    ds = store.load_dataset(cfg)
    df = ds.df
    print(f"Dataset: {cfg.data_file}")
    print(f"  filas: {len(df):,}")
    print(f"  por sensor: {{{', '.join(f'{int(k)}: {int(v):,}' for k, v in df['source'].value_counts().sort_index().items())}}}")
    print(f"  desde: {ds.start}  hasta: {ds.end}")
    print(f"  frp medio: {float(df['frp'].mean()):.2f} MW")

    bbox = cfg.zone_bbox()
    print("\nAgregando por celda × día …")
    daily = grid.daily_counts(ds.cells, df, bbox, cfg.cell_deg)
    print(f"  celdas-día con fuego (unión, sin duplicar): {int(daily['union_cd'].sum()):,}")
    print(f"  celdas-día MODIS: {int(daily['modis_cd'].sum()):,} · VIIRS: {int(daily['viirs_cd'].sum()):,}")

    for medida in ("cell_days", "detections"):
        for gran in ("month", "week"):
            info = bloque(daily, cfg, gran, medida)
            etiqueta = "celdas-día" if medida == "cell_days" else "focos"
            print(f"\n--- {etiqueta} · {gran} ---")
            print(json.dumps(info, ensure_ascii=False, indent=1))

    meses = ["", "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    agg = grid.aggregate_periods(daily, "month")
    cal = calibrate(agg, "cell_days", cfg.overlap_start.year, cfg.overlap_end.year,
                    int(cfg.harmonization["shrink_min_years"]),
                    float(cfg.harmonization["min_periods_for_factor"]))
    ser = harmonize(agg, cal)
    por_mes = ser.groupby("period_index")["value"].sum(min_count=1)
    total = float(por_mes.sum())
    print("\n--- estacionalidad (celdas-día, todos los años) ---")
    for mes, valor in por_mes.items():
        print(f"  {meses[int(mes)]}: {valor:,.0f}  ({valor / total * 100:4.1f} %)")
    pico = int(por_mes.idxmax())
    print(f"  pico: {meses[pico]} · meses >= 10 % del total: "
          f"{', '.join(meses[int(m)] for m in por_mes[por_mes >= total * 0.10].index)}")

    print("\nCopia este bloque completo y pégalo en el chat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
