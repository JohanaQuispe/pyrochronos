// Prueba de humo sin navegador: monta los componentes con un payload real en jsdom.
// Sirve para detectar errores de ejecucion (accesos a undefined, props mal pasadas).
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
global.getComputedStyle = dom.window.getComputedStyle
global.requestAnimationFrame = (cb) => setTimeout(cb, 0)
global.IS_REACT_ACT_ENVIRONMENT = false

const payload = JSON.parse(readFileSync(process.argv[2] || new URL('./fixtures/calendar-month.json', import.meta.url), 'utf8'))

const entry = `
import React from 'react'
import { createRoot } from 'react-dom/client'
import SummaryCards from './src/components/SummaryCards.jsx'
import CalendarHeatmap from './src/components/CalendarHeatmap.jsx'
import AnomalyChart from './src/components/AnomalyChart.jsx'
import HarmonizationPanel from './src/components/HarmonizationPanel.jsx'
import ActionBar from './src/components/ActionBar.jsx'

const data = ${JSON.stringify(payload)}
const params = { zone: 'peru', start: data.meta.start, end: data.meta.end, granularity: data.meta.granularity, measure: data.meta.measure, sources: 'both' }

export function render() {
  const el = document.getElementById('root')
  const root = createRoot(el)
  root.render(React.createElement('div', null,
    React.createElement(SummaryCards, { data }),
    React.createElement(CalendarHeatmap, { data, onPickYear: () => {} }),
    React.createElement(AnomalyChart, { data, years: data.calendar.years, onYearChange: () => {} }),
    React.createElement(HarmonizationPanel, { data }),
    React.createElement(ActionBar, { downloads: { hotspots: '/api/csv/hotspots', series: '/api/csv/series', report: '/api/report' }, data, onExportPng: () => {} }),
  ))
  return new Promise((resolve) => setTimeout(() => resolve(el.innerHTML), 400))
}
`

const result = await build({
  stdin: { contents: entry, resolveDir: process.cwd(), loader: 'jsx' },
  bundle: true,
  write: false,
  format: 'esm',
  platform: 'browser',
  loader: { '.js': 'jsx', '.jsx': 'jsx' },
  define: { 'process.env.NODE_ENV': '"development"', 'import.meta.env': '{"VITE_API_BASE":""}' },
})
writeFileSync('/tmp/smoke-bundle.mjs', result.outputFiles[0].text)
const mod = await import('file:///tmp/smoke-bundle.mjs').catch((e) => {
  console.error('ERROR al cargar el bundle:', e.message)
  process.exit(1)
})
const html = await mod.render()
const checks = [
  ['tarjetas', html.includes('Mes más activo') || html.includes('Mes m&aacute;s activo')],
  ['calendario', html.includes('Calendario de actividad')],
  ['anio 2000', html.includes('2000')],
  ['armonizacion', html.includes('Cómo se armonizó') || html.includes('C&oacute;mo se armoniz')],
  ['descargas', html.includes('Descargar CSV de focos') && html.includes('Reporte ejecutivo')],
  ['celdas renderizadas', (html.match(/role="gridcell"/g) || []).length > 100],
]
let failed = 0
for (const [name, ok] of checks) {
  console.log(`${ok ? 'ok  ' : 'FALLO'} ${name}`)
  if (!ok) failed += 1
}
process.exit(failed ? 1 : 0)
