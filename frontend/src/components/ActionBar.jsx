import React from 'react'
import { fmt } from '../lib/scale'

export default function ActionBar({ downloads, data, onExportPng }) {
  return (
    <section className="card flex flex-wrap items-center gap-2 px-3 py-2" aria-labelledby="dl-title">
      <h2 id="dl-title" className="sr-only">Descargar resultados</h2>
      <a className="btn" href={downloads.hotspots} download>
        ↓ Descargar CSV de focos
        {data ? <span className="text-mist">({fmt(data.cards.total_detections)})</span> : null}
      </a>
      <a className="btn" href={downloads.series} download>
        ↓ Descargar serie armonizada
      </a>
      <a className="btn btn-primary" href={downloads.report} target="_blank" rel="noreferrer">
        ↗ Reporte ejecutivo (PDF)
      </a>
      <button type="button" className="btn" onClick={onExportPng}>
        ↓ Imagen del calendario (PNG)
      </button>
      <p className="ml-auto max-w-md text-[10.5px] leading-snug text-mist">
        El CSV de focos trae fecha, coordenadas, satélite, confianza, FRP y tipo. El reporte se abre listo para
        imprimir o guardar como PDF con las cifras de esta misma búsqueda.
      </p>
    </section>
  )
}
