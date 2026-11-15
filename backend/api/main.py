"""API de PyroChronos (FastAPI).

Todo lo pesado se calcula una vez y se cachea. La app NO consulta a FIRMS en vivo:
sirve lo que ya esta en el almacen local.
"""
from __future__ import annotations

import io
import sys
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyro.calendar import build_calendar, hotspots_geojson  # noqa: E402
from pyro.notify import build_bulletin  # noqa: E402
from pyro.alerts import build_alert  # noqa: E402
from pyro.report import build_report_html  # noqa: E402
from pyro import nrt  # noqa: E402
from pyro.config import ROOT, env, load_config  # noqa: E402
from pyro.store import Dataset, load_dataset  # noqa: E402
from pyro.summary import MONTHS  # noqa: E402

cfg = load_config()
app = FastAPI(title=f"{cfg.name} API", version=cfg.version, docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

_dataset: Dataset | None = None


def dataset() -> Dataset:
    global _dataset
    if _dataset is None:
        _dataset = load_dataset(cfg)
    return _dataset


# --- validacion de parametros ------------------------------------------------
def resolve_zone(zone: str | None, bbox: str | None) -> tuple[tuple[float, float, float, float], str]:
    if bbox:
        try:
            w, s, e, n = (float(x) for x in bbox.split(","))
        except Exception:
            raise HTTPException(400, "bbox debe ser oeste,sur,este,norte")
        if not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
            raise HTTPException(400, "bbox fuera de rango o invertido")
        area = (e - w) * (n - s)
        if area > cfg.max_area_deg2:
            raise HTTPException(
                400,
                f"la zona es demasiado grande ({area:.0f} grados²). Maximo {cfg.max_area_deg2:.0f}. "
                "Usa una zona mas pequena o la zona precargada.",
            )
        return (w, s, e, n), f"Zona dibujada ({w:.2f}, {s:.2f}) - ({e:.2f}, {n:.2f})"
    key = zone or cfg.default_zone
    if key not in cfg.zones:
        raise HTTPException(404, f"zona desconocida: {key}")
    return cfg.zone_bbox(key), cfg.zone_name(key)


def parse_date(value: str | None, default: date) -> date:
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(400, f"fecha invalida: {value} (se espera AAAA-MM-DD)")


@lru_cache(maxsize=128)
def _calendar_cached(bb, zone_name, start, end, granularity, measure, sources, year):
    return build_calendar(
        cfg, dataset(), bb, start, end,
        granularity=granularity, measure=measure, sources=sources,
        zone_name=zone_name, selected_year=year,
    )


# --- endpoints ---------------------------------------------------------------
@app.get("/api/health")
def health():
    ds = dataset()
    return {"ok": True, "rows": int(len(ds.df)), "coverage": ds.coverage(), "version": cfg.version}


@app.get("/api/meta")
def meta():
    ds = dataset()
    cov = ds.coverage()
    return {
        "name": cfg.name,
        "version": cfg.version,
        "disclaimer": cfg.disclaimer,
        "zones": [
            {"key": k, "name": v["name"], "bbox": v["bbox"], "note": v.get("note", "")}
            for k, v in cfg.zones.items()
        ],
        "default_zone": cfg.default_zone,
        "coverage": cov,
        "measures": [{"key": m, "label": "celdas-día con fuego" if m == "cell_days" else "focos detectados"}
                     for m in cfg.measures],
        "default_measure": cfg.default_measure,
        "cell_deg": cfg.cell_deg,
        "sources": [{"key": "both", "label": "Ambos satélites"}, {"key": "modis", "label": "Solo MODIS"},
                    {"key": "viirs", "label": "Solo VIIRS"}],
        "thresholds": cfg.anomalies,
        "quality": {"min_conf_modis": cfg.min_conf_modis, "min_conf_viirs": cfg.min_conf_viirs},
        "months": MONTHS,
        "max_area_deg2": cfg.max_area_deg2,
    }


@app.get("/api/calendar")
def calendar(
    zone: str | None = None,
    bbox: str | None = None,
    start: str | None = None,
    end: str | None = None,
    granularity: Literal["month", "week"] = "month",
    measure: Literal["cell_days", "detections"] | None = None,
    sources: Literal["both", "modis", "viirs"] = "both",
    year: int | None = None,
):
    ds = dataset()
    bb, name = resolve_zone(zone, bbox)
    s = parse_date(start, ds.start)
    e = parse_date(end, ds.end)
    if s < ds.start:
        s = ds.start
    if e > ds.end:
        e = ds.end
    if s > e:
        raise HTTPException(400, "el rango de fechas queda fuera de los datos disponibles")
    payload = _calendar_cached(bb, name, s, e, granularity, measure or cfg.default_measure, sources, year)
    return payload


@app.get("/api/hotspots")
def hotspots(
    zone: str | None = None,
    bbox: str | None = None,
    start: str | None = None,
    end: str | None = None,
    sources: Literal["both", "modis", "viirs"] = "both",
    limit: int = 0,
):
    ds = dataset()
    bb, _ = resolve_zone(zone, bbox)
    s = parse_date(start, ds.start)
    e = parse_date(end, ds.end)
    cap = int(limit) if int(limit) > 0 else int(cfg.api["max_hotspots_geojson"])
    if cap > 100000:
        raise HTTPException(400, "limit maximo 100000")
    return hotspots_geojson(ds, bb, s, e, sources, cap)


def _filter(df: pd.DataFrame, bb, s: date, e: date, sources: str) -> pd.DataFrame:
    d0 = (s - date(1970, 1, 1)).days
    d1 = (e - date(1970, 1, 1)).days
    mask = ((df["day"] >= d0) & (df["day"] <= d1)
            & (df["lat"] >= bb[1]) & (df["lat"] <= bb[3])
            & (df["lon"] >= bb[0]) & (df["lon"] <= bb[2]))
    if sources == "modis":
        mask &= df["source"] == 1
    elif sources == "viirs":
        mask &= df["source"] == 2
    return df.loc[mask]


@app.get("/api/csv/hotspots")
def csv_hotspots(
    zone: str | None = None,
    bbox: str | None = None,
    start: str | None = None,
    end: str | None = None,
    sources: Literal["both", "modis", "viirs"] = "both",
):
    ds = dataset()
    bb, name = resolve_zone(zone, bbox)
    s = parse_date(start, ds.start)
    e = parse_date(end, ds.end)
    sub = _filter(ds.df, bb, s, e, sources).copy()
    if sub.empty:
        raise HTTPException(404, "no hay focos en esa zona y ese rango")

    def rows():
        header = "acq_date,latitude,longitude,satellite,confidence_level,confidence_raw,frp_mw,type\n"
        yield header
        dates = pd.to_datetime(sub["day"].astype("int64"), unit="D").dt.strftime("%Y-%m-%d")
        src = np.where(sub["source"].to_numpy() == 1, "MODIS", "VIIRS")
        frame = pd.DataFrame({
            "acq_date": dates.to_numpy(),
            "latitude": np.round(sub["lat"].to_numpy(), 4),
            "longitude": np.round(sub["lon"].to_numpy(), 4),
            "satellite": src,
            "confidence_level": sub["conf_level"].to_numpy(),
            "confidence_raw": sub["conf_raw"].to_numpy(),
            "frp_mw": np.round(sub["frp"].to_numpy(), 2),
            "type": sub["ftype"].to_numpy(),
        })
        for i in range(0, len(frame), 50000):
            buf = io.StringIO()
            frame.iloc[i:i + 50000].to_csv(buf, index=False, header=False, float_format="%.4f")
            yield buf.getvalue()

    fname = f"pyrochronos_focos_{s}_{e}.csv"
    return StreamingResponse(
        rows(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fname}"',
                 "X-Total-Rows": str(len(sub))},
    )


