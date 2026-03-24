import { createDownloadButton } from '../inject'

export function injectYouTube() {
  if (!/\/watch/.test(location.pathname)) return
  if (document.getElementById('omni-video-dl-host')) return

  const tryInject = (attempts = 0) => {
    if (document.getElementById('omni-video-dl-host')) return
    if (attempts > 20) { createDownloadButton({ position: 'float' }); return }
    const actions = document.querySelector('#top-row #actions, ytd-watch-metadata #actions')
    if (actions) createDownloadButton({ position: 'inline', container: actions })
    else setTimeout(() => tryInject(attempts + 1), 500)
  }
  tryInject()
}
