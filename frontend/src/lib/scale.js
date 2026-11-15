// Rampa secuencial perceptualmente uniforme (estilo plasma/inferno):
// segura para daltonismo, monotona en luminosidad. El significado nunca
// depende solo del color: hay marcas de forma, trama y textos.
// Dos rampas secuenciales perceptualmente uniformes y seguras para daltonismo.
// "fuego" evoca el fuego; "daltonismo" (tipo cividis) mantiene la luminosidad
// monotona tambien para deuteranopia/protanopia.
export const PALETTES = {
  fuego: ['#1b2440', '#3b2a63', '#6b2f6e', '#9c3f5a', '#c85a35', '#e8842a', '#ffc46b'],
  daltonismo: ['#0d1b3e', '#13376a', '#2b5578', '#4a7076', '#7d8a63', '#b0a05a', '#f5e07a'],
}

export let RAMP = PALETTES.fuego

export function setPalette(name) {
  RAMP = PALETTES[name] || PALETTES.fuego
  return RAMP
}

export function rampOf(name) {
  return PALETTES[name] || PALETTES.fuego
}

export function bucketOf(value, max) {
  if (value === null || value === undefined || !Number.isFinite(value) || max <= 0) return -1
  if (value <= 0) return 0
  const t = Math.sqrt(Math.min(value / max, 1))
  return Math.min(7 - 1, Math.floor(t * 7 - 1e-9))
}

export function colorOf(value, max, palette = 'fuego') {
  const ramp = rampOf(palette)
  const b = bucketOf(value, max)
  return b < 0 ? 'transparent' : ramp[b]
}

// limites de cada escalon, para una leyenda con cifras reales
export function legendSteps(max, palette = 'fuego') {
  const ramp = rampOf(palette)
  const out = []
  for (let i = 0; i < ramp.length; i += 1) {
    const from = Math.pow(i / ramp.length, 2) * max
    const to = Math.pow((i + 1) / ramp.length, 2) * max
    out.push({ color: ramp[i], from, to })
  }
  return out
}

export function fmt(n, digits = 0) {
  if (n === null || n === undefined || Number.isNaN(n)) return 'sin dato'
  return new Intl.NumberFormat('es-PE', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(n)
}

export function fmtCompact(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  if (Math.abs(n) >= 1000) return `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)} mil`
  return String(Math.round(n))
}

export const MONTHS = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
]

export const MONTHS_SHORT = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
