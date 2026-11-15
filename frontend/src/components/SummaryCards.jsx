import { useLanguage, monthName } from '../i18n.jsx'
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
  const { lang, t } = useLanguage()
  if (!data) return null
  const { cards } = data
  const last = cards.last_month
  const unit = lang === 'en' ? (data.meta.measure === 'cell_days' ? 'cell-days' : 'detections') : data.meta.measure_label
  const delta = last?.delta_pct
  return (
    <section aria-label={t('Cifras del periodo', 'Period figures')} className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Metric index={1} label={t('Mes más activo', 'Most active month')} value={lang === 'en' ? monthName(cards.most_active_month?.name, lang) ?? '—' : cards.most_active_month?.name ?? '—'} hint={`${fmt(cards.most_active_month?.value)} ${unit} · ${cards.most_active_month?.years_counted ?? 0} ${t('años', 'years')}`} />
      <Metric index={2} label={t('Año más activo', 'Most active year')} value={cards.most_active_year?.period_year ?? '—'} hint={cards.most_active_year?.tie_within_uncertainty ? `${t('Empate técnico con', 'Statistical tie with')} ${cards.most_active_year.runner_up?.period_year}` : `${fmt(cards.most_active_year?.value)} ${unit} · ${t('sujeto a revisión', 'under review')}`} />
      <Metric index={3} label={t('Último mes vs mediana', 'Last month vs median')} value={delta === null || delta === undefined ? '—' : `${delta > 0 ? '+' : ''}${delta.toFixed(0)}%`} hint={last ? `${monthName(last.name, lang)} ${last.period_year} · ${fmt(last.value)} vs ${fmt(last.median)}` : t('Sin datos', 'No data')} />
      <Metric index={4} label={t('Focos en el rango', 'Hotspots in range')} value={fmtCompact(cards.total_detections)} hint={`${fmt(cards.total_detections)} ${t('detecciones sin armonizar', 'unharmonized detections')}`} />
    </section>
  )
}
