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

export interface VideoFormat {
  format_id: string
  ext: string
  resolution: string | null
  filesize: number | null
  note: string | null
  has_video: boolean
  has_audio: boolean
}

export interface VideoInfo {
  title: string
  thumbnail: string | null
  duration: number | null
  platform: string
  formats: VideoFormat[]
}

export interface DownloadTaskResult {
  task_id: string
  status: string
}

export interface TaskStatus {
  task_id: string
  status: 'pending' | 'downloading' | 'done' | 'failed'
  progress: number
  download_url: string | null
  filename: string | null
  method: string | null
  error: string | null
}

export async function parseVideo(url: string): Promise<VideoInfo> {
  const { data } = await api.post<VideoInfo>('/video/parse', { url })
  return data
}

export async function downloadVideo(url: string, formatId?: string): Promise<DownloadTaskResult> {
  const { data } = await api.post<DownloadTaskResult>('/video/download', {
    url,
    format_id: formatId,
  })
  return data
}

export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  const { data } = await api.get<TaskStatus>(`/video/task/${taskId}`)
  return data
}
