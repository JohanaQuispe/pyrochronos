import React, { createContext, useContext, useEffect, useState } from 'react'

const LanguageContext = createContext({ lang: 'es', setLang: () => {}, t: (es) => es })

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => {
    try { return localStorage.getItem('pyrochronos-language') === 'en' ? 'en' : 'es' } catch { return 'es' }
  })
  useEffect(() => {
    document.documentElement.lang = lang
    try { localStorage.setItem('pyrochronos-language', lang) } catch { /* storage is optional */ }
  }, [lang])
  return <LanguageContext.Provider value={{ lang, setLang, t: (es, en) => lang === 'en' ? en : es }}>{children}</LanguageContext.Provider>
}

export function useLanguage() { return useContext(LanguageContext) }

export function monthName(name, lang) {
  if (lang !== 'en' || !name) return name
  const months = { enero: 'January', febrero: 'February', marzo: 'March', abril: 'April', mayo: 'May', junio: 'June', julio: 'July', agosto: 'August', septiembre: 'September', octubre: 'October', noviembre: 'November', diciembre: 'December' }
  return months[String(name).toLowerCase()] || name
}
