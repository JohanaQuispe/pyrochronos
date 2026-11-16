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
global.localStorage = dom.window.localStorage
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
    { key: 'd_15', name: 'Lima', bbox: [-77.9, -13.4, -75.5, -10.2], kind: 'department' },
  ],
  default_zone: 'peru', coverage: calendar.meta.coverage, measures: [], default_measure: 'cell_days',
  cell_deg: 0.01, sources: [], thresholds: {}, quality: {}, months: [], max_area_deg2: 300,
}
const hotspots = { type: 'FeatureCollection', features: [{ type: 'Feature', geometry: { type: 'Point', coordinates: [-69.1, -12.5] }, properties: { day: '2024-09-01', source: 'VIIRS', conf: 1, frp: 3.2 } }], meta: { total: 1, shown: 1, sampled: false } }

let calls = 0
let recentAvailable = false
const urls = []
const requests = []
global.fetch = async (url, options = {}) => {
  requests.push({ url: String(url), ...options })
  calls += 1
  urls.push(String(url))
  const body = url.includes('/api/meta') ? meta
    : url.includes('/api/assistant') ? { answer: 'No hay datos recientes cargados; verifica en campo.' }
    : url.includes('/api/departments/') ? { type: 'Feature', geometry: { type: 'Polygon', coordinates: [[[-77,-12],[-76,-12],[-76,-11],[-77,-12]]] }, properties: { name: 'Lima' } }
    : url.includes('/api/recent/hotspots') ? { type: 'FeatureCollection', features: [], meta: { available: recentAvailable, total: 0, shown: 0, sampled: false, fetched_at: recentAvailable ? '2026-11-16T01:04:07+00:00' : null, last_day: recentAvailable ? '2026-11-15' : null, bbox: [-81.5, -18.5, -68.5, 0.5] } }
    : url.includes('/api/recent?') ? { available: false, reason: 'Sin datos NRT cargados.', meta: {} }
      : url.includes('/api/geofences') ? { count: 0, items: [] }
        : url.includes('/api/groundtruth') ? { summary: { total: 0, counts: { fuego_real: 0, quema_agricola: 0, falsa_alarma: 0 } }, items: [] }
    : url.includes('/api/hotspots') ? hotspots
      : url.includes('/api/bulletin') ? { text: 'boletin de prueba', zone: 'Peru', note: '' }
        : url.includes('/api/alert') ? {
          available: true, level: 'critico', severity: 2, label: 'Ventana crítica', short: 'Actividad histórica máxima',
          action: 'Activa vigilancia diaria.', reasons: ['Referencia: semana 36.', 'Pico en la semana 36.', 'Se espera 100 % del pico.'],
          reference_date: '2026-09-08', week: 36, peak_week: 36, ratio: 1.0,
          window: [{ week: 36, expected: 100, ratio: 1, in_peak: true }, { week: 37, expected: 80, ratio: 0.8, in_peak: true }],
          recent: { available: false }, disclaimer: 'No es un pronóstico.',
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
  ['pestanas', html.includes('Mapa') && html.includes('Historial') && html.includes('Telegram y estado')],
  ['vista de campo', html.includes('Telegram y datos recientes')],
  ['destinatarios claros', html.includes('Información satelital para bomberos y brigadas')],
  ['histórico separado', html.includes('Última fecha del archivo histórico') && html.includes('Los datos recientes se muestran por separado')],
  ['guía y límites visibles', html.includes('Cómo usar el mapa') && html.includes('Un punto de calor no confirma un incendio')],
  ['calendario montado', html.includes('Calendario de actividad')],
  ['guía sencilla de calendario', html.includes('Cada fila es un año y cada columna un mes.') && html.includes('Toca un cuadro para ver el detalle.')],
  ['nota breve y explicación', html.includes('Cifras estimadas y ranking provisionales.') && html.includes('¿Por qué?')],
  ['mapa montado', html.includes('leaflet-container')],
  ['filtros', html.includes('Filtros')],
  ['descargas', html.includes('CSV de focos') || html.includes('Reporte ejecutivo')],
  ['semaforo', html.includes('Ventana cr')],
  ['fetch llamado', calls >= 7],
  ['datos recientes explicados', html.includes('No hay datos recientes cargados')],
  ['ubicaciones consultadas', html.includes('Ubicaciones para recibir avisos')],
  ['veredictos consultados', html.includes('Veredictos registrados')],
  ['logo visible', Boolean(dom.window.document.querySelector('header img[src="/logo.png"]'))],
  ['sin NASA POWER en la interfaz', !html.includes('NASA POWER') && !urls.some((url) => url.includes('/api/climate-context'))],
  ['boletín histórico opcional', html.includes('Borrador de boletín histórico') && html.includes('Copiar el texto no lo envía a Telegram')],
  ['boletín solo en campo', !dom.window.document.querySelector('#panel-mapa').textContent.includes('Borrador de boletín histórico') && dom.window.document.querySelector('#panel-campo').textContent.includes('Borrador de boletín histórico')],
]
const root = dom.window.document.getElementById('root')
root.querySelector('#tab-mapa').click()
await new Promise((r) => setTimeout(r, 100))
checks.push(['pestaña mapa activa', !root.querySelector('#panel-mapa').hidden && root.querySelector('#panel-calendario').hidden])
const mapData = root.querySelector('[aria-label="Datos del mapa"]')
const [recentButton, historyButton] = mapData.querySelectorAll('button')
checks.push(['mapa reciente por defecto', recentButton.getAttribute('aria-pressed') === 'true' && urls.some((url) => url.includes('/api/recent/hotspots'))])
checks.push(['datos ausentes no significan ausencia de focos', root.querySelector('#panel-mapa').textContent.includes('Esto no significa que no haya focos')])
historyButton.click()
await new Promise((r) => setTimeout(r, 100))
checks.push(['cambio a historial', historyButton.getAttribute('aria-pressed') === 'true' && urls.some((url) => url.includes('/api/hotspots')) && root.querySelector('#panel-mapa').textContent.includes('no muestra incendios activos ahora')])
recentAvailable = true
recentButton.click()
await new Promise((r) => setTimeout(r, 100))
checks.push(['fecha de archivo reciente', recentButton.getAttribute('aria-pressed') === 'true' && root.querySelector('#panel-mapa').textContent.includes('2026-11-16T01:04:07+00:00') && root.querySelector('#panel-mapa').textContent.includes('última detección del archivo completo')])
const sensor = root.querySelector('[aria-label="Sensor del mapa"]')
sensor.value = 'viirs'
sensor.dispatchEvent(new dom.window.Event('change', { bubbles: true }))
await new Promise((r) => setTimeout(r, 100))
checks.push(['filtro VIIRS en petición', urls.some((url) => url.includes('/api/recent/hotspots') && url.includes('sources=viirs'))])
const questionButton = [...root.querySelectorAll('button')].find((button) => button.textContent === '¿Hay focos recientes?')
questionButton.click()
await new Promise((r) => setTimeout(r, 100))
checks.push(['consulta del asistente', root.textContent.includes('No hay datos recientes cargados; verifica en campo.') && urls.some((url) => url.includes('/api/assistant'))])
const zoneSelect = root.querySelector('#zone-select')
zoneSelect.value = 'd_15'
zoneSelect.dispatchEvent(new dom.window.Event('change', { bubbles: true }))
await new Promise((r) => setTimeout(r, 150))
checks.push(['selección departamental', urls.some((url) => url.includes('/api/calendar') && url.includes('zone=d_15')) && urls.some((url) => url.includes('/api/departments/d_15'))])
const language = root.querySelector('[aria-label="Idioma / Language"]')
language.value = 'en'
language.dispatchEvent(new dom.window.Event('change', { bubbles: true }))
await new Promise((r) => setTimeout(r, 150))
checks.push(['interfaz en inglés', root.textContent.includes('Satellite information for firefighters') && root.textContent.includes('Activity calendar') && root.textContent.includes('Heat detection map') && root.textContent.includes('Telegram and recent data')])
checks.push(['mapa reciente también en inglés', root.textContent.includes('Recent data') && root.textContent.includes('Historical data') && root.textContent.includes('Last download (UTC)')])
checks.push(['idioma y selección conservados', document.documentElement.lang === 'en' && localStorage.getItem('pyrochronos-language') === 'en' && root.querySelector('#zone-select').value === 'd_15'])
checks.push(['idioma de Telegram explicado', root.textContent.includes('send /language en to the bot')])
const englishQuestion = [...root.querySelectorAll('button')].find((button) => button.textContent === 'Are there recent hotspots?')
englishQuestion.click()
await new Promise((r) => setTimeout(r, 100))
checks.push(['asistente solicita inglés', requests.some((r) => r.url.includes('/api/assistant') && r.body && JSON.parse(r.body).language === 'en')])
checks.push(['reporte solicita inglés', root.querySelector('a[href*="/api/report"]').href.includes('language=en')])
root.querySelector('#tab-calendario').click()
await new Promise((r) => setTimeout(r, 100))
checks.push(['advertencia provisional en inglés', root.textContent.includes('Estimated figures and rankings are provisional.') && root.textContent.includes('Why?')])
const filterButton = [...root.querySelectorAll('button')].find((button) => button.textContent.includes('Filters'))
filterButton.click()
await new Promise((r) => setTimeout(r, 100))
checks.push(['filtros en inglés', root.textContent.includes('Advanced filters') && root.textContent.includes('Colorblind')])
root.querySelector('[aria-label="Close"]').click()
language.value = 'es'
language.dispatchEvent(new dom.window.Event('change', { bubbles: true }))
await new Promise((r) => setTimeout(r, 150))
checks.push(['vuelve al español', document.documentElement.lang === 'es' && localStorage.getItem('pyrochronos-language') === 'es' && root.textContent.includes('Calendario de actividad')])
let failed = 0
for (const [name, ok] of checks) {
  console.log(`${ok ? 'ok  ' : 'FALLO'} ${name}`)
  if (!ok) failed += 1
}
process.exit(failed ? 1 : 0)
