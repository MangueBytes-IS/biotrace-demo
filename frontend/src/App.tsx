import { useState } from 'react'
import axios from 'axios'
import { API_URL, authHeaders } from './api/client'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import ResultsPage from './pages/ResultsPage'
import AppHeader from './components/ui/AppHeader'
import './App.css'

export interface Session {
  email: string
  token: string
}

function readStoredSession(): Session | null {
  try {
    const raw = localStorage.getItem('session')
    return raw ? (JSON.parse(raw) as Session) : null
  } catch {
    return null
  }
}

export default function App() {
  const [session, setSession] = useState<Session | null>(readStoredSession)
  const [openAnalysisId, setOpenAnalysisId] = useState<string | null>(null)

  const handleLogin = (newSession: Session) => {
    try {
      localStorage.setItem('session', JSON.stringify(newSession))
    } catch {
      // Sem localStorage a sessão dura só até recarregar a página
    }
    setSession(newSession)
  }

  const handleLogout = () => {
    if (session) {
      // Invalida o token no servidor; se falhar, a sessão local é encerrada mesmo assim
      axios.post(`${API_URL}/api/logout`, null, { headers: authHeaders(session.token) }).catch(() => {})
    }
    try {
      localStorage.removeItem('session')
    } catch {
      // nada a fazer
    }
    setOpenAnalysisId(null)
    setSession(null)
  }

  if (!session) return <LoginPage onLogin={handleLogin} />

  return (
    <div className="shell">
      <AppHeader email={session.email} onLogout={handleLogout} />
      <main className="shell__main">
        {openAnalysisId ? (
          <ResultsPage token={session.token} analysisId={openAnalysisId} onBack={() => setOpenAnalysisId(null)} />
        ) : (
          <DashboardPage token={session.token} onOpenAnalysis={setOpenAnalysisId} />
        )}
      </main>
      <footer className="shell__footer">BioTraceX NCBI Backend v0.1.0</footer>
    </div>
  )
}
