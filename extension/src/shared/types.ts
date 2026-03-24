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

export interface TaskStatus {
  task_id: string
  status: 'pending' | 'downloading' | 'done' | 'failed'
  progress: number
  download_url: string | null
  filename: string | null
  method: string | null
  error: string | null
}

export interface UserProfile {
  id: number
  phone: string | null
  nickname: string | null
  avatar_url: string | null
  google_email: string | null
  is_vip: boolean
  vip_expire_at: string | null
  ai_quota: number
  is_admin: boolean
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: UserProfile
}

export interface SummaryResponse {
  summary: string
  keypoints: string[]
  timeline: { time: string; text: string }[]
}

export interface SubtitleResponse {
  subtitles: { start: number; end: number; text: string }[]
  full_text: string
  source: string
}

export interface TranslateResponse {
  translations: string[]
  target_lang: string
}
