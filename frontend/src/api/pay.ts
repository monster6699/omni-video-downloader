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

export interface PlanInfo {
  id: string
  name: string
  price: number
  duration_days: number
  description: string
}

export interface CreateOrderResponse {
  order_no: string
  qr_url: string
  amount: number
  pay_method: string
}

export interface OrderStatus {
  order_no: string
  status: 'pending' | 'paid' | 'expired' | 'failed'
  plan_id: string
  amount: number
  pay_method: string
  paid_at: string | null
}

export async function getPlans(): Promise<PlanInfo[]> {
  const { data } = await api.get<PlanInfo[]>('/pay/plans')
  return data
}

export async function createOrder(planId: string, payMethod: string): Promise<CreateOrderResponse> {
  const { data } = await api.post<CreateOrderResponse>('/pay/create', {
    plan_id: planId,
    pay_method: payMethod,
  })
  return data
}

export async function getOrderStatus(orderNo: string): Promise<OrderStatus> {
  const { data } = await api.get<OrderStatus>(`/pay/status/${orderNo}`)
  return data
}
