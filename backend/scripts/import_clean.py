#!/usr/bin/env python3
"""Importa un archivo limpio propio (CSV/XLSX/Parquet) al almacén de PyroChronos.

Sirve cuando los datos no vienen con los nombres de archivo de FIRMS (por ejemplo
`focos_incendios_limpios.csv`) o cuando ya están deduplicados por fuera.

    # 1) mirar qué trae el archivo, sin escribir nada
    python backend/scripts/import_clean.py --file "C:\\ruta\\focos_incendios_limpios.csv" --inspect

    # 2) importarlo (guarda copia del parquet anterior)
    python backend/scripts/import_clean.py --file "..." --write

Modo `--inspect` imprime columnas detectadas, rango de fechas, conteo por satélite y
cuántas filas quedarían fuera por calidad. Nunca sobrescribe sin `--write`.
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from pyro import normalize, store  # noqa: E402
from pyro.config import ROOT, load_config  # noqa: E402

# Nombres de columna aceptados (minúsculas, sin acentos ni guiones bajos extra)
ALIASES = {
    "lat": ["latitude", "latitud", "lat", "y"],
    "lon": ["longitude", "longitud", "lon", "lng", "long", "x"],
    "date": ["acq_date", "fecha", "fecha_adquisicion", "date", "fecha_deteccion", "dia"],
    "time": ["acq_time", "hora", "time", "hora_adquisicion"],
    "satellite": ["satellite", "satelite", "instrument", "instrumento", "source", "fuente", "sat", "sensor"],
    "confidence": ["confidence", "confianza", "conf", "nivel_confianza"],
    "frp": ["frp", "frp_mw", "potencia_radiativa", "power"],
    "type": ["type", "tipo", "tipo_foco"],
}
REQUIRED = ("lat", "lon", "date", "satellite")


def clean_name(name: str) -> str:
    text = str(name).strip().lower()
    for bad in ("á", "é", "í", "ó", "ú", "°", "(", ")", "[", "]", "-", " "):
        text = text.replace(bad, "_")
    return "_".join(part for part in text.split("_") if part)


def detect_columns(columns: list[str]) -> dict[str, str]:
    """Empareja las columnas del archivo con los campos que necesitamos."""
    cleaned = {clean_name(c): c for c in columns}
    found: dict[str, str] = {}
    for field, names in ALIASES.items():
        for candidate in names:
            if candidate in cleaned:
                found[field] = cleaned[candidate]
                break
    return found


def read_any(path: Path) -> pd.DataFrame:
    """Lee CSV (cualquier separador), Excel o Parquet."""
    suffix = path.suffix.lower()
    if suffix in (".parquet", ".pq"):
        return pd.read_parquet(path)
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    with path.open("r", encoding="utf-8-sig", errors="replace") as fh:
        sample = fh.read(8192)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            sep = dialect.delimiter
        except csv.Error:
            sep = ","
        return pd.read_csv(fh, sep=sep, low_memory=False)


def to_source(value) -> int | None:
    """MODIS -> 1, VIIRS -> 2 (los códigos del almacén)."""
    text = str(value).strip().lower()
    if "modis" in text or text in ("1", "1.0"):
        return normalize.SOURCE_MODIS
    if "viirs" in text or text in ("2", "2.0"):
        return normalize.SOURCE_VIIRS
    return None


def to_conf_level(value, source: int) -> int:
    """Confianza a 0/1/2. MODIS llega 0-100; VIIRS llega l/n/h o 0-100."""
    text = str(value).strip().lower()
    if text in ("", "nan", "none"):
        return 1
    if text in ("l", "low", "baja"):
        return 0
    if text in ("n", "nominal", "media"):
        return 1
    if text in ("h", "high", "alta"):
        return 2
    try:
        number = float(text)
    except ValueError:
        return 1
    if number <= 2:  # ya viene como 0/1/2
        return int(round(number))
    # MODIS: 0-100. 30 es el umbral habitual de "nominal", 80 de "alta".
    if number >= 80:
        return 2
    if number >= 30:
        return 1
    return 0


def to_epoch_days(series: pd.Series) -> pd.Series:
    """Fecha a días desde 1970 (el formato interno del almacén)."""
    parsed = pd.to_datetime(series, errors="coerce", utc=False, dayfirst=False)
    missing = parsed.isna()
    if missing.any():  # algunos vienen como 20240131 (entero sin separadores)
        alt = pd.to_datetime(series.astype(str), format="%Y%m%d", errors="coerce")
        parsed = parsed.where(~missing, alt)
    return (parsed - pd.Timestamp("1970-01-01")).dt.days.astype("Int32")


def build_frame(df: pd.DataFrame, cols: dict[str, str]) -> tuple[pd.DataFrame, dict]:
    """Convierte el archivo del usuario al esquema común. Devuelve (tabla, informe)."""
    out = pd.DataFrame()
    out["lat"] = pd.to_numeric(df[cols["lat"]], errors="coerce").astype("float32")
    out["lon"] = pd.to_numeric(df[cols["lon"]], errors="coerce").astype("float32")
    out["day"] = to_epoch_days(df[cols["date"]])  # entero con nulos: se limpia abajo
    out["source"] = df[cols["satellite"]].map(to_source).astype("Int8")
    if "confidence" in cols:
        out["conf_level"] = [
            to_conf_level(v, s if pd.notna(s) else 1)
            for v, s in zip(df[cols["confidence"]], out["source"])
        ]
        out["conf_level"] = pd.Series(out["conf_level"], index=out.index).astype("int8")
    else:
        out["conf_level"] = np.int8(1)
    if "confidence" in cols:
        raw = pd.to_numeric(df[cols["confidence"]], errors="coerce")
        out["conf_raw"] = raw.fillna(-1).clip(-1, 100).astype("int8")
    else:
        out["conf_raw"] = np.int8(-1)
    out["frp"] = (
        pd.to_numeric(df[cols["frp"]], errors="coerce").fillna(0).astype("float32")
        if "frp" in cols
        else np.float32(0)
    )
    out["ftype"] = (
        pd.to_numeric(df[cols["type"]], errors="coerce").fillna(0).clip(0, 127).astype("int8")
        if "type" in cols
        else np.int8(0)
    )
    report = {
        "filas_leidas": int(len(out)),
        "sin_coordenadas": int(out[["lat", "lon"]].isna().any(axis=1).sum()),
        "sin_fecha": int(out["day"].isna().sum()),
        "sin_satelite": int(out["source"].isna().sum()),
        "por_satelite": {int(k): int(v) for k, v in out["source"].value_counts().dropna().items()},
    }
    out = out.dropna(subset=["lat", "lon", "day", "source"])
    out["day"] = out["day"].astype("int32")
    out["source"] = out["source"].astype("int8")
    report["filas_validas"] = int(len(out))
    if not out.empty:
        days = out["day"].to_numpy()
        report["desde"] = str((pd.Timestamp("1970-01-01") + pd.to_timedelta(int(days.min()), "D")).date())
        report["hasta"] = str((pd.Timestamp("1970-01-01") + pd.to_timedelta(int(days.max()), "D")).date())
    return out[normalize.STORE_COLUMNS], report


def main() -> int:
    ap = argparse.ArgumentParser(description="Importa un archivo limpio propio al almacén.")
    ap.add_argument("--file", required=True, help="ruta del CSV/XLSX/Parquet")
    ap.add_argument("--inspect", action="store_true", help="solo muestra qué hay (por defecto)")
    ap.add_argument("--write", action="store_true", help="escribe el parquet (hace copia del anterior)")
    ap.add_argument("--dedupe", default="on", choices=["on", "off"], help="quitar duplicados día+punto+sensor")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"ERROR: no existe {path}")
        return 2

    cfg = load_config()
    df = read_any(path)
    print(f"Archivo: {path.name} · {len(df):,} filas · {len(df.columns)} columnas")
    print("Columnas:", ", ".join(str(c) for c in df.columns[:12]), "…" if len(df.columns) > 12 else "")

    cols = detect_columns(list(df.columns))
    faltan = [f for f in REQUIRED if f not in cols]
    if faltan:
        print(f"\nERROR: no reconozco estas columnas: {faltan}")
        print("Renombra las columnas así (o dime cómo se llaman y lo ajusto):")
        print("  latitude / lat · longitude / lon · acq_date / fecha · satellite / satelite")
        print(f"Detectadas: {cols}")
        return 3
    print("Columnas reconocidas:", ", ".join(f"{k}={v}" for k, v in cols.items()))

    frame, report = build_frame(df, cols)
    print("\nInforme:")
    for key, value in report.items():
        print(f"  {key}: {value}")

    # recorte a la zona configurada y control de calidad, igual que build_dataset
    w, s, e, n = cfg.zone_bbox()
    inside = frame[(frame["lat"] >= s) & (frame["lat"] <= n) & (frame["lon"] >= w) & (frame["lon"] <= e)]
    print(f"  dentro de la zona ({cfg.zone_name()}): {len(inside):,} de {len(frame):,}")
    kept = normalize.filter_quality(inside, cfg.min_conf_modis, cfg.exclude_types, drop_low_viirs=True)
    print(f"  tras control de calidad: {len(kept):,}")

    if args.dedupe == "on":
        before = len(kept)
        kept = kept.drop_duplicates(subset=["day", "lat", "lon", "source"]).reset_index(drop=True)
        print(f"  duplicados quitados: {before - len(kept):,}")

    if not args.write:
        print("\n(modo inspección: no se escribió nada. Añade --write para importar)")
        return 0

    if kept.empty:
        print("\nERROR: no quedaría ninguna fila. No se toca el almacén.")
        return 4

    out_path = cfg.data_file
    if out_path.exists():
        backup = out_path.with_name(f"{out_path.stem}_antes_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.parquet")
        shutil.copy2(out_path, backup)
        print(f"\nCopia del parquet anterior: {backup.name}")

    meta = {
        "source": f"importado de {path.name}",
        "rows_before_quality": int(len(frame)),
        "rows_after_quality": int(len(kept)),
        "imported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    info = store.write_dataset(kept, out_path, meta)
    print(f"Escrito {out_path} · {info['rows']:,} filas · sha {info['sha256']}")
    print("Reinicia la API para que lo lea (uvicorn) y vuelve a mirar el calendario.")
    print("Ojo: si cambian los datos, cambian las cifras del pitch (factor, totales).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
