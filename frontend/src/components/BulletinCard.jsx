import React, { useEffect, useState } from 'react'

export default function BulletinCard({ zone }) {
  const [state, setState] = useState({ text: '', loading: false, error: null, copied: false })

  useEffect(() => {
    const ctrl = new AbortController()
    setState((s) => ({ ...s, loading: true, error: null }))
    fetch(`/api/bulletin?zone=${encodeURIComponent(zone)}`, { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`Error ${r.status}`))))
      .then((body) => setState({ text: body.text, loading: false, error: null, copied: false }))
      .catch((e) => {
        if (e.name !== 'AbortError') setState((s) => ({ ...s, loading: false, error: e.message }))
      })
    return () => ctrl.abort()
  }, [zone])

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(state.text)
      setState((s) => ({ ...s, copied: true }))
      setTimeout(() => setState((s) => ({ ...s, copied: false })), 2000)
    } catch {
      setState((s) => ({ ...s, error: 'El navegador no permitió copiar; selecciona el texto a mano.' }))
    }
  }

  return (
    <details className="card p-3">
      <summary className="cursor-pointer list-none text-sm font-semibold text-white">
        <span className="mr-1 text-fire" aria-hidden="true">▸</span> Aviso para guardaparques (Telegram)
      </summary>
      <p className="mt-2 text-[11px] leading-snug text-mist">
        Borrador de mensaje con las cifras de esta zona. Se envía con
        <code className="mx-1 rounded bg-panelHi px-1">scripts/notify_telegram.py --send</code>
        usando un token que vive solo en el servidor. Es un resumen histórico: no es una alerta en tiempo real.
      </p>
      {state.loading && <p className="mt-2 text-[11px] text-mist">Redactando…</p>}
      {state.error && <p className="mt-2 text-[11px] text-red-300">{state.error}</p>}
      {state.text && (
        <>
          <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap rounded-lg border border-line bg-panelHi/60 p-2 text-[11px] leading-relaxed text-slate-200">
            {state.text}
          </pre>
          <button type="button" className="btn mt-2 px-2 py-1 text-[11px]" onClick={copy}>
            {state.copied ? '¡Copiado!' : 'Copiar mensaje'}
          </button>
        </>
      )}
    </details>
  )
}
