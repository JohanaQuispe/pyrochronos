"""Carga y valida config.yaml. Toda la logica lee de aqui, nunca de constantes sueltas."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path(os.environ.get("PYRO_CONFIG", ROOT / "config.yaml"))


def load_dotenv(path: str | Path | None = None) -> int:
    """Carga el `.env` de la raiz en os.environ SIN pisar lo que ya existe.

    Hace falta para que funcione igual en Linux (`. ./.env`), en Windows
    (PowerShell no tiene `source`) y en el servidor. Un `.env` con `KEY=valor`,
    comentarios con `#` y comillas opcionales. Devuelve cuantas claves anadio.
    """
    dotenv = Path(path) if path else ROOT / ".env"
    if not dotenv.is_file():
        return 0
    added = 0
    try:
        lines = dotenv.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return 0
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        if key.lower().startswith(("set ", "setx ")):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if not key or not value:
            continue
        if key not in os.environ:
            os.environ[key] = value
            added += 1
    return added


# Al importar el paquete, el .env de la raiz queda disponible para todos
# (scripts, API y pruebas). Las variables ya definidas en el sistema mandan.
load_dotenv()


def _as_date(value):
    from datetime import date

    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


@dataclass(frozen=True)
class Config:
    raw: dict[str, Any]

    # --- accesos comodos -------------------------------------------------
    @property
    def name(self) -> str:
        return self.raw["project"]["name"]

    @property
    def version(self) -> str:
        return self.raw["project"]["version"]

    @property
    def disclaimer(self) -> str:
        return self.raw["project"]["disclaimer"].strip()

    @property
    def cell_deg(self) -> float:
        return float(self.raw["grid"]["cell_deg"])

    @property
    def zones(self) -> dict[str, dict]:
        return self.raw["geo"]["zones"]

    @property
    def default_zone(self) -> str:
        return self.raw["geo"]["default_zone"]

    @property
    def max_area_deg2(self) -> float:
        return float(self.raw["geo"]["max_area_deg2"])

    @property
    def min_conf_modis(self) -> int:
        return int(self.raw["quality"]["min_conf_modis"])

    @property
    def min_conf_viirs(self) -> list[str]:
        return list(self.raw["quality"]["min_conf_viirs"])

    @property
    def exclude_types(self) -> list[int]:
        return [int(t) for t in self.raw["quality"].get("exclude_types", [])]

    @property
    def static_source_types(self) -> list[int]:
        return [int(t) for t in self.raw["quality"].get("static_source_types", [])]

    @property
    def default_measure(self) -> str:
        return self.raw["measures"]["default"]

    @property
    def measures(self) -> list[str]:
        return list(self.raw["measures"]["options"])

    @property
    def overlap_start(self):
        return _as_date(self.raw["sources"]["overlap_start"])

    @property
    def overlap_end(self):
        return _as_date(self.raw["sources"]["overlap_end"])

    @property
    def harmonization(self) -> dict[str, Any]:
        return self.raw["harmonization"]

    @property
    def anomalies(self) -> dict[str, Any]:
        return self.raw["anomalies"]

    @property
    def api(self) -> dict[str, Any]:
        return self.raw["api"]

    @property
    def data_file(self) -> Path:
        p = Path(self.raw["api"]["data_file"])
        return p if p.is_absolute() else ROOT / p

    @property
    def source_labels(self) -> dict[str, str]:
        return {k: v["label"] for k, v in self.raw["sources"].items() if isinstance(v, dict) and "label" in v}

    def zone_bbox(self, name: str | None = None) -> tuple[float, float, float, float]:
        z = self.zones[name or self.default_zone]
        w, s, e, n = (float(x) for x in z["bbox"])
        return (w, s, e, n)

    def zone_name(self, name: str | None = None) -> str:
        return self.zones[name or self.default_zone]["name"]


def load_config(path: str | Path | None = None) -> Config:
    p = Path(path) if path else CONFIG_PATH
    with open(p, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    cfg = Config(raw)
    # validaciones: fallar temprano y ruidoso
    for key in ("geo", "grid", "sources", "quality", "anomalies", "api"):
        if key not in raw:
            raise ValueError(f"config.yaml: falta la seccion '{key}'")
    w, s, e, n = cfg.zone_bbox()
    if not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
        raise ValueError(f"bbox de la zona por defecto invalido: {(w, s, e, n)}")
    if not 0.001 <= cfg.cell_deg <= 1:
        raise ValueError("grid.cell_deg debe estar entre 0.001 y 1")
    a = cfg.anomalies
    if not 0 < a["high"] < a["extreme"] <= 100:
        raise ValueError("anomalias: se espera 0 < high < extreme <= 100")
    return cfg


def env(name: str, default: str | None = None) -> str | None:
    """Lee una variable de entorno (claves NUNCA en el codigo)."""
    value = os.environ.get(name, default)
    return value.strip() if isinstance(value, str) else value
