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
    # `instrument` primero: en los CSV de FIRMS trae MODIS/VIIRS, mientras que
    # `satellite` trae sólo letras o números (T, A, N, N20, N21) y no dice el sensor.
    "satellite": ["instrument", "instrumento", "satellite", "satelite", "sensor", "source", "fuente", "sat"],
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


SUPPORTED = (".csv", ".txt", ".xlsx", ".xls", ".parquet", ".pq", ".zip")


def read_any(path: Path) -> pd.DataFrame:
    """Lee CSV (cualquier separador), Excel, Parquet o ZIP con un CSV dentro."""
    suffix = path.suffix.lower()
    if suffix in (".parquet", ".pq"):
        return pd.read_parquet(path)
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    if suffix == ".zip":
        import zipfile

        with zipfile.ZipFile(path) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith((".csv", ".txt"))]
            if not names:
                raise SystemExit(f"ERROR: {path.name} no contiene ningún CSV")
            with zf.open(names[0]) as fh:
                return pd.read_csv(fh, sep=",", low_memory=False, encoding="utf-8-sig")
    with path.open("r", encoding="utf-8-sig", errors="replace") as fh:
        sample = fh.read(8192)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            sep = dialect.delimiter
        except csv.Error:
            sep = ","
        return pd.read_csv(fh, sep=sep, low_memory=False)


def satellite_columns(part: pd.DataFrame) -> list[str]:
    """Columnas del archivo que podrían contener el sensor."""
    encontradas = []
    for col in part.columns:
        if clean_name(col) in ALIASES["satellite"] and col not in encontradas:
            encontradas.append(col)
    return encontradas


def resolve_part_sensor(part: pd.DataFrame, name: str, forced: int | None):
    """Decide el sensor de un archivo y deja una sola columna `_sensor_final`."""
    cols = detect_columns(list(part.columns))
    col = cols.get("satellite")
    if col:
        mapeado = part[col].map(to_source)
        bien = int(mapeado.notna().sum())
        relleno = guess_source_from_name(name) or forced
        if bien and relleno is not None and bien < len(part):
            mapeado = mapeado.fillna({"MODIS": 1, "VIIRS": 2}.get(source_label(relleno)))
        if bien:
            part = part.copy()
            part["_sensor_final"] = mapeado
            return part, f"columna '{col}' ({bien:,} de {len(part):,} filas reconocidas)"

    del_nombre = guess_source_from_name(name)
    elegido = del_nombre if del_nombre is not None else forced
    if elegido is not None:
        origen = "el nombre del archivo" if del_nombre is not None else "--source"
        part = part.drop(columns=satellite_columns(part), errors="ignore")
        part["_sensor_final"] = source_label(elegido)
        return part, f"{source_label(elegido)} deducido de {origen}"

    return part, "sin sensor reconocible"


def guess_source_from_name(name: str) -> int | None:
    """Deduce el sensor por el nombre del archivo (MODIS_SP_historico, VIIRS_NOAA20_...)."""
    text = name.lower()
    if "modis" in text or "terra" in text or "aqua" in text:
        return normalize.SOURCE_MODIS
    if "viirs" in text or "snpp" in text or "noaa20" in text or "noaa21" in text or "jpss" in text:
        return normalize.SOURCE_VIIRS
    return None


def source_label(value: int) -> str:
    return "MODIS" if value == normalize.SOURCE_MODIS else "VIIRS"


def resolve_targets(raw: str) -> tuple[list[Path], str]:
    """Acepta archivo, carpeta o un nombre sin extensión y devuelve qué leer."""
    path = Path(raw).expanduser()
    if path.is_dir():
        found = sorted(f for f in path.rglob("*") if f.suffix.lower() in SUPPORTED and f.is_file())
        return found, "carpeta"
    if path.is_file():
        return [path], "archivo"

    parent = path.parent if str(path.parent) else Path(".")
    stem = path.stem.lower()
    if parent.is_dir():
        same = sorted(f for f in parent.iterdir() if f.suffix.lower() in SUPPORTED
                      and f.stem.lower() == stem and f.is_file())
        if same:
            return same, "mismo nombre, otra extensión"
        parecidos = sorted(f for f in parent.iterdir() if f.suffix.lower() in SUPPORTED
                           and f.stem.lower().startswith(stem[:10]) and f.is_file())
        if parecidos:
            return parecidos, "nombre parecido"
    return [], "no encontrado"


MODIS_CODES = {"1", "1.0", "mod", "modis", "t", "terra", "a", "aqua"}
VIIRS_CODES = {"2", "2.0", "v", "viirs", "n", "npp", "snpp", "n20", "n21",
               "noaa20", "noaa21", "noaa", "jpss", "jpss1", "jpss2"}


