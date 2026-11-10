import { useEffect, useRef, useState } from 'react'
import logo from '../../assets/figma/logo.png'
import chevron from '../../assets/figma/chevron.svg'

function initials(email: string) {
  const name = email.split('@')[0].replace(/[^a-zA-Z]/g, '')
  return (name.slice(0, 2) || 'BX').toUpperCase()
}

export default function AppHeader({ email, onLogout }: { email: string; onLogout: () => void }) {
  const [open, setOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => {
      if (!menuRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])

  return (
    <header className="app-header">
      <div className="app-header__inner">
        <img className="app-header__logo" src={logo} alt="BioTraceX" />
        <div className="user-menu" ref={menuRef}>
          <button
            type="button"
            className="user-menu__trigger"
            aria-haspopup="menu"
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            <span className="user-menu__avatar">{initials(email)}</span>
            <img className="user-menu__chevron" src={chevron} alt="" width="8.20208" height="4.70208" />
          </button>
          {open && (
            <div className="user-menu__dropdown" role="menu">
              <p className="user-menu__email">{email}</p>
              <button type="button" role="menuitem" onClick={onLogout}>Sair</button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
