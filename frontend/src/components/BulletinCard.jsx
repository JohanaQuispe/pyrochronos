import React, { useEffect, useState } from 'react'

// El boletín es un borrador histórico opcional; copiarlo no envía mensajes.
export default function BulletinCard({ zone }) {
  const [state, setState] = useState({ text: '', loading: false, error: null, copied: false })

  useEffect(() => {
    const ctrl = new AbortController()
    setState({ text: '', loading: true, error: null, copied: false })
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
    <details className="card p-5">
      <summary className="cursor-pointer text-base font-semibold text-white">Borrador de boletín histórico <span className="ml-1 text-xs font-normal text-zinc-300">· opcional</span></summary>
      <p className="mt-3 text-[13px] leading-relaxed text-zinc-200">
        Resume la zona seleccionada para compartirla si lo deseas. No se envía automáticamente y no es una alerta de focos recientes. Copiar el texto no lo envía a Telegram.
      </p>
      <p className="mt-3 rounded-xl border border-amber-300/30 bg-amber-300/10 px-3 py-2 text-[12px] leading-relaxed text-amber-100">
        Las cifras armonizadas y el ranking anual son provisionales mientras se revisa el cálculo para periodos con VIIRS sin MODIS.
      </p>
      {state.loading && <p className="mt-3 text-[13px] text-zinc-200">Preparando el borrador…</p>}
      {state.error && <p role="alert" className="mt-3 text-[13px] text-red-200">{state.error}</p>}
      {state.text && (
        <>
          <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap rounded-xl border border-slate-300 bg-slate-50 p-4 text-[12px] leading-relaxed text-slate-800">{state.text}</pre>
          <button type="button" className="btn btn-primary mt-3" onClick={copy}>
            {state.copied ? '¡Copiado!' : 'Copiar borrador'}
          </button>
        </>
      )}
    </details>
  )
}
