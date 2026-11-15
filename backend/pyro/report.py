"""Reporte ejecutivo en HTML (imprimible -> PDF desde el navegador).

Se genera con los mismos numeros de la API: no hay texto inventado. La idea es que
un jefe de brigada o un gestor de tierras pueda llevarse una hoja con lo esencial.
"""
from __future__ import annotations

import base64
import html
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .calendar import build_calendar
from .alerts import build_alert
from .config import Config, ROOT
from .store import Dataset
from .summary import MONTHS, month_name, n

RAMP = ["#1b2440", "#3b2a63", "#6b2f6e", "#9c3f5a", "#c85a35", "#e8842a", "#ffc46b"]


def _bucket(value: float, maxv: float) -> int:
    if value is None or not np.isfinite(value) or maxv <= 0:
        return -1
    if value <= 0:
        return 0
    t = float(np.sqrt(min(value / maxv, 1.0)))
    return min(len(RAMP) - 1, int(t * len(RAMP)))


def _logo() -> str:
    path = ROOT / "frontend" / "public" / "favicon.png"
    if path.exists():
        return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()
    return ""


def build_report_html(cfg: Config, ds: Dataset, bbox, zone_name: str, start, end) -> str:
    payload = build_calendar(cfg, ds, bbox, start, end, "month", cfg.default_measure, "both", zone_name)
    alert = build_alert(cfg, ds, bbox, zone_name)
    cal = payload["calendar"]
    cards = payload["cards"]
    calib = payload["calibration"]
    values = np.array([[np.nan if v is None else v for v in row] for row in cal["values"]], dtype=float)
    maxv = float(cal["max_value"] or 1)
    levels = cal["levels"]
    years = cal["years"]

    # episodios marcados como extremos (los mas recientes primero)
    episodes = []
    for yi, y in enumerate(years):
        for xi, level in enumerate(levels[yi]):
            if level == "extremo":
                episodes.append((y, xi + 1, values[yi][xi], cal["anomaly_pct"][yi][xi]))
    episodes.sort(key=lambda t: (t[0], t[1]), reverse=True)

    rows = []
    for yi, year in enumerate(years):
        cells = []
        for xi in range(len(MONTHS)):
            v = values[yi][xi]
            if not np.isfinite(v):
                cells.append('<td class="na" title="sin dato">·</td>')
                continue
            b = _bucket(v, maxv)
            mark = ""
            if levels[yi][xi] == "extremo":
                mark = "◆"
            elif levels[yi][xi] == "alto":
                mark = "▲"
            est = ' style="background:' + RAMP[max(b, 0)] + '"'
            cells.append(f'<td{est} data-est="{int(bool(cal["estimated"][yi][xi]))}">{mark or int(round(v))}</td>')
        rows.append(f"<tr><th>{year}</th>{''.join(cells)}</tr>")

    recent = alert.get("recent") or {}
    recent_html = ""
    if recent.get("available") and not recent.get("empty"):
        recent_html = f"""
        <div class="box">
          <h3>Actividad reciente cargada (NRT)</h3>
          <p>{n(recent.get('total'))} focos en la zona · últimos 7 días: {n(recent.get('last_7_days'))}
          · MODIS {n(recent['per_source']['MODIS'])} · VIIRS {n(recent['per_source']['VIIRS'])}
          · actualizado {html.escape(str(recent.get('meta', {}).get('fetched_at', 'sin fecha')))}</p>
        </div>"""

    level_class = {"critico": "lv2", "vigilancia": "lv1", "normal": "lv0"}.get(alert["level"], "lv0")
    reasons = "".join(f"<li>{html.escape(r)}</li>" for r in alert.get("reasons", []))
    episodes_html = "".join(
        f"<tr><td>{month_name(m)} de {y}</td><td class='num'>{n(v)}</td><td class='num'>p{int(round(p))}</td></tr>"
        for y, m, v, p in episodes[:8]
    ) or "<tr><td colspan='3'>Sin periodos marcados como extremos con los umbrales actuales.</td></tr>"

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    logo = _logo()

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<title>PyroChronos · reporte ejecutivo · {html.escape(zone_name)}</title>
<style>
  @page {{ size: A4; margin: 14mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, "Segoe UI", Roboto, sans-serif; color: #101828; margin: 0; }}
  header {{ display: flex; gap: 14px; align-items: center; border-bottom: 3px solid #ff8a3d; padding-bottom: 10px; }}
  header img {{ width: 48px; height: 48px; border-radius: 10px; }}
  h1 {{ font-size: 19px; margin: 0; }}
  h2 {{ font-size: 13px; margin: 18px 0 6px; text-transform: uppercase; letter-spacing: .06em; color: #475467; }}
  h3 {{ font-size: 12px; margin: 0 0 4px; }}
  p, li, td, th {{ font-size: 11px; line-height: 1.45; }}
  .sub {{ color: #475467; font-size: 11px; margin: 2px 0 0; }}
  .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 12px; }}
  .card {{ border: 1px solid #e4e7ec; border-radius: 8px; padding: 8px 10px; }}
  .card .k {{ font-size: 10px; text-transform: uppercase; color: #667085; letter-spacing: .04em; }}
  .card .v {{ font-size: 17px; font-weight: 600; }}
  .box {{ border: 1px solid #e4e7ec; border-radius: 8px; padding: 10px; margin-top: 10px; }}
  .lv0 {{ border-left: 6px solid #12b76a; }}
  .lv1 {{ border-left: 6px solid #f79009; }}
  .lv2 {{ border-left: 6px solid #f04438; }}
  table.cal {{ border-collapse: collapse; width: 100%; }}
  table.cal th {{ font-weight: 500; color: #475467; font-size: 9px; padding: 2px; }}
  table.cal td {{ border: 1px solid #fff; text-align: center; font-size: 8.5px; padding: 3px 1px; color: #101828; }}
  table.cal td[data-est="1"] {{ font-style: italic; outline: 1px dashed #98a2b3; outline-offset: -2px; }}
  table.cal td.na {{ color: #98a2b3; background: #f9fafb; }}
  table.data {{ border-collapse: collapse; width: 100%; }}
  table.data th, table.data td {{ border-bottom: 1px solid #eaecf0; padding: 4px 6px; text-align: left; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .legend {{ display: flex; gap: 6px; align-items: center; font-size: 9px; color: #475467; margin-top: 6px; }}
  .legend span.sw {{ width: 16px; height: 9px; display: inline-block; border-radius: 2px; }}
  footer {{ margin-top: 16px; border-top: 1px solid #e4e7ec; padding-top: 8px; color: #667085; font-size: 9.5px; }}
  .print {{ position: fixed; right: 16px; top: 16px; background: #ff8a3d; color: #101828; border: 0;
           padding: 8px 14px; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer; }}
  @media print {{ .print {{ display: none; }} }}
</style></head>
<body>
<button class="print" onclick="window.print()">Imprimir / Guardar como PDF</button>
<header>
  {f'<img src="{logo}" alt="">' if logo else ''}
  <div>
    <h1>PyroChronos · Reporte ejecutivo</h1>
    <p class="sub">{html.escape(zone_name)} · {payload['meta']['start']} a {payload['meta']['end']} ·
    medida: {payload['meta']['measure_label']} armonizadas · generado {generated}</p>
  </div>
</header>

<div class="box {level_class}">
  <h3>{html.escape(alert['label'])} — {html.escape(alert['short'])}</h3>
  <ul>{reasons}</ul>
  <p><strong>Qué hacer:</strong> {html.escape(alert['action'])}</p>
  <p class="sub">{html.escape(alert['disclaimer'])}</p>
</div>

<div class="grid">
  <div class="card"><div class="k">Mes más activo</div><div class="v">{cards.get('most_active_month', {}).get('name', '—')}</div>
    <div class="sub">{n(cards.get('most_active_month', {}).get('value'))} celdas-día</div></div>
  <div class="card"><div class="k">Año más activo</div><div class="v">{cards.get('most_active_year', {}).get('period_year', '—')}</div>
    <div class="sub">{n(cards.get('most_active_year', {}).get('value'))} celdas-día</div></div>
  <div class="card"><div class="k">Último mes vs mediana</div>
    <div class="v">{('%+.0f%%' % cards['last_month']['delta_pct']) if cards.get('last_month', {}).get('delta_pct') is not None else '—'}</div>
    <div class="sub">{html.escape(str(cards.get('last_month', {}).get('level_label', '')))}</div></div>
  <div class="card"><div class="k">Focos en el rango</div><div class="v">{n(cards.get('total_detections'))}</div>
    <div class="sub">detecciones sin armonizar</div></div>
</div>

<h2>Temporada de fuego</h2>
<div class="box">
  <p><strong>{html.escape(cards.get('season', {}).get('label', 'sin temporada definida'))}</strong>
  · pico en {html.escape(cards.get('season', {}).get('peak_name', '—'))}
  · actividad de la temporada = {int(round(100 * cards.get('season', {}).get('share_of_peak', 0)))} % del mes pico.</p>
  <p class="sub">Criterio: meses con al menos un tercio de la actividad del mes de mayor actividad histórica.</p>
</div>

<h2>Calendario de actividad (filas = años, columnas = meses)</h2>
<table class="cal">
  <tr><th></th>{''.join(f'<th>{m[:3]}</th>' for m in MONTHS)}</tr>
  {''.join(rows)}
</table>
<div class="legend">
  <span>Menos</span>
  {''.join(f'<span class="sw" style="background:{c}"></span>' for c in RAMP)}
  <span>Más</span>
  <span>· · · borde punteado = valor estimado (antes de 2012, solo MODIS) · ▲ por encima de lo normal · ◆ muy por encima</span>
</div>

<h2>Periodos extremos recientes (percentil ≥ {payload['thresholds']['extreme']})</h2>
<table class="data">
  <tr><th>Periodo</th><th class="num">Celda-día</th><th class="num">Percentil</th></tr>
  {episodes_html}
</table>

{recent_html}

<h2>Cómo se armonizó (y qué no sabemos)</h2>
<div class="box">
  <p>Escala de referencia: actividad observada por los dos satélites juntos, en celdas-día de
  {payload['meta']['cell_deg']}° (≈1,1 km), contando una celda una vez por día y satélite.</p>
  <p>Factor VIIRS/MODIS: <strong>{calib['global_factor']}</strong>
  (banda p25–p75: {calib['global_p25']} – {calib['global_p75']}); concordancia de las series en el solape:
  <strong>r = {calib['agreement_r']}</strong> sobre {calib['agreement_n']} periodos;
  años de solape: {calib['overlap_years'][0]}–{calib['overlap_years'][-1] if calib['overlap_years'] else '—'}.</p>
  <p>Antes de 2012 solo existe MODIS: esos valores se estiman multiplicando por el factor del mismo mes
  y se marcan con borde punteado; su incertidumbre es la banda del factor. Desde 2012 el valor es observado.</p>
  <p><strong>Límites:</strong> el factor supone que la diferencia de sensibilidad entre satélites es estable;
  no modela cambios de versión ni la sustitución de Suomi-NPP por NOAA-20/21. Los años más recientes pueden
  ser reprocesados por NASA. El número de focos y las celdas-día no son intercambiables.</p>
</div>

<footer>
  Datos: NASA FIRMS, procesamiento estándar (MODIS {payload['meta']['coverage']['modis']['start']}–{payload['meta']['coverage']['modis']['end']};
  VIIRS S-NPP {payload['meta']['coverage']['viirs']['start']}–{payload['meta']['coverage']['viirs']['end']}). Dominio público.
  Calidad aplicada: MODIS ≥ {cfg.min_conf_modis}; VIIRS {', '.join(cfg.min_conf_viirs)}.
  Licencia del código: MIT. · {html.escape(cfg.disclaimer)}
</footer>
</body></html>"""
