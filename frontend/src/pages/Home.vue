<script setup lang="ts">
import { ref } from 'vue'
import { useMessage } from 'naive-ui'
import { parseVideo, downloadVideo, type VideoInfo, type DownloadResult } from '../api/video'
import VideoResult from '../components/VideoResult.vue'

const message = useMessage()
const url = ref('')
const loading = ref(false)
const downloading = ref(false)
const videoInfo = ref<VideoInfo | null>(null)

const quickLinks = [
  { label: 'YouTube', url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' },
  { label: 'Bilibili', url: 'https://www.bilibili.com/video/BV1GJ411x7h7' },
  { label: 'Twitter/X', url: 'https://x.com/elonmusk/status/1234567890' },
]

function fillUrl(link: string) {
  url.value = link
}

async function handleParse() {
  const trimmed = url.value.trim()
  if (!trimmed) {
    message.warning('请输入视频链接')
    return
  }
  loading.value = true
  videoInfo.value = null
  try {
    videoInfo.value = await parseVideo(trimmed)
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '解析失败，请检查链接')
  } finally {
    loading.value = false
  }
}

async function handleDownload(formatId?: string) {
  downloading.value = true
  try {
    const result: DownloadResult = await downloadVideo(url.value.trim(), formatId)
    const displayName = result.filename || 'video.mp4'
    const downloadUrl = `${result.download_url}?name=${encodeURIComponent(displayName)}`
    const a = document.createElement('a')
    a.href = downloadUrl
    a.download = displayName
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    message.success('下载已开始')
  } catch (e: any) {
    console.log(e)
    message.error(e?.response?.data?.detail || '下载失败')
  } finally {
    downloading.value = false
  }
}
</script>

<template>
  <div>
    <!-- Hero -->
    <section class="pt-20 pb-10 px-4 text-center">
      <!-- Badge -->
      <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-green-50 border border-green-200 text-sm text-green-700 mb-8">
        <span class="w-2 h-2 rounded-full bg-green-500 inline-block"></span>
        支持 6 大平台，永久免费使用
      </div>

      <!-- Title -->
      <h1 class="text-4xl md:text-5xl font-extrabold leading-tight tracking-tight mb-5">
        万能视频下载器<span class="text-gradient">，一键保存</span>
      </h1>

      <!-- Subtitle -->
      <p class="text-base md:text-lg text-[var(--color-text-secondary)] max-w-2xl mx-auto leading-relaxed mb-12">
        粘贴视频链接，智能解析，支持多种清晰度下载。YouTube、Bilibili、抖音、TikTok…<br class="hidden md:block">
        随时随地，想下就下
      </p>

      <!-- Search Bar -->
      <div class="max-w-2xl mx-auto">
        <div
          class="flex items-center bg-white rounded-2xl shadow-lg shadow-black/5 border border-[var(--color-border)] transition-shadow focus-within:shadow-xl focus-within:shadow-blue-500/10 focus-within:border-blue-300"
        >
          <!-- Link Icon -->
          <div class="pl-5 pr-2 text-[var(--color-text-secondary)]">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
            </svg>
          </div>

          <!-- Input -->
          <input
            v-model="url"
            type="text"
            placeholder="粘贴视频链接，如 https://www.youtube.com/watch?v=..."
            class="flex-1 h-14 bg-transparent outline-none text-base text-[var(--color-text)] placeholder:text-[var(--color-text-secondary)]/50"
            @keyup.enter="handleParse"
          />

          <!-- Parse Button -->
          <button
            class="h-11 px-6 mr-1.5 rounded-xl font-semibold text-white text-sm flex items-center gap-2 shrink-0 cursor-pointer transition-all duration-200"
            :class="loading ? 'bg-[var(--color-primary)]/70' : 'bg-[var(--color-primary)] hover:bg-[var(--color-primary-dark)] active:scale-95'"
            :disabled="loading"
            @click="handleParse"
          >
            <svg v-if="!loading" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
            </svg>
            <svg v-else class="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83"/></svg>
            {{ loading ? '解析中…' : '解析视频' }}
          </button>
        </div>

        <!-- Quick Links -->
        <div class="flex items-center justify-center gap-3 mt-5 text-sm">
          <span class="text-[var(--color-text-secondary)]">试试：</span>
          <button
            v-for="link in quickLinks"
            :key="link.label"
            class="px-3 py-1 rounded-full border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-primary)] hover:text-[var(--color-primary)] hover:bg-blue-50 transition-all cursor-pointer bg-white"
            @click="fillUrl(link.url)"
          >
            {{ link.label }}
          </button>
        </div>
      </div>
    </section>

    <!-- Result -->
    <section v-if="videoInfo" class="max-w-2xl mx-auto px-4 pb-16">
      <VideoResult :info="videoInfo" :downloading="downloading" @download="handleDownload" />
    </section>
  </div>
</template>
