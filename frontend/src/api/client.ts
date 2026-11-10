import axios from 'axios'

// VITE_API_URL vazio = mesma origem (API e site no mesmo serviço)
export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:5000'

// Contato público para pedidos de exclusão de dados
export const CONTACT_EMAIL = 'manguebytes@gmail.com'

// Limites da versão demo (o backend aplica os mesmos valores)
export const DEMO_SPECIES_LIMIT = 20
export const DEMO_DAILY_LIMIT = 3

export interface AnalysisSummary {
  total_species: number
  with_sequences: number
  without_taxid: number
  without_sequences: number
  without_taxid_list: string[]
  without_sequences_list: string[]
  file_name: string
  file_size: number
  sheets: string[]
}

export interface Analysis {
  id: string
  name?: string
  created_at: string
  status: 'processing' | 'completed' | 'failed'
  species_count: number
  result_file: string | null
  error: string | null
  progress?: number
  progress_message?: string
  summary?: AnalysisSummary | null
}

export const authHeaders = (token: string) => ({ Authorization: `Bearer ${token}` })

export async function downloadAnalysis(token: string, analysis: Analysis) {
  const response = await axios.get(`${API_URL}/api/analyses/${analysis.id}/download`, {
    headers: authHeaders(token),
    responseType: 'blob',
  })
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', analysis.summary?.file_name || `analise_${analysis.id}.xlsx`)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}
