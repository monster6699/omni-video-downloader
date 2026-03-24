import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export class QuotaExhaustedError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'QuotaExhaustedError'
  }
}

/** Axios 可能把纯文本 500 放在 data 里（无 JSON detail），统一抽成可读文案 */
export function extractApiErrorMessage(e: unknown): string {
  if (axios.isAxiosError(e) && e.response) {
    const d = e.response.data
    if (typeof d === 'string' && d.trim()) return d.trim()
    if (d && typeof d === 'object' && typeof (d as { detail?: unknown }).detail === 'string') {
      return (d as { detail: string }).detail
    }
  }
  if (e instanceof Error && e.message) return e.message
  return '请求失败'
}

function handleApiError(e: unknown): never {
  if (axios.isAxiosError(e) && e.response?.status === 403) {
    throw new QuotaExhaustedError(
      e.response.data?.detail || '今日免费 AI 次数已用完，升级 VIP 无限使用',
    )
  }
  if (axios.isAxiosError(e) && (e.response?.status === 503 || e.response?.status === 500)) {
    throw new Error(extractApiErrorMessage(e))
  }
  throw e
}

export interface UsageRules {
  anon_ai_daily_limit: number
  registered_default_ai_quota: number
  vip_ai_unlimited: boolean
  subtitle_public_no_llm_quota: boolean
  anon_limit_scope: string
}

export async function fetchAiUsageRules(): Promise<UsageRules> {
  const { data } = await api.get<UsageRules>('/ai/usage-rules')
  return data
}

export interface AIQuotaStatus {
  mode: 'anonymous' | 'registered' | 'vip'
  unlimited: boolean
  remaining: number | null
  limit: number | null
  used: number | null
  display: string
  redis_unavailable: boolean
}

export async function fetchAiQuotaStatus(): Promise<AIQuotaStatus> {
  const { data } = await api.get<AIQuotaStatus>('/ai/quota-status')
  return data
}

export interface SubtitleItem {
  start: number
  end: number
  text: string
}

export interface SubtitleResponse {
  subtitles: SubtitleItem[]
  full_text: string
  source: string
}

export interface SummaryResponse {
  summary: string
  keypoints: string[]
  timeline: { time: string; content: string }[]
}

export interface MindMapResponse {
  markdown: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export async function fetchSubtitles(url: string): Promise<SubtitleResponse> {
  const { data } = await api.post<SubtitleResponse>('/ai/subtitle', { url })
  return data
}

export async function fetchSummary(
  url: string,
  text?: string,
  source?: string,
): Promise<SummaryResponse> {
  try {
    const { data } = await api.post<SummaryResponse>('/ai/summary', { url, text, source })
    return data
  } catch (e) {
    handleApiError(e)
  }
}

export async function fetchMindMap(
  url: string,
  text?: string,
  source?: string,
): Promise<MindMapResponse> {
  try {
    const { data } = await api.post<MindMapResponse>('/ai/mindmap', { url, text, source })
    return data
  } catch (e) {
    handleApiError(e)
  }
}

export interface TranslateResponse {
  translations: string[]
  target_lang: string
}

export async function translateSubtitles(
  url: string,
  texts: string[],
  targetLang: string = 'zh',
): Promise<TranslateResponse> {
  try {
    const { data } = await api.post<TranslateResponse>('/ai/translate', {
      url,
      texts,
      target_lang: targetLang,
    })
    return data
  } catch (e) {
    handleApiError(e)
  }
}

export async function streamChat(
  url: string,
  question: string,
  history: ChatMessage[],
  onChunk: (text: string) => void,
): Promise<void> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = localStorage.getItem('token')
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch('/api/ai/chat', {
    method: 'POST',
    headers,
    body: JSON.stringify({ url, question, history }),
  })

  if (response.status === 403) {
    const err = await response.json().catch(() => ({ detail: '今日免费 AI 次数已用完' }))
    throw new QuotaExhaustedError(err.detail || '今日免费 AI 次数已用完，升级 VIP 无限使用')
  }

  if (response.status === 503) {
    const err = await response.json().catch(() => ({ detail: '服务暂不可用' }))
    throw new Error(err.detail || '服务暂不可用，请稍后再试')
  }

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '请求失败' }))
    throw new Error(err.detail || '请求失败')
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('无法读取响应流')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const payload = line.slice(6).trim()
      if (payload === '[DONE]') return
      try {
        const parsed = JSON.parse(payload)
        if (parsed.content) onChunk(parsed.content)
        if (parsed.error) throw new Error(parsed.error)
      } catch {
        // skip malformed chunks
      }
    }
  }
}
