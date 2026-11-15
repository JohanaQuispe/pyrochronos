import React, { useState } from 'react'
import { fmt } from '../lib/scale'

const STYLES = {
  critico: { dot: 'bg-red-500', text: 'text-red-300', word: 'Ventana crítica', icon: '🔥' },
  vigilancia: { dot: 'bg-amber-400', text: 'text-amber-200', word: 'Vigilancia', icon: '⚠' },
  normal: { dot: 'bg-emerald-500', text: 'text-emerald-300', word: 'Fuera de temporada', icon: '✓' },
}

/**
 * Semáforo de temporada en una sola línea (el detalle se despliega).
 */
export default function AlertStrip({ alert, loading, dateRef, setDateRef, zoneName }) {
  const [open, setOpen] = useState(false)
  const style = STYLES[alert?.level] || STYLES.normal
  const recent = alert?.recent || {}
  const maxRatio = alert?.window?.length ? Math.max(...alert.window.map((w) => w.ratio)) : null

  return (
    <section aria-live="polite" aria-label="Semáforo de temporada" className="rounded-2xl border border-white/[0.06] bg-white/[0.015]">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3">
        <span className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${style.dot}`} aria-hidden="true" />
          <span className={`text-[13px] font-medium ${style.text}`}>
            {loading ? 'Calculando…' : style.word}
          </span>
        </span>
        <span className="text-[12.5px] text-zinc-400">{zoneName}</span>

        <span className="hidden text-[12px] text-zinc-500 sm:block">
          {alert?.reasons?.[2] || alert?.reasons?.[1] || 'Historial insuficiente en esta zona.'}
        </span>

        {recent.available && !recent.empty ? (
          <span className="chip">{fmt(recent.total)} focos recientes</span>
        ) : null}

        <div className="ml-auto flex items-center gap-3">
          <span className="hidden items-end gap-[3px] sm:flex" aria-hidden="true">
            {(alert?.window || []).map((w) => (
              <span
                key={w.week}
                title={`Semana ${w.week}: ${(w.ratio * 100).toFixed(0)} % del pico histórico`}
                className={`w-[5px] rounded-sm ${w.in_peak ? 'bg-fire' : 'bg-white/25'}`}
                style={{ height: `${Math.max(4, 3 + w.ratio * 20)}px` }}
              />
            ))}
          </span>
          {maxRatio !== null ? (
            <span className="hidden text-[11px] text-zinc-500 md:block">
              próximas {alert.window.length} sem · máx {(maxRatio * 100).toFixed(0)} % del pico
            </span>
          ) : null}
          <button
            type="button"
            className="btn-quiet text-[12px]"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
          >
            {open ? 'Ocultar' : 'Qué hacer'}
          </button>
        </div>
      </div>

      {open && (
        <div className="grid gap-4 border-t border-white/[0.06] px-4 py-3 sm:grid-cols-[1fr_240px]">
          <div className="space-y-1.5">
            <p className="label">Por qué</p>
            <ul className="space-y-0.5 text-[12px] leading-relaxed text-zinc-300">
              {(alert?.reasons || []).map((r) => (
                <li key={r}>· {r}</li>
              ))}
            </ul>
            <p className="text-[12px] leading-relaxed text-zinc-300">
              <span className="text-white">Qué hacer:</span> {alert?.action}
            </p>
            <p className="hint">{alert?.disclaimer}</p>
          </div>
          <div className="space-y-1.5 rounded-xl border border-white/[0.06] p-2.5">
            <label className="block text-[11px] text-zinc-500">
              Ver la zona en otra semana del año
              <input
                type="date"
                value={dateRef || ''}
                onChange={(e) => setDateRef(e.target.value)}
                className="input mt-1 w-full"
              />
            </label>
            <p className="text-[10.5px] leading-snug text-zinc-600">
              Solo elige qué semana del año se compara con el historial; no cambia los datos del calendario.
            </p>
            <button type="button" className="btn w-full justify-center text-[11px]" onClick={() => setDateRef('')}>
              Volver a la semana actual
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
