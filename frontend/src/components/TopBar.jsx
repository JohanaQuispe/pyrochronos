import React, { useState } from 'react'

/**
 * Barra superior mínima: marca, zona, rango y las dos acciones que importan.
 * Todo lo demás vive en el panel de Filtros.
 */
export default function TopBar({ meta, state, setState, years, onShortcut, downloads, onExportPng, onOpenFilters }) {
  const [showDates, setShowDates] = useState(false)
  if (!meta) return null

  const { zones, coverage } = meta
  const preset =
    state.start === coverage.start && state.end === coverage.end
      ? 'all'
      : showDates
        ? 'custom'
        : 'range'

  return (
    <header className="sticky top-0 z-30 border-b border-white/[0.06] bg-[#090c12]/90 backdrop-blur-2xl">
      <div className="mx-auto flex h-16 max-w-[1600px] items-center gap-2 px-4">
        <a href="/" className="flex items-center gap-2.5" aria-label="PyroChronos, inicio">
          <img src="/logo.png" alt="" width="28" height="28" className="h-8 w-8 rounded-xl ring-1 ring-white/10" />
          <span className="leading-none">
            <span className="block text-[15px] font-semibold tracking-tight text-white">PyroChronos</span>
            <span className="hidden text-[10.5px] text-zinc-500 sm:block">FIRE INTELLIGENCE · PERÚ</span>
          </span>
        </a>

        <span aria-hidden="true" className="mx-1 hidden h-5 w-px bg-white/10 md:block" />

        <label className="sr-only" htmlFor="zone-select">
          Zona
        </label>
        <select
          id="zone-select"
          className="input h-8 max-w-[190px] border-transparent bg-transparent hover:border-white/10"
          value={state.zone}
          onChange={(e) => {
            const key = e.target.value
            const z = zones.find((zz) => zz.key === key)
            setState((s) => ({ ...s, zone: key, bbox: z ? z.bbox : s.bbox, year: null }))
          }}
        >
          {zones.map((z) => (
            <option key={z.key} value={z.key}>
              {z.name}
            </option>
          ))}
          {state.zone === 'custom' && <option value="custom">Zona dibujada</option>}
        </select>

        <label className="sr-only" htmlFor="range-select">
          Rango de fechas
        </label>
        <select
          id="range-select"
          className="input h-8 max-w-[150px] border-transparent bg-transparent hover:border-white/10"
          value={preset === 'range' ? 'all' : preset}
          onChange={(e) => {
            const value = e.target.value
            if (value === 'all') {
              setShowDates(false)
              onShortcut('all')
            } else if (value === '5y') {
              setShowDates(false)
              onShortcut('5y')
            } else {
              setShowDates(true)
            }
          }}
        >
          <option value="all">Todo el histórico</option>
          <option value="5y">Últimos 5 años</option>
          <option value="custom">Fechas exactas…</option>
        </select>

        {(preset === 'custom' || showDates) && (
          <div className="hidden items-center gap-1 md:flex">
            <input
              type="date"
              className="input h-8"
              aria-label="Fecha inicial"
              min={coverage.start}
              max={coverage.end}
              value={state.start}
              onChange={(e) => setState((s) => ({ ...s, start: e.target.value }))}
            />
            <span className="text-zinc-600">–</span>
            <input
              type="date"
              className="input h-8"
              aria-label="Fecha final"
              min={coverage.start}
              max={coverage.end}
              value={state.end}
              onChange={(e) => setState((s) => ({ ...s, end: e.target.value }))}
            />
          </div>
        )}

        <div className="ml-auto flex items-center gap-1.5">
          <button type="button" className="btn-quiet" onClick={onOpenFilters} aria-haspopup="dialog">
            <span aria-hidden="true">☰</span>
            <span className="hidden sm:inline">Filtros</span>
          </button>

          <details className="relative">
            <summary className="btn btn-primary cursor-pointer list-none marker:hidden">
              Descargar
              <span aria-hidden="true" className="text-[10px]">▾</span>
            </summary>
            <div className="absolute right-0 z-40 mt-2 w-[280px] overflow-hidden rounded-xl border border-white/10 bg-panel shadow-soft">
              <a className="block px-3 py-2.5 text-[13px] text-zinc-200 hover:bg-white/[0.05]" href={downloads.hotspots} download>
                CSV de focos
                <span className="block text-[10.5px] text-zinc-500">fecha, coordenadas, satélite, confianza, FRP</span>
              </a>
              <a className="block px-3 py-2.5 text-[13px] text-zinc-200 hover:bg-white/[0.05]" href={downloads.series} download>
                CSV de la serie
                <span className="block text-[10.5px] text-zinc-500">valor, estimado, percentil, clasificación</span>
              </a>
              <a
                className="block px-3 py-2.5 text-[13px] text-zinc-200 hover:bg-white/[0.05]"
                href={downloads.report}
                target="_blank"
                rel="noreferrer"
              >
                Reporte ejecutivo (PDF)
                <span className="block text-[10.5px] text-zinc-500">se abre listo para imprimir</span>
              </a>
              <button
                type="button"
                className="block w-full px-3 py-2.5 text-left text-[13px] text-zinc-200 hover:bg-white/[0.05]"
                onClick={onExportPng}
              >
                Imagen del calendario (PNG)
                <span className="block text-[10.5px] text-zinc-500">para presentaciones y WhatsApp</span>
              </button>
            </div>
          </details>
        </div>
      </div>
    </header>
  )
}
