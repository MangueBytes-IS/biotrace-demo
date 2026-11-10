import { useCallback, useEffect, useRef, useState } from 'react'
import axios from 'axios'
import { API_URL, authHeaders, DEMO_DAILY_LIMIT, DEMO_SPECIES_LIMIT, type Analysis } from '../api/client'
import ProgressBar from '../components/ui/ProgressBar'
import PremiumDialog from '../components/ui/PremiumDialog'
import DiamondIcon from '../components/ui/DiamondIcon'
import liveIcon from '../assets/figma/live.svg'
import refreshIcon from '../assets/figma/refresh.svg'
import filterIcon from '../assets/figma/filter.svg'
import eyeIcon from '../assets/figma/eye.svg'
import plusH from '../assets/figma/plus-h.svg'
import plusV from '../assets/figma/plus-v.svg'

const PAGE_SIZE = 10
const POLL_MS = 2000

type StatusFilter = 'all' | Analysis['status']

const STATUS_LABEL: Record<Analysis['status'], string> = {
  processing: 'processando',
  completed: 'concluída',
  failed: 'falhou',
}

const FILTER_LABEL: Record<StatusFilter, string> = {
  all: 'Todos os status',
  processing: 'Processando',
  completed: 'Concluídas',
  failed: 'Falharam',
}

