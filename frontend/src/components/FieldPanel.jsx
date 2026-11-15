import React, { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'

function Metric({ label, value, detail }) {
  return <div className="rounded-xl border border-white/[0.06] bg-white/[0.025] p-3">
    <p className="label">{label}</p>
    <p className="mt-2 text-2xl font-semibold tracking-tight text-white">{value}</p>
    {detail ? <p className="mt-1 text-[10px] text-zinc-500">{detail}</p> : null}
  </div>
}

function Status({ good, children }) {
  return <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] ${good ? 'border-emerald-400/20 bg-emerald-400/[0.06] text-emerald-200' : 'border-amber-400/20 bg-amber-400/[0.06] text-amber-200'}`}>
    <span className={`h-1.5 w-1.5 rounded-full ${good ? 'bg-emerald-400' : 'bg-amber-400'}`} />{children}
  </span>
}

export default function FieldPanel({ zoneParams }) {
  const [recent, setRecent] = useState(null)
  const [geofences, setGeofences] = useState(null)
  const [groundtruth, setGroundtruth] = useState(null)
  const [errors, setErrors] = useState([])
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    setLoading(true)
    const tasks = await Promise.allSettled([
      api.recent(zoneParams),
      api.geofences(),
      api.groundtruth(),
    ])
    setRecent(tasks[0].status === 'fulfilled' ? tasks[0].value : null)
    setGeofences(tasks[1].status === 'fulfilled' ? tasks[1].value : null)
    setGroundtruth(tasks[2].status === 'fulfilled' ? tasks[2].value : null)
    setErrors(tasks.flatMap((task, i) => task.status === 'rejected' ? [['datos recientes', 'geocercas', 'validaciones'][i] + ': ' + task.reason.message] : []))
    setLoading(false)
  }, [zoneParams])

  useEffect(() => { refresh() }, [refresh])

  const counts = groundtruth?.summary?.counts || {}
  const verdictTotal = groundtruth?.summary?.total
  const fences = geofences?.items || []

  return <section className="space-y-4" aria-labelledby="field-title">
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p className="label">Operación y verificación</p>
        <h2 id="field-title" className="mt-1 text-xl font-semibold tracking-tight text-white">Estado de campo</h2>
        <p className="mt-1 max-w-2xl text-[12px] leading-relaxed text-zinc-400">Consulta datos NRT ya descargados, geocercas registradas por Telegram y verificaciones humanas guardadas por el backend.</p>
      </div>
      <button type="button" className="btn" onClick={refresh} disabled={loading}>{loading ? 'Actualizando…' : '↻ Actualizar estado'}</button>
    </div>

    {errors.length > 0 && <div role="status" className="rounded-xl border border-amber-400/20 bg-amber-400/[0.05] p-3 text-[11px] text-amber-100">{errors.join(' · ')}. Revisa la disponibilidad de la API.</div>}

    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Metric label="Focos recientes" value={recent?.available ? (recent.total ?? 0).toLocaleString('es-PE') : '—'} detail={recent?.available ? (recent.empty ? 'Sin detecciones en esta zona' : `Último dato: ${recent.last_day || 'fecha no informada'}`) : (recent?.reason || 'Datos NRT no disponibles')} />
      <Metric label="Últimos 7 días" value={recent?.available && !recent.empty ? (recent.last_7_days ?? 0).toLocaleString('es-PE') : '—'} detail="Detecciones del almacén NRT" />
      <Metric label="Geocercas activas" value={geofences?.count ?? '—'} detail="Ubicaciones registradas por usuarios de Telegram" />
      <Metric label="Validaciones" value={verdictTotal == null ? '—' : verdictTotal.toLocaleString('es-PE')} detail="Veredictos humanos guardados" />
    </div>

    <div className="grid gap-3 lg:grid-cols-2">
      <section className="card p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div><p className="label">NASA FIRMS · NRT</p><h3 className="mt-1 text-sm font-semibold text-white">Disponibilidad de datos recientes</h3></div>
          <Status good={Boolean(recent?.available)}>{recent?.available ? 'Datos cargados' : 'No disponible'}</Status>
        </div>
        {recent?.available && !recent.empty ? <>
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="chip">MODIS: {recent.per_source?.MODIS ?? 0}</span>
            <span className="chip">VIIRS: {recent.per_source?.VIIRS ?? 0}</span>
            <span className="chip">{recent.days_covered ?? 0} días cubiertos</span>
          </div>
          <p className="mt-3 text-[11px] leading-relaxed text-zinc-500">Último día disponible: {recent.last_day || 'no informado'}. Descarga: {recent.meta?.fetched_at || 'fecha no informada'}. Estos datos se consultan desde el almacén, no directamente desde FIRMS.</p>
        </> : <p className="mt-4 text-[12px] leading-relaxed text-zinc-400">{recent?.reason || 'El servicio no devolvió información reciente.'} El calendario histórico funciona de forma independiente.</p>}
      </section>

      <section className="card p-4">
        <p className="label">Validación humana</p><h3 className="mt-1 text-sm font-semibold text-white">Veredictos registrados</h3>
        {verdictTotal == null ? <p className="mt-4 text-[12px] text-zinc-400">No se pudo consultar el resumen de validaciones.</p> : <>
          <div className="mt-4 grid grid-cols-3 gap-2">
            <div className="rounded-xl bg-emerald-400/[0.06] p-3"><p className="text-[10px] text-emerald-200">Fuego real</p><p className="mt-1 text-xl font-semibold text-white">{counts.fuego_real ?? 0}</p></div>
            <div className="rounded-xl bg-amber-400/[0.06] p-3"><p className="text-[10px] text-amber-200">Quema agrícola</p><p className="mt-1 text-xl font-semibold text-white">{counts.quema_agricola ?? 0}</p></div>
            <div className="rounded-xl bg-zinc-400/[0.06] p-3"><p className="text-[10px] text-zinc-300">Falsa alarma</p><p className="mt-1 text-xl font-semibold text-white">{counts.falsa_alarma ?? 0}</p></div>
          </div>
          <p className="mt-3 text-[10.5px] leading-relaxed text-zinc-500">Conteo de registros almacenados; no representa el total de focos detectados.</p>
        </>}
      </section>
    </div>

    <section className="card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2"><div><p className="label">Telegram · posiciones compartidas</p><h3 className="mt-1 text-sm font-semibold text-white">Geocercas registradas</h3></div><span className="chip">{geofences?.count ?? '—'} ubicación(es)</span></div>
      {fences.length ? <div className="mt-3 divide-y divide-white/[0.06]">
        {fences.map((fence) => <div key={fence.telegram_id} className="flex flex-wrap items-center justify-between gap-2 py-3 first:pt-0 last:pb-0">
          <div><p className="text-[12px] font-medium text-zinc-200">{fence.name || `Usuario Telegram ${fence.telegram_id}`}</p><p className="mt-1 text-[10px] text-zinc-500">{Number(fence.lat).toFixed(4)}, {Number(fence.lon).toFixed(4)} · actualizado {fence.updated_at ? new Date(fence.updated_at).toLocaleString('es-PE') : 'sin fecha'}</p></div>
          <span className="chip">Radio {fence.radius_km ?? 10} km</span>
        </div>)}
      </div> : <p className="mt-3 text-[12px] text-zinc-400">{geofences ? 'No hay geocercas activas registradas.' : 'No se pudo consultar la lista de geocercas.'}</p>}
    </section>
    <p className="text-[10px] leading-relaxed text-zinc-600">Una detección satelital es un indicio térmico, no un incendio confirmado. Las ubicaciones mostradas fueron compartidas previamente con el bot; esta web no solicita ni comparte la ubicación del visitante.</p>
  </section>
}