def to_source(value) -> int | None:
    """MODIS -> 1, VIIRS -> 2 (los códigos del almacén).

    Acepta el nombre del instrumento (`MODIS`, `VIIRS`) y también los códigos de
    satélite de FIRMS: MODIS usa T/A (Terra/Aqua) y VIIRS usa N/N20/N21.
    """
    text = str(value).strip().lower()
    if text in ("", "nan", "none"):
        return None
    if "modis" in text or text in MODIS_CODES:
        return normalize.SOURCE_MODIS
    if "viirs" in text or text in VIIRS_CODES:
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
    ap.add_argument("--source", default=None, choices=["modis", "viirs"],
                    help="sensor a declarar si el archivo no trae columna de satélite")
    ap.add_argument("--dedupe", default="on", choices=["on", "off"], help="quitar duplicados día+punto+sensor")
    args = ap.parse_args()
    args.source = {"modis": normalize.SOURCE_MODIS, "viirs": normalize.SOURCE_VIIRS}.get(args.source)

    paths, como = resolve_targets(args.file)
    if not paths:
        print(f"ERROR: no encuentro {args.file}")
        parent = Path(args.file).expanduser().parent
        if parent.is_dir():
            print(f"Esto es lo que hay en {parent}:")
            for f in sorted(parent.iterdir())[:25]:
                print(f"  {f.name}")
        print("\nPásame la ruta exacta del archivo (arrástralo a la ventana de PowerShell y copia lo que aparece).")
        return 2

    cfg = load_config()
    partes = []
    for one in paths:
        print(f"Leyendo {one.name} …")
        part = read_any(one)
        if part.empty:
            print(f"  (vacío, se omite)")
            continue
        part, nota_sensor = resolve_part_sensor(part, one.name, args.source)
        print(f"  sensor: {nota_sensor}")
        if len(paths) > 1:
            part["_origen"] = one.name
        partes.append(part)
    if not partes:
        print("ERROR: no se pudo leer ninguna fila.")
        return 2
    if len(paths) > 1 and como != "carpeta":
        print(f"\nHay {len(paths)} archivos que coinciden con ese nombre:")
        for one in paths:
            print(f"  {one}")
        print("Escríbeme la ruta completa del que quieres, sin adivinar.")
        return 2
    df = pd.concat(partes, ignore_index=True, sort=False)
    if len(paths) > 1:
        print(f"Se juntaron {len(partes)} archivo(s) ({como}).")
    path = paths[0]
    print(f"Archivo: {path.name} · {len(df):,} filas · {len(df.columns)} columnas")
    print("Columnas:", ", ".join(str(c) for c in df.columns[:12]), "…" if len(df.columns) > 12 else "")

    if "_origen" in df.columns:
        origen = df["_origen"]
        df = df.drop(columns=["_origen"])
    else:
        origen = None
    cols = detect_columns(list(df.columns))
    sensor_note = "columna del archivo"
    if "_sensor_final" in df.columns:
        for col in satellite_columns(df):
            if col in (cols.get("satellite"),):
                df = df.drop(columns=[col])
        cols["satellite"] = "_sensor_final"
        sensor_note = "resuelto por archivo (instrumento, nombre o --source)"

    faltan = [f for f in REQUIRED if f not in cols]
    if faltan:
        print(f"\nERROR: no reconozco estas columnas: {faltan}")
        print("Lo que sí encontré:", cols if cols else "nada")
        if "satellite" in faltan:
            print("\nFalta el sensor (MODIS vs VIIRS). Tienes dos salidas:")
            print("  a) importar los archivos por sensor (el nombre los delata):")
            print("     python backend\\scripts\\import_clean.py --file \"...\\MODIS_SP_historico\" --inspect")
            print("  b) declararlo a mano para todo el archivo, si de verdad es de un solo sensor:")
            print("     --source modis   ó   --source viirs")
        if any(f in faltan for f in ("lat", "lon", "date")):
            print("Necesito ubicación y fecha. Nombres que reconozco:")
            print("  latitude / latitud / lat · longitude / longitud / lon · acq_date / fecha / date")
        return 3
    print("Columnas reconocidas:", ", ".join(f"{k}={v}" for k, v in cols.items()))
    if "frp" not in cols:
        print("AVISO: el archivo no trae FRP. El calendario y las anomalías funcionan,")
        print("       pero el indicador de FRP quedará en cero y el reporte lo dirá.")

    frame, report = build_frame(df, cols)
    if origen is not None:
        print("\n  filas por archivo:", {k: int(v) for k, v in origen.value_counts().items()})
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
        "sensor_note": sensor_note,
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
