import React, { useEffect, useState } from 'react'
import { api } from '../api.js'

const LEVEL = {
  seco: { text: 'text-amber-200', dot: 'bg-amber-400' },
  humedo: { text: 'text-sky-300', dot: 'bg-sky-400' },
  normal: { text: 'text-emerald-300', dot: 'bg-emerald-500' },
  sin_datos: { text: 'text-zinc-400', dot: 'bg-zinc-600' },
}

function num(value, digits = 0, suffix = '') {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return `${Number(value).toFixed(digits).replace('.', ',')}${suffix}`
}

/**
 * Contexto de los últimos 30 días (NASA POWER precargado).
 * Si no hay datos, se dice en una línea, sin comandos ni bloques de código.
 */
export default function ClimateCard({ zone }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!zone || zone === 'custom') {
      setData(null)
      return undefined
    }
    const ctrl = new AbortController()
    setError(null)
    api
      .climate({ zone }, ctrl.signal)
      .then(setData)
      .catch((e) => {
        if (e.name !== 'AbortError') setError(e.message)
      })
    return () => ctrl.abort()
  }, [zone])

  if (error) {
    return (
      <section className="card p-4" role="alert">
        <p className="label">Contexto climático</p>
        <p className="mt-1 text-[12px] text-amber-200">No disponible: {error}</p>
      </section>
    )
  }

  if (!data) {
    return (
      <section className="card p-4" aria-busy="true">
        <p className="label">Contexto climático</p>
        <div className="mt-3 h-3 w-2/3 animate-pulse rounded bg-white/[0.06]" />
      </section>
    )
  }

  if (data.available === false) {
    return (
      <section className="card p-4">
        <div className="flex items-center justify-between gap-2">
          <p className="label">Contexto climático</p>
          <span className="chip">sin datos</span>
        </div>
        <p className="mt-2 text-[12.5px] leading-relaxed text-zinc-400">
          Falta precargar NASA POWER para esta zona. El calendario y el semáforo funcionan igual: esto solo añade
          el estado del combustible (lluvia y temperatura de los últimos 30 días).
        </p>
      </section>
    )
  }

  const style = LEVEL[data.level] || LEVEL.sin_datos
  const deficit = data.rain_deficit_pct
  const sign = deficit === null || deficit === undefined || deficit <= 0 ? '' : '+'

  return (
    <section className="card p-4" aria-labelledby="climate-title">
      <div className="flex items-center justify-between gap-2">
        <p id="climate-title" className="label">Contexto climático · 30 días</p>
        <span className={`flex items-center gap-1.5 text-[12px] ${style.text}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} aria-hidden="true" />
          {data.label}
        </span>
      </div>

      <dl className="mt-3 grid grid-cols-3 gap-3">
        <div>
          <dt className="text-[10.5px] uppercase tracking-wider text-zinc-500">Lluvia</dt>
          <dd className="mt-1 text-[15px] font-medium text-white">{num(data.window?.rain_mm, 0, ' mm')}</dd>
          <dd className="text-[10.5px] text-zinc-500">
            {deficit === null || deficit === undefined ? 'sin comparación' : `${sign}${num(deficit, 0, ' %')} vs. años previos`}
          </dd>
        </div>
        <div>
          <dt className="text-[10.5px] uppercase tracking-wider text-zinc-500">T máx</dt>
          <dd className="mt-1 text-[15px] font-medium text-white">{num(data.window?.tmax_mean_c, 1, ' °C')}</dd>
          <dd className="text-[10.5px] text-zinc-500">
            {data.tmax_anomaly_c === null || data.tmax_anomaly_c === undefined
              ? 'sin comparación'
              : `${data.tmax_anomaly_c > 0 ? '+' : ''}${num(data.tmax_anomaly_c, 1, ' °C')} de anomalía`}
          </dd>
        </div>
        <div>
          <dt className="text-[10.5px] uppercase tracking-wider text-zinc-500">Días secos</dt>
          <dd className="mt-1 text-[15px] font-medium text-white">{num(data.window?.dry_days, 0)}</dd>
          <dd className="text-[10.5px] text-zinc-500">de {num(data.window?.days, 0)}</dd>
        </div>
      </dl>

      <p className="mt-3 text-[10.5px] leading-snug text-zinc-600">
        {data.note} Comparado con {data.history_years} año(s). Fuente: {data.source}.
      </p>
    </section>
  )
}
