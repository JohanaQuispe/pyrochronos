import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api'
import TopBar from './components/TopBar.jsx'
import SummaryCards from './components/SummaryCards.jsx'
import CalendarHeatmap from './components/CalendarHeatmap.jsx'
import AnomalyChart from './components/AnomalyChart.jsx'
import MapPanel from './components/MapPanel.jsx'
import Downloads from './components/Downloads.jsx'
import HarmonizationPanel from './components/HarmonizationPanel.jsx'
import { fmt } from './lib/scale'

export default function App() {
  const [meta, setMeta] = useState(null)
  const [state, setState] = useState(null)
  const [data, setData] = useState(null)
  const [hotspots, setHotspots] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [hotLoading, setHotLoading] = useState(false)
  const reqId = useRef(0)

  // 1) metadatos
  useEffect(() => {
    const ctrl = new AbortController()
    api
      .meta(ctrl.signal)
      .then((m) => {
        setMeta(m)
        const zone = m.zones.find((z) => z.key === m.default_zone) || m.zones[0]
        setState({
          zone: zone.key,
          bbox: zone.bbox,
          customBBox: null,
          start: m.coverage.start,
          end: m.coverage.end,
          granularity: 'month',
          measure: m.default_measure,
          sources: 'both',
          year: null,
        })
      })
      .catch((e) => {
        if (e.name !== 'AbortError') setError(`No se pudo cargar la información inicial: ${e.message}`)
      })
    return () => ctrl.abort()
  }, [])

  const activeBBox = useMemo(() => {
    if (!state) return null
    if (state.bbox) return state.bbox
    const z = meta?.zones.find((zz) => zz.key === state.zone)
    return z ? z.bbox : null
  }, [state, meta])

  // 2) calendario
  useEffect(() => {
    if (!state || !activeBBox) return undefined
    const id = ++reqId.current
    const ctrl = new AbortController()
    setLoading(true)
    setError(null)
    api
      .calendar(
        {
          zone: state.zone === 'custom' ? undefined : state.zone,
          bbox: state.zone === 'custom' ? activeBBox.join(',') : undefined,
          start: state.start,
          end: state.end,
          granularity: state.granularity,
          measure: state.measure,
          sources: state.sources,
          year: state.year || undefined,
        },
        ctrl.signal,
      )
      .then((payload) => {
        if (id === reqId.current) {
          setData(payload)
          setLoading(false)
        }
      })
      .catch((e) => {
        if (e.name === 'AbortError') return
        if (id === reqId.current) {
          setError(e.message)
          setLoading(false)
        }
      })
    return () => ctrl.abort()
  }, [state, activeBBox])

  // 3) focos del mapa
  useEffect(() => {
    if (!state || !activeBBox || state.zone === 'custom' || state.bbox !== activeBBox) {
      // para zonas dibujadas también se piden focos
    }
    if (!state) return undefined
    const ctrl = new AbortController()
    setHotLoading(true)
    api
      .hotspots(
        {
          zone: state.zone === 'custom' ? undefined : state.zone,
          bbox: state.zone === 'custom' ? activeBBox.join(',') : undefined,
          start: state.start,
          end: state.end,
          sources: state.sources,
        },
        ctrl.signal,
      )
      .then((g) => {
        setHotspots(g)
        setHotLoading(false)
      })
      .catch((e) => {
        if (e.name !== 'AbortError') setHotLoading(false)
      })
    return () => ctrl.abort()
  }, [state, activeBBox])

  const onBBoxChange = useCallback(
    (bbox) => setState((s) => ({ ...s, zone: 'custom', bbox })),
    [],
  )

  const onShortcut = (kind) => {
    if (!meta || !state) return
    if (kind === 'all') setState((s) => ({ ...s, start: meta.coverage.start, end: meta.coverage.end }))
    if (kind === '5y') {
      const end = new Date(`${meta.coverage.end}T00:00:00Z`)
      const start = new Date(end)
      start.setUTCFullYear(end.getUTCFullYear() - 4)
      start.setUTCMonth(0)
      start.setUTCDate(1)
      setState((s) => ({ ...s, start: start.toISOString().slice(0, 10), end: meta.coverage.end }))
    }
  }

  const years = data?.calendar.years ?? []

  return (
    <div className="min-h-full bg-ink">
      <a
        href="#cal-title"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-fire focus:px-3 focus:py-1 focus:text-ink"
      >
        Saltar al calendario
      </a>

      {meta && state && (
        <TopBar meta={meta} state={state} setState={setState} years={years} onShortcut={onShortcut} />
      )}

      <div className="mx-auto max-w-[1600px] px-4 py-3">
        <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-[11px] text-amber-100">
          <span aria-hidden="true">⚠</span>
          <span>
            <strong>Datos reales</strong> de NASA FIRMS (archivos anuales por país, procesamiento estándar). La serie
            termina el <strong>{meta?.coverage.end ?? '…'}</strong>: no es detección en tiempo real ni predicción.
          </span>
        </div>

        <div aria-live="polite" className="sr-only">
          {loading ? 'Calculando el calendario…' : data ? 'Calendario actualizado' : 'Sin datos'}
        </div>

        {error && (
          <div role="alert" className="mb-3 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-100">
            {error}
          </div>
        )}

        {!data && loading && (
          <div className="grid gap-3 lg:grid-cols-[minmax(320px,34%)_1fr]">
            <div className="card h-[520px] animate-pulse bg-panel/60" />
            <div className="space-y-3">
              <div className="card h-24 animate-pulse bg-panel/60" />
              <div className="card h-72 animate-pulse bg-panel/60" />
            </div>
          </div>
        )}

        {data && state && (
          <div className="grid items-start gap-3 lg:grid-cols-[minmax(320px,34%)_1fr]">
            <div className="space-y-3 lg:sticky lg:top-3">
              <MapPanel
                bbox={activeBBox}
                hotspots={hotspots}
                meta={data.meta}
                onBBoxChange={onBBoxChange}
                loading={hotLoading}
              />
              <section className="card p-3" aria-labelledby="sum-title">
                <h2 id="sum-title" className="text-sm font-semibold text-white">
                  En una frase
                </h2>
                <p className="mt-1 text-[12px] leading-relaxed text-slate-200">{data.summary}</p>
                <p className="mt-2 text-[10.5px] leading-snug text-mist">
                  Este texto se arma con los números calculados por el sistema (plantillas, sin IA generativa).
                </p>
              </section>
              <Downloads params={{ ...state, bbox: state.zone === 'custom' ? activeBBox.join(',') : undefined }} data={data} />
            </div>

            <div className="space-y-3">
              <SummaryCards data={data} />
              <CalendarHeatmap data={data} onPickYear={(year) => setState((s) => ({ ...s, year }))} />
              <AnomalyChart
                data={data}
                years={years}
                onYearChange={(year) => setState((s) => ({ ...s, year }))}
              />
              <HarmonizationPanel data={data} />
              <section className="card p-3" aria-labelledby="how-title">
                <h2 id="how-title" className="text-sm font-semibold text-white">Cómo leer el calendario en 30 segundos</h2>
                <ol className="mt-1 list-decimal space-y-1 pl-5 text-[11.5px] leading-relaxed text-slate-200">
                  <li>Busca la columna más oscura/naranja: esa es tu temporada de fuego.</li>
                  <li>Recorre una fila: es un año completo. Compara filas para ver años anómalos.</li>
                  <li>
                    Los símbolos ▲ y ◆ marcan periodos por encima de lo normal; la trama rayada, valores estimados
                    porque en esa fecha solo existía MODIS.
                  </li>
                  <li>El número de arriba a la izquierda del mapa es el total de focos del rango elegido.</li>
                </ol>
              </section>
            </div>
          </div>
        )}

        <footer className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-line pt-3 text-[10.5px] text-mist">
          <span>
            Datos: NASA FIRMS (MODIS {meta?.coverage.modis.start}–{meta?.coverage.modis.end}; VIIRS S-NPP{' '}
            {meta?.coverage.viirs.start}–{meta?.coverage.viirs.end}). Dominio público.
          </span>
          <span>
            {fmt(meta?.coverage.detections)} detecciones en el almacén · {meta?.name} v{meta?.version}
          </span>
          <span>Licencia MIT · Uso de IA declarado en docs/ia.md</span>
          <span className="ml-auto">{meta?.disclaimer}</span>
        </footer>
      </div>
    </div>
  )
}
