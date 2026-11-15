import React, { useState } from 'react'
import { fmt } from '../lib/scale'

const STYLES = {
  critico: { dot: 'bg-red-400', text: 'text-red-300', word: 'Ventana crítica', border: 'border-red-400/20' },
  vigilancia: { dot: 'bg-amber-400', text: 'text-amber-200', word: 'Vigilancia', border: 'border-amber-400/20' },
  normal: { dot: 'bg-zinc-400', text: 'text-zinc-200', word: 'Fuera de temporada', border: 'border-white/10' },
}

export default function AlertStrip({ alert, loading, dateRef, setDateRef, zoneName }) {
  const [open, setOpen] = useState(false)
  const available = !!alert && alert.available !== false && !!STYLES[alert.level]
  const style = available ? STYLES[alert.level] : STYLES.normal
  const recent = alert?.recent || {}
  return (
    <section aria-live="polite" aria-label="Semáforo de temporada" className={`overflow-hidden rounded-2xl border ${style.border} bg-[#151416]`}>
      <div className="grid gap-4 p-4 sm:p-5 lg:grid-cols-[250px_1fr_auto] lg:items-center">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Semáforo estacional · {zoneName}</p>
          <p className={`mt-2 flex items-center gap-2.5 text-[18px] font-semibold ${style.text}`}>
            <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${style.dot}`} aria-hidden="true" />
            {loading ? 'Calculando…' : available ? style.word : 'Sin información'}
          </p>
        </div>
        <div className="border-white/[0.08] lg:border-l lg:pl-5">
          <p className="text-[12px] leading-relaxed text-zinc-300">{loading ? 'Consultando el historial de la zona.' : alert?.reasons?.[2] || alert?.reasons?.[1] || 'No se pudo obtener el análisis estacional.'}</p>
          <p className="mt-1 text-[11px] text-zinc-500">Basado en el historial; no indica incendios activos ni es un pronóstico.</p>
          {recent.available && !recent.empty && <p className="mt-1 text-[11px] text-zinc-400">{fmt(recent.total)} focos en datos NRT cargados; verifica la fecha en el mapa.</p>}
        </div>
        <button type="button" className="btn justify-center" onClick={() => setOpen((o) => !o)} aria-expanded={open}>{open ? 'Ocultar detalle' : 'Ver detalle'} <span aria-hidden="true">{open ? '↑' : '↗'}</span></button>
      </div>
      {open && <div className="grid gap-4 border-t border-white/[0.06] p-4 sm:grid-cols-[1fr_240px] sm:p-5">
        <div className="space-y-2">
          <p className="label">Cómo se calculó</p>
          <ul className="space-y-1 text-[12px] leading-relaxed text-zinc-300">{(alert?.reasons || []).map((r) => <li key={r}>· {r}</li>)}</ul>
          {alert?.action && <p className="text-[12px] leading-relaxed text-zinc-300"><span className="text-white">Sugerencia:</span> {alert.action}</p>}
          <p className="hint">{alert?.disclaimer}</p>
        </div>
        <div className="space-y-2 rounded-xl border border-white/[0.06] p-3">
          <label className="block text-[11px] text-zinc-400">Ver otra semana del año<input type="date" value={dateRef || ''} onChange={(e) => setDateRef(e.target.value)} className="input mt-1 w-full" /></label>
          <p className="text-[11px] text-zinc-500">No cambia los datos del calendario.</p>
          <button type="button" className="btn w-full justify-center text-[11px]" onClick={() => setDateRef('')}>Volver a la semana actual</button>
        </div>
      </div>}
    </section>
  )
}
