import { useLanguage } from '../i18n.jsx'
import React, { useState } from 'react'
import { fmt } from '../lib/scale'

const STYLES = {
  critico: { dot: 'bg-red-400', text: 'text-red-300', word: 'Ventana crítica', border: 'border-red-400/20' },
  vigilancia: { dot: 'bg-amber-400', text: 'text-amber-200', word: 'Vigilancia', border: 'border-amber-400/20' },
  normal: { dot: 'bg-zinc-400', text: 'text-zinc-200', word: 'Fuera de temporada', border: 'border-white/10' },
}

export default function AlertStrip({ alert, loading, dateRef, setDateRef, zoneName }) {
  const { lang, t } = useLanguage()
  const [open, setOpen] = useState(false)
  const available = !!alert && alert.available !== false && !!STYLES[alert.level]
  const style = available ? STYLES[alert.level] : STYLES.normal
  const recent = alert?.recent || {}
  const englishDetail = available ? `Historical peak: week ${alert.peak_week ?? 'unknown'}. In the next four weeks, week ${alert.best_week ?? 'unknown'} has ${Math.round((alert.ratio || 0) * 100)}% of peak historical activity.${alert.recent_ratio != null ? ` Recent detections are ${alert.recent_ratio.toFixed(1)}× the historical median for this week and may affect the indicator.` : ''}` : 'Not enough historical data for this area.'
  return (
    <section aria-live="polite" aria-label={t('Semáforo de temporada', 'Seasonal indicator')} className={`overflow-hidden rounded-2xl border ${style.border} bg-panel`}>
      <div className="grid gap-4 p-4 sm:p-5 lg:grid-cols-[250px_1fr_auto] lg:items-center">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">{t('Semáforo estacional', 'Seasonal indicator')} · {zoneName}</p>
          <p className={`mt-2 flex items-center gap-2.5 text-[18px] font-semibold ${style.text}`}>
            <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${style.dot}`} aria-hidden="true" />
            {loading ? t('Calculando…', 'Calculating…') : available ? (lang === 'en' ? ({ critico: 'Critical season', vigilancia: 'Watch season', normal: 'Outside season' }[alert.level]) : style.word) : t('Sin información', 'No information')}
          </p>
        </div>
        <div className="border-white/[0.08] lg:border-l lg:pl-5">
          <p className="text-[12px] leading-relaxed text-zinc-300">{loading ? t('Consultando el historial de la zona.', 'Loading the area’s history.') : lang === 'en' ? englishDetail : alert?.reasons?.[2] || alert?.reasons?.[1] || 'No se pudo obtener el análisis estacional.'}</p>
          <p className="mt-1 text-[11px] text-zinc-500">{t('Basado en el historial; no indica incendios activos ni es un pronóstico.', 'Based on historical data and, when available, recent detections; not a forecast or confirmation of active fires.')}</p>
          {recent.available && !recent.empty && <p className="mt-1 text-[11px] text-zinc-400">{fmt(recent.total)} {t('focos en datos NRT cargados; verifica la fecha en el mapa.', 'hotspots in loaded NRT data; check the date on the map.')}</p>}
        </div>
        <button type="button" className="btn justify-center" onClick={() => setOpen((o) => !o)} aria-expanded={open}>{open ? t('Ocultar detalle', 'Hide details') : t('Ver detalle', 'View details')} <span aria-hidden="true">{open ? '↑' : '↗'}</span></button>
      </div>
      {open && <div className="grid gap-4 border-t border-white/[0.06] p-4 sm:grid-cols-[1fr_240px] sm:p-5">
        <div className="space-y-2">
          <p className="label">{t('Cómo se calculó', 'How it was calculated')}</p>
          {lang === 'en' ? <>
            <p className="text-[12px] text-zinc-300">{englishDetail} {available && alert.week != null ? `Reference week: ${alert.week}.` : ''}</p>
            <p className="hint">Not a weather forecast or a prediction of ignitions. Verify conditions with official sources.</p>
          </> : <>
            <ul className="space-y-1 text-[12px] leading-relaxed text-zinc-300">{(alert?.reasons || []).map((r) => <li key={r}>· {r}</li>)}</ul>
            {alert?.action && <p className="text-[12px] leading-relaxed text-zinc-300"><span className="text-white">Sugerencia:</span> {alert.action}</p>}
            <p className="hint">{alert?.disclaimer}</p>
          </>}
        </div>
        <div className="space-y-2 rounded-xl border border-white/[0.06] p-3">
          <label className="block text-[11px] text-zinc-400">{t('Ver otra semana del año', 'View another week')}<input type="date" value={dateRef || ''} onChange={(e) => setDateRef(e.target.value)} className="input mt-1 w-full" /></label>
          <p className="text-[11px] text-zinc-500">{t('No cambia los datos del calendario.', 'Does not change the calendar data.')}</p>
          <button type="button" className="btn w-full justify-center text-[11px]" onClick={() => setDateRef('')}>{t('Volver a la semana actual', 'Return to current week')}</button>
        </div>
      </div>}
    </section>
  )
}
