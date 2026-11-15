// Rampa secuencial perceptualmente uniforme (estilo plasma/inferno):
// segura para daltonismo, monotona en luminosidad. El significado nunca
// depende solo del color: hay marcas de forma, trama y textos.
export const RAMP = [
  '#1b2440',
  '#3b2a63',
  '#6b2f6e',
  '#9c3f5a',
  '#c85a35',
  '#e8842a',
  '#ffc46b',
]

export function bucketOf(value, max) {
  if (value === null || value === undefined || !Number.isFinite(value) || max <= 0) return -1
  if (value <= 0) return 0
  const t = Math.sqrt(Math.min(value / max, 1))
  return Math.min(RAMP.length - 1, Math.floor(t * RAMP.length - 1e-9))
}

export function colorOf(value, max) {
  const b = bucketOf(value, max)
  return b < 0 ? 'transparent' : RAMP[b]
}

// limites de cada escalon, para una leyenda con cifras reales
export function legendSteps(max) {
  const out = []
  for (let i = 0; i < RAMP.length; i += 1) {
    const from = Math.pow(i / RAMP.length, 2) * max
    const to = Math.pow((i + 1) / RAMP.length, 2) * max
    out.push({ color: RAMP[i], from, to })
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
