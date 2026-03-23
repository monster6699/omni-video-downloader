<script setup lang="ts">
import { ref, computed, inject } from 'vue'
import { useMessage, NInput, NSkeleton } from 'naive-ui'
import { Languages, Loader2 } from 'lucide-vue-next'
import type { SubtitleItem } from '../../api/ai'
import { translateSubtitles, QuotaExhaustedError } from '../../api/ai'

const props = defineProps<{
  url: string
  subtitles: SubtitleItem[]
  fullText: string
  source: string
  loading: boolean
  error: string
}>()

const message = useMessage()
const refreshAiQuota = inject<(() => void) | undefined>('refreshAiQuota', undefined)
const searchQuery = ref('')
const targetLang = ref('zh')
const translating = ref(false)
const translations = ref<string[]>([])
const translateError = ref('')

const langOptions = [
  { label: '中文', value: 'zh' },
  { label: 'English', value: 'en' },
  { label: '日本語', value: 'ja' },
  { label: '한국어', value: 'ko' },
  { label: 'Français', value: 'fr' },
  { label: 'Español', value: 'es' },
  { label: 'Deutsch', value: 'de' },
]

const indexedSubtitles = computed(() =>
  props.subtitles.map((s, i) => ({ ...s, _idx: i }))
)

const filteredSubtitles = computed(() => {
  if (!searchQuery.value.trim()) return indexedSubtitles.value
  const q = searchQuery.value.toLowerCase()
  return indexedSubtitles.value.filter((s) => {
    if (s.text.toLowerCase().includes(q)) return true
    const t = translations.value[s._idx]
    return t ? t.toLowerCase().includes(q) : false
  })
})

const sourceLabel = computed(() => {
  if (props.source === 'cc') return '字幕'
  return ''
})

const hasTranslations = computed(() => translations.value.length > 0)

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

function copyAll() {
  if (!props.fullText) return
  let text = props.fullText
  if (hasTranslations.value) {
    text = props.subtitles
      .map((s, i) => `${s.text}\n${translations.value[i] || ''}`)
      .join('\n')
  }
  navigator.clipboard.writeText(text).then(() => {
    message.success('已复制全部文本')
  })
}

function copyLine(text: string, idx: number) {
  const t = translations.value[idx]
  const content = t ? `${text}\n${t}` : text
  navigator.clipboard.writeText(content).then(() => {
    message.success('已复制')
  })
}

async function handleTranslate() {
  if (props.subtitles.length === 0) return
  translating.value = true
  translateError.value = ''
  try {
    const texts = props.subtitles.map((s) => s.text)
    const result = await translateSubtitles(props.url, texts, targetLang.value)
    translations.value = result.translations
    message.success('翻译完成')
    refreshAiQuota?.()
  } catch (e: any) {
    if (e instanceof QuotaExhaustedError) {
      translateError.value = e.message
    } else {
      translateError.value = e?.response?.data?.detail || e?.message || '翻译失败'
    }
    message.error(translateError.value)
  } finally {
    translating.value = false
  }
}
</script>

<template>
  <div class="py-4">
    <!-- Loading -->
    <div v-if="loading" class="space-y-3 py-4">
      <div class="flex items-center gap-2 text-sm text-purple-600 mb-2">
        <svg class="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83"/>
        </svg>
        正在提取字幕...
      </div>
      <NSkeleton text :repeat="6" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="text-center py-6">
      <p class="text-sm text-red-500">{{ error }}</p>
    </div>

    <!-- Empty -->
    <div v-else-if="subtitles.length === 0" class="text-center py-8">
      <div class="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-3">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M17 11h1a3 3 0 0 1 0 6h-1"/><path d="M9 12v6"/><path d="M13 12v6"/>
          <path d="M14 7.5c-1 0-1.44.5-3 .5s-2-.5-3-.5-1.72.5-2.5.5a2.5 2.5 0 0 1 0-5c.78 0 1.57.5 2.5.5S9.44 2 11 2s2 1 3 1 1.72-.5 2.5-.5a2.5 2.5 0 0 1 0 5c-.78 0-1.5-.5-2.5-.5Z"/>
        </svg>
      </div>
      <p class="text-sm text-[var(--color-text-secondary)]">当前视频无字幕或无法获取字幕</p>
    </div>

    <!-- Subtitle/Danmaku List -->
    <div v-else>
      <!-- Toolbar -->
      <div class="flex items-center gap-2 mb-4 flex-wrap">
        <NInput
          v-model:value="searchQuery"
          placeholder="搜索内容..."
          size="small"
          clearable
          class="flex-1 min-w-[140px]"
        >
          <template #prefix>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
          </template>
        </NInput>
        <select
          v-model="targetLang"
          class="h-[30px] px-2 rounded-lg text-xs font-medium bg-gray-50 border border-gray-200 text-slate-700 cursor-pointer focus:outline-none focus:ring-1 focus:ring-indigo-400"
        >
          <option v-for="opt in langOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <button
          :disabled="translating || subtitles.length === 0"
          class="shrink-0 h-[30px] px-3 rounded-lg text-xs font-medium bg-indigo-50 text-indigo-600 hover:bg-indigo-100 disabled:opacity-50 transition-colors cursor-pointer inline-flex items-center gap-1.5"
          @click="handleTranslate"
        >
          <Loader2 v-if="translating" class="w-3 h-3 animate-spin" />
          <Languages v-else class="w-3 h-3" />
          {{ translating ? '翻译中...' : '翻译' }}
        </button>
        <button
          class="shrink-0 h-[30px] px-3 rounded-lg text-xs font-medium bg-gray-100 hover:bg-gray-200 text-[var(--color-text)] transition-colors cursor-pointer"
          @click="copyAll"
        >
          复制全部
        </button>
      </div>

      <div class="text-xs text-[var(--color-text-secondary)] mb-2">
        共 {{ subtitles.length }} 条{{ sourceLabel }}
        <span v-if="searchQuery">, 匹配 {{ filteredSubtitles.length }} 条</span>
        <span v-if="hasTranslations" class="text-indigo-500 ml-1">· 已翻译</span>
      </div>

      <!-- List -->
      <div class="max-h-[400px] overflow-y-auto space-y-1 pr-1">
        <div
          v-for="item in filteredSubtitles"
          :key="item._idx"
          class="flex items-start gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 group transition-colors cursor-pointer"
          @click="copyLine(item.text, item._idx)"
        >
          <span class="shrink-0 text-xs font-mono text-purple-500 pt-0.5 min-w-[52px]">
            {{ formatTime(item.start) }}
          </span>
          <div class="flex-1 min-w-0">
            <span class="text-sm text-[var(--color-text)] leading-relaxed block">{{ item.text }}</span>
            <span
              v-if="translations[item._idx]"
              class="text-xs text-indigo-600/80 leading-relaxed block mt-0.5"
            >{{ translations[item._idx] }}</span>
          </div>
          <svg class="shrink-0 mt-0.5 opacity-0 group-hover:opacity-50 transition-opacity" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>
          </svg>
        </div>
      </div>
    </div>
  </div>
</template>
