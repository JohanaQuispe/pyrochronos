"""Estado de campo: geocercas de usuarios y validacion humana ("ground truth").

Hoy se guarda en JSON dentro de `data/derived/` (fuera de git) porque la demo no
puede depender de un servicio externo. La firma de las funciones es la misma que
necesitaria una tabla de Supabase, asi que cambiar de almacen es cambiar el
cuerpo de este modulo, no el resto del sistema.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .config import Config
from .geofence import VERDICTS

GEOFENCES_FILE = "geofences.json"
VERDICTS_FILE = "groundtruth.json"
ALERTS_FILE = "alerts_sent.json"


def _path(cfg: Config, name: str) -> Path:
    """Carpeta del estado de campo (configurable con PYRO_FIELD_DIR)."""
    override = os.environ.get("PYRO_FIELD_DIR")
    base = Path(override) if override else cfg.data_file.parent
    return base / name


def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")) or {}
    except (ValueError, OSError):
        return {}


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


# --- geocercas -------------------------------------------------------------

def load_geofences(cfg: Config) -> dict[str, dict]:
    return _read(_path(cfg, GEOFENCES_FILE))


def save_geofence(
    cfg: Config,
    telegram_id: int | str,
    lat: float,
    lon: float,
    radius_km: float = 10.0,
    name: str | None = None,
    role: str | None = None,
) -> dict:
    """Registra o actualiza la posicion de un usuario de campo."""
    data = load_geofences(cfg)
    record = {
        "telegram_id": str(telegram_id),
        "lat": float(lat),
        "lon": float(lon),
        "radius_km": float(radius_km),
        "name": name or data.get(str(telegram_id), {}).get("name"),
        "role": role or data.get(str(telegram_id), {}).get("role"),
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    data[str(telegram_id)] = record
    _write(_path(cfg, GEOFENCES_FILE), data)
    return record


def active_geofences(cfg: Config) -> list[dict]:
    return [g for g in load_geofences(cfg).values() if g.get("lat") is not None]


# --- validacion humana -----------------------------------------------------

def load_verdicts(cfg: Config) -> list[dict]:
    data = _read(_path(cfg, VERDICTS_FILE))
    return list(data.values())


def save_verdict(
    cfg: Config,
    hotspot_id: int | str,
    telegram_id: int | str | None,
    verdict: str,
    meta: dict | None = None,
) -> dict:
    """Guarda el veredicto; el ultimo gana (el de campo manda sobre el de escritorio)."""
    if verdict not in VERDICTS:
        raise ValueError(f"veredicto desconocido: {verdict}")
    data = _read(_path(cfg, VERDICTS_FILE))
    key = str(hotspot_id)
    previous = data.get(key, {})
    record = {
        "hotspot_id": key,
        "verdict": verdict,
        "label": VERDICTS[verdict],
        "telegram_id": str(telegram_id) if telegram_id is not None else previous.get("telegram_id"),
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "history": (previous.get("history") or [])[-9:]
        + [{"verdict": verdict, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "telegram_id": str(telegram_id) if telegram_id is not None else None}],
    }
    for key_meta, value in (meta or {}).items():
        record[key_meta] = value
    data[key] = record
    _write(_path(cfg, VERDICTS_FILE), data)
    return record


def verdict_summary(cfg: Config) -> dict:
    counts = {code: 0 for code in VERDICTS}
    for item in load_verdicts(cfg):
        if item.get("verdict") in counts:
            counts[item["verdict"]] += 1
    total = sum(counts.values())
    return {"counts": counts, "total": total}


# --- avisos ya enviados (para no repetir el mismo foco) --------------------

def load_sent(cfg: Config) -> dict:
    return _read(_path(cfg, ALERTS_FILE))


def mark_sent(cfg: Config, telegram_id: int | str, hotspot_id: int | str) -> None:
    data = load_sent(cfg)
    key = f"{telegram_id}:{hotspot_id}"
    data[key] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _write(_path(cfg, ALERTS_FILE), data)


def already_sent(cfg: Config, telegram_id: int | str, hotspot_id: int | str) -> bool:
    return f"{telegram_id}:{hotspot_id}" in load_sent(cfg)