@app.get("/api/csv/series")
def csv_series(
    zone: str | None = None,
    bbox: str | None = None,
    start: str | None = None,
    end: str | None = None,
    granularity: Literal["month", "week"] = "month",
    measure: Literal["cell_days", "detections"] | None = None,
    sources: Literal["both", "modis", "viirs"] = "both",
):
    payload = calendar(zone=zone, bbox=bbox, start=start, end=end,
                       granularity=granularity, measure=measure, sources=sources)
    years = payload["calendar"]["years"]
    periods = payload["meta"]["periods"]
    labels = payload["meta"]["period_labels"]
    recs = []
    for i, y in enumerate(years):
        for j, p in enumerate(periods):
            v = payload["calendar"]["values"][i][j]
            if v is None:
                continue
            recs.append({
                "year": y,
                "period": p,
                "period_label": labels[j],
                "harmonized": round(v, 2),
                "estimated": bool(payload["calendar"]["estimated"][i][j]),
                "anomaly_pct": payload["calendar"]["anomaly_pct"][i][j],
                "level": payload["calendar"]["levels"][i][j],
                "measure": payload["meta"]["measure"],
                "zone": payload["meta"]["zone"],
            })
    buf = io.StringIO()
    pd.DataFrame(recs).to_csv(buf, index=False)
    fname = f"pyrochronos_serie_{granularity}_{payload['meta']['start']}_{payload['meta']['end']}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@app.get("/api/alert")
