import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export interface UserProfile {
  id: number
  phone: string | null
  nickname: string | null
  avatar_url: string | null
  google_email: string | null
  is_vip: boolean
  vip_expire_at: string | null
  /** monthly | yearly — last paid plan; null if unknown / legacy */
  vip_plan_id: string | null
  ai_quota: number
  is_admin: boolean
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: UserProfile
}

export async function register(phone: string, password: string, nickname?: string): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/auth/register', { phone, password, nickname })
  return data
}

export async function login(phone: string, password: string): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/auth/login', { phone, password })
  return data
}

export async function googleLogin(idToken: string): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/auth/google', { id_token: idToken })
  return data
}

export async function getMe(): Promise<UserProfile> {
  const { data } = await api.get<UserProfile>('/auth/me')
  return data
}

export interface DownloadHistoryItem {
  id: number
  url: string
  platform: string
  title: string | null
  thumbnail: string | null
  format_id: string | null
  resolution: string | null
  method: string
  status: string
  file_path: string | null
  created_at: string
}

export async function recordDownload(payload: {
  url: string
  platform: string
  title?: string
  thumbnail?: string
  format_id?: string
  resolution?: string
  method?: string
}): Promise<DownloadHistoryItem> {
  const { data } = await api.post<DownloadHistoryItem>('/user/downloads', payload)
  return data
}

export async function listDownloads(page = 1, pageSize = 20): Promise<{ items: DownloadHistoryItem[]; total: number }> {
  const { data } = await api.get('/user/downloads', { params: { page, page_size: pageSize } })
  return data
}
