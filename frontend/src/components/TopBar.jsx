import React from 'react'

export default function TopBar({
  meta, state, setState, years, onShortcut, downloads, onExportPng,
}) {
  if (!meta) return null
  const { zones, coverage } = meta
  const seg = (key, text) => (
    <button
      key={key}
      type="button"
      aria-pressed={state.granularity === key}
      className={`rounded-md px-2.5 py-1 text-[13px] ${
        state.granularity === key ? 'bg-fire/20 text-ember' : 'text-mist hover:text-white'
      }`}
      onClick={() => setState((s) => ({ ...s, granularity: key }))}
    >
      {text}
    </button>
  )

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-panel/95 backdrop-blur">
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-x-3 gap-y-2 px-4 py-2">
        <a href="/" className="flex items-center gap-2" aria-label="PyroChronos, inicio">
          <img
            src="/logo.png"
            alt=""
            width="34"
            height="34"
            className="h-[34px] w-[34px] rounded-lg ring-1 ring-fire/30"
          />
          <span className="leading-tight">
            <span className="block text-[15px] font-semibold tracking-tight text-white">PyroChronos</span>
            <span className="hidden text-[10.5px] text-mist sm:block">Calendario de incendios · MODIS + VIIRS</span>
          </span>
        </a>

        <div className="mx-1 hidden h-8 w-px bg-line lg:block" />

        <label className="flex items-center gap-2">
          <span className="label">Zona</span>
          <select
            className="max-w-[220px] rounded-lg border border-line bg-panelHi px-2 py-1.5 text-sm"
            value={state.zone}
            onChange={(e) => {
              const key = e.target.value
              const z = zones.find((zz) => zz.key === key)
              setState((s) => ({ ...s, zone: key, bbox: z ? z.bbox : s.bbox, year: null }))
            }}
          >
            {zones.map((z) => (
              <option key={z.key} value={z.key}>{z.name}</option>
            ))}
            {state.zone === 'custom' && <option value="custom">Zona dibujada</option>}
          </select>
        </label>

        <div className="flex items-center gap-1.5">
          <span className="label">Rango</span>
          <input
            type="date"
            aria-label="Fecha inicial"
            className="rounded-lg border border-line bg-panelHi px-2 py-1.5 text-sm"
            min={coverage.start}
            max={coverage.end}
            value={state.start}
            onChange={(e) => setState((s) => ({ ...s, start: e.target.value }))}
          />
          <span className="text-mist">–</span>
          <input
            type="date"
            aria-label="Fecha final"
            className="rounded-lg border border-line bg-panelHi px-2 py-1.5 text-sm"
            min={coverage.start}
            max={coverage.end}
            value={state.end}
            onChange={(e) => setState((s) => ({ ...s, end: e.target.value }))}
          />
          <button type="button" className="chip hover:border-fire/60" onClick={() => onShortcut('all')}>
            Todo
          </button>
          <button type="button" className="chip hover:border-fire/60" onClick={() => onShortcut('5y')}>
            5 años
          </button>
        </div>

        <fieldset className="flex items-center gap-1 rounded-lg border border-line bg-panelHi p-0.5">
          <legend className="sr-only">Agrupación del calendario</legend>
          <span className="px-1 text-[11px] text-mist">Ver por</span>
          {seg('week', 'Semana')}
          {seg('month', 'Mes')}
        </fieldset>

        <div className="ml-auto flex items-center gap-2">
          <details className="relative">
            <summary className="btn btn-primary cursor-pointer list-none px-3 py-1.5 text-sm marker:hidden">
              Descargar <span aria-hidden="true">▾</span>
            </summary>
            <div className="absolute right-0 z-40 mt-1 w-64 overflow-hidden rounded-xl border border-line bg-panel shadow-2xl">
              <a className="block px-3 py-2 text-sm hover:bg-panelHi" href={downloads.hotspots} download>
                CSV de focos del periodo
                <span className="block text-[10.5px] text-mist">fecha, coordenadas, satélite, confianza, FRP</span>
              </a>
              <a className="block px-3 py-2 text-sm hover:bg-panelHi" href={downloads.series} download>
                CSV de la serie armonizada
                <span className="block text-[10.5px] text-mist">valor, estimado, percentil y clasificación</span>
              </a>
              <a className="block px-3 py-2 text-sm hover:bg-panelHi" href={downloads.report} target="_blank" rel="noreferrer">
                Reporte ejecutivo (PDF)
                <span className="block text-[10.5px] text-mist">se abre listo para imprimir o guardar</span>
              </a>
              <button type="button" className="block w-full px-3 py-2 text-left text-sm hover:bg-panelHi" onClick={onExportPng}>
                Imagen del calendario (PNG)
                <span className="block text-[10.5px] text-mist">para presentaciones y WhatsApp</span>
              </button>
            </div>
          </details>
        </div>
      </div>

      <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-x-3 gap-y-1 border-t border-line/60 px-4 py-1.5">
        <fieldset className="flex items-center gap-1 rounded-lg border border-line bg-panelHi p-0.5">
          <legend className="sr-only">Medida</legend>
          <span className="px-1 text-[11px] text-mist">Medida</span>
          {[['cell_days', 'Celdas-día'], ['detections', 'Focos']].map(([key, text]) => (
            <button
              key={key}
              type="button"
              aria-pressed={state.measure === key}
              className={`rounded-md px-2 py-0.5 text-[12px] ${
                state.measure === key ? 'bg-fire/20 text-ember' : 'text-mist hover:text-white'
              }`}
              onClick={() => setState((s) => ({ ...s, measure: key }))}
            >
              {text}
            </button>
          ))}
        </fieldset>

        <fieldset className="flex items-center gap-1 rounded-lg border border-line bg-panelHi p-0.5">
          <legend className="sr-only">Paleta de color</legend>
          <span className="px-1 text-[11px] text-mist">Paleta</span>
          {[['fuego', 'Fuego'], ['daltonismo', 'Daltonismo']].map(([key, text]) => (
            <button
              key={key}
              type="button"
              aria-pressed={state.palette === key}
              className={`rounded-md px-2 py-0.5 text-[12px] ${
                state.palette === key ? 'bg-fire/20 text-ember' : 'text-mist hover:text-white'
              }`}
              onClick={() => setState((s) => ({ ...s, palette: key }))}
            >
              {text}
            </button>
          ))}
        </fieldset>

        <label className="flex items-center gap-1.5" title="Modo de verificación: ver una sola fuente">
          <span className="text-[11px] text-mist">Fuente</span>
          <select
            className="rounded-lg border border-line bg-panelHi/60 px-2 py-0.5 text-xs text-mist"
            value={state.sources}
            onChange={(e) => setState((s) => ({ ...s, sources: e.target.value }))}
          >
            <option value="both">Ambos (armonizado)</option>
            <option value="modis">Solo MODIS</option>
            <option value="viirs">Solo VIIRS</option>
          </select>
        </label>

        <p className="ml-auto text-[10.5px] text-mist">
          Datos {coverage.start} → {coverage.end} · MODIS desde {coverage.modis.start} · VIIRS desde{' '}
          {coverage.viirs.start}
          {years.length ? ` · ${years.length} años en el calendario` : ''}
        </p>
      </div>
    </header>
  )
}
