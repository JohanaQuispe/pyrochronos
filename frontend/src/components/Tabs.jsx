import React, { useRef } from 'react'

/**
 * Pestañas accesibles (role=tablist + navegación con flechas).
 * `items`: [{ key, label, hint? }]
 */
export default function Tabs({ items, value, onChange, className = '' }) {
  const refs = useRef({})

  const onKeyDown = (event) => {
    if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return
    event.preventDefault()
    const index = items.findIndex((item) => item.key === value)
    let next = index
    if (event.key === 'ArrowRight') next = (index + 1) % items.length
    if (event.key === 'ArrowLeft') next = (index - 1 + items.length) % items.length
    if (event.key === 'Home') next = 0
    if (event.key === 'End') next = items.length - 1
    const target = items[next]
    onChange(target.key)
    refs.current[target.key]?.focus()
  }

  return (
    <div
      role="tablist"
      aria-label="Vistas de PyroChronos"
      onKeyDown={onKeyDown}
      className={`flex items-center gap-1.5 overflow-x-auto ${className}`}
    >
      {items.map((item) => {
        const active = item.key === value
        return (
          <button
            key={item.key}
            ref={(el) => {
              refs.current[item.key] = el
            }}
            role="tab"
            id={`tab-${item.key}`}
            aria-selected={active}
            aria-controls={`panel-${item.key}`}
            tabIndex={active ? 0 : -1}
            type="button"
            onClick={() => onChange(item.key)}
            className={`relative rounded-xl px-3 py-2.5 text-[12.5px] sm:px-4 sm:text-[13px] transition ${
              active ? 'bg-white/[0.075] text-white shadow-[inset_0_0_0_1px_rgba(255,255,255,.06)]' : 'text-zinc-500 hover:bg-white/[0.035] hover:text-zinc-200'
            }`}
          >
            {item.label}
            {item.hint ? (
              <span className="ml-1.5 hidden text-[11px] text-zinc-600 sm:inline">{item.hint}</span>
            ) : null}
            <span
              aria-hidden="true"
              className={`absolute inset-x-3 -bottom-px h-[2px] transition-opacity ${
                active ? 'bg-fire opacity-100' : 'opacity-0'
              }`}
            />
          </button>
        )
      })}
    </div>
  )
}