def alert(zone: str | None = None, bbox: str | None = None, date_ref: str | None = None, weeks: int = 4):
    """Semaforo de temporada de la zona (anticipatorio, con la historia de esa zona)."""
    ds = dataset()
    bb, name = resolve_zone(zone, bbox)
    ref = parse_date(date_ref, None) if date_ref else None
    if weeks < 1 or weeks > 12:
        raise HTTPException(400, "weeks debe estar entre 1 y 12")
    out = _alert_cached(bb, name, ref.isoformat() if ref else None, int(weeks))
    return out


def _alert_cached(bb, zone_name, ref_iso, weeks):
    from datetime import date as _date

    return build_alert(cfg, dataset(), bb, zone_name,
                       reference_date=_date.fromisoformat(ref_iso) if ref_iso else None,
                       lookahead_weeks=weeks)


@app.get("/api/recent")
def recent(zone: str | None = None, bbox: str | None = None):
    """Estado de los datos recientes (NRT) cargados. Si no hay, se dice claramente."""
    bb, _ = resolve_zone(zone, bbox)
    return nrt.stats(cfg, bb)


@app.get("/api/report")
def report(zone: str | None = None, bbox: str | None = None, start: str | None = None, end: str | None = None):
    """Reporte ejecutivo imprimible (Guardar como PDF desde el navegador)."""
    ds = dataset()
    bb, name = resolve_zone(zone, bbox)
    s = parse_date(start, ds.start)
    e = parse_date(end, ds.end)
    if s < ds.start:
        s = ds.start
    if e > ds.end:
        e = ds.end
    if s > e:
        raise HTTPException(400, "rango de fechas invalido")
    html = build_report_html(cfg, ds, bb, name, s, e)
    return HTMLResponse(html)


@app.get("/api/bulletin")
def bulletin(zone: str | None = None, years_back: int = 3):
    """Texto listo para pegar en un grupo de guardaparques (Telegram).

    El envio automatico vive en backend/scripts/notify_telegram.py y usa un token
    que solo existe en el servidor. Esta ruta solo redacta con cifras calculadas.
    """
    ds = dataset()
    key = zone or cfg.default_zone
    if key not in cfg.zones:
        raise HTTPException(404, f"zona desconocida: {key}")
    text = build_bulletin(cfg, ds, key, years_back)
    return {"zone": cfg.zone_name(key), "text": text, "note": "Historico, no es una alerta en tiempo real."}


# --- contexto meteorologico (NASA POWER, solo desde cache) -------------------
from pyro import power  # noqa: E402


@app.get("/api/climate-context")
def climate_context(zone: str | None = None, date_ref: str | None = None):
    """Déficit de lluvia y anomalía de Tmax de los últimos 30 días (NASA POWER).

    Lee `data/derived/power_<zona>.json` precargado con download_power.py. Si no
    existe, responde `available: false` con las instrucciones: no se inventa nada.
    """
    key = zone or cfg.default_zone
    if key not in cfg.zones:
        raise HTTPException(404, f"zona desconocida: {key}")
    ref = parse_date(date_ref, None) if date_ref else None
    return power.climate_context(cfg, key, ref)


