import React, { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { fmt } from '../lib/scale'
import { api } from '../api'
import { useLanguage } from '../i18n.jsx'

const START_VIEW = { center: [-9.5, -75.0], zoom: 5 }

export default function MapPanel({ bbox, zone, hotspots, meta, onBBoxChange, loading, visible = true,
  layer, onLayerChange, source, onSourceChange, highConfidence, onHighConfidenceChange, mapError }) {
  const { lang, t } = useLanguage()
  const mapEl = useRef(null)
  const mapRef = useRef(null)
  const rectRef = useRef(null)
  const boundaryRef = useRef(null)
  const dotsRef = useRef(null)
  const [boundaryError, setBoundaryError] = useState(false)
  const drawRef = useRef({ active: false, start: null })
  const [drawing, setDrawing] = useState(false)
  const [coords, setCoords] = useState({ w: '', s: '', e: '', n: '' })
  const coverage = hotspots?.meta?.bbox
  const fullCoverage = Array.isArray(coverage) && bbox && coverage[0] <= bbox[0] && coverage[1] <= bbox[1] && coverage[2] >= bbox[2] && coverage[3] >= bbox[3]

  useEffect(() => {
    if (mapRef.current || !mapEl.current) return undefined
    const map = L.map(mapEl.current, {
      center: START_VIEW.center,
      zoom: START_VIEW.zoom,
      preferCanvas: true,
      attributionControl: true,
    })
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 12,
      attribution: '© OpenStreetMap',
    }).addTo(map)
    dotsRef.current = L.layerGroup().addTo(map)
    mapRef.current = map

    map.on('mousedown', (e) => {
      if (!drawRef.current.active) return
      drawRef.current.start = e.latlng
      map.dragging.disable()
    })
    map.on('mousemove', (e) => {
      if (!drawRef.current.active || !drawRef.current.start) return
      const bounds = L.latLngBounds(drawRef.current.start, e.latlng)
      if (!rectRef.current) {
        rectRef.current = L.rectangle(bounds, { color: '#ff8a3d', weight: 2, fillOpacity: 0.08 }).addTo(map)
      } else {
        rectRef.current.setBounds(bounds)
      }
    })
    map.on('mouseup', (e) => {
      if (!drawRef.current.active || !drawRef.current.start) return
      const b = L.latLngBounds(drawRef.current.start, e.latlng)
      drawRef.current.start = null
      map.dragging.enable()
      const next = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()]
      const tooSmall = Math.abs(next[2] - next[0]) < 0.05 || Math.abs(next[3] - next[1]) < 0.05
      if (!tooSmall) onBBoxChange(next)
      setDrawing(false)
      drawRef.current.active = false
    })

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [onBBoxChange])

  // al volver a esta pestaña, Leaflet debe recalcular su tamaño
  useEffect(() => {
    if (!visible) return undefined
    const map = mapRef.current
    if (!map) return undefined
    const id = setTimeout(() => map.invalidateSize(), 80)
    return () => clearTimeout(id)
  }, [visible])

  // rectangulo de la zona activa
  useEffect(() => {
    const map = mapRef.current
    if (!map || !bbox) return
    const bounds = [[bbox[1], bbox[0]], [bbox[3], bbox[2]]]
    if (!rectRef.current) {
      rectRef.current = L.rectangle(bounds, { color: '#ff8a3d', weight: 2, fillOpacity: 0.06 }).addTo(map)
    } else {
      rectRef.current.setBounds(bounds)
    }
    setCoords({ w: bbox[0], s: bbox[1], e: bbox[2], n: bbox[3] })
  }, [bbox])

  // Límite departamental simplificado; no se utiliza para zonas dibujadas.
  useEffect(() => {
    const map = mapRef.current
    if (!map) return undefined
    if (boundaryRef.current) { map.removeLayer(boundaryRef.current); boundaryRef.current = null }
    setBoundaryError(false)
    if (!zone?.startsWith('d_')) return undefined
    const ctrl = new AbortController()
    api.department(zone, ctrl.signal).then((geometry) => {
      boundaryRef.current = L.geoJSON(geometry, { style: { color: '#e4e4e7', weight: 2, fillOpacity: 0.03 }, interactive: false }).addTo(map)
    }).catch((err) => { if (err.name !== 'AbortError') setBoundaryError(true) })
    return () => ctrl.abort()
  }, [zone])

  useEffect(() => {
    if (!visible || !bbox || !mapRef.current) return undefined
    const timer = setTimeout(() => mapRef.current?.fitBounds([[bbox[1], bbox[0]], [bbox[3], bbox[2]]], { padding: [20, 20], maxZoom: 9 }), 100)
    return () => clearTimeout(timer)
  }, [bbox, visible])

  // focos
  useEffect(() => {
    const group = dotsRef.current
    if (!group) return
    group.clearLayers()
    if (!hotspots) return
    // defensa: si el navegador no puede dibujar en canvas, se sigue mostrando el mapa
    let renderer = null
    try {
      renderer = L.canvas({ padding: 0.4 })
    } catch {
      renderer = null
    }
    try {
      drawDots(group, hotspots, renderer)
    } catch (err) {
      console.warn('No se pudieron dibujar los focos:', err)
    }
  }, [hotspots, lang])

  function drawDots(group, features, renderer) {
    for (const f of features.features) {
      const [lon, lat] = f.geometry.coordinates
      const isViirs = f.properties.source === 'VIIRS'
      const details = document.createElement('div')
      const description = document.createElement('p')
      description.textContent = `${t('Foco de calor', 'Heat detection')} · ${f.properties.day} (UTC) · ${f.properties.source} · ${t('confianza', 'confidence')} ${
        (lang === 'en' ? ['low', 'nominal', 'high'] : ['baja', 'nominal', 'alta'])[f.properties.conf] || t('no disponible', 'not available')
      } · FRP ${f.properties.frp == null ? t('no disponible', 'not available') : `${f.properties.frp} MW`} · ${lat.toFixed(4)}, ${lon.toFixed(4)}`
      const note = document.createElement('p')
      note.textContent = t('Detección satelital, no incendio confirmado. Hora, viento y acceso no disponibles.', 'Satellite detection, not a confirmed fire. Time, wind and access are not available.')
      const link = document.createElement('a')
      link.href = `https://www.google.com/maps/search/?api=1&query=${lat},${lon}`
      link.target = '_blank'
      link.rel = 'noopener noreferrer'
      link.textContent = t('Abrir coordenadas en Google Maps', 'Open coordinates in Google Maps')
      details.append(description, note, link)
      L.circleMarker([lat, lon], {
        renderer,
        radius: isViirs ? 3 : 3.5,
        color: isViirs ? '#ffd166' : '#ff6b1a',
        weight: 0,
        fillOpacity: 0.72,
      }).bindPopup(details).addTo(group)
    }
  }

  useEffect(() => {
    drawRef.current.active = drawing
    const map = mapRef.current
    if (map) {
      if (drawing) map.getContainer().style.cursor = 'crosshair'
      else map.getContainer().style.cursor = ''
    }
  }, [drawing])

  const applyCoords = () => {
    const w = Number(coords.w)
    const s = Number(coords.s)
    const e = Number(coords.e)
    const n = Number(coords.n)
    if ([w, s, e, n].some((v) => Number.isNaN(v)) || w >= e || s >= n) {
      alert(t('Las coordenadas no son válidas: se espera oeste < este y sur < norte.', 'Invalid coordinates: west must be less than east and south less than north.'))
      return
    }
    onBBoxChange([w, s, e, n])
  }

  return (
    <section
      className="flex h-full min-h-[420px] flex-col overflow-hidden rounded-2xl border border-white/[0.12] bg-panel shadow-soft"
      aria-labelledby="map-title"
    >
      <div className="flex items-center justify-between gap-2 px-4 py-3">
        <div>
          <h2 id="map-title" className="text-[16px] font-semibold text-white">{t('Explorar detecciones', 'Explore detections')}</h2>
          <p className="hint">{t('Toca un punto para ver sus datos y coordenadas', 'Select a point to see its details and coordinates')}</p>
        </div>
        <button
          type="button"
          className={`btn text-[12px] ${drawing ? 'btn-primary' : ''}`}
          onClick={() => setDrawing((d) => !d)}
          aria-pressed={drawing}
        >
          {drawing ? t('Arrastra en el mapa…', 'Drag on the map…') : t('Dibujar zona', 'Draw area')}
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2 px-4 pb-2 text-[11px]">
        <label className="text-zinc-400">{t('Capa', 'Layer')}{' '}
          <select className="input" aria-label={t('Capa del mapa', 'Map layer')} value={layer} onChange={(e) => onLayerChange(e.target.value)}>
            <option value="history">{t('Historial seleccionado', 'Selected history')}</option>
            <option value="recent">{t('Datos NRT cargados', 'Loaded NRT data')}</option>
          </select>
        </label>
        <label className="text-zinc-400">Sensor{' '}
          <select className="input" aria-label={t('Sensor del mapa', 'Map sensor')} value={source} onChange={(e) => onSourceChange(e.target.value)}>
            <option value="both">{t('MODIS y VIIRS', 'MODIS and VIIRS')}</option>
            <option value="viirs">{t('Solo VIIRS', 'VIIRS only')}</option>
            <option value="modis">{t('Solo MODIS', 'MODIS only')}</option>
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-zinc-400">
          <input type="checkbox" checked={highConfidence} onChange={(e) => onHighConfidenceChange(e.target.checked)} />
          {t('Solo alta confianza', 'High confidence only')}
        </label>
      </div>
      <p className="px-4 pb-2 text-[10.5px] leading-snug text-zinc-400" role="status">
        {mapError ? `${t('No se pudo cargar la capa', 'Could not load layer')}: ${mapError}`
          : layer === 'history' ? t('Historial del periodo elegido; no indica focos activos ahora.', 'Historical data for the selected period; it does not show current active fires.')
            : !hotspots ? t('Consultando datos NRT guardados; no es una consulta en vivo.', 'Loading stored NRT data; this is not a live query.')
              : !hotspots.meta.available ? t('Sin datos NRT cargados. No significa que no haya focos.', 'No NRT data loaded. This does not mean there are no hotspots.')
                : `${t('NRT guardado · última descarga', 'Stored NRT · last download')}: ${hotspots.meta.fetched_at || t('desconocida', 'unknown')} · ${t('última detección', 'last detection')}: ${hotspots.meta.last_day || t('desconocida', 'unknown')}. ${fullCoverage ? '' : t('Cobertura completa de la zona no verificada. ', 'Full area coverage not verified. ')}${t('Puede estar desactualizado; no es tiempo real.', 'May be outdated; not real time.')}`}
      </p>

      {zone?.startsWith('d_') && <p className="px-4 pb-2 text-[10.5px] text-zinc-400">{boundaryError ? t('No se pudo cargar el contorno.', 'Could not load the boundary.') : t('Contorno departamental simplificado (INEI 2007); puede diferir del límite oficial actual.', 'Simplified department boundary (INEI 2007); it may differ from the current official boundary.')}</p>}
      <div className="flex items-end gap-1.5 px-4 pb-3">
        {[['w', t('O', 'W')], ['s', 'S'], ['e', 'E'], ['n', 'N']].map(([key, text]) => (
          <label key={key} className="flex-1 text-[9.5px] text-mist">
            <span className="sr-only">
              {key === 'w' ? t('Oeste', 'West') : key === 's' ? t('Sur', 'South') : key === 'e' ? t('Este', 'East') : t('Norte', 'North')}
            </span>
            <span aria-hidden="true" className="mb-0.5 block">{text}</span>
            <input
              type="number"
              step="0.01"
              aria-label={key === 'w' ? t('Oeste', 'West') : key === 's' ? t('Sur', 'South') : key === 'e' ? t('Este', 'East') : t('Norte', 'North')}
              className="input w-full px-1 py-0.5 text-[10.5px] tabular-nums"
              value={coords[key]}
              onChange={(e) => setCoords((c) => ({ ...c, [key]: e.target.value }))}
            />
          </label>
        ))}
        <button type="button" className="btn shrink-0 px-2 py-1 text-[10.5px]" onClick={applyCoords} title={t('Aplicar coordenadas', 'Apply coordinates')}>
          {t('Aplicar', 'Apply')}
        </button>
      </div>

      <div className="relative flex-1">
        <div ref={mapEl} className="absolute inset-0" role="application" aria-label={t('Mapa con los focos de calor del periodo', 'Map of heat detections in the period')} />
        {loading && (
          <div className="absolute inset-0 z-[400] grid place-items-center bg-ink/50 text-[12px] text-zinc-400 backdrop-blur-[1px]">
            {t('Cargando focos…', 'Loading hotspots…')}
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-white/[0.06] px-4 py-2 text-[10.5px] text-zinc-500">
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full bg-[#ff6b1a]" aria-hidden="true" /> MODIS
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full bg-[#ffd166]" aria-hidden="true" /> VIIRS
        </span>
        <span>
          {hotspots
            ? `${fmt(hotspots.meta.shown)} ${t('de', 'of')} ${fmt(hotspots.meta.total)} ${t('focos', 'hotspots')}${hotspots.meta.sampled ? t(' (muestra)', ' (sample)') : ''}`
            : t('Sin focos', 'No hotspots')}
        </span>
        <span className="ml-auto">{t('Colores = sensor, no prioridad', 'Colors = sensor, not priority')}{meta?.cell_deg ? ` · ${meta.cell_deg}° ${t('por celda', 'per cell')}` : ''}</span>
      </div>
    </section>
  )
}
