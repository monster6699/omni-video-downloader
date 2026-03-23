<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Download, Clock, ExternalLink, Loader2, Inbox, ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { listDownloads, type DownloadHistoryItem } from '../api/auth'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const { isLoggedIn, waitForSession } = useAuth()

const items = ref<DownloadHistoryItem[]>([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)

const platformLabels: Record<string, string> = {
  youtube: 'YouTube',
  bilibili: 'Bilibili',
  douyin: '抖音',
  tiktok: 'TikTok',
  twitter: 'Twitter/X',
  instagram: 'Instagram',
}

function formatTime(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'short', day: 'numeric' })
}

const totalPages = () => Math.max(1, Math.ceil(total.value / 20))

async function loadPage(p: number) {
  loading.value = true
  try {
    const data = await listDownloads(p, 20)
    items.value = data.items
    total.value = data.total
    page.value = p
  } catch {
    /* silent */
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await waitForSession()
  if (!isLoggedIn.value) {
    router.replace('/')
    return
  }
  loadPage(1)
})
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 sm:px-6 py-10">
    <!-- Header -->
    <div class="flex items-center gap-4 mb-8">
      <div class="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center">
        <Download class="w-5 h-5 text-indigo-600" />
      </div>
      <div>
        <h1 class="text-2xl font-bold text-slate-900">下载记录</h1>
        <p class="text-sm text-slate-500 mt-0.5">
          <template v-if="total > 0">共 {{ total }} 条记录</template>
          <template v-else>登录后的下载会自动记录在这里</template>
        </p>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading && items.length === 0" class="flex items-center justify-center py-32">
      <Loader2 class="w-8 h-8 text-indigo-500 animate-spin" />
    </div>

    <!-- Empty -->
    <div v-else-if="!loading && items.length === 0" class="flex flex-col items-center justify-center py-32 text-slate-400">
      <Inbox class="w-16 h-16 mb-4 text-slate-300" />
      <p class="text-lg font-medium text-slate-500">暂无下载记录</p>
      <p class="text-sm mt-1">去首页下载视频后，记录会自动出现在这里</p>
      <button @click="router.push('/')" class="mt-6 px-6 py-2.5 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition-colors">
        去下载视频
      </button>
    </div>

    <!-- List -->
    <div v-else class="space-y-3">
      <div
        v-for="item in items"
        :key="item.id"
        class="bg-white rounded-2xl border border-slate-200 p-4 flex items-center gap-4 hover:shadow-sm transition-shadow"
      >
        <!-- Thumbnail -->
        <div class="w-28 h-20 rounded-xl bg-slate-100 overflow-hidden shrink-0">
          <img
            v-if="item.thumbnail"
            :src="item.thumbnail.startsWith('http') ? `/api/video/proxy/image?url=${encodeURIComponent(item.thumbnail)}` : item.thumbnail"
            class="w-full h-full object-cover"
            loading="lazy"
          />
          <div v-else class="w-full h-full flex items-center justify-center">
            <Download class="w-6 h-6 text-slate-300" />
          </div>
        </div>

        <!-- Info -->
        <div class="flex-1 min-w-0">
          <p class="font-medium text-slate-800 truncate text-base">
            {{ item.title || item.url }}
          </p>
          <div class="flex items-center gap-3 mt-2 text-xs text-slate-400 flex-wrap">
            <span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 font-medium">
              {{ platformLabels[item.platform] || item.platform }}
            </span>
            <span v-if="item.resolution" class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-500">
              {{ item.resolution }}
            </span>
            <span v-if="item.method === 'direct'" class="px-2 py-0.5 rounded-md bg-blue-50 text-blue-600">
              直链
            </span>
            <span class="flex items-center gap-1">
              <Clock class="w-3 h-3" />
              {{ formatTime(item.created_at) }}
            </span>
          </div>
        </div>

        <!-- Action -->
        <a
          :href="item.url"
          target="_blank"
          rel="noopener noreferrer"
          class="p-2.5 rounded-xl hover:bg-slate-100 transition-colors shrink-0"
          title="打开原视频"
        >
          <ExternalLink class="w-4 h-4 text-slate-400" />
        </a>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="total > 20" class="flex items-center justify-center gap-4 mt-8">
      <button
        :disabled="page <= 1"
        @click="loadPage(page - 1)"
        class="flex items-center gap-1 px-4 py-2 text-sm rounded-xl border border-slate-200 hover:bg-slate-50 disabled:opacity-40 transition-colors"
      >
        <ChevronLeft class="w-4 h-4" />
        上一页
      </button>
      <span class="text-sm text-slate-500 tabular-nums">{{ page }} / {{ totalPages() }}</span>
      <button
        :disabled="page >= totalPages()"
        @click="loadPage(page + 1)"
        class="flex items-center gap-1 px-4 py-2 text-sm rounded-xl border border-slate-200 hover:bg-slate-50 disabled:opacity-40 transition-colors"
      >
        下一页
        <ChevronRight class="w-4 h-4" />
      </button>
    </div>
  </div>
</template>
