import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api'
import TopBar from './components/TopBar.jsx'
import AlertStrip from './components/AlertStrip.jsx'
import SummaryCards from './components/SummaryCards.jsx'
import CalendarHeatmap from './components/CalendarHeatmap.jsx'
import AnomalyChart from './components/AnomalyChart.jsx'
import MapPanel from './components/MapPanel.jsx'
import ActionBar from './components/ActionBar.jsx'
import HarmonizationPanel from './components/HarmonizationPanel.jsx'
import BulletinCard from './components/BulletinCard.jsx'
import { exportCalendarPng } from './lib/exportPng'
import { fmt } from './lib/scale'

const BASE = import.meta.env.VITE_API_BASE || ''

export default function App() {
  const [meta, setMeta] = useState(null)
  const [state, setState] = useState(null)
  const [data, setData] = useState(null)
  const [alert, setAlert] = useState(null)
  const [alertLoading, setAlertLoading] = useState(true)
  const [dateRef, setDateRef] = useState('')
  const [hotspots, setHotspots] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [hotLoading, setHotLoading] = useState(false)
  const reqId = useRef(0)

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
          start: m.coverage.start,
          end: m.coverage.end,
          granularity: 'month',
          measure: m.default_measure,
          palette: 'fuego',
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

  const zoneParams = useMemo(() => {
    if (!state || !activeBBox) return {}
    return state.zone === 'custom'
      ? { bbox: activeBBox.join(',') }
      : { zone: state.zone }
  }, [state, activeBBox])

  // calendario
  useEffect(() => {
    if (!state || !activeBBox) return undefined
    const id = ++reqId.current
    const ctrl = new AbortController()
    setLoading(true)
    setError(null)
    api
      .calendar(
        {
          ...zoneParams,
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
  }, [state, activeBBox, zoneParams])

  // semáforo de temporada
  useEffect(() => {
    if (!state || !activeBBox) return undefined
    const ctrl = new AbortController()
    setAlertLoading(true)
    api
      .alert({ ...zoneParams, date_ref: dateRef || undefined }, ctrl.signal)
      .then((a) => {
        setAlert(a)
        setAlertLoading(false)
      })
      .catch((e) => {
        if (e.name !== 'AbortError') setAlertLoading(false)
      })
    return () => ctrl.abort()
  }, [state, activeBBox, zoneParams, dateRef])

  // focos del mapa
  useEffect(() => {
    if (!state || !activeBBox) return undefined
    const ctrl = new AbortController()
    setHotLoading(true)
    api
      .hotspots({ ...zoneParams, start: state.start, end: state.end, sources: state.sources }, ctrl.signal)
      .then((g) => {
        setHotspots(g)
        setHotLoading(false)
      })
      .catch((e) => {
        if (e.name !== 'AbortError') setHotLoading(false)
      })
    return () => ctrl.abort()
  }, [state, activeBBox, zoneParams])

  const onBBoxChange = useCallback((bbox) => setState((s) => ({ ...s, zone: 'custom', bbox })), [])

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

  const downloads = useMemo(() => {
    const common = {
      ...zoneParams,
      start: state?.start,
      end: state?.end,
      sources: state?.sources,
    }
    const qs = (obj) =>
      new URLSearchParams(
        Object.fromEntries(Object.entries(obj).filter(([, v]) => v !== undefined && v !== null && v !== '')),
      ).toString()
    return {
      hotspots: `${BASE}/api/csv/hotspots?${qs(common)}`,
      series: `${BASE}/api/csv/series?${qs({ ...common, granularity: state?.granularity, measure: state?.measure })}`,
      report: `${BASE}/api/report?${qs({ ...zoneParams, start: state?.start, end: state?.end })}`,
    }
  }, [state, zoneParams])

  const onExportPng = () => {
    if (!data) return
    try {
      exportCalendarPng(data, `pyrochronos_calendario_${data.meta.zone.replace(/\s+/g, '_')}.png`, state.palette)
    } catch (e) {
      alert(`No se pudo generar la imagen: ${e.message}`)
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
        <TopBar
          meta={meta}
          state={state}
          setState={setState}
          years={years}
          onShortcut={onShortcut}
          downloads={downloads}
          onExportPng={onExportPng}
        />
      )}

      <div className="mx-auto max-w-[1600px] px-4 py-3">
        <div aria-live="polite" className="sr-only">
          {loading ? 'Calculando el calendario…' : data ? 'Calendario actualizado' : 'Sin datos'}
        </div>

        {error && (
          <div role="alert" className="mb-3 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-100">
            {error}
          </div>
        )}

        <div className="mb-3 space-y-2">
          <AlertStrip
            alert={alert}
            loading={alertLoading}
            dateRef={dateRef}
            setDateRef={setDateRef}
            zoneName={meta?.zones.find((z) => z.key === state?.zone)?.name || (state?.zone === 'custom' ? 'Zona dibujada' : '')}
          />
          <p className="text-[10.5px] leading-snug text-mist">
            <strong className="text-slate-300">Datos reales de NASA FIRMS</strong> (archivos anuales por país,
            procesamiento estándar) hasta <strong className="text-slate-300">{meta?.coverage.end ?? '…'}</strong>. El
            semáforo usa la estacionalidad histórica de la zona; no es un pronóstico ni detección en tiempo real.
          </p>
        </div>

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
            <div className="space-y-3 lg:sticky lg:top-[104px]">
              <MapPanel
                bbox={activeBBox}
                hotspots={hotspots}
                meta={data.meta}
                onBBoxChange={onBBoxChange}
                loading={hotLoading}
              />
              <section className="card p-3" aria-labelledby="sum-title">
                <h2 id="sum-title" className="text-sm font-semibold text-white">En una frase</h2>
                {data.cards.season && (
                  <p className="mb-1.5 flex flex-wrap items-center gap-1.5">
                    <span className="rounded-full border border-fire/50 bg-fire/15 px-2 py-0.5 text-[11px] font-medium text-ember">
                      Temporada de fuego: {data.cards.season.label}
                    </span>
                    <span className="text-[10.5px] text-mist">pico en {data.cards.season.peak_name}</span>
                  </p>
                )}
                <p className="mt-1 text-[12px] leading-relaxed text-slate-200">{data.summary}</p>
                <p className="mt-2 text-[10.5px] leading-snug text-mist">
                  Texto armado con plantillas sobre los números del sistema (sin IA generativa).
                </p>
              </section>
              {state.zone !== 'custom' && <BulletinCard zone={state.zone} />}
            </div>

            <div className="space-y-3">
              <SummaryCards data={data} />
              <CalendarHeatmap
                data={data}
                palette={state.palette}
                onPickYear={(year) => setState((s) => ({ ...s, year }))}
              />
              <AnomalyChart data={data} years={years} onYearChange={(year) => setState((s) => ({ ...s, year }))} />
              <ActionBar downloads={downloads} data={data} onExportPng={onExportPng} />
              <HarmonizationPanel data={data} />
              <section className="card p-3" aria-labelledby="how-title">
                <h2 id="how-title" className="text-sm font-semibold text-white">Cómo leer el calendario en 30 segundos</h2>
                <ol className="mt-1 list-decimal space-y-1 pl-5 text-[11.5px] leading-relaxed text-slate-200">
                  <li>Busca la columna más intensa: esa es tu temporada de fuego.</li>
                  <li>Recorre una fila: es un año completo. Compara filas para ver años anómalos.</li>
                  <li>
                    ▲ y ◆ marcan periodos por encima de lo normal; la trama rayada, valores estimados porque en esa
                    fecha solo existía MODIS.
                  </li>
                  <li>El semáforo de arriba dice en qué punto de esa temporada estás hoy.</li>
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
          <span>{fmt(meta?.coverage.detections)} detecciones en el almacén · {meta?.name} v{meta?.version}</span>
          <span>Licencia MIT · Uso de IA declarado en docs/ia.md</span>
          <span className="ml-auto">{meta?.disclaimer}</span>
        </footer>
      </div>
    </div>
  )
}
