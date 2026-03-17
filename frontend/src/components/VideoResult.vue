<script setup lang="ts">
import { ref, computed } from 'vue'
import { NSelect, NTag } from 'naive-ui'
import type { VideoInfo } from '../api/video'

const props = defineProps<{ info: VideoInfo; downloading?: boolean }>()
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
  if (!seconds) return '--'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
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
  <div class="bg-white rounded-2xl border border-[var(--color-border)] shadow-lg shadow-black/5 overflow-hidden">
    <div class="flex flex-col md:flex-row">
      <!-- Thumbnail -->
      <div class="w-full md:w-80 shrink-0 bg-gray-100">
        <img
          v-if="info.thumbnail"
          :src="info.thumbnail"
          :alt="info.title"
          class="w-full h-48 md:h-full object-cover"
        />
        <div v-else class="w-full h-48 flex items-center justify-center text-[var(--color-text-secondary)] text-sm">
          无封面
        </div>
      </div>

      <!-- Info -->
      <div class="flex-1 p-6 flex flex-col gap-4">
        <h2 class="text-base font-semibold leading-snug text-[var(--color-text)] line-clamp-2">
          {{ info.title }}
        </h2>

        <div class="flex items-center gap-2">
          <NTag :bordered="false" type="info" size="small" round>{{ platformLabel }}</NTag>
          <NTag :bordered="false" size="small" round>{{ formatDuration(info.duration) }}</NTag>
        </div>

        <div v-if="formatOptions.length">
          <NSelect
            v-model:value="selectedFormat"
            :options="formatOptions"
            placeholder="选择清晰度"
            size="medium"
          />
        </div>

        <button
          class="h-11 rounded-xl font-semibold text-white text-sm flex items-center justify-center gap-2 transition-all duration-200"
          :class="downloading ? 'bg-[var(--color-primary)]/70 cursor-wait' : 'bg-[var(--color-primary)] hover:bg-[var(--color-primary-dark)] active:scale-[0.98] cursor-pointer'"
          :disabled="downloading"
          @click="handleDownload"
        >
          <svg v-if="!downloading" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          <svg v-else class="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83"/>
          </svg>
          {{ downloading ? '服务器下载中，请稍候…' : '下载视频' }}
        </button>
      </div>
    </div>
  </div>
</template>
