<script setup lang="ts">
import { ref, computed } from 'vue'
import { Play, Download, Clock, Loader2 } from 'lucide-vue-next'
import type { VideoInfo } from '../api/video'

const props = withDefaults(
  defineProps<{ info: VideoInfo; downloading?: boolean; compact?: boolean; statusText?: string }>(),
  { compact: false, statusText: '' },
)
const emit = defineEmits<{ download: [formatId?: string] }>()

const selectedFormat = ref<string | undefined>(undefined)

const formatOptions = computed(() =>
  props.info.formats.map((f) => ({
    label: `${f.resolution || f.note || f.format_id} (${f.ext})${f.filesize ? ' · ' + formatSize(f.filesize) : ''}`,
    value: f.format_id,
  }))
)

const platformLabel = computed(() => {
  const map: Record<string, string> = {
    youtube: 'YouTube',
    bilibili: 'Bilibili',
    douyin: '抖音',
    tiktok: 'TikTok',
    twitter: 'Twitter/X',
    instagram: 'Instagram',
  }
  return map[props.info.platform] || props.info.platform
})

function formatDuration(seconds: number | null): string {
  if (!seconds) return '--:--'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  const formattedM = h > 0 ? m.toString().padStart(2, '0') : m.toString()
  const formattedS = s.toString().padStart(2, '0')
  return h > 0 ? `${h}:${formattedM}:${formattedS}` : `${formattedM}:${formattedS}`
}

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function handleDownload() {
  emit('download', selectedFormat.value)
}
</script>

<template>
  <div :class="compact ? 'flex flex-col gap-4' : 'flex flex-col sm:flex-row gap-4'">
    <!-- Thumbnail -->
    <div
      class="relative shrink-0 rounded-2xl overflow-hidden bg-slate-100 group transition-all aspect-video"
      :class="compact ? 'w-full aspect-video' : 'w-full sm:w-56 md:w-64 lg:w-72 sm:aspect-[4/3]'"
    >
      <img
        v-if="info.thumbnail"
        :src="info.thumbnail"
        :alt="info.title"
        class="w-full h-full object-cover"
      />
      <div v-else class="w-full h-full flex items-center justify-center text-slate-400 text-sm">
        无封面
      </div>
      <div class="absolute inset-0 bg-black/20 group-hover:bg-black/30 transition-colors flex items-center justify-center">
        <div class="w-12 h-12 bg-white/30 backdrop-blur-sm rounded-full flex items-center justify-center border border-white/50">
          <Play class="w-6 h-6 text-white fill-white ml-1" />
        </div>
      </div>
      <div v-if="info.duration" class="absolute bottom-2 right-2 px-2 py-1 bg-black/70 text-white text-xs font-medium rounded-md backdrop-blur-sm">
        {{ formatDuration(info.duration) }}
      </div>
    </div>

    <!-- Info -->
    <div class="flex-1 flex flex-col justify-between min-w-0">
      <div>
        <div class="flex items-center gap-2 mb-2">
          <span class="inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 bg-indigo-50 text-indigo-600 rounded-md">
            {{ platformLabel }}
          </span>
          <span class="flex items-center gap-1 text-xs text-slate-500">
            <Clock class="w-3 h-3" />
            未知时长
          </span>
        </div>
        <h2 class="font-bold text-slate-900 leading-snug line-clamp-2 text-lg sm:text-xl">
          {{ info.title }}
        </h2>
        <p class="mt-2 text-sm text-slate-500 line-clamp-2">
          正在准备为您提供最佳下载体验。
        </p>
      </div>

      <div class="mt-6 flex flex-col justify-end">
        <div :class="compact ? 'flex flex-col gap-2 mt-3' : 'flex gap-2 mt-3 flex-col sm:flex-row'">
          <div :class="compact ? 'relative w-full' : 'relative flex-1 min-w-0'">
            <select v-model="selectedFormat" class="w-full appearance-none bg-slate-50 border border-slate-200 text-slate-700 py-2.5 pl-3 pr-8 sm:pl-4 sm:pr-10 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 text-sm font-medium cursor-pointer">
              <option :value="undefined" disabled>选择清晰度</option>
              <option v-for="opt in formatOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
          <button 
            @click="handleDownload"
            :disabled="downloading || formatOptions.length > 0 && !selectedFormat"
            :class="compact ? 'w-full' : 'flex-1 sm:flex-none'"
            class="flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-70 disabled:hover:bg-indigo-600 text-white px-6 py-2.5 rounded-xl text-sm font-semibold transition-colors shadow-sm cursor-pointer shrink-0"
          >
            <Loader2 v-if="downloading" class="w-4 h-4 sm:w-5 sm:h-5 animate-spin" />
            <Download v-else class="w-4 h-4 sm:w-5 sm:h-5" />
            {{ downloading ? (statusText || '准备中...') : '下载视频' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
