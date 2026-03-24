import { getToken } from './storage'
import type { VideoInfo, TaskStatus, AuthResponse, UserProfile, SummaryResponse, SubtitleResponse, TranslateResponse } from './types'

const API_BASE = 'http://localhost:8000/api'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`
  console.log(`[OmniDL] ${options.method || 'GET'} ${path} | auth: ${token ? 'yes' : 'NO'}`)
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    console.warn(`[OmniDL] ${path} → ${res.status}:`, body.detail)
    throw new ApiError(res.status, body.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export function parseVideo(url: string): Promise<VideoInfo> {
  return apiFetch('/video/parse', { method: 'POST', body: JSON.stringify({ url }) })
}

export function startDownload(url: string, formatId?: string): Promise<{ task_id: string; status: string }> {
  return apiFetch('/video/download', { method: 'POST', body: JSON.stringify({ url, format_id: formatId }) })
}

export function getTaskStatus(taskId: string): Promise<TaskStatus> {
  return apiFetch(`/video/task/${taskId}`)
}

export function getImageProxyUrl(url: string): string {
  return `${API_BASE}/video/proxy/image?url=${encodeURIComponent(url)}`
}

export function login(phone: string, password: string): Promise<AuthResponse> {
  return apiFetch('/auth/login', { method: 'POST', body: JSON.stringify({ phone, password }) })
}

export function getMe(): Promise<UserProfile> {
  return apiFetch('/auth/me')
}

export function fetchSubtitle(url: string): Promise<SubtitleResponse> {
  return apiFetch('/ai/subtitle', { method: 'POST', body: JSON.stringify({ url }) })
}

export function fetchSummary(url: string, text?: string, source?: string): Promise<SummaryResponse> {
  const body: Record<string, string> = { url }
  if (text) body.text = text
  if (source) body.source = source
  return apiFetch('/ai/summary', { method: 'POST', body: JSON.stringify(body) })
}

export function fetchMindMap(url: string, text?: string, source?: string): Promise<{ markdown: string }> {
  const body: Record<string, string> = { url }
  if (text) body.text = text
  if (source) body.source = source
  return apiFetch('/ai/mindmap', { method: 'POST', body: JSON.stringify(body) })
}

export function translateSubtitles(url: string, texts: string[], targetLang: string): Promise<TranslateResponse> {
  return apiFetch('/ai/translate', {
    method: 'POST',
    body: JSON.stringify({ url, texts, target_lang: targetLang }),
  })
}

export async function streamChat(
  url: string,
  question: string,
  history: { role: string; content: string }[],
  onChunk: (text: string) => void,
): Promise<void> {
  const token = await getToken()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}/ai/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ url, question, history }),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, body.detail || `HTTP ${res.status}`)
  }

  const reader = res.body?.getReader()
  if (!reader) throw new Error('No response body')

  const decoder = new TextDecoder()
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const text = decoder.decode(value, { stream: true })
    for (const line of text.split('\n')) {
      if (line.startsWith('data: ')) {
        const raw = line.slice(6)
        if (raw === '[DONE]') return
        try {
          const parsed = JSON.parse(raw)
          if (parsed.content) onChunk(parsed.content)
          else if (parsed.error) onChunk(`\n[错误] ${parsed.error}`)
        } catch {
          onChunk(raw)
        }
      }
    }
  }
}
