import { createDownloadButton } from '../inject'

export function injectBilibili() {
  if (!/\/video\//.test(location.pathname)) return
  if (document.getElementById('omni-video-dl-host')) return

  const tryInject = (attempts = 0) => {
    if (document.getElementById('omni-video-dl-host')) return
    if (attempts > 20) { createDownloadButton({ position: 'float' }); return }
    const toolbar = document.querySelector(
      '.video-toolbar-left-main, .video-toolbar-left, .video-toolbar-container, .video-toolbar'
    )
    if (toolbar) createDownloadButton({ position: 'inline', container: toolbar })
    else setTimeout(() => tryInject(attempts + 1), 500)
  }
  tryInject()
}
