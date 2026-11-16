import React, { useState } from 'react'
import { useLanguage } from '../i18n.jsx'

export default function TopBar({ meta, state, setState, onShortcut, downloads, onExportPng, onOpenFilters }) {
  const [showDates, setShowDates] = useState(false)
  const { lang, setLang, t } = useLanguage()
  if (!meta) return null
  const { zones, coverage } = meta
  const range = showDates ? 'custom' : state.start === coverage.start && state.end === coverage.end ? 'all' : '5y'
  return (
    <header className="relative z-30 border-b border-orange-200/10 bg-[#17130f]">
      <div className="mx-auto max-w-[1500px] px-4 sm:px-6">
        <div className="flex min-h-[74px] flex-wrap items-center gap-3 py-3 sm:gap-5">
          <a href="/" className="mr-auto flex min-w-[180px] items-center gap-3" aria-label={t('PyroChronos, inicio', 'PyroChronos, home')}>
            <img src="/logo.png" alt="" aria-hidden="true" className="h-11 w-11 rounded-xl border border-white/15 object-cover" />
            <span>
              <span className="block text-[16px] font-semibold leading-tight tracking-tight text-white">PyroChronos<span className="text-orange-400">.</span></span>
              <span className="mt-0.5 block text-[10px] font-medium uppercase tracking-[0.13em] text-zinc-500">{t('Inteligencia territorial', 'Territorial intelligence')}</span>
            </span>
          </a>
          <div className="hidden items-center gap-3 border-l border-white/10 pl-5 text-[11px] text-zinc-500 lg:flex">
            <span className="h-1.5 w-1.5 rounded-full bg-zinc-400" /> NASA FIRMS <span className="text-zinc-700">/</span> MODIS + VIIRS
          </div>
          <label className="flex items-center gap-2 text-[12px] text-mist">
            <span className="sr-only">{t('Idioma', 'Language')}</span>
            <select aria-label="Idioma / Language" className="input" value={lang} onChange={(e) => setLang(e.target.value)}>
              <option value="es">Español</option>
              <option value="en">English</option>
            </select>
          </label>
          <button type="button" className="btn" onClick={onOpenFilters} aria-haspopup="dialog">
            <span aria-hidden="true">☷</span> {t('Filtros', 'Filters')}
          </button>
          <details className="relative">
            <summary className="btn cursor-pointer list-none marker:hidden">{t('Descargar', 'Download')} <span aria-hidden="true">↗</span></summary>
            <div className="absolute right-0 z-40 mt-2 w-[270px] overflow-hidden rounded-xl border border-white/10 bg-panel shadow-soft">
              <a className="block px-4 py-3 text-[13px] text-zinc-200 hover:bg-white/[0.05]" href={downloads.hotspots} download>{t('CSV de focos', 'Hotspots CSV')} <span className="block text-[11px] text-zinc-500">{t('Fecha, ubicación y sensor', 'Date, location and sensor')}</span></a>
              <a className="block px-4 py-3 text-[13px] text-zinc-200 hover:bg-white/[0.05]" href={downloads.series} download>{t('CSV de la serie', 'Series CSV')} <span className="block text-[11px] text-zinc-500">{t('Valores y estimaciones', 'Values and estimates')}</span></a>
              <a className="block px-4 py-3 text-[13px] text-zinc-200 hover:bg-white/[0.05]" href={downloads.report} target="_blank" rel="noreferrer">{t('Reporte ejecutivo (PDF)', 'Executive report (PDF)')} <span className="block text-[11px] text-zinc-500">{t('Abrir e imprimir', 'Open and print')}</span></a>
              <button type="button" className="block w-full px-4 py-3 text-left text-[13px] text-zinc-200 hover:bg-white/[0.05]" onClick={onExportPng}>{t('Imagen del calendario (PNG)', 'Calendar image (PNG)')}</button>
            </div>
          </details>
        </div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-t border-white/[0.06] py-3">
          <span className="mr-1 text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">{t('Zona o departamento', 'Area or department')}</span>
          <label className="sr-only" htmlFor="zone-select">{t('Zona', 'Area')}</label>
          <select id="zone-select" className="input min-w-0 max-w-full sm:min-w-[200px]" value={state.zone} onChange={(e) => {
            const key = e.target.value
            const z = zones.find((zz) => zz.key === key)
            setState((s) => ({ ...s, zone: key, bbox: z ? z.bbox : s.bbox, year: null }))
          }}>
            <optgroup label={t('Zonas generales', 'General areas')}>{zones.filter((z) => z.kind !== 'department').map((z) => <option key={z.key} value={z.key}>{z.name}{z.key === 'peru' ? '' : t(' · zona aproximada', ' · approximate area')}</option>)}</optgroup>
            <optgroup label={t('Departamentos · límites simplificados', 'Departments · simplified boundaries')}>{zones.filter((z) => z.kind === 'department').map((z) => <option key={z.key} value={z.key}>{z.name}</option>)}</optgroup>
            {state.zone === 'custom' && <option value="custom">{t('Zona dibujada', 'Drawn area')}</option>}
          </select>
          <label className="text-[11px] text-zinc-400" htmlFor="range-select">{t('Fechas del historial', 'Historical dates')}</label>
          <select id="range-select" className="input" value={range} onChange={(e) => {
            if (e.target.value === 'custom') setShowDates(true)
            else { setShowDates(false); onShortcut(e.target.value) }
          }}>
            <option value="all">{t('Todo el histórico', 'Full history')}</option>
            <option value="5y">{t('Últimos 5 años', 'Last 5 years')}</option>
            <option value="custom">{t('Fechas exactas…', 'Custom dates…')}</option>
          </select>
          {showDates && <div className="flex flex-wrap items-center gap-2">
            <input type="date" className="input" aria-label={t('Fecha inicial', 'Start date')} min={coverage.start} max={coverage.end} value={state.start} onChange={(e) => setState((s) => ({ ...s, start: e.target.value }))} />
            <span className="text-zinc-500">—</span>
            <input type="date" className="input" aria-label={t('Fecha final', 'End date')} min={coverage.start} max={coverage.end} value={state.end} onChange={(e) => setState((s) => ({ ...s, end: e.target.value }))} />
          </div>}
          <span className="ml-auto hidden text-[11px] tabular-nums text-zinc-500 xl:block">{t('Archivo histórico:', 'Historical file:')} {coverage.start} — {coverage.end}</span>
        </div>
      </div>
    </header>
  )
}
