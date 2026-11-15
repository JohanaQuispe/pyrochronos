"""Modo reciente (NRT): focos de las ultimas horas/dias desde la API 'area' de FIRMS.

  https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{FUENTE}/{o,s,e,n}/{dias}[/{AAAA-MM-DD}]

- Fuentes NRT: VIIRS_SNPP_NRT, VIIRS_NOAA20_NRT, MODIS_NRT (latencia tipica ~3 h).
- La clave va en la variable de entorno FIRMS_MAP_KEY. Nunca en el codigo ni en la web.
- El resultado se guarda aparte de la serie historica (recent.parquet) para no mezclar
  lo observado ahora con el calendario armonizado.

Si no hay datos recientes cargados, todo el sistema funciona igual: la web lo dice.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from . import normalize as nz
from .config import Config, env

MAX_DAYS_PER_QUERY = 5
NRT_SOURCES = ("VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "MODIS_NRT")


def recent_path(cfg: Config) -> Path:
    return cfg.data_file.parent / "recent.parquet"


def meta_path(cfg: Config) -> Path:
    return cfg.data_file.parent / "recent.json"


def load_recent(cfg: Config) -> tuple[pd.DataFrame | None, dict]:
    path = recent_path(cfg)
    if not path.exists():
        return None, {}
    df = pd.read_parquet(path)
    meta = json.loads(meta_path(cfg).read_text()) if meta_path(cfg).exists() else {}
    return df, meta


def fetch_recent(
    cfg: Config,
    bbox: tuple[float, float, float, float],
    days: int = 3,
    sources: tuple[str, ...] = NRT_SOURCES,
    pause: float = 1.0,
) -> pd.DataFrame:
    """Descarga los focos de los ultimos `days` dias y los devuelve ya normalizados."""
    key = env("FIRMS_MAP_KEY")
    if not key:
        raise RuntimeError("falta FIRMS_MAP_KEY en el entorno (ver .env.example)")
    if not 1 <= days <= 10:
        raise ValueError("days debe estar entre 1 y 10")

    end = date.today()
    start = end - timedelta(days=days - 1)
    area = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
    frames: list[pd.DataFrame] = []

    for source in sources:
        cursor = start
        while cursor <= end:
            chunk = min(MAX_DAYS_PER_QUERY, (end - cursor).days + 1)
            url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{source}/{area}/{chunk}/{cursor.isoformat()}"
            try:
                resp = requests.get(url, timeout=120)
            except Exception as exc:
                print(f"  aviso: {source} {cursor} -> {exc}")
                break
            if resp.status_code != 200 or "Invalid MAP_KEY" in resp.text[:200]:
                print(f"  aviso: {source} {cursor} -> HTTP {resp.status_code} {resp.text[:120]}")
                break
            text = resp.text.strip()
            if not text or len(text.splitlines()) <= 1:
                cursor += timedelta(days=chunk)
                continue
            import io

            raw = pd.read_csv(io.StringIO(text), dtype={"confidence": "string"})
            product = "modis" if source.startswith("MODIS") else "viirs"
            frames.append(nz.normalize_frame(raw, product, cfg.min_conf_modis, bbox))
            cursor += timedelta(days=chunk)

    if not frames:
        return pd.DataFrame(columns=nz.STORE_COLUMNS)
    df = pd.concat(frames, ignore_index=True)
    df = nz.filter_quality(df, cfg.min_conf_modis, cfg.exclude_types)
    return df.drop_duplicates(subset=["day", "lat", "lon", "source"]).reset_index(drop=True)


def save_recent(cfg: Config, df: pd.DataFrame, sources: tuple[str, ...], days: int) -> dict:
    path = recent_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, compression="zstd")
    meta = {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rows": int(len(df)),
        "days": int(days),
        "sources": list(sources),
        "first_day": str((date(1970, 1, 1) + timedelta(days=int(df["day"].min()))).isoformat()) if len(df) else None,
        "last_day": str((date(1970, 1, 1) + timedelta(days=int(df["day"].max()))).isoformat()) if len(df) else None,
    }
    meta_path(cfg).write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta


def stats(cfg: Config, bbox: tuple[float, float, float, float]) -> dict:
    """Resumen de los datos recientes dentro de una zona (o "no disponible")."""
    df, meta = load_recent(cfg)
    if df is None or df.empty:
        return {"available": False, "reason": "No hay datos recientes cargados.", "meta": meta}
    mask = ((df["lat"] >= bbox[1]) & (df["lat"] <= bbox[3])
            & (df["lon"] >= bbox[0]) & (df["lon"] <= bbox[2]))
    sub = df.loc[mask]
    if sub.empty:
        return {"available": True, "empty": True, "total": 0, "meta": meta,
                "reason": "Hay datos recientes cargados, pero no en esta zona."}
    days = (date(1970, 1, 1) + pd.to_timedelta(sub["day"].astype("int64"), unit="D")).dt.date
    per_day = sub.groupby(sub["day"]).size()
    last_day = max(days) if len(days) else None
    last7 = sub[sub["day"] >= (max(sub["day"]) - 6)]
    return {
        "available": True,
        "empty": False,
        "total": int(len(sub)),
        "last_7_days": int(len(last7)),
        "last_day": str(last_day),
        "days_covered": int(sub["day"].nunique()),
        "per_source": {"MODIS": int((sub["source"] == 1).sum()), "VIIRS": int((sub["source"] == 2).sum())},
        "per_day": [{"day": str(date(1970, 1, 1) + timedelta(days=int(d))), "count": int(c)}
                    for d, c in per_day.items()],
        "meta": meta,
    }
