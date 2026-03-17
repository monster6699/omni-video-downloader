import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

const downloadApi = axios.create({
  baseURL: '/api',
  timeout: 600000,
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

export interface DownloadResult {
  download_url: string
  method: string
  filename: string | null
}

export async function parseVideo(url: string): Promise<VideoInfo> {
  const { data } = await api.post<VideoInfo>('/video/parse', { url })
  return data
}

export async function downloadVideo(url: string, formatId?: string): Promise<DownloadResult> {
  const { data } = await downloadApi.post<DownloadResult>('/video/download', {
    url,
    format_id: formatId,
  })
  return data
}
