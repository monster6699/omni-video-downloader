const API_BASE = 'http://localhost:8000/api'

export function createDownloadButton(opts: {
  position?: 'float' | 'inline'
  container?: Element | null
}): HTMLElement {
  const host = document.createElement('div')
  host.id = 'omni-video-dl-host'
  const shadow = host.attachShadow({ mode: 'closed' })

  const style = document.createElement('style')
  style.textContent = btnStyles(opts.position || 'float')
  shadow.appendChild(style)

  const btn = document.createElement('button')
  btn.className = 'omni-btn'
  btn.innerHTML = btnIcon('idle')
  btn.addEventListener('click', (e) => {
    e.stopPropagation()
    e.preventDefault()
    handleClick(btn, location.href)
  })
  shadow.appendChild(btn)

  if (opts.container) {
    opts.container.appendChild(host)
  } else {
    document.body.appendChild(host)
  }
  return host
}

function btnIcon(state: string): string {
  const icons: Record<string, string> = {
    idle: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M8 2v8M4 7l4 4 4-4M2 14h12"/></svg><span>Download</span>`,
    loading: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="spin"><path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4"/></svg><span>处理中…</span>`,
    done: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 8l4 4 6-7"/></svg><span>已发送</span>`,
  }
  return icons[state] || icons.idle
}

async function handleClick(btn: HTMLButtonElement, url: string) {
  btn.innerHTML = btnIcon('loading')

  if (typeof chrome !== 'undefined' && chrome.runtime?.sendMessage) {
    try {
      chrome.runtime.sendMessage({ type: 'DOWNLOAD_VIDEO', url })
      btn.innerHTML = btnIcon('done')
      setTimeout(() => { btn.innerHTML = btnIcon('idle') }, 3000)
      return
    } catch { /* fall through */ }
  }

  try {
    const res = await fetch(`${API_BASE}/video/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    btn.innerHTML = btnIcon('done')
    pollTaskDirect(data.task_id)
    setTimeout(() => { btn.innerHTML = btnIcon('idle') }, 3000)
  } catch (err) {
    console.error('[OmniDL] download error', err)
    btn.innerHTML = btnIcon('idle')
  }
}

async function pollTaskDirect(taskId: string) {
  for (let i = 0; i < 200; i++) {
    try {
      const res = await fetch(`${API_BASE}/video/task/${taskId}`)
      const d = await res.json()
      if (d.status === 'done' && d.download_url) {
        const full = d.method === 'server' && !d.download_url.startsWith('http')
          ? `http://localhost:8000${d.download_url}` : d.download_url
        const a = document.createElement('a')
        a.href = full; a.download = d.filename || 'video.mp4'
        a.style.display = 'none'; document.body.appendChild(a)
        a.click(); document.body.removeChild(a)
        return
      }
      if (d.status === 'failed') return
    } catch { /* retry */ }
    await new Promise(r => setTimeout(r, 2000))
  }
}

function btnStyles(position: 'float' | 'inline'): string {
  return `
    @keyframes omni-fadein { from { opacity:0; transform:translateY(8px) scale(.95); } to { opacity:1; transform:translateY(0) scale(1); } }
    @keyframes spin { to { transform: rotate(360deg); } }
    .omni-btn {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 7px 14px;
      background: linear-gradient(135deg, #4f46e5, #7c3aed);
      color: #fff; border: none; border-radius: 8px;
      font-size: 13px; font-weight: 600;
      font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
      cursor: pointer; transition: all .2s;
      box-shadow: 0 2px 8px rgba(79,70,229,.3);
      animation: omni-fadein .3s ease;
      ${position === 'float' ? 'position:fixed;bottom:24px;right:24px;z-index:2147483647;' : ''}
    }
    .omni-btn:hover { transform:translateY(-1px); box-shadow:0 4px 14px rgba(79,70,229,.5); }
    .omni-btn:active { transform:translateY(0); }
    .omni-btn .spin { animation: spin 1s linear infinite; }
  `
}
