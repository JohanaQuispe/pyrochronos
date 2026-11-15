"""Departamentos usando polígonos simplificados INEI-2007, no límites oficiales vigentes.

Clasifica cada detección por coordenadas antes de agrupar las celdas-día. No requiere
Shapely: prueba de punto en polígono vectorizada con NumPy; incluye la frontera.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .config import ROOT

PATH = ROOT / 'data' / 'geo' / 'peru_departamentos_inei2007_simplificado.geojson'
DISPLAY = {'ANCASH': 'Áncash', 'APURIMAC': 'Apurímac', 'HUANUCO': 'Huánuco',
           'JUNIN': 'Junín', 'SAN MARTIN': 'San Martín'}


@lru_cache(maxsize=1)
def all_departments() -> dict:
    raw = json.loads(PATH.read_text(encoding='utf-8'))
    result = {}
    for feature in raw['features']:
        prop = feature['properties']
        code, name = str(prop['FIRST_IDDP']), prop['NOMBDEP']
        geom = feature['geometry']
        polygons = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
        xs, ys = [], []
        for poly in polygons:
            for ring in poly:
                for x, y, *_ in ring:
                    xs.append(float(x)); ys.append(float(y))
        result[f'd_{code}'] = {'key': f'd_{code}', 'name': DISPLAY.get(name, name.title()),
                                'bbox': [min(xs), min(ys), max(xs), max(ys)],
                                'kind': 'department', 'geometry': geom,
                                'note': 'Límite simplificado INEI 2007, no oficial vigente.'}
    return result


def _ring_mask(x: np.ndarray, y: np.ndarray, ring) -> tuple[np.ndarray, np.ndarray]:
    inside = np.zeros(len(x), dtype=bool)
    border = np.zeros(len(x), dtype=bool)
    for i in range(len(ring)):
        x1, y1 = ring[i - 1][:2]
        x2, y2 = ring[i][:2]
        if x1 == x2 and y1 == y2:
            continue
        # Horizontal boundaries handled separately; avoids division by zero.
        if y1 != y2:
            cross = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1)
            inside ^= cross
        on_line = np.abs((x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)) <= 1e-10
        border |= on_line & (x >= min(x1, x2) - 1e-10) & (x <= max(x1, x2) + 1e-10) & (y >= min(y1, y2) - 1e-10) & (y <= max(y1, y2) + 1e-10)
    return inside, border


def filter_frame(df: pd.DataFrame, key: str | None) -> pd.DataFrame:
    if not key or key not in all_departments():
        return df
    dept = all_departments()[key]
    w, s, e, n = dept['bbox']
    candidate = df.loc[(df['lon'] >= w) & (df['lon'] <= e) & (df['lat'] >= s) & (df['lat'] <= n)]
    if candidate.empty:
        return candidate.copy()
    x = candidate['lon'].to_numpy(dtype=np.float64)
    y = candidate['lat'].to_numpy(dtype=np.float64)
    geom = dept['geometry']
    polygons = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
    selected = np.zeros(len(candidate), dtype=bool)
    for poly in polygons:
        within, boundary = _ring_mask(x, y, poly[0])
        for hole in poly[1:]:
            in_hole, on_hole = _ring_mask(x, y, hole)
            within &= ~in_hole
            boundary |= on_hole
        selected |= within | boundary
    return candidate.loc[selected].copy()
