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

export interface AdminUserItem {
  id: number
  phone: string | null
  nickname: string | null
  google_email: string | null
  is_vip: boolean
  vip_expire_at: string | null
  ai_quota: number
  is_admin: boolean
  created_at: string
  download_count: number
  ai_task_count: number
}

export interface AdminUserList {
  items: AdminUserItem[]
  total: number
}

export interface AdminUserUpdate {
  is_vip?: boolean
  vip_expire_at?: string | null
  ai_quota?: number
  is_admin?: boolean
  nickname?: string
}

export interface AdminStats {
  total_users: number
  vip_users: number
  today_downloads: number
  today_ai_tasks: number
  ai_type_distribution: Record<string, number>
}

export async function fetchAdminUsers(
  page = 1,
  pageSize = 20,
  keyword = '',
): Promise<AdminUserList> {
  const { data } = await api.get<AdminUserList>('/admin/users', {
    params: { page, page_size: pageSize, keyword },
  })
  return data
}

export async function updateAdminUser(userId: number, update: AdminUserUpdate): Promise<void> {
  await api.put(`/admin/users/${userId}`, update)
}

export async function fetchAdminStats(): Promise<AdminStats> {
  const { data } = await api.get<AdminStats>('/admin/stats')
  return data
}

export interface AdminVipPricing {
  monthly_fen: number
  yearly_fen: number
  updated_at: string | null
}

export async function fetchAdminVipPricing(): Promise<AdminVipPricing> {
  const { data } = await api.get<AdminVipPricing>('/admin/vip-pricing')
  return data
}

export async function updateAdminVipPricing(payload: {
  monthly_fen: number
  yearly_fen: number
}): Promise<AdminVipPricing> {
  const { data } = await api.put<AdminVipPricing>('/admin/vip-pricing', payload)
  return data
}
