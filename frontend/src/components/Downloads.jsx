import React from 'react'
import { api } from '../api'
import { fmt } from '../lib/scale'

export default function Downloads({ params, data }) {
  const csvHot = api.csvUrl('/api/csv/hotspots', {
    zone: params.zone === 'custom' ? undefined : params.zone,
    bbox: params.bbox,
    start: params.start,
    end: params.end,
    sources: params.sources,
  })
  const csvSeries = api.csvUrl('/api/csv/series', {
    zone: params.zone === 'custom' ? undefined : params.zone,
    bbox: params.bbox,
    start: params.start,
    end: params.end,
    granularity: params.granularity,
    measure: params.measure,
    sources: params.sources,
  })

  return (
    <section className="card p-3" aria-labelledby="dl-title">
      <h2 id="dl-title" className="text-sm font-semibold text-white">Descargar resultados</h2>
      <p className="mt-0.5 text-[11px] text-mist">
        Los CSV se generan con la zona y el rango que tienes seleccionados.
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        <a className="btn" href={csvHot} download>
          ↓ CSV de focos
          {data ? <span className="text-mist">({fmt(data.cards.total_detections)})</span> : null}
        </a>
        <a className="btn" href={csvSeries} download>
          ↓ CSV de la serie armonizada
        </a>
      </div>
      <p className="mt-2 text-[10.5px] leading-snug text-mist">
        El CSV de focos trae fecha, latitud, longitud, satélite, nivel de confianza, FRP y tipo de fuente. El CSV de la
        serie trae el valor armonizado, si es estimado o no, el percentil y la clasificación de cada periodo.
      </p>
    </section>
  )
}
