import React from 'react'
import { fmt } from '../lib/scale'
import { useLanguage } from '../i18n.jsx'

export default function HarmonizationPanel({ data }) {
  const { lang } = useLanguage()
  const c = data.calibration
  const meta = data.meta
  const th = data.thresholds
  if (lang === 'en') return <details className="card p-4">
    <summary className="cursor-pointer text-sm font-semibold text-white">How harmonization works and its limits</summary>
    <div className="mt-3 grid gap-3 sm:grid-cols-3">
      <div className="rounded-lg border border-line bg-panelHi/60 p-3"><p className="label">Union / MODIS factor</p><p className="mt-1 text-lg font-semibold">{c.applicable ? fmt(c.global_factor, 2) : 'Not applicable'}</p><p className="hint mt-1">Calculated from years with both satellites ({c.overlap_years[0] ?? '—'}–{c.overlap_years[c.overlap_years.length - 1] ?? '—'}).</p></div>
      <div className="rounded-lg border border-line bg-panelHi/60 p-3"><p className="label">Factor uncertainty</p><p className="mt-1 text-lg font-semibold">{c.applicable ? `${fmt(c.global_p25, 2)} – ${fmt(c.global_p75, 2)}` : '—'}</p><p className="hint mt-1">25th–75th percentile range of the ratios; hatching marks estimates.</p></div>
      <div className="rounded-lg border border-line bg-panelHi/60 p-3"><p className="label">Satellite agreement</p><p className="mt-1 text-lg font-semibold">{c.agreement_r === null ? '—' : `r = ${c.agreement_r}`}</p><p className="hint mt-1">Correlation over {c.agreement_n} overlapping periods. Correlation does not establish equivalence.</p></div>
    </div>
    <div className="mt-3 space-y-2 text-[12px] leading-relaxed text-mist">
      <p>The main measure is cell-days with heat detections: each {meta.cell_deg}° cell counts once per day across the sensors. This reduces duplicates but does not eliminate differences in resolution or coverage. Raw hotspots count individual detections.</p>
      <p>Estimated periods are marked with hatching. The use of the union/MODIS factor for periods with VIIRS but no MODIS is under review; harmonized figures and rankings are provisional.</p>
      <p>Anomalies compare a period with the same period (±1) in other years. Thresholds are percentiles {th.high} and {th.extreme}, requiring at least {th.min_history_years} historical years and {th.min_value} cell-days. Symbols supplement color.</p>
      <p>FIRMS source types include vegetation, volcanoes, industrial sources and offshore detections; these types are not currently excluded by default.</p>
      <p className="rounded-lg border border-amber-400/30 bg-amber-400/10 p-3 text-amber-100">Recent years may be incomplete or revised; coverage ends {meta.coverage.end}. The factor assumes stable sensor sensitivity and does not model algorithm changes or sensor loss.</p>
    </div>
  </details>
  return (
    <details className="card p-3" aria-labelledby="harm-title">
      <summary
        id="harm-title"
        className="cursor-pointer list-none text-sm font-semibold text-white marker:hidden"
      >
        <span className="mr-1 text-fire" aria-hidden="true">▸</span> Cómo se armonizó (y qué no sabemos)
      </summary>

      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border border-line bg-panelHi/60 p-2">
          <p className="label">Factor unión / MODIS</p>
          <p className="text-lg font-semibold text-white">{c.applicable ? fmt(c.global_factor, 2) : 'no aplica'}</p>
          <p className="text-[10.5px] leading-snug text-mist">
            Cuántas veces más actividad ve el conjunto de los dos satélites que MODIS solo. Se calcula solo con los años
            en que ambos coinciden ({c.overlap_years[0] ?? '—'}–{c.overlap_years[c.overlap_years.length - 1] ?? '—'}).
          </p>
        </div>
        <div className="rounded-lg border border-line bg-panelHi/60 p-2">
          <p className="label">Incertidumbre del factor</p>
          <p className="text-lg font-semibold text-white">
            {c.applicable ? `${fmt(c.global_p25, 2)} – ${fmt(c.global_p75, 2)}` : '—'}
          </p>
          <p className="text-[10.5px] leading-snug text-mist">
            Rango entre percentiles 25 y 75 del cociente entre años. Los valores estimados se dibujan con trama
            rayada y su banda usa este rango.
          </p>
        </div>
        <div className="rounded-lg border border-line bg-panelHi/60 p-2">
          <p className="label">Concordancia entre satélites</p>
          <p className="text-lg font-semibold text-white">
            {c.agreement_r === null ? '—' : `r = ${c.agreement_r}`}
          </p>
          <p className="text-[10.5px] leading-snug text-mist">
            Correlación de las series de ambos satélites en {c.agreement_n} periodos de solape. Cuanto más cerca de 1,
            más se parecen sus patrones.
          </p>
        </div>
      </div>

      <div className="mt-3 space-y-2 text-[11.5px] leading-relaxed text-slate-200">
        <p>
          <strong className="text-white">Qué medimos.</strong> La medida principal es <em>celdas-día con fuego</em>: una
          celda de {meta.cell_deg}° cuenta una vez por día en la unión de sensores. Esto reduce la duplicación, pero
          no elimina las diferencias de resolución ni de cobertura. La medida <em>focos detectados</em> cuenta cada detección.
        </p>
        <p>
          <strong className="text-white">Qué es “estimado”.</strong> Cuando solo hay detecciones de un sensor en un periodo,
          el programa aplica un factor y marca el valor con trama. Se está revisando el uso del factor unión/MODIS en
          periodos con VIIRS sin MODIS; por ello las cifras armonizadas son provisionales.
        </p>
        <p>
          <strong className="text-white">Anomalías.</strong> Cada periodo se compara con el mismo periodo (±1) de los
          demás años, sin incluir el año evaluado. Se marcan “por encima de lo normal” desde el percentil {th.high} y
          “muy por encima” desde el {th.extreme}, exigiendo al menos {th.min_history_years} años de historial y{' '}
          {th.min_value} celdas-día. El símbolo (▲ ◆) y el borde acompañan al color: el significado nunca depende solo
          del color.
        </p>
        <p>
          <strong className="text-white">Fuentes fijas de calor.</strong> FIRMS trae una columna <code>type</code> que
          distingue vegetación (0), volcán (1), fuente fija industrial (2) y costa (3). Hoy no se excluyen; se pueden
          excluir cambiando <code>quality.exclude_types</code> en <code>config.yaml</code>.
        </p>
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-2">
          <p className="font-semibold text-amber-200">Lo que no está resuelto (y lo decimos)</p>
          <ul className="mt-1 list-disc space-y-1 pl-4 text-[11px] text-amber-100/90">
            <li>
              Los años más recientes pueden cambiar: NASA reprocesa la serie estándar y publica los últimos meses
              aparte. Nuestra cobertura termina en {meta.coverage.end}.
            </li>
            <li>
              El factor asume que la diferencia de sensibilidad entre satélites es estable en el tiempo; no modela
              cambios de versión del algoritmo ni la pérdida de sensores.
            </li>
            <li>
              Los años recientes del archivo por país pueden estar incompletos respecto de la revisión final de
              FIRMS (marcado como POR VERIFICAR en la documentación).
            </li>
          </ul>
        </div>
      </div>
    </details>
  )
}
