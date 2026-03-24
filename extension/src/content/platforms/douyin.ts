import { createDownloadButton } from '../inject'

export function injectDouyin() {
  if (document.getElementById('omni-video-dl-host')) return
  createDownloadButton({ position: 'float' })
}
