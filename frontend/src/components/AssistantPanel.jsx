import React, { useState } from 'react'
import { api } from '../api'

const suggestions = ['¿Hay focos recientes?', '¿Cómo está la temporada?', '¿Cómo recibo avisos?']

export default function AssistantPanel({ zoneParams, zoneName }) {
  const [question, setQuestion] = useState('')
  const [conversation, setConversation] = useState([])
  const [busy, setBusy] = useState(false)
  async function ask(text) {
    const value = text.trim()
    if (!value || busy) return
    setQuestion('')
    setBusy(true)
    setConversation((c) => [...c, { who: 'Tú', text: value }])
    try {
      const result = await api.ask(value, zoneParams)
      setConversation((c) => [...c, { who: 'Asistente', text: result.answer }])
    } catch {
      setConversation((c) => [...c, { who: 'Asistente', text: 'No pude consultar la información. Comprueba la conexión e inténtalo de nuevo.' }])
    } finally { setBusy(false) }
  }
  return <section className="card p-5" aria-labelledby="assistant-title">
    <p className="label">Consulta rápida · {zoneName || 'zona seleccionada'}</p>
    <h2 id="assistant-title" className="mt-2 text-lg font-semibold text-white">Pregúntale a PyroChronos</h2>
    <p className="mt-1 text-[12px] leading-relaxed text-zinc-400">Respuestas acotadas para la zona seleccionada. Telegram vigila la zona con la que se inició el bot; cambiar esta selección no cambia sus avisos.</p>
    <div className="mt-4 flex flex-wrap gap-2">{suggestions.map((q) => <button key={q} type="button" className="btn text-[11px]" disabled={busy} onClick={() => ask(q)}>{q}</button>)}</div>
    <div className="mt-4 max-h-72 space-y-3 overflow-y-auto" aria-live="polite" aria-label="Respuestas del asistente">
      {conversation.map((msg, i) => <div key={i} className={`rounded-xl border p-3 text-[12.5px] leading-relaxed ${msg.who === 'Tú' ? 'ml-6 border-white/10 bg-white/[0.04] text-zinc-200' : 'mr-6 border-orange-400/20 bg-orange-400/[0.04] text-zinc-200'}`}><strong className="mb-1 block text-[11px] text-zinc-400">{msg.who}</strong>{msg.text}</div>)}
      {busy && <p className="hint">Consultando…</p>}
    </div>
    <form className="mt-4 flex gap-2" onSubmit={(e) => { e.preventDefault(); ask(question) }}>
      <label htmlFor="assistant-question" className="sr-only">Tu pregunta</label>
      <input id="assistant-question" className="input min-w-0 flex-1" placeholder="Escribe una pregunta…" value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={500} />
      <button className="btn btn-primary" disabled={busy || !question.trim()} type="submit">Preguntar</button>
    </form>
    <p className="hint mt-3">Los datos pueden estar desactualizados. Un foco de calor no es un incendio confirmado.</p>
  </section>
}
