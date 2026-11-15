import React from 'react'
import { fmt, fmtCompact } from '../lib/scale'

function Metric({ label, value, hint, index }) {
  return (
    <div className="min-w-0 rounded-2xl border border-white/[0.12] bg-panel p-4 shadow-soft sm:p-5">
      <div className="flex items-center justify-between gap-2"><p className="text-[12px] font-medium text-zinc-400">{label}</p><span aria-hidden="true" className="text-[10px] font-medium tabular-nums text-zinc-600">0{index}</span></div>
      <p className="mt-5 text-[25px] font-semibold leading-none tracking-tight text-white sm:text-[28px]">{value}</p>
      <p className="mt-2 min-h-[28px] text-[11px] leading-snug text-zinc-500">{hint}</p>
    </div>
  )
}

export default function SummaryCards({ data }) {
  if (!data) return null
  const { cards } = data
  const last = cards.last_month
  const unit = data.meta.measure_label
  const delta = last?.delta_pct
  return (
    <section aria-label="Cifras del periodo" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Metric index={1} label="Mes más activo" value={cards.most_active_month?.name ?? '—'} hint={`${fmt(cards.most_active_month?.value)} ${unit} · ${cards.most_active_month?.years_counted ?? 0} años`} />
      <Metric index={2} label="Año más activo" value={cards.most_active_year?.period_year ?? '—'} hint={cards.most_active_year?.tie_within_uncertainty ? `Empate técnico con ${cards.most_active_year.runner_up?.period_year}` : `${fmt(cards.most_active_year?.value)} ${unit} · sujeto a revisión`} />
      <Metric index={3} label="Último mes vs mediana" value={delta === null || delta === undefined ? '—' : `${delta > 0 ? '+' : ''}${delta.toFixed(0)}%`} hint={last ? `${last.name} ${last.period_year} · ${fmt(last.value)} vs ${fmt(last.median)}` : 'Sin datos'} />
      <Metric index={4} label="Focos en el rango" value={fmtCompact(cards.total_detections)} hint={`${fmt(cards.total_detections)} detecciones sin armonizar`} />
    </section>
  )
}
