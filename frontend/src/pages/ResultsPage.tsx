import { useCallback, useEffect, useState } from 'react'
import axios from 'axios'
import { API_URL, authHeaders, downloadAnalysis, type Analysis } from '../api/client'
import DiamondIcon from '../components/ui/DiamondIcon'
import LayeredIcon from '../components/ui/LayeredIcon'
import PremiumDialog from '../components/ui/PremiumDialog'
import ProgressBar from '../components/ui/ProgressBar'
import arrowLeft from '../assets/figma/arrow-left.svg'
import downloadIcon from '../assets/figma/download.svg'
import sendMailIcon from '../assets/figma/send-mail.svg'
import file1 from '../assets/figma/file-1.svg'
import file2 from '../assets/figma/file-2.svg'
import warn1 from '../assets/figma/warn-1.svg'
import warn2 from '../assets/figma/warn-2.svg'
import warn3 from '../assets/figma/warn-3.svg'
import xcircle1 from '../assets/figma/xcircle-1.svg'
import xcircle2 from '../assets/figma/xcircle-2.svg'
import xcircle3 from '../assets/figma/xcircle-3.svg'

function formatSize(bytes: number) {
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export default function ResultsPage({ token, analysisId, onBack }: {
  token: string
  analysisId: string
  onBack: () => void
}) {
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [error, setError] = useState('')
  const [downloading, setDownloading] = useState(false)
  const [premiumOpen, setPremiumOpen] = useState(false)
  const closePremium = useCallback(() => setPremiumOpen(false), [])

  useEffect(() => {
    let timer: number | undefined
    let cancelled = false
    const load = async () => {
      try {
        const res = await axios.get(`${API_URL}/api/analyses/${analysisId}`, { headers: authHeaders(token) })
        if (cancelled) return
        setAnalysis(res.data)
        if (res.data.status === 'processing') timer = window.setTimeout(load, 2000)
      } catch (err: any) {
        if (!cancelled) setError(err.response?.data?.error || 'Erro ao carregar análise')
      }
    }
    load()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [analysisId, token])

  const handleDownload = async () => {
    if (!analysis) return
    setDownloading(true)
    try {
      await downloadAnalysis(token, analysis)
    } finally {
      setDownloading(false)
    }
  }

  const s = analysis?.summary

  return (
    <div className="page">
      <div className="page__heading">
        <div>
          <p className="eyebrow">Painel de sequenciamento · GenBank/NCBI</p>
          <h1 className="page__title">Leitura de Resultados</h1>
        </div>
        <button type="button" className="back-link" onClick={onBack}>
          <img src={arrowLeft} alt="" width="14" height="14" />
          <span>Voltar para análises</span>
        </button>
      </div>

      {error && <section className="card"><p className="form-error">{error}</p></section>}
      {!analysis && !error && (
        <section className="card"><ProgressBar value={0} label="Carregando análise" /></section>
      )}

      <PremiumDialog open={premiumOpen} onClose={closePremium} />

      {analysis && (
        <>
          <section className="card job-card">
            <div>
              <h2 className="job-card__name">{analysis.name || 'Análise'}</h2>
              <p className="job-card__id">{analysis.id}</p>
            </div>
            {analysis.status === 'completed' && (
              <div className="job-card__actions">
                <button type="button" className="btn-ghost btn-lg" onClick={handleDownload} disabled={downloading}>
                  <img src={downloadIcon} alt="" width="15" height="15" />
                  {downloading ? 'Baixando...' : 'Download Excel'}
                </button>
                <button type="button" className="btn-accent btn-lg" onClick={() => setPremiumOpen(true)}>
                  <img src={sendMailIcon} alt="" width="15" height="15" />
                  Enviar por email
                  <DiamondIcon size={12} />
                </button>
              </div>
            )}
          </section>

          {analysis.status === 'processing' && (
            <section className="card" aria-live="polite">
              <ProgressBar value={analysis.progress ?? 0} label={analysis.progress_message || 'Na fila'} />
            </section>
          )}

          {analysis.status === 'failed' && (
            <section className="card">
              <p className="form-error">A análise falhou.</p>
              <pre className="error-log">{analysis.error}</pre>
            </section>
          )}

          {analysis.status === 'completed' && !s && (
            <section className="card">
              <p className="muted">
                O resumo desta análise não está disponível (ela foi criada antes desta versão). O Excel pode ser
                baixado normalmente.
              </p>
            </section>
          )}

          {analysis.status === 'completed' && s && (
            <>
              <section className="card stats">
                <div><strong>{s.total_species}</strong><span>Total de espécies</span></div>
                <div><strong>{s.with_sequences}</strong><span>Com sequências</span></div>
                <div><strong>{s.without_taxid}</strong><span>Sem TaxID</span></div>
                <div><strong>{s.without_sequences}</strong><span>Sem sequências</span></div>
              </section>

              <section className="card output-card">
                <h3 className="card__title card__title--icon">
                  <LayeredIcon
                    width={20}
                    height={20}
                    layers={[
                      { src: file1, box: '12.5% 25%', bleed: '-6.14% -9.21%' },
                      { src: file2, box: '12.5% 25% 70.83% 58.33%', bleed: '-27.62%' },
                    ]}
                  />
                  Arquivo de saída
                </h3>
                <p className="muted">{s.file_name} · {formatSize(s.file_size)}</p>
                <ul className="chips">
                  {s.sheets.map((sheet) => <li key={sheet}>{sheet}</li>)}
                </ul>
              </section>

              <div className="lists">
                <section className="card species-card">
                  <header>
                    <h3 className="card__title card__title--icon">
                      <LayeredIcon
                        width={27}
                        height={27}
                        layers={[
                          { src: warn1, box: '16.67% 10.42%', bleed: '-10.41% -7.86% -5.31% -7.86%' },
                          { src: warn2, box: '41.67% 50% 39.58% 50%', bleed: '-18.89% -0.96px' },
                          { src: warn3, box: '70% 50% 29.17% 50%', bleed: '-425% -0.96px' },
                        ]}
                      />
                      Sem TaxID
                    </h3>
                    <span className="count-pill">{s.without_taxid}</span>
                  </header>
                  {s.without_taxid_list.length === 0
                    ? <p className="muted">Todas as espécies tiveram TaxID encontrado.</p>
                    : <ul className="species-list">{s.without_taxid_list.map((n) => <li key={n}>{n}</li>)}</ul>}
                </section>

                <section className="card species-card">
                  <header>
                    <h3 className="card__title card__title--icon">
                      <LayeredIcon
                        width={26}
                        height={26}
                        layers={[
                          { src: xcircle1, box: '12.5%', bleed: '-4.72%' },
                          { src: xcircle2, box: '37.5%', bleed: '-20.03%' },
                          { src: xcircle3, box: '37.5%', bleed: '-20.03%' },
                        ]}
                      />
                      Sem sequências
                    </h3>
                    <span className="count-pill">{s.without_sequences}</span>
                  </header>
                  {s.without_sequences_list.length === 0
                    ? <p className="muted">Todas as espécies com TaxID tiveram sequências.</p>
                    : <ul className="species-list species-list--muted">{s.without_sequences_list.map((n) => <li key={n}>{n}</li>)}</ul>}
                </section>
              </div>

              <p className="footnote">Rankings e gráficos detalhados estão disponíveis no relatório Excel exportado.</p>
            </>
          )}
        </>
      )}
    </div>
  )
}
