import { injectYouTube } from './platforms/youtube'
import { injectBilibili } from './platforms/bilibili'
import { injectDouyin } from './platforms/douyin'
import { injectTikTok } from './platforms/tiktok'

type Platform = 'youtube' | 'bilibili' | 'douyin' | 'tiktok'

const INJECTORS: Record<Platform, () => void> = {
  youtube: injectYouTube,
  bilibili: injectBilibili,
  douyin: injectDouyin,
  tiktok: injectTikTok,
}

function detectPlatform(): Platform | null {
  const h = location.hostname
  if (h.includes('youtube.com')) return 'youtube'
  if (h.includes('bilibili.com')) return 'bilibili'
  if (h.includes('douyin.com')) return 'douyin'
  if (h.includes('tiktok.com')) return 'tiktok'
  return null
}

let currentPlatform: Platform | null = null

function inject() {
  currentPlatform = detectPlatform()
  if (!currentPlatform) return
  document.getElementById('omni-video-dl-host')?.remove()
  INJECTORS[currentPlatform]()
}

function isVideoPath(): boolean {
  const p = location.pathname
  if (!currentPlatform) return false
  if (currentPlatform === 'youtube') return /\/watch/.test(p)
  if (currentPlatform === 'bilibili') return /\/video\//.test(p)
  if (currentPlatform === 'douyin') return /\/video\//.test(p)
  if (currentPlatform === 'tiktok') return /\/@.+\/video\//.test(p)
  return false
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', inject)
} else {
  inject()
}

let lastUrl = location.href
new MutationObserver(() => {
  if (location.href !== lastUrl) {
    lastUrl = location.href
    document.getElementById('omni-video-dl-host')?.remove()
    setTimeout(inject, 1000)
  }
}).observe(document.body, { childList: true, subtree: true })

setInterval(() => {
  if (!isVideoPath()) return
  if (!document.getElementById('omni-video-dl-host')) {
    INJECTORS[currentPlatform!]()
  }
}, 3000)
