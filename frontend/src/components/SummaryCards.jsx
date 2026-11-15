import React from 'react'
import { fmt, fmtCompact } from '../lib/scale'

function Metric({ label, value, unit, hint, tone = 'quiet' }) {
  const accent = tone === 'warn' ? 'text-ember' : 'text-white'
  return (
    <div className="min-w-0 px-4 first:pl-0 last:pr-0">
      <p className="label truncate">{label}</p>
      <p className={`metric mt-2 ${accent}`}>
        {value}
        {unit ? <span className="ml-1 text-[12px] font-normal text-zinc-500">{unit}</span> : null}
      </p>
      <p className="hint mt-1 line-clamp-2">{hint}</p>
    </div>
  )
}

/**
 * Cuatro cifras, sin cajas: separadores finos en lugar de bordes.
 */
export default function SummaryCards({ data }) {
  if (!data) return null
  const { cards } = data
  const last = cards.last_month
  const unit = data.meta.measure_label
  const delta = last?.delta_pct

  return (
    <section aria-label="Cifras del periodo" className="grid grid-cols-2 divide-y divide-white/[0.06] rounded-2xl border border-white/[0.06] bg-white/[0.015] py-4 sm:divide-y-0 md:grid-cols-4 md:divide-x">
      <div className="pt-1 md:pt-0">
        <Metric
          label="Mes más activo"
          value={cards.most_active_month?.name ?? '—'}
          hint={`${fmt(cards.most_active_month?.value)} ${unit} · ${cards.most_active_month?.years_counted ?? 0} años`}
        />
      </div>
      <Metric
        label="Año más activo"
        value={cards.most_active_year?.period_year ?? '—'}
        hint={
          cards.most_active_year?.tie_within_uncertainty
            ? `Empate técnico con ${cards.most_active_year.runner_up?.period_year}: la diferencia cabe en la incertidumbre`
            : `${fmt(cards.most_active_year?.value)} ${unit}${cards.most_active_year?.estimated_share > 0.5 ? ' · estimado' : ''}`
        }
      />
      <Metric
        label="Último mes vs mediana"
        value={delta === null || delta === undefined ? '—' : `${delta > 0 ? '+' : ''}${delta.toFixed(0)}%`}
        tone={delta !== null && delta !== undefined && delta > 20 ? 'warn' : 'quiet'}
        hint={last ? `${last.name} ${last.period_year} · ${fmt(last.value)} vs ${fmt(last.median)}` : 'Sin datos'}
      />
      <Metric label="Focos en el rango" value={fmtCompact(cards.total_detections)} hint={`${fmt(cards.total_detections)} detecciones sin armonizar`} />
    </section>
  )
}
