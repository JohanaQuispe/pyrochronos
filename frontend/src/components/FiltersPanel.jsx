import { useLanguage } from '../i18n.jsx'
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
  const { lang, t } = useLanguage()
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
        aria-label={t('Cerrar filtros', 'Close filters')}
        onClick={onClose}
        className="absolute inset-0 bg-black/60 backdrop-blur-[2px]"
      />
      <div className="relative flex h-full w-full max-w-[350px] flex-col border-l border-white/[0.07] bg-panel shadow-soft">
        <div className="flex items-center justify-between px-4 py-3">
          <h2 id="filters-title" className="text-[14px] font-medium text-white">
            {t('Filtros avanzados', 'Advanced filters')}
          </h2>
          <button ref={closeRef} type="button" className="btn-quiet" onClick={onClose} aria-label={t('Cerrar', 'Close')}>
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 pb-4">
          <Row title={t('Agrupación', 'Grouping')} hint={t('La semana muestra el detalle fino de la temporada; el mes, la vista de conjunto.', 'Weeks show detail; months provide an overview.')}>
            <Segmented
              name={t('Agrupación del calendario', 'Calendar grouping')}
              value={state.granularity}
              onChange={(granularity) => set({ granularity })}
              options={[['month', t('Mes', 'Month')], ['week', t('Semana', 'Week')]]}
            />
          </Row>

          <Row title={t('Medida', 'Measure')} hint={t('Celdas-día: celdas de ~1 km² con detecciones por día. Focos: detecciones sin armonizar.', 'Cell-days: grid cells with detections per day. Hotspots: raw detections.')}>
            <Segmented
              name={t('Medida', 'Measure')}
              value={state.measure}
              onChange={(measure) => set({ measure })}
              options={[['cell_days', t('Celdas-día', 'Cell-days')], ['detections', t('Focos', 'Hotspots')]]}
            />
          </Row>

          <Row title={t('Fuente', 'Source')} hint={t('Elige un satélite para ver sus observaciones o ambos para ver la serie armonizada.', 'Choose an individual satellite or the harmonized series.')}>
            <select
              className="input w-full"
              aria-label={t('Fuente satelital', 'Satellite source')}
              value={state.sources}
              onChange={(e) => set({ sources: e.target.value })}
            >
              <option value="both">{t('Ambos (armonizado)', 'Both (harmonized)')}</option>
              <option value="modis">{t('Solo MODIS', 'MODIS only')}</option>
              <option value="viirs">{t('Solo VIIRS', 'VIIRS only')}</option>
            </select>
          </Row>

          <Row title={t('Paleta', 'Palette')} hint={t('La rampa «Daltonismo» mantiene la lectura con deuteranopia o protanopia.', 'The colorblind palette remains readable with deuteranopia or protanopia.')}>
            <Segmented
              name={t('Paleta de color', 'Color palette')}
              value={state.palette}
              onChange={(palette) => set({ palette })}
              options={[['fuego', t('Fuego', 'Fire')], ['daltonismo', t('Daltonismo', 'Colorblind')]]}
            />
          </Row>

          <Row title={t('Año enfocado', 'Focused year')} hint={t('Resalta un año en el mapa y en el gráfico de anomalías.', 'Highlights a year in the map and anomaly chart.')}>
            <select
              className="input w-full"
              aria-label={t('Año enfocado', 'Focused year')}
              value={state.year || ''}
              onChange={(e) => set({ year: e.target.value ? Number(e.target.value) : null })}
            >
              <option value="">{t('Todos los años', 'All years')}</option>
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
            {t('Restablecer', 'Reset')}
          </button>
        </div>
      </div>
    </div>
  )
}
