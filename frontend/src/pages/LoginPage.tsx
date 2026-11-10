import { useState } from 'react'
import axios from 'axios'
import { API_URL, CONTACT_EMAIL } from '../api/client'
import type { Session } from '../App'
import LayeredIcon from '../components/ui/LayeredIcon'
import loginBg from '../assets/figma/login-bg.png'
import logo from '../assets/figma/logo.png'
import mail1 from '../assets/figma/mail-1.svg'
import mail2 from '../assets/figma/mail-2.svg'
import featFlow from '../assets/figma/feat-flow.svg'
import featShield from '../assets/figma/feat-shield.svg'
import featLock from '../assets/figma/feat-lock.svg'

const MIN_PASSWORD_LENGTH = 8

const FEATURES = [
  { icon: featFlow, size: 19.54, title: 'Fluxo automatizado', text: 'Do CSV ao relatório completo' },
  { icon: featShield, size: 19.5, title: 'Ambiente protegido', text: 'Seu e-mail identifica as consultas ao NCBI' },
  { icon: featLock, size: 19.5, title: 'Seus dados sob controle', text: 'Histórico e arquivos centralizados' },
]

export default function LoginPage({ onLogin }: { onLogin: (session: Session) => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const isRegister = mode === 'register'

  const switchMode = () => {
    setMode(isRegister ? 'login' : 'register')
    setError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (isRegister && password.length < MIN_PASSWORD_LENGTH) {
      setError(`A senha precisa ter pelo menos ${MIN_PASSWORD_LENGTH} caracteres.`)
      return
    }
    setLoading(true)
    try {
      const normalized = email.trim()
      const endpoint = isRegister ? '/api/register' : '/api/login'
      const { data } = await axios.post(`${API_URL}${endpoint}`, { email: normalized, password })
      onLogin({ email: normalized, token: data.token })
    } catch (err: any) {
      setError(err.response?.data?.error || 'Não foi possível entrar. Verifique se o backend está rodando.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login">
      <aside className="login__hero" style={{ backgroundImage: `url(${loginBg})` }}>
        <img className="login__logo" src={logo} alt="BioTraceX" />

        <div className="login__pitch">
          <p className="login__eyebrow">Inteligência para pesquisa genética</p>
          <h1 className="login__headline">
            Dados científicos.<br />
            <span>Decisões mais claras.</span>
          </h1>
          <p className="login__lead">
            Extraia, organize e acompanhe dados do GenBank em uma experiência segura e desenhada para
            pesquisadores.
          </p>

          <ul className="login__features">
            {FEATURES.map((f) => (
              <li key={f.title}>
                <span className="login__feature-icon">
                  <img src={f.icon} alt="" width={f.size} height={f.size} />
                </span>
                <span>
                  <strong>{f.title}</strong>
                  <small>{f.text}</small>
                </span>
              </li>
            ))}
          </ul>
        </div>
      </aside>

      <main className="login__panel">
        <div className="login__card">
          <p className="login__kicker">Acesso seguro</p>
          <h2 className="login__title">{isRegister ? 'Criar conta' : 'Bem-vindo de volta'}</h2>
          <p className="login__subtitle">
            {isRegister ? 'Escolha um e-mail e uma senha.' : 'Informe seu e-mail e senha para continuar.'}
          </p>

          <form className="login__form" onSubmit={handleSubmit}>
            <label className="field-label" htmlFor="login-email">E-mail</label>
            <div className="input-wrap">
              <LayeredIcon
                width={16}
                height={16}
                style={{ position: 'absolute', left: 15, top: 17 }}
                layers={[
                  { src: mail1, box: '20.83% 12.5%', bleed: '-6.07% -4.72%' },
                  { src: mail2, box: '25% 14.58% 45.83% 14.58%', bleed: '-17.09% -7.04% -15.73% -7.04%' },
                ]}
              />
              <input
                id="login-email"
                type="email"
                placeholder="seu@email.com"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <label className="field-label login__password-label" htmlFor="login-password">Senha</label>
            <div className="input-wrap">
              <input
                id="login-password"
                type="password"
                placeholder={isRegister ? `Mínimo de ${MIN_PASSWORD_LENGTH} caracteres` : 'Sua senha'}
                autoComplete={isRegister ? 'new-password' : 'current-password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <p className="login__hint">
              Este e-mail é enviado ao NCBI (Entrez) para identificar suas consultas.
            </p>

            {error && <p className="form-error" role="alert">{error}</p>}

            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Aguarde...' : isRegister ? 'Criar conta' : 'Entrar na plataforma'}
            </button>
          </form>

          <p className="login__switch">
            {isRegister ? 'Já tem conta?' : 'Ainda não tem conta?'}{' '}
            <button type="button" className="back-link" onClick={switchMode}>
              {isRegister ? 'Entrar' : 'Criar conta'}
            </button>
          </p>

          <div className="login__footer">
            <p>
              Versão demo: não use senhas nem dados pessoais sensíveis. Para excluir sua conta e seus
              dados, escreva para{' '}
              <a href={`mailto:${CONTACT_EMAIL}?subject=Exclusão de conta BioTraceX`}>{CONTACT_EMAIL}</a>.
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
