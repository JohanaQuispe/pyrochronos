import React, { useState } from 'react'
import { api } from '../api'
import { useLanguage } from '../i18n.jsx'

const suggestions = [['¿Hay focos recientes?', 'Are there recent hotspots?'], ['¿Cómo está la temporada?', 'What is the season like?'], ['¿Cómo recibo avisos?', 'How do I receive alerts?']]

export default function AssistantPanel({ zoneParams, zoneName }) {
  const { lang, t } = useLanguage()
  const [question, setQuestion] = useState('')
  const [conversation, setConversation] = useState([])
  const [busy, setBusy] = useState(false)
  async function ask(text, displayText = text) {
    const value = text.trim()
    if (!value || busy) return
    setQuestion('')
    setBusy(true)
    setConversation((c) => [...c, { who: 'Tú', text: displayText.trim() }])
    try {
      const result = await api.ask(value, { ...zoneParams, language: lang })
      setConversation((c) => [...c, { who: 'Asistente', text: result.answer }])
    } catch {
      setConversation((c) => [...c, { who: 'Asistente', text: t('No pude consultar la información. Comprueba la conexión e inténtalo de nuevo.', 'Could not load information. Check the connection and try again.') }])
    } finally { setBusy(false) }
  }
  return <section className="card p-5" aria-labelledby="assistant-title">
    <p className="label">{t('Consulta rápida', 'Quick questions')} · {zoneName || t('zona seleccionada', 'selected area')}</p>
    <h2 id="assistant-title" className="mt-2 text-lg font-semibold text-white">{t('Pregúntale a PyroChronos', 'Ask PyroChronos')}</h2>
    <p className="mt-1 text-[12px] leading-relaxed text-zinc-400">{t('Respuestas acotadas para la zona seleccionada. Telegram vigila la zona con la que se inició el bot; cambiar esta selección no cambia sus avisos.', 'Limited answers for the selected area. Telegram monitors the area configured when the bot starts; changing this selection does not change its alerts.')}</p>
    <div className="mt-4 flex flex-wrap gap-2">{suggestions.map(([es, en]) => <button key={es} type="button" className="btn text-[11px]" disabled={busy} onClick={() => ask(lang === 'en' ? en : es)}>{lang === 'en' ? en : es}</button>)}</div>
    <div className="mt-4 max-h-72 space-y-3 overflow-y-auto" aria-live="polite" aria-label={t('Respuestas del asistente', 'Assistant responses')}>
      {conversation.map((msg, i) => <div key={i} className={`rounded-xl border p-3 text-[12.5px] leading-relaxed ${msg.who === 'Tú' ? 'ml-6 border-white/10 bg-white/[0.04] text-zinc-200' : 'mr-6 border-orange-400/20 bg-orange-400/[0.04] text-zinc-200'}`}><strong className="mb-1 block text-[11px] text-zinc-400">{msg.who === 'Tú' ? t('Tú', 'You') : t('Asistente', 'Assistant')}</strong>{msg.text}</div>)}
      {busy && <p className="hint">{t('Consultando…', 'Loading…')}</p>}
    </div>
    <form className="mt-4 flex gap-2" onSubmit={(e) => { e.preventDefault(); ask(question) }}>
      <label htmlFor="assistant-question" className="sr-only">{t('Tu pregunta', 'Your question')}</label>
      <input id="assistant-question" className="input min-w-0 flex-1" placeholder={t('Escribe una pregunta…', 'Write a question…')} value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={500} />
      <button className="btn btn-primary" disabled={busy || !question.trim()} type="submit">{t('Preguntar', 'Ask')}</button>
    </form>
    <p className="hint mt-3">{t('Los datos pueden estar desactualizados. Un foco de calor no es un incendio confirmado.', 'Data may be outdated. A heat detection is not a confirmed fire.')}</p>
  </section>
}
