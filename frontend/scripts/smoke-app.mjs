// Prueba de humo de la aplicacion completa con fetch simulado.
import { JSDOM } from 'jsdom'
import { build } from 'esbuild'
import { readFileSync, writeFileSync } from 'node:fs'

const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', {
  url: 'http://localhost/',
  pretendToBeVisual: true,
})
global.window = dom.window
global.document = dom.window.document
Object.defineProperty(global, 'navigator', { value: dom.window.navigator, configurable: true })
global.HTMLElement = dom.window.HTMLElement
global.SVGElement = dom.window.SVGElement
global.getComputedStyle = dom.window.getComputedStyle
global.requestAnimationFrame = (cb) => setTimeout(cb, 0)
global.alert = () => {}
// jsdom no implementa canvas: damos un contexto 2D de mentira para que Leaflet no aborte
const fakeCtx = new Proxy(
  {},
  { get: (t, k) => (k in t ? t[k] : () => {}), set: (t, k, v) => { t[k] = v; return true } },
)
dom.window.HTMLCanvasElement.prototype.getContext = () => fakeCtx

const calendar = JSON.parse(readFileSync(new URL('./fixtures/calendar-month.json', import.meta.url), 'utf8'))
const meta = {
  name: 'PyroChronos', version: '1.0.0', disclaimer: calendar.meta.disclaimer,
  zones: [
    { key: 'peru', name: 'Peru', bbox: [-81.5, -18.5, -68.5, 0.5], note: '' },
    { key: 'madrededios', name: 'Madre de Dios', bbox: [-70.6, -13.4, -68.6, -11], note: '' },
  ],
  default_zone: 'peru', coverage: calendar.meta.coverage, measures: [], default_measure: 'cell_days',
  cell_deg: 0.01, sources: [], thresholds: {}, quality: {}, months: [], max_area_deg2: 300,
}
const hotspots = { type: 'FeatureCollection', features: [{ type: 'Feature', geometry: { type: 'Point', coordinates: [-69.1, -12.5] }, properties: { day: '2024-09-01', source: 'VIIRS', conf: 1, frp: 3.2 } }], meta: { total: 1, shown: 1, sampled: false } }

let calls = 0
global.fetch = async (url) => {
  calls += 1
  const body = url.includes('/api/meta') ? meta
    : url.includes('/api/hotspots') ? hotspots
      : url.includes('/api/bulletin') ? { text: 'boletin de prueba', zone: 'Peru', note: '' }
        : url.includes('/api/alert') ? {
          available: true, level: 'critico', severity: 2, label: 'Ventana crítica', short: 'Actividad histórica máxima',
          action: 'Activa vigilancia diaria.', reasons: ['Referencia: semana 36.', 'Pico en la semana 36.', 'Se espera 100 % del pico.'],
          reference_date: '2026-09-08', week: 36, peak_week: 36, ratio: 1.0,
          window: [{ week: 36, expected: 100, ratio: 1, in_peak: true }, { week: 37, expected: 80, ratio: 0.8, in_peak: true }],
          recent: { available: false }, disclaimer: 'No es un pronóstico.',
        }
        : url.includes('/api/climate-context') ? {
          available: true, zone: 'Madre de Dios', source: 'NASA POWER',
          point: { lat: -12.2, lon: -69.6 }, fetched_at: '2026-11-15T10:00:00Z',
          window: { start: '2026-10-16', end: '2026-11-14', days: 30, rain_mm: 41, dry_days: 24, tmax_mean_c: 32.4, rh_mean_pct: 68 },
          history_years: 5, rain_climatology_mm: 120, rain_deficit_pct: -65.8, tmax_anomaly_c: 1.9,
          level: 'seco', label: 'más seco de lo normal', note: 'Reanálisis NASA POWER en un punto central de la zona.',
        }
        : calendar
  return { ok: true, status: 200, json: async () => body }
}
dom.window.fetch = global.fetch

const result = await build({
  stdin: {
    contents: `
import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './src/App.jsx'
createRoot(document.getElementById('root')).render(React.createElement(App))
`,
    resolveDir: process.cwd(),
    loader: 'jsx',
  },
  bundle: true,
  write: false,
  format: 'esm',
  platform: 'browser',
  loader: { '.js': 'jsx', '.jsx': 'jsx', '.css': 'empty' },
  define: { 'process.env.NODE_ENV': '"development"', 'import.meta.env': '{"VITE_API_BASE":""}' },
})
writeFileSync('/tmp/smoke-app-bundle.mjs', result.outputFiles[0].text)
global.__jsdomRoot = dom.window.document.getElementById('root')

await import('file:///tmp/smoke-app-bundle.mjs')
await new Promise((r) => setTimeout(r, 1500))

const html = dom.window.document.getElementById('root').innerHTML
const checks = [
  ['cabecera', html.includes('PyroChronos')],
  ['pestanas', html.includes('Calendario histórico') && html.includes('Mapa y alertas')],
  ['calendario montado', html.includes('Calendario de actividad')],
  ['mapa montado', html.includes('leaflet-container')],
  ['filtros', html.includes('Filtros')],
  ['descargas', html.includes('CSV de focos') || html.includes('Reporte ejecutivo')],
  ['semaforo', html.includes('Ventana cr')],
  ['fetch llamado', calls >= 4],
  ['contexto climatico', /más seco de lo normal/.test(html)],
]
let failed = 0
for (const [name, ok] of checks) {
  console.log(`${ok ? 'ok  ' : 'FALLO'} ${name}`)
  if (!ok) failed += 1
}
process.exit(failed ? 1 : 0)
