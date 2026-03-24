<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import type { VideoInfo, TaskStatus } from '../../shared/types'
import { startDownload, getTaskStatus } from '../../shared/api'

const props = defineProps<{ video: VideoInfo; url: string }>()

const selectedFormat = ref(props.video.formats[0]?.format_id || '')
const task = ref<TaskStatus | null>(null)
const downloading = ref(false)
const error = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

const formats = computed(() => props.video.formats.filter((f) => f.has_video))

const statusText = computed(() => {
  if (!task.value) return ''
  const t = task.value
  if (t.status === 'pending') return '准备中…'
  if (t.status === 'downloading') return `下载中 ${t.progress}%`
  if (t.status === 'done') return '完成!'
  if (t.status === 'failed') return t.error || '下载失败'
  return t.status
})

async function handleDownload() {
  if (downloading.value) return
  downloading.value = true; error.value = ''; task.value = null
  try {
    const res = await startDownload(props.url, selectedFormat.value || undefined)
    startPolling(res.task_id)
  } catch (e: unknown) { error.value = (e as Error).message || '下载失败'; downloading.value = false }
}

function startPolling(taskId: string) {
  pollTimer = setInterval(async () => {
    try {
      task.value = await getTaskStatus(taskId)
      if (task.value.status === 'done') {
        stopPolling(); downloading.value = false
        if (task.value.download_url) triggerDownload(task.value)
      } else if (task.value.status === 'failed') {
        stopPolling(); downloading.value = false
        error.value = task.value.error || '下载失败'
      }
    } catch { stopPolling(); downloading.value = false; error.value = '服务器连接中断' }
  }, 1500)
}

function triggerDownload(t: TaskStatus) {
  const url = t.download_url!
  const full = t.method === 'server' && !url.startsWith('http') ? `http://localhost:8000${url}` : url
  try {
    chrome.downloads.download({ url: full, filename: t.filename || undefined })
  } catch {
    chrome.tabs.create({ url: full })
  }
}

function stopPolling() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null } }

function fmtSize(bytes: number | null): string {
  if (!bytes) return ''
  return bytes < 1048576 ? `${(bytes / 1024).toFixed(0)} KB` : `${(bytes / 1048576).toFixed(1)} MB`
}

onUnmounted(stopPolling)
</script>

<template>
  <div class="mt-3 space-y-2.5">
    <select v-if="formats.length > 1" v-model="selectedFormat"
      class="w-full appearance-none bg-slate-50 border border-slate-200 text-slate-700 text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 cursor-pointer">
      <option v-for="f in formats" :key="f.format_id" :value="f.format_id">
        {{ f.resolution || f.format_id }} · {{ f.ext }} {{ fmtSize(f.filesize) }} {{ f.note ? `(${f.note})` : '' }}
      </option>
    </select>
    <button
      class="w-full py-2.5 rounded-xl font-semibold text-sm transition flex items-center justify-center gap-2 shadow-sm"
      :class="downloading ? 'bg-indigo-400 text-white cursor-wait' : 'bg-indigo-600 hover:bg-indigo-700 text-white cursor-pointer'"
      :disabled="downloading" @click="handleDownload">
      <template v-if="!downloading"><span>⬇</span> <span>下载视频</span></template>
      <template v-else>
        <div class="w-4 h-4 border-2 border-white/50 border-t-white rounded-full animate-spin" />
        <span>{{ statusText }}</span>
      </template>
    </button>
    <div v-if="downloading && (task?.progress ?? 0) > 0" class="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
      <div class="h-full bg-indigo-600 rounded-full transition-all duration-300" :style="{ width: `${task!.progress}%` }" />
    </div>
    <p v-if="task?.status === 'done'" class="text-center text-emerald-600 text-sm font-medium">✓ 下载已开始</p>
    <p v-if="error" class="text-center text-red-500 text-xs">{{ error }}</p>
  </div>
</template>
