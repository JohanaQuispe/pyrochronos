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
      className={`flex items-center gap-1 ${className}`}
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
            className={`relative rounded-lg px-3 py-2 text-[13.5px] transition ${
              active ? 'text-white' : 'text-zinc-500 hover:text-zinc-200'
            }`}
          >
            {item.label}
            {item.hint ? (
              <span className="ml-1.5 hidden text-[11px] text-zinc-600 sm:inline">{item.hint}</span>
            ) : null}
            <span
              aria-hidden="true"
              className={`absolute inset-x-2 -bottom-px h-px transition-opacity ${
                active ? 'bg-fire opacity-100' : 'opacity-0'
              }`}
            />
          </button>
        )
      })}
    </div>
  )
}
