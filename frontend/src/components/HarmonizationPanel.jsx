import React from 'react'
import { fmt } from '../lib/scale'

export default function HarmonizationPanel({ data }) {
  const c = data.calibration
  const meta = data.meta
  const th = data.thresholds
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
          <p className="label">Factor VIIRS/MODIS</p>
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
          celda de {meta.cell_deg}° (≈1,1 km) cuenta una vez por día y satélite. Así la mayor resolución de VIIRS
          (≈375 m) no infla los años recientes. La segunda medida, <em>focos detectados</em>, cuenta cada detección
          suelta y siempre se muestra como referencia, no como la serie armonizada.
        </p>
        <p>
          <strong className="text-white">Qué es “estimado”.</strong> Antes de 2012 solo existe MODIS. El valor de esos
          periodos se estima multiplicando lo observado por el factor del mismo mes (o semana) del año, con su banda de
          incertidumbre. En el calendario aparecen con trama rayada. Desde 2012 el valor es observado por los dos
          satélites.
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
