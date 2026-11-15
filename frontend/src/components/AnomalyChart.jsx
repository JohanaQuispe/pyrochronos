import React, { useMemo } from 'react'
import { MONTHS, MONTHS_SHORT, fmt } from '../lib/scale'
import { useLanguage, monthName } from '../i18n.jsx'

const W = 900
const H = 260
const PAD = { l: 46, r: 14, t: 14, b: 26 }

export default function AnomalyChart({ data, onYearChange, years }) {
  const { lang, t } = useLanguage()
  const chart = data.chart
  const isWeek = data.meta.granularity === 'week'

  const { pathYear, pathMedian, pathBand, ticks, xOf, max } = useMemo(() => {
    const n = chart.labels.length
    const vals = [...chart.value, ...chart.median, ...(chart.p75 || [])].filter(
      (v) => v !== null && v !== undefined,
    )
    const max = Math.max(1, ...vals) * 1.08
    const xOf = (i) => PAD.l + (i * (W - PAD.l - PAD.r)) / Math.max(1, n - 1)
    const yOf = (v) => H - PAD.b - (v / max) * (H - PAD.t - PAD.b)

    const line = (arr) => {
      let d = ''
      let open = false
      arr.forEach((v, i) => {
        if (v === null || v === undefined) {
          open = false
          return
        }
        d += `${open ? 'L' : 'M'}${xOf(i).toFixed(1)},${yOf(v).toFixed(1)} `
        open = true
      })
      return d.trim()
    }

    let band = ''
    if (chart.p25 && chart.p75) {
      const top = chart.p75.map((v, i) => [xOf(i), v])
      const bottom = [...chart.p25].reverse().map((v, i) => [xOf(chart.p25.length - 1 - i), v])
      const pts = [...top.filter(([, v]) => v !== null), ...bottom.filter(([, v]) => v !== null)]
      if (pts.length > 1) {
        band = `M${pts[0][0].toFixed(1)},${yOf(pts[0][1]).toFixed(1)} ` +
          pts.slice(1).map(([x, v]) => `L${x.toFixed(1)},${yOf(v).toFixed(1)}`).join(' ') + ' Z'
      }
    }
    const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => ({ v: max * f, y: yOf(max * f) }))
    return { n, pathYear: line(chart.value), pathMedian: line(chart.median), pathBand: band, ticks, xOf, max }
  }, [chart])

  const yOf = (v) => H - PAD.b - (v / max) * (H - PAD.t - PAD.b)

  return (
    <section className="card p-3" aria-labelledby="chart-title">
      <div className="mb-2 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 id="chart-title" className="text-sm font-semibold text-white">
            {chart.year} {t('frente a la mediana histórica', 'vs historical median')}
          </h2>
          <p className="text-[11px] text-mist">
            {t('Cada punto es', 'Each point is')} {isWeek ? t('una semana', 'a week') : t('un mes', 'a month')}{t('; la línea gris es la mediana de los demás años y la banda el rango entre percentiles 25 y 75.', '; the gray line is the median of other years, and the band is the 25th–75th percentile range.')}
          </p>
        </div>
        <label className="flex items-center gap-2 text-[11px] text-mist">
          {t('Año', 'Year')}
          <select
            className="rounded-lg border border-line bg-panelHi px-2 py-1 text-sm text-slate-100"
            value={chart.year}
            onChange={(e) => onYearChange(Number(e.target.value))}
          >
            {years.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </label>
      </div>

      <figure className="m-0">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="w-full"
          role="img"
          aria-label={`${t('Actividad de', 'Activity in')} ${chart.year} ${t('frente a la mediana histórica y la banda de percentiles 25 a 75', 'vs the historical median and 25th–75th percentile band')}`}
        >
          <title>{t('Actividad de', 'Activity in')} {chart.year} {t('frente a la mediana histórica', 'vs historical median')}</title>
          <desc>
            {t('La línea naranja es', 'The orange line is')} {chart.year}{t(', la línea gris discontinua es la mediana de los demás años y la banda gris el rango entre los percentiles 25 y 75.', '; the dashed gray line is the median of the other years and the band shows the 25th–75th percentiles.')}
          </desc>
          {ticks.map((t) => (
            <g key={t.y}>
              <line x1={PAD.l} x2={W - PAD.r} y1={t.y} y2={t.y} stroke="#504337" strokeWidth="1" />
              <text x={PAD.l - 6} y={t.y + 3} textAnchor="end" fontSize="9.5" fill="#e2d2bc">
                {fmt(t.v, 0)}
              </text>
            </g>
          ))}
          {pathBand && <path d={pathBand} fill="#665341" opacity="0.75" />}
          {pathMedian && (
            <path d={pathMedian} fill="none" stroke="#e2d2bc" strokeWidth="1.6" strokeDasharray="5 3" />
          )}
          {pathYear && <path d={pathYear} fill="none" stroke="#ff8a3d" strokeWidth="2.4" strokeLinejoin="round" />}
          {chart.value.map((v, i) =>
            v === null ? null : (
              <circle key={i} cx={xOf(i)} cy={yOf(v)} r="2.4" fill="#ffb703">
                <title>{`${isWeek ? `${t('Semana', 'Week')} ${chart.labels[i]}` : monthName(MONTHS[chart.labels[i] - 1], lang)}: ${fmt(v)}`}</title>
              </circle>
            ),
          )}
          {(isWeek ? chart.labels.filter((p) => p % 4 === 1) : chart.labels).map((p) => {
            const i = chart.labels.indexOf(p)
            return (
              <text key={p} x={xOf(i)} y={H - 8} textAnchor="middle" fontSize="9.5" fill="#e2d2bc">
                {isWeek ? p : (lang === 'en' ? monthName(MONTHS[p - 1], lang).slice(0, 3) : MONTHS_SHORT[p - 1])}
              </text>
            )
          })}
        </svg>
        <figcaption className="mt-1 flex flex-wrap items-center gap-3 text-[10.5px] text-mist">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-[2px] w-5 bg-[#ff8a3d]" aria-hidden="true" /> {chart.year}
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-[2px] w-5 border-t border-dashed border-mist" aria-hidden="true" /> {t('mediana histórica', 'historical median')}
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-4 bg-[#665341]" aria-hidden="true" /> {t('percentiles 25–75', '25th–75th percentiles')}
          </span>
        </figcaption>
      </figure>
    </section>
  )
}
