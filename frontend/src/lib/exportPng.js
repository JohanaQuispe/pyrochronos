// Exporta el calendario a PNG dibujando directamente en un canvas.
// No depende del DOM: usa los mismos datos que la interfaz.
import { MONTHS_SHORT, RAMP, bucketOf, fmt } from './scale'

const CELL_W = 26
const CELL_H = 16
const LEFT = 54
const TOP = 74
const PAD = 18

export function exportCalendarPng(data, fileName = 'pyrochronos_calendario.png') {
  const cal = data.calendar
  const meta = data.meta
  const periods = meta.periods
  const years = cal.years
  const isWeek = meta.granularity === 'week'
  const max = cal.max_value || 1

  const width = LEFT + periods.length * CELL_W + PAD * 2
  const height = TOP + years.length * CELL_H + 96
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('El navegador no permite dibujar el PNG')

  ctx.fillStyle = '#0b1220'
  ctx.fillRect(0, 0, width, height)

  ctx.fillStyle = '#ffffff'
  ctx.font = 'bold 15px system-ui, sans-serif'
  ctx.fillText(`PyroChronos · ${meta.zone}`, PAD, 26)
  ctx.fillStyle = '#a8b6cf'
  ctx.font = '11px system-ui, sans-serif'
  ctx.fillText(
    `${meta.start} a ${meta.end} · ${meta.measure_label} armonizadas · filas = años, columnas = ${
      isWeek ? 'semanas' : 'meses'
    }`,
    PAD,
    44,
  )
  ctx.fillText('Rayado = valor estimado (antes de 2012, solo MODIS) · ▲ alto · ◆ extremo', PAD, 60)

  ctx.font = '10px system-ui, sans-serif'
  periods.forEach((p, xi) => {
    if (isWeek && p % 4 !== 1) return
    ctx.fillStyle = '#a8b6cf'
    ctx.fillText(isWeek ? String(p) : MONTHS_SHORT[p - 1], LEFT + xi * CELL_W + 6, TOP - 6)
  })

  years.forEach((year, yi) => {
    const y = TOP + yi * CELL_H
    ctx.fillStyle = '#a8b6cf'
    ctx.font = '10px system-ui, sans-serif'
    ctx.fillText(String(year), 8, y + CELL_H - 4)
    periods.forEach((p, xi) => {
      const value = cal.values[yi][xi]
      const x = LEFT + xi * CELL_W
      if (value === null) {
        ctx.strokeStyle = '#243354'
        ctx.setLineDash([2, 2])
        ctx.strokeRect(x + 0.5, y + 0.5, CELL_W - 2, CELL_H - 2)
        ctx.setLineDash([])
        return
      }
      const b = bucketOf(value, max)
      ctx.fillStyle = b < 0 ? '#1b2440' : RAMP[b]
      ctx.fillRect(x, y, CELL_W - 2, CELL_H - 2)
      if (cal.estimated[yi][xi]) {
        ctx.strokeStyle = 'rgba(255,255,255,0.35)'
        ctx.lineWidth = 1
        for (let k = -CELL_H; k < CELL_W; k += 4) {
          ctx.beginPath()
          ctx.moveTo(x + k, y + CELL_H - 2)
          ctx.lineTo(x + k + CELL_H, y)
          ctx.stroke()
        }
      }
      const level = cal.levels[yi][xi]
      if (level === 'alto' || level === 'extremo') {
        ctx.fillStyle = level === 'extremo' ? '#ffb703' : '#ffffff'
        ctx.font = '8px system-ui, sans-serif'
        ctx.fillText(level === 'extremo' ? '◆' : '▲', x + CELL_W - 10, y + 8)
      }
    })
  })

  // leyenda
  const ly = height - 58
  ctx.fillStyle = '#a8b6cf'
  ctx.font = '10px system-ui, sans-serif'
  ctx.fillText('Menos actividad', PAD, ly + 10)
  let lx = PAD + 92
  RAMP.forEach((color, i) => {
    const from = (i / RAMP.length) ** 2 * max
    const to = ((i + 1) / RAMP.length) ** 2 * max
    ctx.fillStyle = color
    ctx.fillRect(lx, ly, 22, 11)
    ctx.fillStyle = '#a8b6cf'
    ctx.fillText(`${fmt(from)}–${fmt(to)}`, lx + 26, ly + 10)
    lx += 96
  })
  ctx.fillStyle = '#7d8aa3'
  ctx.fillText(
    `Datos: NASA FIRMS (MODIS + VIIRS). Valor armonizado con factor ${fmt(data.calibration.global_factor, 2)}. ${
      data.meta.disclaimer
    }`,
    PAD,
    height - 16,
  )

  canvas.toBlob((blob) => {
    if (!blob) return
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = fileName
    a.click()
    URL.revokeObjectURL(url)
  }, 'image/png')
}
