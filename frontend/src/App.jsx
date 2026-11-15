import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api'
import TopBar from './components/TopBar.jsx'
import Tabs from './components/Tabs.jsx'
import FiltersPanel from './components/FiltersPanel.jsx'
import AlertStrip from './components/AlertStrip.jsx'
import SummaryCards from './components/SummaryCards.jsx'
import ClimateCard from './components/ClimateCard.jsx'
import CalendarHeatmap from './components/CalendarHeatmap.jsx'
import AnomalyChart from './components/AnomalyChart.jsx'
import MapPanel from './components/MapPanel.jsx'
import HarmonizationPanel from './components/HarmonizationPanel.jsx'
import BulletinCard from './components/BulletinCard.jsx'
import FieldPanel from './components/FieldPanel.jsx'
import AssistantPanel from './components/AssistantPanel.jsx'
import { exportCalendarPng } from './lib/exportPng'
import { fmt } from './lib/scale'

const BASE = import.meta.env.VITE_API_BASE || ''

const TABS = [
  { key: 'mapa', label: 'Monitoreo', hint: 'campo' },
  { key: 'calendario', label: 'Histórico' },
  { key: 'campo', label: 'Campo y Telegram' },
]

export default function App() {
  const [meta, setMeta] = useState(null)
  const [state, setState] = useState(null)
  const [data, setData] = useState(null)
  const [alert, setAlert] = useState(null)
  const [alertLoading, setAlertLoading] = useState(true)
  const [dateRef, setDateRef] = useState('')
  const [hotspots, setHotspots] = useState(null)
  const [mapLayer, setMapLayer] = useState('history')
  const [mapSource, setMapSource] = useState('both')
  const [highConfidence, setHighConfidence] = useState(false)
  const [recentTick, setRecentTick] = useState(0)
  const [mapError, setMapError] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [hotLoading, setHotLoading] = useState(false)
  const [tab, setTab] = useState('mapa')
  const [filtersOpen, setFiltersOpen] = useState(false)
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
    return state.zone === 'custom' ? { bbox: activeBBox.join(',') } : { zone: state.zone }
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
    setAlert(null)
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

  // La capa NRT se relee del servidor; esta consulta no descarga datos de FIRMS.
  useEffect(() => {
    if (mapLayer !== 'recent') return undefined
    const timer = setInterval(() => setRecentTick((tick) => tick + 1), 60000)
    return () => clearInterval(timer)
  }, [mapLayer])

  // focos del mapa
  useEffect(() => {
    if (!state || !activeBBox) return undefined
    const ctrl = new AbortController()
    setHotLoading(true)
    setHotspots(null)
    setMapError(null)
    const common = { ...zoneParams, sources: mapSource, conf_min: highConfidence ? 2 : 0 }
    const request = mapLayer === 'recent'
      ? api.recentHotspots(common, ctrl.signal)
      : api.hotspots({ ...common, start: state.start, end: state.end }, ctrl.signal)
    request.then((g) => {
      setHotspots(g)
      setHotLoading(false)
    }).catch((e) => {
      if (e.name !== 'AbortError') {
        setMapError(e.message)
        setHotLoading(false)
      }
    })
    return () => ctrl.abort()
  }, [state, activeBBox, zoneParams, mapLayer, mapSource, highConfidence, recentTick])

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
    const common = { ...zoneParams, start: state?.start, end: state?.end, sources: state?.sources }
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
      window.alert(`No se pudo generar la imagen: ${e.message}`)
    }
  }

  const years = data?.calendar.years ?? []
  const zoneName =
    meta?.zones.find((z) => z.key === state?.zone)?.name || (state?.zone === 'custom' ? 'Zona dibujada' : '')

  return (
    <div className="min-h-full">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-ember focus:px-3 focus:py-1 focus:text-ink"
      >
        Saltar al contenido
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
          onOpenFilters={() => setFiltersOpen(true)}
        />
      )}

      {state && (
        <FiltersPanel
          open={filtersOpen}
          onClose={() => setFiltersOpen(false)}
          state={state}
          setState={setState}
          years={years}
        />
      )}

      <div className="border-b border-white/[0.06] bg-[#0b0b0d]">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between overflow-x-auto px-4 sm:px-6">
          <Tabs items={TABS} value={tab} onChange={setTab} />
          <p className="hidden text-[11px] text-zinc-600 md:block">
            {zoneName} · datos hasta {meta?.coverage.end ?? '…'} · {years.length || '—'} años
          </p>
        </div>
      </div>

      <main id="main" className="mx-auto max-w-[1500px] px-4 pb-10 pt-6 sm:px-6 sm:pt-8">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-500">Monitoreo territorial / {zoneName || 'Perú'}</p>
            <h1 className="text-[25px] font-semibold tracking-tight text-white sm:text-[32px]">{tab === 'calendario' ? 'Calendario histórico' : tab === 'campo' ? 'Campo y Telegram' : 'Mapa y alertas'}</h1>
            <p className="mt-1 max-w-2xl text-[13px] leading-relaxed text-zinc-400">{tab === 'calendario' ? 'Identifica patrones históricos de focos de calor en tu zona.' : tab === 'campo' ? 'Consulta el estado de los datos para el trabajo de campo.' : 'Explora las detecciones disponibles y sus coordenadas.'}</p>
          </div>
          <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] px-4 py-2 text-[11px] text-zinc-400">
            <span className="mr-2 inline-block h-1.5 w-1.5 rounded-full bg-zinc-400" /> Datos hasta <span className="font-medium tabular-nums text-zinc-200">{meta?.coverage.end || '—'}</span>
          </div>
        </div>
        <div aria-live="polite" className="sr-only">
          {loading ? 'Calculando el calendario…' : data ? 'Calendario actualizado' : 'Sin datos'}
        </div>

        {error && (
          <div role="alert" className="mb-3 rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-[13px] text-red-200">
            {error}
          </div>
        )}

        {!data && loading && (
          <div className="space-y-3">
            <div className="h-14 animate-pulse rounded-2xl bg-white/[0.03]" />
            <div className="h-32 animate-pulse rounded-2xl bg-white/[0.03]" />
            <div className="h-[420px] animate-pulse rounded-2xl bg-white/[0.03]" />
          </div>
        )}

        {/* --- Vista histórica ------------------------------------------- */}
        <div
          role="tabpanel"
          id="panel-calendario"
          aria-labelledby="tab-calendario"
          hidden={tab !== 'calendario'}
          className="space-y-3"
        >
          {data && state && (
            <>
              <AlertStrip alert={alert} loading={alertLoading} dateRef={dateRef} setDateRef={setDateRef} zoneName={zoneName} />
              {state.sources === 'both' && <div role="note" className="rounded-xl border border-amber-400/20 bg-amber-400/[0.05] px-4 py-3 text-[12px] leading-relaxed text-zinc-300"><strong className="text-amber-200">Resultados armonizados provisionales.</strong> Se está revisando el cálculo para periodos con VIIRS sin MODIS. No uses los totales o el ranking anual como definitivos.</div>}
              <div className="flex items-end justify-between pt-3"><div><p className="label">Resumen de la zona</p><h2 className="mt-1 text-[18px] font-semibold text-white">La actividad en perspectiva</h2></div><span className="hidden text-[11px] text-zinc-500 sm:block">PERIODO SELECCIONADO</span></div>
              <SummaryCards data={data} />

              <CalendarHeatmap
                data={data}
                palette={state.palette}
                onPickYear={(year) => setState((s) => ({ ...s, year }))}
              />

              <div className="grid gap-3 lg:grid-cols-[1.55fr_1fr]">
                <AnomalyChart data={data} years={years} onYearChange={(year) => setState((s) => ({ ...s, year }))} />
                <div className="space-y-3">
                  <ClimateCard zone={state.zone} />
                  <section className="card p-4" aria-labelledby="how-title">
                    <h2 id="how-title" className="label">
                      Cómo leerlo en 30 segundos
                    </h2>
                    <ol className="mt-2 space-y-1.5 text-[12px] leading-relaxed text-zinc-400">
                      <li>1 · La columna más intensa es la temporada de fuego de la zona.</li>
                      <li>2 · Cada fila es un año; compara filas para encontrar años anómalos.</li>
                      <li>3 · ▲ y ◆ marcan periodos sobre lo normal; la trama rayada indica valores estimados.</li>
                      <li>4 · El semáforo dice en qué punto de esa temporada estamos hoy.</li>
                    </ol>
                  </section>
                </div>
              </div>

              <HarmonizationPanel data={data} />
            </>
          )}
        </div>

        {/* --- Monitoreo táctico ----------------------------------------- */}
        <div
          role="tabpanel"
          id="panel-mapa"
          aria-labelledby="tab-mapa"
          hidden={tab !== 'mapa'}
          className="grid items-start gap-4 xl:grid-cols-[1.65fr_1fr]"
        >
          <div className="h-[680px] sm:h-[700px] xl:h-[calc(100vh-210px)] xl:min-h-[680px]">
            <MapPanel
              bbox={activeBBox}
              hotspots={hotspots}
              meta={data?.meta}
              onBBoxChange={onBBoxChange}
              loading={hotLoading}
              mapError={mapError}
              layer={mapLayer}
              onLayerChange={setMapLayer}
              source={mapSource}
              onSourceChange={setMapSource}
              highConfidence={highConfidence}
              onHighConfidenceChange={setHighConfidence}
              visible={tab === 'mapa'}
            />
          </div>

          <div className="space-y-3">
            <AssistantPanel zoneParams={zoneParams} zoneName={zoneName} />
            <AlertStrip alert={alert} loading={alertLoading} dateRef={dateRef} setDateRef={setDateRef} zoneName={zoneName} />
            <ClimateCard zone={state?.zone} />
            {state && state.zone !== 'custom' && <BulletinCard zone={state.zone} />}
            <section className="card p-4">
              <h2 className="label">Qué mirar aquí</h2>
              <p className="mt-2 text-[12px] leading-relaxed text-zinc-400">
                Los puntos son detecciones del periodo elegido. Dibuja un recuadro para analizar solo esa zona: el
                calendario y las cifras se recalculan para el área dibujada.
              </p>
              <p className="mt-2 text-[10.5px] leading-snug text-zinc-600">
                Un píxel de fuego no es un incendio confirmado: puede ser quema agrícola, una fuente industrial o una
                falsa alarma.
              </p>
            </section>
          </div>
        </div>

        <div role="tabpanel" id="panel-campo" aria-labelledby="tab-campo" hidden={tab !== 'campo'} className="space-y-3">
          <FieldPanel zone={state?.zone} zoneParams={zoneParams} />
          {state && state.zone !== 'custom' && <BulletinCard zone={state.zone} />}
        </div>

        <footer className="mt-6 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-white/[0.06] pt-4 text-[10.5px] text-zinc-600">
          <span>
            NASA FIRMS · MODIS {meta?.coverage.modis.start}–{meta?.coverage.modis.end} · VIIRS{' '}
            {meta?.coverage.viirs.start}–{meta?.coverage.viirs.end}
          </span>
          <span>{fmt(meta?.coverage.detections)} detecciones · {meta?.name} v{meta?.version}</span>
          <span>MIT · IA declarada en docs/ia.md</span>
          <span className="ml-auto text-right">{meta?.disclaimer}</span>
        </footer>
      </main>
    </div>
  )
}
