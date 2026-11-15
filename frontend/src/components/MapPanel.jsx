import React, { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { fmt } from '../lib/scale'

const START_VIEW = { center: [-9.5, -75.0], zoom: 5 }

export default function MapPanel({ bbox, hotspots, meta, onBBoxChange, loading, visible = true }) {
  const mapEl = useRef(null)
  const mapRef = useRef(null)
  const rectRef = useRef(null)
  const dotsRef = useRef(null)
  const drawRef = useRef({ active: false, start: null })
  const [drawing, setDrawing] = useState(false)
  const [coords, setCoords] = useState({ w: '', s: '', e: '', n: '' })

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

  // focos
  useEffect(() => {
    const group = dotsRef.current
    if (!group || !hotspots) return
    group.clearLayers()
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
  }, [hotspots])

  function drawDots(group, features, renderer) {
    for (const f of features.features) {
      const [lon, lat] = f.geometry.coordinates
      const isViirs = f.properties.source === 'VIIRS'
      L.circleMarker([lat, lon], {
        renderer,
        radius: isViirs ? 2 : 2.6,
        color: isViirs ? '#ffd166' : '#ff6b1a',
        weight: 0,
        fillOpacity: 0.72,
      })
        .bindTooltip(
          `${f.properties.day} · ${f.properties.source} · confianza ${
            ['baja', 'nominal', 'alta'][f.properties.conf] || '—'
          }${f.properties.frp ? ` · FRP ${f.properties.frp} MW` : ''}`,
        )
        .addTo(group)
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
      alert('Las coordenadas no son válidas: se espera oeste < este y sur < norte.')
      return
    }
    onBBoxChange([w, s, e, n])
  }

  return (
    <section
      className="flex h-full min-h-[420px] flex-col overflow-hidden rounded-2xl border border-white/[0.06] bg-white/[0.015]"
      aria-labelledby="map-title"
    >
      <div className="flex items-center justify-between gap-2 px-4 py-3">
        <div>
          <h2 id="map-title" className="text-[13px] font-medium text-white">Zona de interés</h2>
          <p className="hint">Focos del periodo seleccionado</p>
        </div>
        <button
          type="button"
          className={`btn text-[12px] ${drawing ? 'btn-primary' : ''}`}
          onClick={() => setDrawing((d) => !d)}
          aria-pressed={drawing}
        >
          {drawing ? 'Arrastra en el mapa…' : 'Dibujar zona'}
        </button>
      </div>

      <div className="flex items-end gap-1.5 px-4 pb-3">
        {[['w', 'O'], ['s', 'S'], ['e', 'E'], ['n', 'N']].map(([key, text]) => (
          <label key={key} className="flex-1 text-[9.5px] text-mist">
            <span className="sr-only">
              {key === 'w' ? 'Oeste' : key === 's' ? 'Sur' : key === 'e' ? 'Este' : 'Norte'}
            </span>
            <span aria-hidden="true" className="mb-0.5 block">{text}</span>
            <input
              type="number"
              step="0.01"
              aria-label={key === 'w' ? 'Oeste' : key === 's' ? 'Sur' : key === 'e' ? 'Este' : 'Norte'}
              className="input w-full px-1 py-0.5 text-[10.5px] tabular-nums"
              value={coords[key]}
              onChange={(e) => setCoords((c) => ({ ...c, [key]: e.target.value }))}
            />
          </label>
        ))}
        <button type="button" className="btn shrink-0 px-2 py-1 text-[10.5px]" onClick={applyCoords} title="Aplicar coordenadas">
          Aplicar
        </button>
      </div>

      <div className="relative flex-1">
        <div ref={mapEl} className="absolute inset-0" role="application" aria-label="Mapa con los focos de calor del periodo" />
        {loading && (
          <div className="absolute inset-0 z-[400] grid place-items-center bg-ink/50 text-[12px] text-zinc-400 backdrop-blur-[1px]">
            Cargando focos…
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
            ? `${fmt(hotspots.meta.shown)} de ${fmt(hotspots.meta.total)} focos${hotspots.meta.sampled ? ' (muestra)' : ''}`
            : 'Sin focos'}
        </span>
        <span className="ml-auto">{meta?.cell_deg}° ≈ 1,1 km por celda</span>
      </div>
    </section>
  )
}
