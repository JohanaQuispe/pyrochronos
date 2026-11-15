import React, { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api.js'
import { useLanguage } from '../i18n.jsx'

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

export default function FieldPanel({ zoneParams, bbox }) {
  const { lang, t } = useLanguage()
  const [recent, setRecent] = useState(null)
  const [geofences, setGeofences] = useState(null)
  const [groundtruth, setGroundtruth] = useState(null)
  const [errors, setErrors] = useState([])
  const [loading, setLoading] = useState(true)
  const requestId = useRef(0)

  const refresh = useCallback(async () => {
    const id = ++requestId.current
    setLoading(true)
    setRecent(null)
    const tasks = await Promise.allSettled([
      api.recent(zoneParams),
      api.geofences(),
      api.groundtruth(),
    ])
    if (id !== requestId.current) return
    setRecent(tasks[0].status === 'fulfilled' ? tasks[0].value : null)
    setGeofences(tasks[1].status === 'fulfilled' ? tasks[1].value : null)
    setGroundtruth(tasks[2].status === 'fulfilled' ? tasks[2].value : null)
    setErrors(tasks.flatMap((task, i) => task.status === 'rejected' ? [['datos recientes', 'geocercas', 'validaciones'][i] + ': ' + task.reason.message] : []))
    setLoading(false)
  }, [zoneParams])

  useEffect(() => { refresh(); return () => { requestId.current += 1 } }, [refresh])

  const counts = groundtruth?.summary?.counts || {}
  const verdictTotal = groundtruth?.summary?.total
  const fences = geofences?.items || []
  const covered = Array.isArray(recent?.meta?.bbox) && bbox && recent.meta.bbox[0] <= bbox[0] && recent.meta.bbox[1] <= bbox[1] && recent.meta.bbox[2] >= bbox[2] && recent.meta.bbox[3] >= bbox[3]

  return <section className="space-y-4" aria-labelledby="field-title">
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p className="label">{t('Operación y verificación', 'Operations and verification')}</p>
        <h2 id="field-title" className="mt-1 text-xl font-semibold tracking-tight text-white">{t('Estado de campo', 'Field status')}</h2>
        <p className="mt-1 max-w-2xl text-[12px] leading-relaxed text-zinc-400">{t('Consulta datos NRT ya descargados, geocercas registradas por Telegram y verificaciones humanas guardadas por el backend.', 'Review downloaded NRT data, Telegram geofences and human reports stored by the server.')}</p>
      </div>
      <button type="button" className="btn" onClick={refresh} disabled={loading}>{loading ? t('Actualizando…', 'Updating…') : t('↻ Actualizar estado', '↻ Refresh status')}</button>
    </div>

    {errors.length > 0 && <div role="status" className="rounded-xl border border-amber-400/20 bg-amber-400/[0.05] p-3 text-[11px] text-amber-100">{errors.join(' · ')}. {t('Revisa la disponibilidad de la API.', 'Check API availability.')}</div>}

    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Metric label={t('Focos recientes', 'Recent hotspots')} value={recent?.available ? (recent.total ?? 0).toLocaleString('es-PE') : '—'} detail={recent?.available ? (recent.empty ? t('Sin detecciones en esta zona', 'No detections in this area') : `${t('Último dato', 'Latest data')}: ${recent.last_day || t('fecha no informada', 'date unavailable')}`) : ((lang === 'en' ? 'NRT data unavailable' : recent?.reason || 'Datos NRT no disponibles'))} />
      <Metric label={t('Últimos 7 días', 'Last 7 days')} value={recent?.available && !recent.empty ? (recent.last_7_days ?? 0).toLocaleString('es-PE') : '—'} detail={t('Detecciones del almacén NRT', 'Detections in NRT storage')} />
      <Metric label={t('Ubicaciones registradas', 'Registered locations')} value={geofences?.count ?? '—'} detail={t('No confirma que el bot esté activo', 'Does not confirm the bot is running')} />
      <Metric label={t('Validaciones', 'Reports')} value={verdictTotal == null ? '—' : verdictTotal.toLocaleString('es-PE')} detail={t('Veredictos humanos guardados', 'Saved human reports')} />
    </div>

    <div className="grid gap-3 lg:grid-cols-2">
      <section className="card p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div><p className="label">NASA FIRMS · NRT</p><h3 className="mt-1 text-sm font-semibold text-white">{t('Disponibilidad de datos recientes', 'Recent data availability')}</h3></div>
          <Status good={Boolean(recent?.available)}>{recent?.available ? t('Datos cargados', 'Data loaded') : t('No disponible', 'Unavailable')}</Status>
        </div>
        {recent?.available && !recent.empty ? <>
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="chip">MODIS: {recent.per_source?.MODIS ?? 0}</span>
            <span className="chip">VIIRS: {recent.per_source?.VIIRS ?? 0}</span>
            <span className="chip">{recent.days_covered ?? 0} {t('días con detecciones', 'days with detections')}</span>
          </div>
          <p className="mt-3 text-[11px] leading-relaxed text-zinc-500">{t('Último día disponible:', 'Latest available day:')} {recent.last_day || t('no informado', 'unknown')}. {t('Descarga:', 'Downloaded:')} {recent.meta?.fetched_at || t('fecha no informada', 'unknown')}. {t('Estos datos se consultan desde el almacén, no directamente desde FIRMS.', 'These data are read from storage, not directly from FIRMS.')}</p>
        </> : <p className="mt-4 text-[12px] leading-relaxed text-zinc-400">{lang === 'en' ? 'No recent information returned. The historical calendar works independently.' : (recent?.reason || 'El servicio no devolvió información reciente.') + ' El calendario histórico funciona de forma independiente.'}</p>}
        <p className="mt-2 text-[11px] leading-relaxed text-zinc-500">{covered ? t('La descarga cubre el recuadro de la zona.', 'The download covers the area’s bounding box.') : t('Cobertura de la zona no verificada; la ausencia de detecciones no confirma que no existan focos.', 'Area coverage is unverified; no detections does not mean there are no hotspots.')} {t('Puede estar desactualizada y no es una consulta en vivo.', 'Data may be outdated; this is not a live query.')}</p>
      </section>

      <section className="card p-4">
        <p className="label">{t('Validación humana', 'Human verification')}</p><h3 className="mt-1 text-sm font-semibold text-white">{t('Veredictos registrados', 'Recorded reports')}</h3>
        {verdictTotal == null ? <p className="mt-4 text-[12px] text-zinc-400">{t('No se pudo consultar el resumen de validaciones.', 'Could not load the report summary.')}</p> : <>
          <div className="mt-4 grid grid-cols-3 gap-2">
            <div className="rounded-xl bg-emerald-400/[0.06] p-3"><p className="text-[10px] text-emerald-200">{t('Fuego real', 'Real fire')}</p><p className="mt-1 text-xl font-semibold text-white">{counts.fuego_real ?? 0}</p></div>
            <div className="rounded-xl bg-amber-400/[0.06] p-3"><p className="text-[10px] text-amber-200">{t('Quema agrícola', 'Agricultural burn')}</p><p className="mt-1 text-xl font-semibold text-white">{counts.quema_agricola ?? 0}</p></div>
            <div className="rounded-xl bg-zinc-400/[0.06] p-3"><p className="text-[10px] text-zinc-300">{t('Falsa alarma', 'False alarm')}</p><p className="mt-1 text-xl font-semibold text-white">{counts.falsa_alarma ?? 0}</p></div>
          </div>
          <p className="mt-3 text-[10.5px] leading-relaxed text-zinc-500">{t('Conteo de registros almacenados; no representa el total de focos detectados.', 'Stored reports; not the total number of detected hotspots.')}</p>
        </>}
      </section>
    </div>

    <section className="card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2"><div><p className="label">{t('Telegram · posiciones compartidas', 'Telegram · shared locations')}</p><h3 className="mt-1 text-sm font-semibold text-white">{t('Geocercas registradas', 'Registered geofences')}</h3></div><span className="chip">{geofences?.count ?? '—'} {t('ubicación(es)', 'location(s)')}</span></div>
      {fences.length ? <div className="mt-3 divide-y divide-white/[0.06]">
        {fences.map((fence) => <div key={fence.telegram_id} className="flex flex-wrap items-center justify-between gap-2 py-3 first:pt-0 last:pb-0">
          <div><p className="text-[12px] font-medium text-zinc-200">{fence.name || `${t('Usuario Telegram', 'Telegram user')} ${fence.telegram_id}`}</p><p className="mt-1 text-[10px] text-zinc-500">{Number(fence.lat).toFixed(4)}, {Number(fence.lon).toFixed(4)} · {t('actualizado', 'updated')} {fence.updated_at ? new Date(fence.updated_at).toLocaleString('es-PE') : t('sin fecha', 'no date')}</p></div>
          <span className="chip">{t('Radio', 'Radius')} {fence.radius_km ?? 10} km</span>
        </div>)}
      </div> : <p className="mt-3 text-[12px] text-zinc-400">{geofences ? t('No hay geocercas activas registradas.', 'No active geofences registered.') : t('No se pudo consultar la lista de geocercas.', 'Could not load geofences.')}</p>}
    </section>
    <p className="text-[10px] leading-relaxed text-zinc-600">{t('Una detección satelital es un indicio térmico, no un incendio confirmado. Las ubicaciones mostradas fueron compartidas previamente con el bot; esta web no solicita ni comparte la ubicación del visitante.', 'A satellite detection is a heat indication, not a confirmed fire. Locations shown were previously shared with the bot; this website does not request or share the visitor’s location.')}</p>
  </section>
}