# --- capa de campo (geocercas, validacion humana) ----------------------------
from pydantic import BaseModel, Field  # noqa: E402

from pyro import geofence, groundtruth  # noqa: E402


@app.get("/api/historical-grid")
def historical_grid(
    bbox: str | None = None,
    zone: str | None = None,
    start: str | None = None,
    end: str | None = None,
    granularity: Literal["month", "week"] = "week",
    measure: Literal["cell_days", "detections"] | None = None,
    sources: Literal["both", "modis", "viirs"] = "both",
    year: int | None = None,
):
    """Matriz del calendario en llamas para un BBox (mismo motor que /api/calendar)."""
    return calendar(zone=zone, bbox=bbox, start=start, end=end, granularity=granularity,
                    measure=measure, sources=sources, year=year)


class GeofenceIn(BaseModel):
    telegram_id: int
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    radius_km: float = Field(default=10.0, ge=1, le=100)
    name: str | None = None
    role: str | None = None


@app.post("/api/register-geofence")
def register_geofence(body: GeofenceIn, request: Request):
    """Registra la posicion de un usuario de campo y devuelve que focos tiene cerca.

    Solo lo usa el servidor (bot/CLI): si existe PYRO_SETUP_KEY, hay que mandarla en
    la cabecera X-Setup-Key. Nunca se llama desde el navegador con datos de terceros.
    """
    expected = env("PYRO_SETUP_KEY")
    if expected and request.headers.get("x-setup-key") != expected:
        raise HTTPException(401, "falta o no coincide la cabecera X-Setup-Key")
    rec = groundtruth.save_geofence(cfg, body.telegram_id, body.lat, body.lon,
                                    body.radius_km, body.name, body.role)
    recent_df, _ = nrt.load_recent(cfg)
    near = []
    if recent_df is not None and not recent_df.empty:
        bb = (body.lon - 0.5, body.lat - 0.5, body.lon + 0.5, body.lat + 0.5)
        window = recent_df[(recent_df["lat"] >= bb[1]) & (recent_df["lat"] <= bb[3])
                           & (recent_df["lon"] >= bb[0]) & (recent_df["lon"] <= bb[2])]
        if not window.empty:
            marked = geofence.mark_critical(window)
            hits = geofence.nearest(marked, body.lat, body.lon, body.radius_km)
            near = hits[["lat", "lon", "frp", "distance_km", "cardinal"]].round(4).to_dict("records")
    return {"ok": True, "geofence": rec, "nearby_critical_hotspots": near,
            "note": "Geocerca guardada. Los avisos los envia el bot, no la web."}


@app.get("/api/geofences")
def geofences():
    """Geocercas activas (para pintar los puestos de campo en el mapa)."""
    items = groundtruth.active_geofences(cfg)
    return {"count": len(items), "items": items}


class VerdictIn(BaseModel):
    hotspot_id: str
    verdict: Literal["fuego_real", "quema_agricola", "falsa_alarma"]
    telegram_id: int | None = None


@app.post("/api/groundtruth")
def post_groundtruth(body: VerdictIn):
    """Guarda una validacion humana (la misma que llega por los botones del bot)."""
    rec = groundtruth.save_verdict(cfg, body.hotspot_id, body.telegram_id, body.verdict)
    return {"ok": True, "record": rec, "summary": groundtruth.verdict_summary(cfg)}


@app.get("/api/groundtruth")
def get_groundtruth():
    """Veredictos de campo y su resumen."""
    return {"summary": groundtruth.verdict_summary(cfg), "items": groundtruth.load_verdicts(cfg)}


# --- frontend compilado ------------------------------------------------------
DIST = ROOT / "backend" / "webapp"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/")
    def index():
        return FileResponse(DIST / "index.html")

    @app.get("/{path:path}")
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, f"ruta de API desconocida: /{path}")
        target = DIST / path
        if target.is_file():
            return FileResponse(target)
        return FileResponse(DIST / "index.html")
