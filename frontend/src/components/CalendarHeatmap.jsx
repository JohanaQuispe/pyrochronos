import React, { useCallback, useMemo, useRef, useState } from 'react'
import { MONTHS, MONTHS_SHORT, colorOf, fmt, legendSteps } from '../lib/scale'

const LEVEL_GLYPH = { alto: '▲', extremo: '◆' }

export default function CalendarHeatmap({ data, onPickYear }) {
  const [tip, setTip] = useState(null)
  const gridRef = useRef(null)
  const meta = data.meta
  const cal = data.calendar
  const periods = meta.periods
  const labels = meta.period_labels
  const max = cal.max_value || 1
  const isWeek = meta.granularity === 'week'
  const cellW = isWeek ? 19 : 0

  const template = useMemo(
    () => (isWeek ? `44px repeat(${periods.length}, ${cellW}px)` : `44px repeat(${periods.length}, minmax(0, 1fr))`),
    [isWeek, periods.length],
  )

  const describe = useCallback(
    (yi, xi) => {
      const value = cal.values[yi][xi]
      const year = cal.years[yi]
      const p = periods[xi]
      const label = isWeek ? `semana ${p}` : MONTHS[p - 1]
      if (value === null) return `${label} de ${year}: sin dato (fuera de la cobertura de los satélites)`
      const parts = [`${label} de ${year}: ${fmt(value)} celdas-día`]
      if (cal.estimated[yi][xi]) parts.push('valor estimado desde MODIS')
      if (cal.levels[yi][xi]) {
        parts.push(
          `percentil ${cal.anomaly_pct[yi][xi]} (${cal.levels[yi][xi] === 'extremo' ? 'muy por encima de lo normal' : cal.levels[yi][xi] === 'alto' ? 'por encima de lo normal' : 'dentro de lo normal'})`,
        )
      }
      return parts.join(' · ')
    },
    [cal, isWeek, periods],
  )

  const onKeyDown = (event) => {
    const keys = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Home', 'End']
    if (!keys.includes(event.key)) return
    const target = event.target
    if (!target?.dataset?.yi) return
    let yi = Number(target.dataset.yi)
    let xi = Number(target.dataset.xi)
    const lastY = cal.years.length - 1
    const lastX = periods.length - 1
    if (event.key === 'ArrowUp') yi = Math.max(0, yi - 1)
    if (event.key === 'ArrowDown') yi = Math.min(lastY, yi + 1)
    if (event.key === 'ArrowLeft') xi = Math.max(0, xi - 1)
    if (event.key === 'ArrowRight') xi = Math.min(lastX, xi + 1)
    if (event.key === 'Home') xi = 0
    if (event.key === 'End') xi = lastX
    event.preventDefault()
    const next = gridRef.current?.querySelector(`[data-yi="${yi}"][data-xi="${xi}"]`)
    if (next) next.focus()
  }

  const showTip = (event, yi, xi) => {
    const rect = event.currentTarget.getBoundingClientRect()
    setTip({ yi, xi, x: rect.left + rect.width / 2, y: rect.top, text: describe(yi, xi) })
  }

  return (
    <section className="card p-3" aria-labelledby="cal-title">
      <div className="mb-2 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 id="cal-title" className="text-sm font-semibold text-white">
            Calendario de actividad
          </h2>
          <p className="text-[11px] text-mist">
            Filas: años · Columnas: {isWeek ? 'semanas del año (1–53)' : 'meses'} · Color: {meta.measure_label}
            {meta.sources === 'both' ? ' armonizadas' : ` (solo ${meta.sources === 'modis' ? 'MODIS' : 'VIIRS'})`}
          </p>
        </div>
        <ul className="flex flex-wrap items-center gap-3 text-[11px] text-mist">
          <li className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-[3px] hatch border border-line" aria-hidden="true" />
            estimado (antes de 2012)
          </li>
          <li className="flex items-center gap-1.5">
            <span aria-hidden="true" className="text-[10px] text-white">▲</span> por encima de lo normal
          </li>
          <li className="flex items-center gap-1.5">
            <span aria-hidden="true" className="text-[10px] text-ember">◆</span> muy por encima
          </li>
          <li className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-[3px] border border-dashed border-line" aria-hidden="true" />
            sin dato
          </li>
        </ul>
      </div>

      <div className="overflow-x-auto pb-1">
        <div
          ref={gridRef}
          role="grid"
          aria-label={`Calendario de actividad por año y ${isWeek ? 'semana' : 'mes'}`}
          className="grid gap-[2px]"
          style={{ gridTemplateColumns: template, minWidth: isWeek ? 44 + periods.length * 21 : 520 }}
          onKeyDown={onKeyDown}
        >
          <div role="columnheader" aria-hidden="true" className="h-4" />
          {periods.map((p, xi) => (
            <div
              key={`h-${p}`}
              role="columnheader"
              className="h-4 text-center text-[9.5px] leading-4 text-mist"
              title={isWeek ? `Semana ${p}` : MONTHS[p - 1]}
            >
              {isWeek ? (p % 4 === 1 ? p : '') : MONTHS_SHORT[p - 1]}
            </div>
          ))}

          {cal.years.map((year, yi) => (
            <React.Fragment key={year}>
              <button
                type="button"
                role="rowheader"
                className={`pr-1 text-right text-[10.5px] tabular-nums ${
                  Number(data.chart.year) === year ? 'font-semibold text-ember' : 'text-mist hover:text-white'
                }`}
                onClick={() => onPickYear && onPickYear(year)}
                title={`Ver la comparación de ${year} con su mediana`}
              >
                {year}
              </button>
              {periods.map((p, xi) => {
                const value = cal.values[yi][xi]
                const level = cal.levels[yi][xi]
                const estimated = cal.estimated[yi][xi]
                const isNull = value === null
                const color = colorOf(value, max)
                return (
                  <button
                    key={`${year}-${p}`}
                    type="button"
                    role="gridcell"
                    tabIndex={yi === 0 && xi === 0 ? 0 : -1}
                    data-yi={yi}
                    data-xi={xi}
                    aria-label={describe(yi, xi)}
                    onMouseEnter={(e) => showTip(e, yi, xi)}
                    onMouseLeave={() => setTip(null)}
                    onFocus={(e) => showTip(e, yi, xi)}
                    onBlur={() => setTip(null)}
                    className={`relative overflow-hidden rounded-[2px] ${
                      isWeek ? 'h-[15px]' : 'h-[17px]'
                    } ${isNull ? 'border border-dashed border-line/70' : 'border border-black/20'} ${
                      level === 'extremo' ? 'ring-1 ring-ember' : ''
                    } hover:brightness-125`}
                    style={{ backgroundColor: isNull ? 'transparent' : color }}
                  >
                    {estimated && !isNull && <span className="hatch absolute inset-0" aria-hidden="true" />}
                    {level && LEVEL_GLYPH[level] && (
                      <span
                        aria-hidden="true"
                        className={`absolute right-[1px] top-[-2px] text-[8px] leading-3 ${
                          level === 'extremo' ? 'text-ember' : 'text-white/85'
                        }`}
                      >
                        {LEVEL_GLYPH[level]}
                      </span>
                    )}
                  </button>
                )
              })}
            </React.Fragment>
          ))}
        </div>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-2 text-[10.5px] text-mist">
        <span className="mr-1">Menos actividad</span>
        {legendSteps(max).map((s) => (
          <span key={s.color} className="flex items-center gap-1">
            <span className="inline-block h-3 w-4 rounded-[2px]" style={{ backgroundColor: s.color }} aria-hidden="true" />
            <span className="tabular-nums">{fmt(s.from)}–{fmt(s.to)}</span>
          </span>
        ))}
        <span className="ml-1">Más actividad</span>
        <span className="ml-auto text-[10px]">Escala cuadrática (raíz) para que se vean también los valores bajos.</span>
      </div>

      {tip && (
        <div
          role="status"
          className="pointer-events-none fixed z-50 max-w-xs -translate-x-1/2 -translate-y-full rounded-lg border border-line bg-panel px-2 py-1 text-[11px] text-slate-100 shadow-xl"
          style={{ left: tip.x, top: tip.y - 6 }}
        >
          {tip.text}
        </div>
      )}
    </section>
  )
}
