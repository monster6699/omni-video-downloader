const API_BASE = 'http://localhost:8000/api'

const VIDEO_PATTERNS = [
  /youtube\.com\/watch/, /youtu\.be\//,
  /bilibili\.com\/video/, /douyin\.com\/video/,
  /tiktok\.com\/@.+\/video/,
  /twitter\.com\/.+\/status/, /x\.com\/.+\/status/,
  /instagram\.com\/(p|reel)\//,
]

function isVideoPage(url: string): boolean {
  return VIDEO_PATTERNS.some((p) => p.test(url))
}

async function getToken(): Promise<string | null> {
  const r = await chrome.storage.local.get('omni_token')
  return r.omni_token || null
}

async function handleDownload(url: string) {
  try {
    const token = await getToken()
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`

    const res = await fetch(`${API_BASE}/video/download`, {
      method: 'POST', headers,
      body: JSON.stringify({ url }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    pollTask(data.task_id, token)
  } catch (err) {
    console.error('[OmniDL] background download error', err)
  }
}

async function pollTask(taskId: string, token: string | null) {
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`

  for (let i = 0; i < 200; i++) {
    try {
      const res = await fetch(`${API_BASE}/video/task/${taskId}`, { headers })
      const d = await res.json()
      if (d.status === 'done' && d.download_url) {
        const full = d.method === 'server' && !d.download_url.startsWith('http')
          ? `http://localhost:8000${d.download_url}` : d.download_url
        chrome.downloads.download({ url: full, filename: d.filename || undefined })
        return
      }
      if (d.status === 'failed') return
    } catch { /* retry */ }
    await new Promise((r) => setTimeout(r, 2000))
  }
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === 'GET_TAB_URL') {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      sendResponse({ url: tabs[0]?.url || '' })
    })
    return true
  }
  if (message.type === 'OPEN_TAB') {
    chrome.tabs.create({ url: message.url })
    sendResponse({ ok: true })
    return true
  }
  if (message.type === 'DOWNLOAD_VIDEO') {
    handleDownload(message.url)
    sendResponse({ ok: true })
    return true
  }
})

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url) {
    chrome.action.setBadgeText({ tabId, text: isVideoPage(tab.url) ? '●' : '' })
    chrome.action.setBadgeBackgroundColor({ tabId, color: '#4f46e5' })
  }
})
