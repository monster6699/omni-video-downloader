/**
 * Zips extension/dist into frontend/public/downloads/omnivideo-extension.zip
 * (Chrome expects zip root to contain manifest.json.)
 */
import archiver from 'archiver'
import { createWriteStream, existsSync, readdirSync, statSync } from 'fs'
import { mkdir } from 'fs/promises'
import { dirname, join } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const frontendRoot = join(__dirname, '..')
const dist = join(frontendRoot, '..', 'extension', 'dist')
const outDir = join(frontendRoot, 'public', 'downloads')
const outZip = join(outDir, 'omnivideo-extension.zip')

if (!existsSync(join(dist, 'manifest.json'))) {
  console.error('Missing extension/dist/manifest.json. Run: cd extension && npm ci && npm run build')
  process.exit(1)
}

function addDir(archive, dir, prefix = '') {
  for (const name of readdirSync(dir)) {
    const abs = join(dir, name)
    const entryName = prefix ? `${prefix}/${name}` : name
    if (statSync(abs).isDirectory()) {
      addDir(archive, abs, entryName)
    } else {
      archive.file(abs, { name: entryName })
    }
  }
}

await mkdir(outDir, { recursive: true })

const output = createWriteStream(outZip)
const archive = archiver('zip', { zlib: { level: 9 } })

await new Promise((resolve, reject) => {
  output.on('close', resolve)
  output.on('error', reject)
  archive.on('error', reject)
  archive.pipe(output)
  addDir(archive, dist)
  archive.finalize()
})

console.log(`Wrote ${outZip} (${archive.pointer()} bytes)`)
