<script setup lang="ts">
import { computed } from 'vue'
import type { VideoInfo } from '../../shared/types'

const API_HOST = 'http://localhost:8000'
const props = defineProps<{ video: VideoInfo }>()

const thumbnail = computed(() => {
  const raw = props.video.thumbnail
  if (!raw) return ''
  if (raw.startsWith('/api/')) return `${API_HOST}${raw}`
  return raw
})

const duration = computed(() => {
  if (!props.video.duration) return ''
  const h = Math.floor(props.video.duration / 3600)
  const m = Math.floor((props.video.duration % 3600) / 60)
  const s = props.video.duration % 60
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  return `${m}:${s.toString().padStart(2, '0')}`
})

const PLATFORM_LABELS: Record<string, string> = {
  youtube: 'YouTube', bilibili: 'Bilibili', douyin: '抖音',
  tiktok: 'TikTok', twitter: 'Twitter/X', instagram: 'Instagram',
}
</script>

<template>
  <div class="rounded-2xl overflow-hidden bg-white border border-slate-200 shadow-sm">
    <div v-if="thumbnail" class="relative aspect-video bg-slate-100">
      <img
        :src="thumbnail"
        :alt="video.title"
        class="w-full h-full object-cover"
        referrerpolicy="no-referrer"
        loading="lazy"
      />
      <div class="absolute inset-0 bg-black/10 flex items-center justify-center">
        <div class="w-10 h-10 bg-white/30 backdrop-blur-sm rounded-full flex items-center justify-center border border-white/40">
          <span class="text-white text-lg ml-0.5">▶</span>
        </div>
      </div>
      <span v-if="duration" class="absolute bottom-2 right-2 bg-black/70 text-white text-xs px-1.5 py-0.5 rounded font-mono backdrop-blur-sm">
        {{ duration }}
      </span>
    </div>
    <div class="p-3">
      <div class="flex items-center gap-2 mb-1.5">
        <span class="text-xs font-semibold px-2 py-0.5 bg-indigo-50 text-indigo-600 rounded-md">
          {{ PLATFORM_LABELS[video.platform] || video.platform }}
        </span>
      </div>
      <h3 class="text-sm font-bold text-slate-900 line-clamp-2 leading-snug">{{ video.title }}</h3>
    </div>
  </div>
</template>
