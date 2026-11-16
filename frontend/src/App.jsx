import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api'
import TopBar from './components/TopBar.jsx'
import Tabs from './components/Tabs.jsx'
import FiltersPanel from './components/FiltersPanel.jsx'
import AlertStrip from './components/AlertStrip.jsx'
import SummaryCards from './components/SummaryCards.jsx'
import CalendarHeatmap from './components/CalendarHeatmap.jsx'
import AnomalyChart from './components/AnomalyChart.jsx'
import MapPanel from './components/MapPanel.jsx'
import HarmonizationPanel from './components/HarmonizationPanel.jsx'
import BulletinCard from './components/BulletinCard.jsx'
import FieldPanel from './components/FieldPanel.jsx'
import AssistantPanel from './components/AssistantPanel.jsx'
import { exportCalendarPng } from './lib/exportPng'
import { fmt } from './lib/scale'
import { LanguageProvider, useLanguage } from './i18n.jsx'

const BASE = import.meta.env.VITE_API_BASE || ''

export default function App() {
  return <LanguageProvider><AppContent /></LanguageProvider>
}

function AppContent() {
  const { lang, t } = useLanguage()
  const TABS = [
    { key: 'mapa', label: t('Mapa', 'Map') },
    { key: 'calendario', label: t('Historial', 'History') },
    { key: 'campo', label: t('Telegram y estado', 'Telegram & status') },
  ]
  const [meta, setMeta] = useState(null)
  const [state, setState] = useState(null)
  const [data, setData] = useState(null)
  const [alert, setAlert] = useState(null)
  const [alertLoading, setAlertLoading] = useState(true)
  const [dateRef, setDateRef] = useState('')
  const [hotspots, setHotspots] = useState(null)
  const [mapLayer, setMapLayer] = useState('recent')
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
    setData(null)
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
      report: `${BASE}/api/report?${qs({ ...zoneParams, start: state?.start, end: state?.end, language: lang })}`,
    }
  }, [state, zoneParams, lang])

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
        {t('Saltar al contenido', 'Skip to content')}
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

      <div className="border-b border-orange-200/10 bg-[#282019]">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between overflow-x-auto px-4 sm:px-6">
          <Tabs items={TABS} value={tab} onChange={setTab} />
          <p className="hidden text-[11px] text-zinc-600 md:block">
            {zoneName} · {t('histórico hasta', 'historical data through')} {meta?.coverage.end ?? '…'} · {years.length || '—'} {t('años', 'years')}
          </p>
        </div>
      </div>

      <main id="main" className="mx-auto max-w-[1600px] px-4 pb-10 pt-5 sm:px-6 sm:pt-7 lg:px-8">
        <div className="mb-6 flex flex-col justify-between gap-4 border-b border-white/[0.07] pb-5 sm:flex-row sm:items-end">
          <div>
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-orange-300">NASA FIRMS · MODIS + VIIRS · {zoneName || 'Perú'}</p>
            <h1 className="text-[25px] font-semibold tracking-tight text-white sm:text-[32px]">{t('Información satelital para bomberos y brigadas', 'Satellite information for firefighters and field teams')}</h1>
            <p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-zinc-300">{tab === 'calendario' ? t('Consulta temporadas y compara años anteriores. El historial es independiente de los datos recientes.', 'Explore seasons and compare past years. Historical data are separate from recent data.') : tab === 'campo' ? t('Revisa los datos recientes guardados y las ubicaciones registradas para avisos en Telegram.', 'Review saved recent data and locations registered for Telegram alerts.') : t('Elige tu zona y revisa los puntos recientes en el mapa. Consulta la fecha antes de usarlos.', 'Choose your area and review recent points on the map. Check their date before using them.')}</p>
          </div>
          <div className="self-start rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-[11px] text-zinc-300 sm:self-auto">
            <span className="block font-medium text-zinc-200">{t('Última fecha del archivo histórico', 'Latest date in historical file')}: {meta?.coverage.end || '—'}</span>
            <span className="block text-zinc-400">{t('Los datos recientes se muestran por separado en el mapa.', 'Recent data are shown separately on the map.')}</span>
          </div>
        </div>
        <div aria-live="polite" className="sr-only">
          {loading ? t('Calculando el calendario…', 'Calculating calendar…') : data ? t('Calendario actualizado', 'Calendar updated') : t('Sin datos', 'No data')}
        </div>

        {lang === 'en' && <p role="note" className="mb-4 rounded-xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-[12px] text-amber-100">Some server error details may remain in Spanish. To switch Telegram messages, send /language en to the bot.</p>}
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
              {state.sources === 'both' && <div role="note" className="rounded-xl border border-amber-400/20 bg-amber-400/[0.05] px-4 py-3 text-[12px] leading-relaxed text-zinc-300">
                <strong className="text-amber-200">{t('Cifras estimadas y ranking provisionales.', 'Estimated figures and rankings are provisional.')}</strong>
                <details className="mt-1"><summary className="cursor-pointer">{t('¿Por qué?', 'Why?')}</summary><p className="mt-1">{t('Se usan factores distintos para MODIS y VIIRS. Aún falta validar VIIRS y recalcular las cifras con tus datos.', 'Separate factors are used for MODIS and VIIRS. VIIRS still needs validation and figures must be recalculated with your data.')}</p></details>
              </div>}
              <CalendarHeatmap
                data={data}
                palette={state.palette}
                onPickYear={(year) => setState((s) => ({ ...s, year }))}
              />
              <div className="flex items-end justify-between pt-3"><div><p className="label">{t('Resumen de la zona', 'Area summary')}</p><h2 className="mt-1 text-[18px] font-semibold text-white">{t('La actividad en perspectiva', 'Activity in perspective')}</h2></div><span className="hidden text-[11px] text-zinc-500 sm:block">{t('PERIODO SELECCIONADO', 'SELECTED PERIOD')}</span></div>
              <SummaryCards data={data} />
              <AlertStrip alert={alert} loading={alertLoading} dateRef={dateRef} setDateRef={setDateRef} zoneName={zoneName} />

              <div className="grid gap-3 lg:grid-cols-[1.55fr_1fr]">
                <AnomalyChart data={data} years={years} onYearChange={(year) => setState((s) => ({ ...s, year }))} />
                <div className="space-y-3">
                  <section className="card p-4" aria-labelledby="how-title">
                    <h2 id="how-title" className="label">
                      {t('Cómo leerlo en 30 segundos', 'How to read this in 30 seconds')}
                    </h2>
                    <ol className="mt-2 space-y-1.5 text-[12px] leading-relaxed text-zinc-400">
                      <li>{t('1 · Cada fila es un año y cada columna un mes o una semana.', '1 · Each row is a year and each column a month or week.')}</li>
                      <li>{t('2 · Los colores más intensos indican valores mayores para la medida elegida.', '2 · Stronger colors indicate higher values for the selected measure.')}</li>
                      <li>{t('3 · ▲ y ◆ comparan cada periodo con su historial; las rayas indican estimaciones.', '3 · ▲ and ◆ compare each period with its history; hatching indicates estimates.')}</li>
                      <li>{t('4 · El indicador estacional usa el historial y, cuando hay, datos recientes; no predice incendios.', '4 · The seasonal indicator uses history and, when available, recent data; it does not predict fires.')}</li>
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
              zone={state?.zone}
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
            <section className="card border-orange-400/25 p-4" aria-labelledby="quick-guide-title">
              <h2 id="quick-guide-title" className="text-sm font-semibold text-white">{t('Cómo usar el mapa', 'How to use the map')}</h2>
              <ol className="mt-2 space-y-1.5 text-[12px] leading-relaxed text-zinc-300">
                <li>{t('1. Elige tu zona arriba y revisa la fecha de descarga.', '1. Choose your area above and check the download date.')}</li>
                <li>{t('2. Toca un punto para ver su fecha, ubicación y sensor.', '2. Select a point to see its date, location and sensor.')}</li>
                <li>{t('3. Verifica la información en campo y con fuentes oficiales.', '3. Verify the information in the field and with official sources.')}</li>
              </ol>
              <p className="mt-3 text-[11px] leading-relaxed text-amber-200">{t('Un punto de calor no confirma un incendio. Los datos pueden tener retraso; no son una alerta oficial.', 'A heat detection does not confirm a fire. Data may be delayed and are not an official warning.')}</p>
            </section>
            <AssistantPanel zoneParams={zoneParams} zoneName={zoneName} />
            <AlertStrip alert={alert} loading={alertLoading} dateRef={dateRef} setDateRef={setDateRef} zoneName={zoneName} />
          </div>
        </div>

        <div role="tabpanel" id="panel-campo" aria-labelledby="tab-campo" hidden={tab !== 'campo'} className="space-y-3">
          <FieldPanel zone={state?.zone} zoneParams={zoneParams} bbox={activeBBox} />
          {state && state.zone !== 'custom' && !state.zone.startsWith('d_') && <BulletinCard zone={state.zone} />}
        </div>

        <footer className="mt-6 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-white/[0.06] pt-4 text-[10.5px] text-zinc-600">
          <span>
            NASA FIRMS · MODIS {meta?.coverage.modis.start}–{meta?.coverage.modis.end} · VIIRS{' '}
            {meta?.coverage.viirs.start}–{meta?.coverage.viirs.end}
          </span>
          <span>{fmt(meta?.coverage.detections)} {t('detecciones', 'detections')} · {meta?.name} v{meta?.version}</span>
          <span>{t('MIT · IA declarada en docs/ia.md', 'MIT · AI disclosure in docs/ia.md')}</span>
          <span className="ml-auto text-right">{lang === 'en' ? 'Historical satellite heat detections. Not a real-time detection or fire prediction system.' : meta?.disclaimer}</span>
        </footer>
      </main>
    </div>
  )
}
