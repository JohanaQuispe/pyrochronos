const BASE = import.meta.env.VITE_API_BASE || ''

function qs(params) {
  const clean = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''),
  )
  return new URLSearchParams(clean).toString()
}

async function get(path, params, signal) {
  let res
  try {
    res = await fetch(`${BASE}${path}?${qs(params)}`, { signal })
  } catch (err) {
    if (err.name === 'AbortError') throw err
    throw new Error('No hay conexión con el servidor de PyroChronos. Comprueba que la app esté iniciada y vuelve a cargar la página.')
  }
  if (!res.ok) {
    let detail = `Error ${res.status}`
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch { /* respuesta no JSON */ }
    throw new Error(detail)
  }
  return res.json()
}

export const api = {
  meta: (signal) => get('/api/meta', {}, signal),
  department: (key, signal) => get(`/api/departments/${encodeURIComponent(key)}`, {}, signal),
  calendar: (params, signal) => get('/api/calendar', params, signal),
  hotspots: (params, signal) => get('/api/hotspots', params, signal),
  recentHotspots: (params, signal) => get('/api/recent/hotspots', params, signal),
  alert: (params, signal) => get('/api/alert', params, signal),
  recent: (params, signal) => get('/api/recent', params, signal),
  ask: async (question, params, signal) => {
    const res = await fetch(`${BASE}/api/assistant`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, ...params }), signal })
    if (!res.ok) throw new Error(`Error ${res.status}`)
    return res.json()
  },
  geofences: (signal) => get('/api/geofences', {}, signal),
  groundtruth: (signal) => get('/api/groundtruth', {}, signal),
  csvUrl: (path, params) => `${BASE}${path}?${qs(params)}`,
}
