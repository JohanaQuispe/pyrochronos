import React from 'react'
import { fmt, fmtCompact } from '../lib/scale'

function Card({ title, children, tone = 'default', hint }) {
  const ring = tone === 'warn' ? 'border-fire/50' : 'border-line'
  return (
    <div className={`card ${ring} p-3`}>
      <p className="label">{title}</p>
      <div className="mt-1">{children}</div>
      {hint && <p className="mt-1 text-[11px] leading-snug text-mist">{hint}</p>}
    </div>
  )
}

export default function SummaryCards({ data }) {
  if (!data) return null
  const { cards } = data
  const last = cards.last_month
  const unit = data.meta.measure_label
  const delta = last?.delta_pct
  const tone = delta === null || delta === undefined ? 'default' : delta > 20 ? 'warn' : 'default'

  return (
    <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
      <Card title="Mes más activo" hint={cards.most_active_month ? `${cards.most_active_month.years_counted} años con datos` : undefined}>
        <p className="text-xl font-semibold capitalize text-white">{cards.most_active_month?.name ?? '—'}</p>
        <p className="text-xs text-mist">{fmt(cards.most_active_month?.value)} {unit} (armonizado)</p>
      </Card>

      <Card
        title="Año más activo"
        hint={
          cards.most_active_year?.tie_within_uncertainty
            ? `Empate técnico con ${cards.most_active_year.runner_up?.period_year}: la diferencia es menor que la incertidumbre.`
            : cards.most_active_year?.runner_up
              ? `Segundo: ${cards.most_active_year.runner_up.period_year} con ${fmt(cards.most_active_year.runner_up.value)}.`
              : undefined
        }
      >
        <p className="text-xl font-semibold text-white">{cards.most_active_year?.period_year ?? '—'}</p>
        <p className="text-xs text-mist">
          {fmt(cards.most_active_year?.value)} {unit}
          {cards.most_active_year?.estimated_share > 0.5 ? ' (estimado)' : ' (observado)'}
        </p>
      </Card>

      <Card
        title="Último mes vs mediana"
        tone={tone}
        hint={last ? `${last.name} de ${last.period_year} · ${last.level_label}` : undefined}
      >
        <p className="flex items-baseline gap-2 text-xl font-semibold text-white">
          {delta === null || delta === undefined ? '—' : `${delta > 0 ? '+' : ''}${delta.toFixed(0)}%`}
          <span className="text-xs font-normal text-mist">
            {last?.value !== undefined ? `(${fmt(last.value)} vs ${fmt(last.median)})` : ''}
          </span>
        </p>
      </Card>

      <Card title="Focos en el rango" hint="Detecciones tal como llegan de FIRMS (sin armonizar)">
        <p className="text-xl font-semibold text-white">{fmtCompact(cards.total_detections)}</p>
        <p className="text-xs text-mist">{fmt(cards.total_detections)} focos</p>
      </Card>
    </div>
  )
}
