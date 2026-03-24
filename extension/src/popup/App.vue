<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { parseVideo, ApiError } from '../shared/api'
import { isLikelyVideoPageUrl } from '../shared/videoUrlPatterns'
import { getUser } from '../shared/storage'
import type { VideoInfo, UserProfile } from '../shared/types'
import VideoInfoCard from './components/VideoInfo.vue'
import DownloadPanel from './components/DownloadPanel.vue'
import LoginPanel from './components/LoginPanel.vue'
import AIPanel from './components/AIPanel.vue'

const currentUrl = ref('')
const videoInfo = ref<VideoInfo | null>(null)
const loading = ref(false)
const error = ref('')
const user = ref<UserProfile | null>(null)
const showAI = ref(false)

const isVideoUrl = computed(() => isLikelyVideoPageUrl(currentUrl.value))

async function doParse() {
  if (!currentUrl.value || !isVideoUrl.value) return
  loading.value = true; error.value = ''; videoInfo.value = null
  try { videoInfo.value = await parseVideo(currentUrl.value) }
  catch (e) {
    error.value = e instanceof ApiError ? e.message : '无法连接到服务器，请确认后端已启动'
  } finally { loading.value = false }
}

onMounted(async () => {
  try { const u = await getUser(); if (u) user.value = u as UserProfile } catch {}
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
    currentUrl.value = tab?.url || ''
  } catch { currentUrl.value = '' }
  if (isVideoUrl.value) await doParse()
})
</script>

<template>
  <div class="min-h-50 flex flex-col">
    <header class="bg-white border-b border-slate-200 px-4 py-2.5 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-2">
        <div class="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center">
          <span class="text-white text-xs font-bold">▶</span>
        </div>
        <span class="font-bold text-sm tracking-tight text-slate-900">OmniVideo</span>
        <span class="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-indigo-50 text-indigo-600 border border-indigo-100">万能视频下载</span>
      </div>
      <LoginPanel :user="user" @login="u => user = u" @logout="user = null" />
    </header>

    <main class="flex-1 p-4">
      <div v-if="loading" class="space-y-3">
        <div class="rounded-2xl overflow-hidden bg-white border border-slate-200">
          <div class="skeleton aspect-video" />
          <div class="p-3 space-y-2"><div class="skeleton h-3 w-16" /><div class="skeleton h-4 w-full" /><div class="skeleton h-4 w-3/4" /></div>
        </div>
        <div class="skeleton h-10 w-full rounded-xl" />
      </div>

      <div v-else-if="error" class="text-center py-6">
        <div class="text-2xl mb-2">⚠️</div>
        <p class="text-red-500 text-sm mb-3">{{ error }}</p>
        <button class="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm rounded-xl transition" @click="doParse">重试</button>
      </div>

      <div v-else-if="!isVideoUrl" class="text-center py-8">
        <div class="text-3xl mb-3">🎬</div>
        <p class="text-sm text-slate-500 leading-relaxed">请打开一个视频页面，然后点击此插件。</p>
        <p class="text-xs text-slate-400 mt-2">支持 YouTube · Bilibili · 抖音 · TikTok · Twitter · Instagram</p>
      </div>

      <transition name="slide">
        <div v-if="videoInfo && !loading && !error">
          <VideoInfoCard :video="videoInfo" />
          <DownloadPanel :video="videoInfo" :url="currentUrl" />
          <button
            class="w-full mt-3 py-2 text-sm font-medium rounded-xl transition flex items-center justify-center gap-1.5"
            :class="showAI ? 'bg-indigo-100 text-indigo-700 hover:bg-indigo-200' : 'text-indigo-600 bg-indigo-50 hover:bg-indigo-100 border border-indigo-100'"
            @click="showAI = !showAI"
          >
            <span>✨</span>
            <span>{{ showAI ? '收起 AI 分析' : 'AI 视频分析' }}</span>
          </button>
          <transition name="fade">
            <AIPanel v-if="showAI" :url="currentUrl" />
          </transition>
          <a :href="`http://localhost:5173/?url=${encodeURIComponent(currentUrl)}`" target="_blank"
            class="block mt-3 text-center text-xs text-slate-400 hover:text-indigo-500 transition">在网站上打开完整版 →</a>
        </div>
      </transition>
    </main>
  </div>
</template>
