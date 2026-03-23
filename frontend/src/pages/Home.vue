<script setup lang="ts">
import { ref, watch, computed, nextTick } from 'vue'
import { useMessage } from 'naive-ui'
import { Search, Link as LinkIcon, CheckCircle2, Loader2, Sparkles } from 'lucide-vue-next'
import { parseVideo, downloadVideo, getTaskStatus, type VideoInfo, type TaskStatus } from '../api/video'
import VideoResult from '../components/VideoResult.vue'
import AIPanel from '../components/AIPanel.vue'

const message = useMessage()
const url = ref('')
const loading = ref(false)
const downloading = ref(false)
const downloadProgress = ref(0)
const downloadStatusText = ref('')
const videoInfo = ref<VideoInfo | null>(null)
const showAI = ref(false)
const aiPanelMounted = ref(false)
const videoCompactLayout = ref(false)

/** 双栏布局：AI 展开或收起过渡中 */
const aiLayoutSplit = computed(() => showAI.value || videoCompactLayout.value)

async function onAIPanelAfterLeave() {
  await nextTick()
  requestAnimationFrame(() => {
    videoCompactLayout.value = false
  })
}

const quickLinks = [
  { label: 'YouTube', url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' },
  { label: 'Bilibili', url: 'https://www.bilibili.com/video/BV1GJ411x7h7' },
  { label: 'Twitter/X', url: 'https://x.com/elonmusk/status/1234567890' },
]

watch(videoInfo, () => {
  showAI.value = false
  aiPanelMounted.value = false
  videoCompactLayout.value = false
})

watch(showAI, (v) => {
  if (v) videoCompactLayout.value = true
})

function fillUrl(link: string) { url.value = link }

async function handleParse() {
  const trimmed = url.value.trim()
  if (!trimmed) { message.warning('请输入视频链接'); return }
  loading.value = true
  videoInfo.value = null
  try { videoInfo.value = await parseVideo(trimmed) }
  catch (e: any) { message.error(e?.response?.data?.detail || '解析失败，请检查链接') }
  finally { loading.value = false }
}

function toggleAI() {
  if (!showAI.value) aiPanelMounted.value = true
  showAI.value = !showAI.value
}

async function handleDownload(formatId?: string) {
  downloading.value = true
  downloadProgress.value = 0
  downloadStatusText.value = '准备中...'
  try {
    const { task_id } = await downloadVideo(url.value.trim(), formatId)
    await pollTaskUntilDone(task_id)
  } catch (e: any) {
    message.error(e?.response?.data?.detail || e?.message || '下载失败')
  } finally {
    downloading.value = false
    downloadProgress.value = 0
    downloadStatusText.value = ''
  }
}

async function pollTaskUntilDone(taskId: string) {
  const MAX_POLLS = 300
  for (let i = 0; i < MAX_POLLS && downloading.value; i++) {
    const status: TaskStatus = await getTaskStatus(taskId)
    downloadProgress.value = status.progress

    if (status.status === 'downloading') {
      downloadStatusText.value = status.progress > 5
        ? `下载中 ${status.progress}%`
        : '下载中...'
    }

    if (status.status === 'done') {
      triggerFileDownload(status)
      message.success('下载已完成')
      return
    }

    if (status.status === 'failed') {
      throw new Error(status.error || '下载失败')
    }

    await new Promise((resolve) => setTimeout(resolve, 2000))
  }
  throw new Error('下载超时')
}

function triggerFileDownload(status: TaskStatus) {
  const displayName = status.filename || 'video.mp4'
  if (status.method === 'direct') {
    const a = document.createElement('a')
    a.href = status.download_url!
    a.target = '_blank'
    a.rel = 'noopener noreferrer'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  } else {
    const a = document.createElement('a')
    a.href = `${status.download_url}?name=${encodeURIComponent(displayName)}`
    a.download = displayName
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }
}
</script>

<template>
  <div class="pt-16 pb-12 px-4 sm:px-6">
    <!-- Hero -->
    <div class="max-w-3xl mx-auto text-center space-y-6">
      <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-100 text-emerald-700 text-sm font-medium mb-2">
        <CheckCircle2 class="w-4 h-4" />
        支持 6 大平台，永久免费使用
      </div>
      <h1 class="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900">
        万能视频下载器，<span class="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-violet-600">一键保存</span>
      </h1>
      <p class="text-slate-500 text-lg max-w-2xl mx-auto">
        粘贴视频链接，智能解析，支持多种清晰度下载。轻松获取 YouTube、Bilibili、抖音、TikTok... 随时随地，想下就下。
      </p>

      <!-- Input -->
      <div class="mt-8 relative max-w-2xl mx-auto group">
        <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <LinkIcon class="h-5 w-5 text-slate-400" />
        </div>
        <input v-model="url" type="text"
          class="block w-full pl-11 pr-36 py-4 bg-white border border-slate-200 rounded-2xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 shadow-sm transition-all text-lg"
          placeholder="https://www.youtube.com/watch?v=..."
          @keyup.enter="handleParse" />
        <div class="absolute inset-y-1.5 right-1.5">
          <button @click="handleParse" :disabled="loading"
            class="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-70 text-white px-5 py-2.5 rounded-xl font-medium transition-colors shadow-sm h-full">
            <Loader2 v-if="loading" class="w-4 h-4 animate-spin" />
            <Search v-else class="w-4 h-4" />
            {{ loading ? '解析中...' : '解析视频' }}
          </button>
        </div>
      </div>

      <!-- Quick Links -->
      <div class="pt-4 flex items-center justify-center gap-3 text-sm text-slate-500">
        <span>试试:</span>
        <button v-for="link in quickLinks" :key="link.label"
          class="px-3 py-1 bg-white border border-slate-200 rounded-full hover:bg-slate-50 hover:border-slate-300 transition-colors"
          @click="fillUrl(link.url)">{{ link.label }}</button>
      </div>
    </div>

    <!-- Result：不用 max-width transition，避免收起时整行大幅闪动 -->
    <div v-if="videoInfo" class="mx-auto mt-8 w-full"
      :class="aiLayoutSplit ? 'max-w-[1600px] flex flex-col lg:flex-row items-start gap-4 lg:gap-6' : 'max-w-4xl space-y-6'">
      
      <!-- Video Card：左右分布时限制左侧宽度（偏窄），右侧 AI 占剩余 -->
      <div class="bg-white rounded-3xl p-4 sm:p-5 shadow-sm border border-slate-200 min-w-0"
        :class="aiLayoutSplit ? 'w-full shrink-0 lg:min-w-[300px] lg:max-w-[520px] xl:max-w-[560px]' : 'w-full'">
        <VideoResult
          :info="videoInfo"
          :downloading="downloading"
          :compact="videoCompactLayout"
          :status-text="downloadStatusText"
          @download="handleDownload"
        />
        <!-- AI Toggle Button -->
        <div class="flex justify-end mt-4">
          <button type="button" @click="toggleAI"
            :class="showAI
              ? 'bg-purple-100 text-purple-700 hover:bg-purple-200'
              : 'text-purple-600 bg-purple-50 hover:bg-purple-100 border border-purple-100 hover:border-purple-200 shadow-sm'"
            class="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all shrink-0 whitespace-nowrap">
            <Sparkles class="w-4 h-4" />
            {{ showAI ? '收起 AI 分析' : 'AI 视频分析' }}
          </button>
        </div>
      </div>

      <!-- AI Panel：双栏时才参与 flex；单栏时 hidden，避免 flex-1 空列把左侧挤在中间 -->
      <div
        v-if="videoInfo && aiPanelMounted"
        class="min-w-0 lg:overflow-hidden"
        :class="aiLayoutSplit ? 'w-full flex-1' : 'hidden'"
      >
        <Transition name="ai-panel" @after-leave="onAIPanelAfterLeave">
          <div v-show="showAI" class="w-full min-w-0">
            <AIPanel :url="url.trim()" :video-info="videoInfo" />
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ai-panel-enter-active,
.ai-panel-leave-active {
  transition:
    opacity 0.45s cubic-bezier(0.4, 0, 0.2, 1),
    transform 0.45s cubic-bezier(0.4, 0, 0.2, 1);
}
.ai-panel-enter-from,
.ai-panel-leave-to {
  opacity: 0;
  transform: translateX(1rem);
}
</style>