export default function DashboardPage({ token, onOpenAnalysis }: {
  token: string
  onOpenAnalysis: (id: string) => void
}) {
  const [analyses, setAnalyses] = useState<Analysis[]>([])
  const [filter, setFilter] = useState<StatusFilter>('all')
  const [page, setPage] = useState(1)
  const [showNewJob, setShowNewJob] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [todayCount, setTodayCount] = useState(0)
  const [premiumOpen, setPremiumOpen] = useState(false)
  const closePremium = useCallback(() => setPremiumOpen(false), [])
  const fileInput = useRef<HTMLInputElement>(null)

  const loadAnalyses = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/api/analyses`, { headers: authHeaders(token) })
      setAnalyses(response.data.analyses)
      setTodayCount(response.data.today_count ?? 0)
    } catch (err) {
      console.error('Erro ao carregar análises:', err)
    }
  }, [token])

  useEffect(() => {
    loadAnalyses()
  }, [loadAnalyses])

  const runningCount = analyses.filter((a) => a.status === 'processing').length

  // Atualização ao vivo enquanto houver análise rodando
  useEffect(() => {
    if (runningCount === 0) return
    const timer = window.setInterval(loadAnalyses, POLL_MS)
    return () => window.clearInterval(timer)
  }, [runningCount, loadAnalyses])

  const handleRefresh = async () => {
    setRefreshing(true)
    await loadAnalyses()
    setRefreshing(false)
  }

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) {
      setError('Selecione um arquivo CSV')
      return
    }
    setError('')
    setSubmitting(true)
    try {
      // Checagem rápida no navegador; o backend valida de novo
      const text = await file.text()
      const speciesCount = text.split('\n').filter((line) => line.trim()).length
      if (speciesCount > DEMO_SPECIES_LIMIT) {
        setError(
          `Você excedeu o limite da versão demo: seu arquivo tem ${speciesCount} espécies e o máximo é ${DEMO_SPECIES_LIMIT}.`,
        )
        return
      }
      const formData = new FormData()
      formData.append('file', file)
      const response = await axios.post(`${API_URL}/api/analyses`, formData, { headers: authHeaders(token) })
      setFile(null)
      setShowNewJob(false)
      // Abre a leitura de resultados, que mostra o progresso até a análise terminar
      onOpenAnalysis(response.data.id)
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erro ao criar análise')
    } finally {
      setSubmitting(false)
    }
  }

  // Número da raia = ordem de criação (a lista chega da mais nova para a mais antiga)
  const lanes = analyses.map((a, i) => ({ analysis: a, lane: analyses.length - i }))
  const visible = lanes.filter(({ analysis }) => filter === 'all' || analysis.status === filter)
  const totalPages = Math.max(1, Math.ceil(visible.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const rows = visible.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  return (
    <div className="page">
      <div className="page__heading">
        <div>
          <p className="eyebrow">Painel de sequenciamento</p>
          <h1 className="page__title">Raias de Coleta</h1>
          <p className="page__lead">
            Cada análise ocupa uma raia e atualiza automaticamente, sem recarregar a página.
          </p>
        </div>

        <div className="toolbar">
          <label className="btn-ghost btn-lg toolbar__filter">
            <img src={filterIcon} alt="" width="15" height="15" />
            <span>{FILTER_LABEL[filter]}</span>
            <select
              aria-label="Filtrar por status"
              value={filter}
              onChange={(e) => {
                setFilter(e.target.value as StatusFilter)
                setPage(1)
              }}
            >
              {(Object.keys(FILTER_LABEL) as StatusFilter[]).map((key) => (
                <option key={key} value={key}>{FILTER_LABEL[key]}</option>
              ))}
            </select>
          </label>
          <button type="button" className="btn-ghost btn-lg" onClick={handleRefresh} disabled={refreshing}>
            <img src={refreshIcon} alt="" width="14" height="14" />
            Atualizar
          </button>
          <button
            type="button"
            className="btn-accent btn-lg"
            aria-expanded={showNewJob}
            onClick={() => setShowNewJob((v) => !v)}
          >
            <span className="plus-icon" aria-hidden="true">
              <img src={plusH} alt="" width="10" height="1" />
              <img src={plusV} alt="" width="10" height="1" />
            </span>
            Nova análise
          </button>
        </div>
      </div>

      <div className="demo-notice" role="note">
        <p>
          <strong>Versão demo:</strong> cada análise aceita até {DEMO_SPECIES_LIMIT} espécies,
          com até {DEMO_DAILY_LIMIT} análises por dia ({todayCount}/{DEMO_DAILY_LIMIT} hoje).
          Uma coleta roda por vez.
        </p>
        <button type="button" className="premium-link" onClick={() => setPremiumOpen(true)}>
          <DiamondIcon />
          Versão Premium
          <span className="soon">Em breve</span>
        </button>
      </div>

      <PremiumDialog open={premiumOpen} onClose={closePremium} />

      {showNewJob && (
        <section className="card upload-card">
          <div>
            <h2 className="card__title">Enviar CSV de espécies</h2>
            <p className="muted">
              CSV com um nome científico por linha (ex: Panthera leo).
              Limite da versão demo: até {DEMO_SPECIES_LIMIT} espécies.
            </p>
          </div>
          <form className="upload-form" onSubmit={handleUpload}>
            <label className={`file-input${file ? ' file-input--filled' : ''}`}>
              <input
                ref={fileInput}
                type="file"
                accept=".csv"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                disabled={submitting}
              />
              <span>{file ? file.name : 'Escolher arquivo CSV'}</span>
            </label>
            <button type="submit" className="btn-accent" disabled={submitting || !file}>
              {submitting ? 'Enviando...' : 'Analisar'}
            </button>
          </form>
          {submitting && <ProgressBar value={2} label="Enviando arquivo" />}
          {error && <p className="form-error" role="alert">{error}</p>}
        </section>
      )}

      <div className="lanes-meta">
        <span className="live">
          <img src={liveIcon} alt="" width="18" height="13.1039" />
          atualização ao vivo
        </span>
        <span className="lanes-meta__count">{currentPage} de {totalPages}</span>
      </div>

      <section className="lanes" aria-label="Raias de coleta">
        <div className="lanes__row lanes__row--head" role="row">
          <span>Raia</span>
          <span>Status</span>
          <span>Progresso</span>
          <span>Etapa</span>
          <span>Criado</span>
          <span aria-hidden="true" />
        </div>

        {rows.length === 0 && (
          <p className="lanes__empty">
            {analyses.length === 0 ? 'Nenhuma análise ainda. Clique em Nova análise para começar.' : 'Nenhuma raia com esse status.'}
          </p>
        )}

        {rows.map(({ analysis: a, lane }) => {
          const percent = Math.max(0, Math.min(100, Math.round(a.progress ?? (a.status === 'completed' ? 100 : 0))))
          return (
            <div key={a.id} className="lanes__row" role="row">
              <div className="lane__name">
                <strong>{a.name || 'Análise'}</strong>
                <span>RAIA {String(lane).padStart(2, '0')} · {a.id.slice(0, 8)}</span>
              </div>

              <div>
                <span className={`lane-chip lane-chip--${a.status}`}>
                  <i aria-hidden="true" />
                  {STATUS_LABEL[a.status]}
                </span>
              </div>

              <div className="lane__progress">
                <div
                  className="lane__track"
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={percent}
                  aria-label={`Progresso de ${a.name || 'análise'}`}
                >
                  <div className="lane__fill" style={{ width: `${percent}%` }} />
                </div>
                <span>{percent}%</span>
              </div>

              <div className="lane__step">
                {a.status === 'failed' ? (
                  <span className="lane__error" role="alert">{a.error || 'Erro na análise'}</span>
                ) : (
                  <span>{a.status === 'completed' ? 'Análise concluída' : a.progress_message || 'Na fila'}</span>
                )}
              </div>

              <div className="lane__date">{new Date(a.created_at).toLocaleString('pt-BR')}</div>

              <div className="lane__action">
                <button
                  type="button"
                  className="icon-btn"
                  aria-label={a.status === 'processing' ? 'Acompanhar análise' : 'Ver análise'}
                  onClick={() => onOpenAnalysis(a.id)}
                >
                  <img src={eyeIcon} alt="" width="18" height="18" />
                </button>
              </div>
            </div>
          )
        })}
      </section>

      {totalPages > 1 && (
        <div className="pager">
          <button type="button" className="btn-ghost btn-sm" disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}>
            Anterior
          </button>
          <button type="button" className="btn-ghost btn-sm" disabled={currentPage === totalPages} onClick={() => setPage(currentPage + 1)}>
            Próxima
          </button>
        </div>
      )}
    </div>
  )
}
