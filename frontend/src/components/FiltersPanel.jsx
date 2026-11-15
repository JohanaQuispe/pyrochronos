import React, { useEffect, useRef } from 'react'

function Row({ title, hint, children }) {
  return (
    <div className="space-y-1.5 border-b border-white/[0.05] py-3 last:border-0">
      <p className="label">{title}</p>
      {children}
      {hint ? <p className="hint">{hint}</p> : null}
    </div>
  )
}

function Segmented({ options, value, onChange, name }) {
  return (
    <div role="group" aria-label={name} className="flex flex-wrap gap-1">
      {options.map(([key, text]) => (
        <button
          key={key}
          type="button"
          aria-pressed={value === key}
          onClick={() => onChange(key)}
          className={`seg ${value === key ? 'seg-on' : ''}`}
        >
          {text}
        </button>
      ))}
    </div>
  )
}

/**
 * Panel lateral de ajustes secundarios. Todo lo que ensuciaba la barra vive aquí.
 * Se abre con el botón "Filtros" y se cierra con Escape, la X o el fondo.
 */
export default function FiltersPanel({ open, onClose, state, setState, years }) {
  const closeRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    closeRef.current?.focus()
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null
  const set = (patch) => setState((s) => ({ ...s, ...patch }))

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-labelledby="filters-title">
      <button
        type="button"
        aria-label="Cerrar filtros"
        onClick={onClose}
        className="absolute inset-0 bg-black/60 backdrop-blur-[2px]"
      />
      <div className="relative flex h-full w-full max-w-[350px] flex-col border-l border-white/[0.07] bg-panel shadow-soft">
        <div className="flex items-center justify-between px-4 py-3">
          <h2 id="filters-title" className="text-[14px] font-medium text-white">
            Filtros avanzados
          </h2>
          <button ref={closeRef} type="button" className="btn-quiet" onClick={onClose} aria-label="Cerrar">
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 pb-4">
          <Row title="Agrupación" hint="La semana muestra el detalle fino de la temporada; el mes, la vista de conjunto.">
            <Segmented
              name="Agrupación del calendario"
              value={state.granularity}
              onChange={(granularity) => set({ granularity })}
              options={[['month', 'Mes'], ['week', 'Semana']]}
            />
          </Row>

          <Row title="Medida" hint="Celdas-día: cuántas celdas de ~1 km² tuvieron fuego. Focos: detecciones crudas.">
            <Segmented
              name="Medida"
              value={state.measure}
              onChange={(measure) => set({ measure })}
              options={[['cell_days', 'Celdas-día'], ['detections', 'Focos']]}
            />
          </Row>

          <Row title="Fuente" hint="Solo para verificar: muestra un satélite aislado. El calendario se armoniza siempre con ambos.">
            <select
              className="input w-full"
              aria-label="Fuente satelital"
              value={state.sources}
              onChange={(e) => set({ sources: e.target.value })}
            >
              <option value="both">Ambos (armonizado)</option>
              <option value="modis">Solo MODIS</option>
              <option value="viirs">Solo VIIRS</option>
            </select>
          </Row>

          <Row title="Paleta" hint="La rampa «Daltonismo» mantiene la lectura con deuteranopia o protanopia.">
            <Segmented
              name="Paleta de color"
              value={state.palette}
              onChange={(palette) => set({ palette })}
              options={[['fuego', 'Fuego'], ['daltonismo', 'Daltonismo']]}
            />
          </Row>

          <Row title="Año enfocado" hint="Resalta un año en el mapa y en el gráfico de anomalías.">
            <select
              className="input w-full"
              aria-label="Año enfocado"
              value={state.year || ''}
              onChange={(e) => set({ year: e.target.value ? Number(e.target.value) : null })}
            >
              <option value="">Todos los años</option>
              {years.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </Row>

          <button
            type="button"
            className="btn mt-3 w-full justify-center"
            onClick={() => set({ granularity: 'month', measure: 'cell_days', sources: 'both', palette: 'fuego', year: null })}
          >
            Restablecer
          </button>
        </div>
      </div>
    </div>
  )
}
