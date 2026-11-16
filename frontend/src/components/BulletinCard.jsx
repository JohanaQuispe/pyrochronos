import React, { useEffect, useState } from 'react'
import { useLanguage } from '../i18n.jsx'

// El boletín es un borrador histórico opcional; copiarlo no envía mensajes.
export default function BulletinCard({ zone }) {
  const { t, lang } = useLanguage()
  const [state, setState] = useState({ text: '', loading: false, error: null, copied: false })

  useEffect(() => {
    const ctrl = new AbortController()
    setState({ text: '', loading: true, error: null, copied: false })
    fetch(`/api/bulletin?zone=${encodeURIComponent(zone)}&language=${lang}`, { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`Error ${r.status}`))))
      .then((body) => setState({ text: body.text, loading: false, error: null, copied: false }))
      .catch((e) => {
        if (e.name !== 'AbortError') setState((s) => ({ ...s, loading: false, error: e.message }))
      })
    return () => ctrl.abort()
  }, [zone, lang])

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
      <summary className="cursor-pointer text-base font-semibold text-white">{t('Borrador de boletín histórico', 'Historical bulletin draft')} <span className="ml-1 text-xs font-normal text-zinc-300">· {t('opcional', 'optional')}</span></summary>
      <p className="mt-3 text-[13px] leading-relaxed text-zinc-200">
        {t('Resume la zona seleccionada para compartirla si lo deseas. No se envía automáticamente y no es una alerta de focos recientes. Copiar el texto no lo envía a Telegram.', 'A summary of the selected area to share if you wish. It is not sent automatically and is not a recent-hotspot alert. Copying it does not send it to Telegram.')}
      </p>
      <p className="mt-3 rounded-xl border border-amber-300/30 bg-amber-300/10 px-3 py-2 text-[12px] leading-relaxed text-amber-100">
        {t('Las cifras estimadas y el ranking anual son provisionales; la validación depende de los datos y la zona.', 'Estimated figures and annual rankings are provisional; validation depends on the data and area.')}
      </p>
      {state.loading && <p className="mt-3 text-[13px] text-zinc-200">{t('Preparando el borrador…', 'Preparing draft…')}</p>}
      {state.error && <p role="alert" className="mt-3 text-[13px] text-red-200">{state.error}</p>}
      {state.text && (
        <>
          <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap rounded-xl border border-amber-200 bg-amber-50 p-4 text-[12px] leading-relaxed text-stone-900">{state.text}</pre>
          <button type="button" className="btn btn-primary mt-3" onClick={copy}>
            {state.copied ? t('¡Copiado!', 'Copied!') : t('Copiar borrador', 'Copy draft')}
          </button>
        </>
      )}
    </details>
  )
}
