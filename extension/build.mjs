import { build as viteBuild } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import * as esbuild from 'esbuild'
import { rmSync, mkdirSync, cpSync, writeFileSync, existsSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import { deflateSync } from 'zlib'

const __dirname = dirname(fileURLToPath(import.meta.url))
const DIST = resolve(__dirname, 'dist')

function crc32(buf) {
  let crc = 0xffffffff
  for (const byte of buf) {
    crc ^= byte
    for (let i = 0; i < 8; i++) crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0)
  }
  return (crc ^ 0xffffffff) >>> 0
}

function pngChunk(type, data) {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length)
  const t = Buffer.from(type)
  const c = Buffer.alloc(4); c.writeUInt32BE(crc32(Buffer.concat([t, data])))
  return Buffer.concat([len, t, data, c])
}

function generateIcon(size) {
  const raw = Buffer.alloc(size * (1 + size * 4))
  const r = Math.max(1, Math.floor(size * 0.18))
  for (let y = 0; y < size; y++) {
    const row = y * (1 + size * 4); raw[row] = 0
    for (let x = 0; x < size; x++) {
      const px = row + 1 + x * 4; const t = y / size
      raw[px] = Math.round(79 * (1 - t) + 99 * t)
      raw[px + 1] = Math.round(70 * (1 - t) + 102 * t)
      raw[px + 2] = Math.round(229 * (1 - t) + 241 * t)
      const dx = Math.min(x, size - 1 - x); const dy = Math.min(y, size - 1 - y)
      raw[px + 3] = (dx < r && dy < r && Math.hypot(r - dx, r - dy) > r) ? 0 : 255
    }
  }
  const ihdr = Buffer.alloc(13)
  ihdr.writeUInt32BE(size, 0); ihdr.writeUInt32BE(size, 4); ihdr[8] = 8; ihdr[9] = 6
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    pngChunk('IHDR', ihdr), pngChunk('IDAT', deflateSync(raw)), pngChunk('IEND', Buffer.alloc(0)),
  ])
}

async function buildExtension() {
  console.log('Building extension...\n')
  if (existsSync(DIST)) rmSync(DIST, { recursive: true })

  const iconsDir = resolve(DIST, 'icons')
  mkdirSync(iconsDir, { recursive: true })
  for (const size of [16, 48, 128]) {
    writeFileSync(resolve(iconsDir, `icon-${size}.png`), generateIcon(size))
  }
  console.log('[icons] generated 16/48/128')

  await viteBuild({
    root: resolve(__dirname, 'src/popup'),
    plugins: [vue(), tailwindcss()],
    base: './',
    build: { outDir: resolve(DIST, 'popup'), emptyOutDir: true, minify: true },
    logLevel: 'warn',
  })
  console.log('[popup] built')

  await esbuild.build({
    entryPoints: [resolve(__dirname, 'src/content/index.ts')],
    bundle: true, outfile: resolve(DIST, 'content/index.js'),
    format: 'iife', target: 'chrome120', minify: true,
  })
  console.log('[content] built')

  await esbuild.build({
    entryPoints: [resolve(__dirname, 'src/background/index.ts')],
    bundle: true, outfile: resolve(DIST, 'background/index.js'),
    format: 'iife', target: 'chrome120', minify: true,
  })
  console.log('[background] built')

  cpSync(resolve(__dirname, 'manifest.json'), resolve(DIST, 'manifest.json'))
  console.log('\nDone! Load dist/ as unpacked extension in chrome://extensions/')
}

buildExtension().catch((err) => { console.error(err); process.exit(1) })
