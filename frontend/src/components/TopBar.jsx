import React, { useState } from 'react'

export default function TopBar({ meta, state, setState, onShortcut, downloads, onExportPng, onOpenFilters }) {
  const [showDates, setShowDates] = useState(false)
  if (!meta) return null
  const { zones, coverage } = meta
  const range = showDates ? 'custom' : state.start === coverage.start && state.end === coverage.end ? 'all' : '5y'
  return (
    <header className="relative z-30 border-b border-white/[0.08] bg-[#0b0b0d]">
      <div className="mx-auto max-w-[1500px] px-4 sm:px-6">
        <div className="flex min-h-[74px] flex-wrap items-center gap-3 py-3 sm:gap-5">
          <a href="/" className="mr-auto flex min-w-[180px] items-center gap-3" aria-label="PyroChronos, inicio">
            <span aria-hidden="true" className="grid h-10 w-10 place-items-center rounded-xl border border-white/15 bg-white/[0.04] text-[18px] font-bold tracking-tight text-white">P<span className="sr-only">yroChronos</span></span>
            <span>
              <span className="block text-[16px] font-semibold leading-tight tracking-tight text-white">PyroChronos<span className="text-orange-400">.</span></span>
              <span className="mt-0.5 block text-[10px] font-medium uppercase tracking-[0.13em] text-zinc-500">Inteligencia territorial</span>
            </span>
          </a>
          <div className="hidden items-center gap-3 border-l border-white/10 pl-5 text-[11px] text-zinc-500 lg:flex">
            <span className="h-1.5 w-1.5 rounded-full bg-zinc-400" /> NASA FIRMS <span className="text-zinc-700">/</span> MODIS + VIIRS
          </div>
          <button type="button" className="btn" onClick={onOpenFilters} aria-haspopup="dialog">
            <span aria-hidden="true">☷</span> Filtros
          </button>
          <details className="relative">
            <summary className="btn cursor-pointer list-none marker:hidden">Descargar <span aria-hidden="true">↗</span></summary>
            <div className="absolute right-0 z-40 mt-2 w-[270px] overflow-hidden rounded-xl border border-white/10 bg-panel shadow-soft">
              <a className="block px-4 py-3 text-[13px] text-zinc-200 hover:bg-white/[0.05]" href={downloads.hotspots} download>CSV de focos <span className="block text-[11px] text-zinc-500">Fecha, ubicación y sensor</span></a>
              <a className="block px-4 py-3 text-[13px] text-zinc-200 hover:bg-white/[0.05]" href={downloads.series} download>CSV de la serie <span className="block text-[11px] text-zinc-500">Valores y estimaciones</span></a>
              <a className="block px-4 py-3 text-[13px] text-zinc-200 hover:bg-white/[0.05]" href={downloads.report} target="_blank" rel="noreferrer">Reporte ejecutivo (PDF) <span className="block text-[11px] text-zinc-500">Abrir e imprimir</span></a>
              <button type="button" className="block w-full px-4 py-3 text-left text-[13px] text-zinc-200 hover:bg-white/[0.05]" onClick={onExportPng}>Imagen del calendario (PNG)</button>
            </div>
          </details>
        </div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-t border-white/[0.06] py-3">
          <span className="mr-1 text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Área de análisis</span>
          <label className="sr-only" htmlFor="zone-select">Zona</label>
          <select id="zone-select" className="input min-w-0 max-w-full sm:min-w-[200px]" value={state.zone} onChange={(e) => {
            const key = e.target.value
            const z = zones.find((zz) => zz.key === key)
            setState((s) => ({ ...s, zone: key, bbox: z ? z.bbox : s.bbox, year: null }))
          }}>
            {zones.map((z) => <option key={z.key} value={z.key}>{z.name}</option>)}
            {state.zone === 'custom' && <option value="custom">Zona dibujada</option>}
          </select>
          <label className="sr-only" htmlFor="range-select">Rango de fechas</label>
          <select id="range-select" className="input" value={range} onChange={(e) => {
            if (e.target.value === 'custom') setShowDates(true)
            else { setShowDates(false); onShortcut(e.target.value) }
          }}>
            <option value="all">Todo el histórico</option>
            <option value="5y">Últimos 5 años</option>
            <option value="custom">Fechas exactas…</option>
          </select>
          {showDates && <div className="flex flex-wrap items-center gap-2">
            <input type="date" className="input" aria-label="Fecha inicial" min={coverage.start} max={coverage.end} value={state.start} onChange={(e) => setState((s) => ({ ...s, start: e.target.value }))} />
            <span className="text-zinc-500">—</span>
            <input type="date" className="input" aria-label="Fecha final" min={coverage.start} max={coverage.end} value={state.end} onChange={(e) => setState((s) => ({ ...s, end: e.target.value }))} />
          </div>}
          <span className="ml-auto hidden text-[11px] tabular-nums text-zinc-500 xl:block">Cobertura cargada: {coverage.start} — {coverage.end}</span>
        </div>
      </div>
    </header>
  )
}
