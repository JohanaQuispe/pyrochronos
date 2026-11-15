"""Acceso a datos. Hoy: Parquet local. Manana: Supabase, sin tocar la logica.

La app nunca llama a la API de FIRMS en vivo: lee del almacen.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .config import Config
from .normalize import EPOCH, SOURCE_MODIS, SOURCE_VIIRS


@dataclass
class Dataset:
    """Detecciones normalizadas + metadatos de cobertura."""

    df: pd.DataFrame
    generated_at: str
    source_version: str
    cell_deg: float = 0.01

    @property
    def start(self) -> date:
        return (EPOCH + np.timedelta64(int(self.df["day"].min()), "D")).astype(date)

    @property
    def end(self) -> date:
        return (EPOCH + np.timedelta64(int(self.df["day"].max()), "D")).astype(date)

    @property
    def cells(self) -> pd.DataFrame:
        """Celdas unicas por dia, celda y satelite (medida principal). Se calcula una vez."""
        cached = getattr(self, "_cells", None)
        if cached is None:
            from .grid import build_cells

            cached = build_cells(self.df, self.cell_deg)
            self._cells = cached
        return cached

    def coverage(self) -> dict:
        out = {"start": str(self.start), "end": str(self.end)}
        for src, label in ((SOURCE_MODIS, "modis"), (SOURCE_VIIRS, "viirs")):
            sub = self.df.loc[self.df["source"] == src, "day"]
            out[label] = {
                "start": str((EPOCH + np.timedelta64(int(sub.min()), "D")).astype(date)) if len(sub) else None,
                "end": str((EPOCH + np.timedelta64(int(sub.max()), "D")).astype(date)) if len(sub) else None,
                "detections": int(len(sub)),
            }
        out["detections"] = int(len(self.df))
        return out


def write_dataset(df: pd.DataFrame, path: Path, meta: dict | None = None) -> dict:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, compression="zstd")
    digest = hashlib.sha256()
    for col in df.columns:
        digest.update(pd.util.hash_pandas_object(df[col], index=False).values.tobytes())
    info = {
        "file": path.name,
        "rows": int(len(df)),
        "sha256": digest.hexdigest()[:16],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **(meta or {}),
    }
    (path.parent / "dataset.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    return info


@lru_cache(maxsize=4)
def _read(path: str, mtime: float) -> tuple[pd.DataFrame, dict]:
    df = pd.read_parquet(path)
    meta_path = Path(path).with_name("dataset.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    return df, meta


def load_dataset(cfg: Config) -> Dataset:
    path = cfg.data_file
    if not path.exists():
        raise FileNotFoundError(
            f"no existe {path}. Construye los datos primero:\n"
            f"  python backend/scripts/build_dataset.py --raw <carpeta con los CSV de FIRMS>"
        )
    df, meta = _read(str(path), path.stat().st_mtime)
    return Dataset(
        df=df,
        generated_at=meta.get("generated_at", ""),
        source_version=meta.get("source_version", "local"),
        cell_deg=cfg.cell_deg,
    )
