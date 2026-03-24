import { createDownloadButton } from '../inject'

export function injectTikTok() {
  if (document.getElementById('omni-video-dl-host')) return
  createDownloadButton({ position: 'float' })
}
