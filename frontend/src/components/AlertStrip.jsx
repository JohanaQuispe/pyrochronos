import React, { useState } from 'react'
import { fmt } from '../lib/scale'

const STYLES = {
  critico: {
    wrap: 'border-red-500/50 bg-red-500/10',
    dot: 'bg-red-500',
    text: 'text-red-200',
    icon: '🔥',
    word: 'Ventana crítica',
  },
  vigilancia: {
    wrap: 'border-amber-500/50 bg-amber-500/10',
    dot: 'bg-amber-400',
    text: 'text-amber-100',
    icon: '⚠',
    word: 'Vigilancia',
  },
  normal: {
    wrap: 'border-emerald-500/40 bg-emerald-500/10',
    dot: 'bg-emerald-500',
    text: 'text-emerald-100',
    icon: '✓',
    word: 'Fuera de temporada',
  },
}

export default function AlertStrip({ alert, loading, dateRef, setDateRef, zoneName }) {
  const [open, setOpen] = useState(false)
  const style = STYLES[alert?.level] || STYLES.normal
  const recent = alert?.recent || {}

  return (
    <section
      className={`card border ${style.wrap} px-3 py-2`}
      aria-live="polite"
      aria-label="Semáforo de temporada"
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${style.dot} text-[13px]`} aria-hidden="true">
          <span className="text-ink">{style.icon}</span>
        </span>

        <div className="min-w-[220px] flex-1">
          <p className={`text-[13px] font-semibold ${style.text}`}>
            {loading ? 'Calculando el semáforo…' : `${style.word} · ${zoneName || ''}`}
            {recent.available && !recent.empty ? (
              <span className="ml-2 rounded-full border border-line bg-panelHi px-2 py-0.5 text-[10px] font-normal text-mist">
                reciente: {fmt(recent.total)} focos ({fmt(recent.last_7_days)} en 7 días)
              </span>
            ) : null}
          </p>
          <p className="text-[11.5px] leading-snug text-slate-200">
            {alert?.reasons?.[2] || alert?.reasons?.[1] || 'Historial insuficiente en esta zona.'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-end gap-[3px]" aria-hidden="true">
            {(alert?.window || []).map((w) => (
              <span
                key={w.week}
                title={`Semana ${w.week}: ${(w.ratio * 100).toFixed(0)} % del pico histórico`}
                className={`w-[7px] rounded-sm ${w.in_peak ? 'bg-red-400' : 'bg-fire/70'}`}
                style={{ height: `${Math.max(5, 4 + w.ratio * 26)}px` }}
              />
            ))}
          </div>
          <div className="text-right">
            <p className="text-[10px] uppercase tracking-wide text-mist">Próximas semanas</p>
            <p className="text-[11px] text-slate-200">
              {alert?.window?.length ? `${alert.window.length} · máx ${(Math.max(...alert.window.map((w) => w.ratio)) * 100).toFixed(0)} % del pico` : '—'}
            </p>
          </div>
        </div>

        <button type="button" className="btn px-2 py-1 text-[11px]" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
          {open ? 'Ocultar detalle' : 'Qué hacer'}
        </button>
      </div>

      {open && (
        <div className="mt-2 grid gap-2 border-t border-line/70 pt-2 sm:grid-cols-[1fr_260px]">
          <div>
            <p className="text-[11px] font-semibold text-white">Por qué</p>
            <ul className="mt-0.5 list-disc space-y-0.5 pl-4 text-[11px] text-slate-200">
              {(alert?.reasons || []).map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
            <p className="mt-1.5 text-[11px] text-slate-200">
              <strong className="text-white">Qué hacer:</strong> {alert?.action}
            </p>
            <p className="mt-1 text-[10.5px] leading-snug text-mist">{alert?.disclaimer}</p>
          </div>
          <div className="rounded-lg border border-line bg-panelHi/50 p-2">
            <label className="block text-[10.5px] text-mist">
              Ver la zona en otra semana del año
              <input
                type="date"
                value={dateRef || ''}
                onChange={(e) => setDateRef(e.target.value)}
                className="mt-1 w-full rounded border border-line bg-panel px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
            <p className="mt-1 text-[10px] leading-snug text-mist">
              La fecha solo elige la semana del año que se compara con el historial; no cambia los datos del
              calendario. Útil para revisar cómo se ve la zona en plena temporada.
            </p>
            <button type="button" className="btn mt-1.5 w-full px-2 py-1 text-[10.5px]" onClick={() => setDateRef('')}>
              Volver a la semana actual
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
