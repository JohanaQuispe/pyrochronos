import React, { useEffect, useState } from 'react'
import { api } from '../api'

// Solo resume lo almacenado; no afirma que el bot esté conectado o vigilando en vivo.
export default function FieldPanel({ zoneParams, bbox }) {
  const [recent, setRecent] = useState(null)
  const [counts, setCounts] = useState(null)
  const [verdicts, setVerdicts] = useState(null)
  useEffect(() => {
    const ctrl = new AbortController()
    setRecent(null)
    api.recent(zoneParams, ctrl.signal).then(setRecent).catch((err) => {
      if (err.name !== 'AbortError') setRecent({ available: false, reason: 'No se pudo consultar el estado.' })
    })
    return () => ctrl.abort()
  }, [zoneParams])
  useEffect(() => {
    const ctrl = new AbortController()
    api.geofences(ctrl.signal).then((v) => setCounts(v.count)).catch(() => {})
    api.groundtruth(ctrl.signal).then((v) => setVerdicts(v.summary?.total)).catch(() => {})
    return () => ctrl.abort()
  }, [])
  const covered = Array.isArray(recent?.meta?.bbox) && bbox && recent.meta.bbox[0] <= bbox[0] && recent.meta.bbox[1] <= bbox[1] && recent.meta.bbox[2] >= bbox[2] && recent.meta.bbox[3] >= bbox[3]
  return <section className="card p-5" aria-labelledby="field-title">
    <p className="label">Telegram y validación</p>
    <h2 id="field-title" className="mt-2 text-lg font-semibold text-white">Estado de campo</h2>
    <div className="mt-4 grid gap-3 sm:grid-cols-3">
      <div className="rounded-xl border border-white/10 p-4"><p className="label">Datos recientes</p><p className="mt-2 text-sm text-white">{!recent ? 'Consultando…' : recent.available ? `${recent.total ?? 0} focos en la zona` : 'No disponibles'}</p><p className="hint mt-2">Última descarga: {recent?.meta?.fetched_at || 'desconocida'}. {covered ? '' : 'Cobertura de la zona no verificada. '}No es una consulta en vivo.</p></div>
      <div className="rounded-xl border border-white/10 p-4"><p className="label">Ubicaciones registradas</p><p className="mt-2 text-sm text-white">{counts == null ? 'No disponible' : counts}</p><p className="hint mt-2">Tener ubicaciones guardadas no confirma que el bot esté activo.</p></div>
      <div className="rounded-xl border border-white/10 p-4"><p className="label">Respuestas guardadas</p><p className="mt-2 text-sm text-white">{verdicts == null ? 'No disponible' : verdicts}</p><p className="hint mt-2">Fuego real, quema agrícola o falsa alarma reportados.</p></div>
    </div>
    <p className="mt-4 text-[12px] leading-relaxed text-zinc-400">Los avisos dependen de datos recientes cargados y del bot en ejecución. Una detección satelital no confirma un incendio; verifica por fuentes operativas.</p>
  </section>
}
