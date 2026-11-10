import { useEffect, useRef } from 'react'
import { DEMO_DAILY_LIMIT, DEMO_SPECIES_LIMIT } from '../../api/client'

// Demo x premium. Os valores "premium" são o que pretendemos oferecer: confirmar antes de divulgar.
const COMPARISON = [
  { label: 'Espécies por análise', demo: `Até ${DEMO_SPECIES_LIMIT}`, premium: 'Sem limite' },
  { label: 'Análises por dia', demo: `${DEMO_DAILY_LIMIT} por dia`, premium: 'Sem limite' },
  { label: 'Coletas ao mesmo tempo', demo: 'Uma por vez', premium: 'Várias' },
  { label: 'Velocidade da coleta', demo: 'Padrão', premium: 'Mais rápida' },
  { label: 'Envio por email', demo: 'Não', premium: 'Sim' },
]

export default function PremiumDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    closeRef.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="modal-overlay" onMouseDown={onClose}>
      <div
        className="modal premium"
        role="dialog"
        aria-modal="true"
        aria-labelledby="premium-title"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <p className="eyebrow">Versão premium</p>
        <h2 id="premium-title" className="modal__title">
          O que vem no premium
          <span className="soon">Em breve</span>
        </h2>
        <p className="muted">
          A versão premium ainda está em desenvolvimento. Veja o que muda em relação à demo:
        </p>

        <div className="compare" role="table" aria-label="Comparação entre demo e premium">
          <div className="compare__row compare__row--head" role="row">
            <span role="columnheader">Recurso</span>
            <span role="columnheader">Demo</span>
            <span role="columnheader">Premium</span>
          </div>
          {COMPARISON.map((c) => (
            <div key={c.label} className="compare__row" role="row">
              <span role="cell">{c.label}</span>
              <span role="cell" className="compare__demo">{c.demo}</span>
              <span role="cell" className="compare__premium">{c.premium}</span>
            </div>
          ))}
        </div>

        <p className="muted compare__more">E muito mais, conforme o desenvolvimento avança.</p>

        <div className="modal__actions">
          <button ref={closeRef} type="button" className="btn-accent" onClick={onClose}>
            Entendi
          </button>
        </div>
      </div>
    </div>
  )
}
