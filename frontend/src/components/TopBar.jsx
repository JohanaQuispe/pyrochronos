import React from 'react'

function Flame() {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" aria-hidden="true" className="shrink-0">
      <path
        d="M12 2c3.2 4.2 6.5 6.6 6.5 11a6.5 6.5 0 1 1-13 0c0-2.1.9-3.6 2.2-5.2.5 1.6 1.4 2.4 2.3 2.6C9.4 8 10.3 5.2 12 2Z"
        fill="url(#g)"
      />
      <defs>
        <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#ffb703" />
          <stop offset="100%" stopColor="#ff6b1a" />
        </linearGradient>
      </defs>
    </svg>
  )
}

export default function TopBar({ meta, state, setState, years, onShortcut }) {
  if (!meta) return null
  const { zones, coverage } = meta
  return (
    <header className="border-b border-line bg-panel/70 backdrop-blur">
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-3 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <Flame />
          <div className="leading-tight">
            <h1 className="text-[15px] font-semibold tracking-tight text-white">PyroChronos</h1>
            <p className="text-[10.5px] text-mist">Calendario histórico de incendios · MODIS + VIIRS</p>
          </div>
        </div>

        <div className="mx-1 hidden h-8 w-px bg-line sm:block" />

        <label className="flex items-center gap-2">
          <span className="label">Zona</span>
          <select
            className="rounded-lg border border-line bg-panelHi px-2 py-1.5 text-sm"
            value={state.zone}
            onChange={(e) => {
              const key = e.target.value
              const z = zones.find((zz) => zz.key === key)
              setState((s) => ({ ...s, zone: key, bbox: null, customBBox: z ? z.bbox : s.customBBox }))
            }}
          >
            {zones.map((z) => (
              <option key={z.key} value={z.key}>{z.name}</option>
            ))}
            <option value="custom">Zona dibujada…</option>
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
        </div>

        <div className="flex gap-1">
          <button type="button" className="chip hover:border-fire/60" onClick={() => onShortcut('all')}>
            Todo el historial
          </button>
          <button type="button" className="chip hover:border-fire/60" onClick={() => onShortcut('5y')}>
            Últimos 5 años
          </button>
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-3">
          <fieldset className="flex items-center gap-1 rounded-lg border border-line bg-panelHi p-0.5">
            <legend className="sr-only">Agrupación del calendario</legend>
            {[['month', 'Mes'], ['week', 'Semana']].map(([key, text]) => (
              <button
                key={key}
                type="button"
                aria-pressed={state.granularity === key}
                className={`rounded-md px-2.5 py-1 text-sm ${
                  state.granularity === key ? 'bg-fire/20 text-ember' : 'text-mist hover:text-white'
                }`}
                onClick={() => setState((s) => ({ ...s, granularity: key }))}
              >
                {text}
              </button>
            ))}
          </fieldset>

          <label className="flex items-center gap-2">
            <span className="label">Medida</span>
            <select
              className="rounded-lg border border-line bg-panelHi px-2 py-1.5 text-sm"
              value={state.measure}
              onChange={(e) => setState((s) => ({ ...s, measure: e.target.value }))}
            >
              <option value="cell_days">Celdas-día con fuego</option>
              <option value="detections">Focos detectados</option>
            </select>
          </label>

          <label className="flex items-center gap-2" title="Modo de verificación: ver una sola fuente">
            <span className="label">Fuente</span>
            <select
              className="rounded-lg border border-line bg-panelHi/60 px-2 py-1.5 text-xs text-mist"
              value={state.sources}
              onChange={(e) => setState((s) => ({ ...s, sources: e.target.value }))}
            >
              <option value="both">Ambos (armonizado)</option>
              <option value="modis">Solo MODIS</option>
              <option value="viirs">Solo VIIRS</option>
            </select>
          </label>
        </div>
      </div>
      {years.length > 0 && (
        <div className="mx-auto flex max-w-[1600px] items-center gap-2 px-4 pb-2 text-[11px] text-mist">
          <span>
            Cobertura real de los datos: <strong className="text-slate-200">{meta.coverage.start}</strong> a{' '}
            <strong className="text-slate-200">{meta.coverage.end}</strong> · MODIS desde {meta.coverage.modis.start} ·
            VIIRS desde {meta.coverage.viirs.start}
          </span>
        </div>
      )}
    </header>
  )
}
