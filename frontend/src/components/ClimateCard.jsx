import React, { useEffect, useState } from 'react'
import { api } from '../api.js'

const LEVEL_STYLE = {
  seco: { chip: 'border-ember/60 bg-fire/20 text-ember', icon: '☀️' },
  humedo: { chip: 'border-sky-400/50 bg-sky-400/10 text-sky-200', icon: '🌧️' },
  normal: { chip: 'border-emerald-400/50 bg-emerald-400/10 text-emerald-200', icon: '🌿' },
  sin_datos: { chip: 'border-line bg-white/5 text-mist', icon: '·' },
}

function num(value, digits = 0, suffix = '') {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return `${Number(value).toFixed(digits).replace('.', ',')}${suffix}`
}

/**
 * Contexto meteorológico de los últimos 30 días (NASA POWER, precargado).
 * Si no hay archivo de caché, lo dice con el comando exacto para generarlo.
 */
export default function ClimateCard({ zone }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!zone || zone === 'custom') {
      setData(null)
      return undefined
    }
    const ctrl = new AbortController()
    setLoading(true)
    setError(null)
    api
      .climate({ zone }, ctrl.signal)
      .then((d) => {
        setData(d)
        setLoading(false)
      })
      .catch((e) => {
        if (e.name !== 'AbortError') {
          setError(e.message)
          setLoading(false)
        }
      })
    return () => ctrl.abort()
  }, [zone])

  if (loading) {
    return (
      <section className="card p-3" aria-busy="true">
        <h2 className="text-sm font-semibold text-white">Contexto climático</h2>
        <p className="mt-1 text-[11.5px] text-mist">Consultando NASA POWER…</p>
      </section>
    )
  }

  if (error) {
    return (
      <section className="card p-3" role="alert">
        <h2 className="text-sm font-semibold text-white">Contexto climático</h2>
        <p className="mt-1 text-[11.5px] text-ember">No se pudo cargar: {error}</p>
      </section>
    )
  }

  if (!data || data.available === false) {
    return (
      <section className="card p-3">
        <h2 className="text-sm font-semibold text-white">Contexto climático (NASA POWER)</h2>
        <p className="mt-1 text-[11.5px] leading-relaxed text-slate-200">
          Sin datos cargados para esta zona. El calendario funciona igual: esto solo añade el estado del
          combustible (lluvia y temperatura de los últimos 30 días).
        </p>
        <code className="mt-1.5 block rounded bg-black/40 px-2 py-1 text-[10.5px] text-mist">
          {data?.how_to || 'python backend/scripts/download_power.py --zone madrededios --years 5'}
        </code>
      </section>
    )
  }

  const style = LEVEL_STYLE[data.level] || LEVEL_STYLE.sin_datos
  const deficit = data.rain_deficit_pct
  const sign = deficit === null || deficit === undefined ? '' : deficit > 0 ? '+' : ''

  return (
    <section className="card p-3" aria-labelledby="climate-title">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="climate-title" className="text-sm font-semibold text-white">
          Contexto climático · últimos 30 días
        </h2>
        <span className={`rounded-full border px-2 py-0.5 text-[10.5px] font-medium ${style.chip}`}>
          <span aria-hidden="true">{style.icon} </span>
          {data.label}
        </span>
      </div>
      <dl className="mt-2 grid grid-cols-3 gap-2 text-center">
        <div className="rounded border border-line bg-black/20 px-1.5 py-1">
          <dt className="text-[10px] uppercase tracking-wide text-mist">Lluvia</dt>
          <dd className="text-[13px] font-semibold text-white">{num(data.window?.rain_mm, 0, ' mm')}</dd>
          <dd className="text-[10px] text-mist">
            {deficit === null || deficit === undefined ? 'sin comparación' : `${sign}${num(deficit, 0, ' %')} vs. años previos`}
          </dd>
        </div>
        <div className="rounded border border-line bg-black/20 px-1.5 py-1">
          <dt className="text-[10px] uppercase tracking-wide text-mist">T máx</dt>
          <dd className="text-[13px] font-semibold text-white">{num(data.window?.tmax_mean_c, 1, ' °C')}</dd>
          <dd className="text-[10px] text-mist">
            {data.tmax_anomaly_c === null || data.tmax_anomaly_c === undefined
              ? 'sin comparación'
              : `${data.tmax_anomaly_c > 0 ? '+' : ''}${num(data.tmax_anomaly_c, 1, ' °C')} de anomalía`}
          </dd>
        </div>
        <div className="rounded border border-line bg-black/20 px-1.5 py-1">
          <dt className="text-[10px] uppercase tracking-wide text-mist">Días secos</dt>
          <dd className="text-[13px] font-semibold text-white">{num(data.window?.dry_days, 0)}</dd>
          <dd className="text-[10px] text-mist">de {num(data.window?.days, 0)} con datos</dd>
        </div>
      </dl>
      <p className="mt-1.5 text-[10.5px] leading-snug text-mist">
        {data.note} Comparado con {data.history_years} año(s). Fuente: {data.source}.
      </p>
    </section>
  )
}
