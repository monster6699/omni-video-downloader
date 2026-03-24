<script setup lang="ts">
import { ref, onMounted, provide } from 'vue'
import { NTabs, NTabPane } from 'naive-ui'
import { Sparkles, FileText, MessageSquare, Network, Gauge } from 'lucide-vue-next'
import type { VideoInfo } from '../api/video'
import {
  fetchSubtitles,
  fetchSummary,
  fetchMindMap,
  fetchAiQuotaStatus,
  QuotaExhaustedError,
  extractApiErrorMessage,
  type SubtitleResponse,
  type SummaryResponse,
  type MindMapResponse,
  type AIQuotaStatus,
} from '../api/ai'
import SummaryView from './ai/SummaryView.vue'
import SubtitleView from './ai/SubtitleView.vue'
import MindMapView from './ai/MindMapView.vue'
import QAView from './ai/QAView.vue'

const props = defineProps<{
  url: string
  videoInfo: VideoInfo
}>()

const activeTab = ref('summary')

const subtitleData = ref<SubtitleResponse | null>(null)
const subtitleLoading = ref(false)
const subtitleError = ref('')

const summaryData = ref<SummaryResponse | null>(null)
const summaryLoading = ref(false)
const summaryError = ref('')

const mindmapData = ref<MindMapResponse | null>(null)
const mindmapLoading = ref(false)
const mindmapError = ref('')

const quotaExhausted = ref(false)
const quotaMessage = ref('')

const quotaStatus = ref<AIQuotaStatus | null>(null)
const quotaStatusLoading = ref(false)

async function loadQuotaStatus() {
  quotaStatusLoading.value = true
  try {
    quotaStatus.value = await fetchAiQuotaStatus()
  } catch {
    quotaStatus.value = null
  } finally {
    quotaStatusLoading.value = false
  }
}

provide('refreshAiQuota', loadQuotaStatus)

function handleQuotaError(e: unknown): string {
  if (e instanceof QuotaExhaustedError) {
    quotaExhausted.value = true
    quotaMessage.value = e.message
    return e.message
  }
  return extractApiErrorMessage(e) || '生成失败'
}

async function runAnalysis() {
  subtitleData.value = null
  summaryData.value = null
  mindmapData.value = null
  subtitleError.value = ''
  summaryError.value = ''
  mindmapError.value = ''
  subtitleLoading.value = true
  summaryLoading.value = true
  mindmapLoading.value = true

  try {
    const subResult = await fetchSubtitles(props.url)
    subtitleData.value = subResult
    subtitleLoading.value = false

    const contextText = subResult.full_text
    const contextSource = subResult.source
    const hasText = contextText.trim().length > 0

    const summaryPromise = fetchSummary(props.url, hasText ? contextText : undefined, hasText ? contextSource : undefined)
      .then((r) => { summaryData.value = r })
      .catch((e) => { summaryError.value = handleQuotaError(e) })
      .finally(() => { summaryLoading.value = false })

    const mindmapPromise = fetchMindMap(props.url, hasText ? contextText : undefined, hasText ? contextSource : undefined)
      .then((r) => { mindmapData.value = r })
      .catch((e) => { mindmapError.value = handleQuotaError(e) })
      .finally(() => { mindmapLoading.value = false })

    await Promise.allSettled([summaryPromise, mindmapPromise])
    loadQuotaStatus()
  } catch (e: any) {
    subtitleError.value = e?.response?.data?.detail || e?.message || '字幕提取失败'
    subtitleLoading.value = false
    summaryLoading.value = false
    mindmapLoading.value = false
  }
}

onMounted(() => {
  loadQuotaStatus()
  runAnalysis()
})
</script>

<template>
  <div class="ai-panel flex-1 bg-white rounded-3xl shadow-sm border border-slate-200 overflow-hidden w-full h-full flex flex-col">
    <div class="px-6 py-4 border-b border-slate-100 flex items-center gap-3">
      <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-600 to-violet-600 flex items-center justify-center shadow-sm">
        <Sparkles class="w-4 h-4 text-white" />
      </div>
      <div class="flex-1 min-w-0">
        <h3 class="font-bold text-lg text-slate-900 flex items-center gap-2 flex-wrap">
          AI 视频分析
          <span class="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/80">
            Beta
          </span>
        </h3>
        <p
          v-if="quotaStatusLoading && !quotaStatus"
          class="mt-1 text-xs text-slate-400"
        >
          正在加载额度…
        </p>
        <p
          v-else-if="quotaStatus"
          class="mt-1 text-xs text-slate-600 flex items-start gap-1.5"
        >
          <Gauge
            class="w-3.5 h-3.5 shrink-0 mt-0.5"
            :class="quotaStatus.mode === 'vip' ? 'text-amber-500' : 'text-indigo-500'"
          />
          <span>{{ quotaStatus.display }}</span>
        </p>
      </div>
    </div>

    <div v-if="quotaExhausted" class="mx-6 mt-3 px-4 py-3 rounded-xl bg-amber-50 border border-amber-200 flex items-center gap-3">
      <div class="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center shrink-0">
        <Sparkles class="w-4 h-4 text-amber-600" />
      </div>
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium text-amber-800">{{ quotaMessage }}</p>
        <p class="text-xs text-amber-600 mt-0.5">升级 VIP 会员可无限使用 AI 功能</p>
      </div>
    </div>

    <div class="px-6 pt-2 pb-0 flex-1">
      <NTabs v-model:value="activeTab" type="line" animated class="ai-tabs">
        <NTabPane name="summary">
          <template #tab>
            <span class="inline-flex items-center gap-2">
              <FileText class="w-4 h-4 shrink-0" />
              总结摘要
            </span>
          </template>
          <SummaryView :data="summaryData" :loading="summaryLoading" :error="summaryError" />
        </NTabPane>
        <NTabPane name="subtitle">
          <template #tab>
            <span class="inline-flex items-center gap-2">
              <MessageSquare class="w-4 h-4 shrink-0" />
              字幕文本
            </span>
          </template>
          <SubtitleView
            :url="props.url"
            :subtitles="subtitleData?.subtitles ?? []"
            :full-text="subtitleData?.full_text ?? ''"
            :source="subtitleData?.source ?? 'none'"
            :loading="subtitleLoading"
            :error="subtitleError"
          />
        </NTabPane>
        <NTabPane name="mindmap">
          <template #tab>
            <span class="inline-flex items-center gap-2">
              <Network class="w-4 h-4 shrink-0" />
              思维导图
            </span>
          </template>
          <MindMapView
            :markdown="mindmapData?.markdown ?? ''"
            :loading="mindmapLoading"
            :error="mindmapError"
          />
        </NTabPane>
        <NTabPane name="qa">
          <template #tab>
            <span class="inline-flex items-center gap-2">
              <Sparkles class="w-4 h-4 shrink-0" />
              AI 问答
            </span>
          </template>
          <QAView :url="props.url" />
        </NTabPane>
      </NTabs>
    </div>
  </div>
</template>

<style scoped>
/* 与 Home 主色一致：激活 indigo-600，未激活 slate-500 */
.ai-tabs :deep(.n-tabs-nav) {
  border-bottom: 1px solid #e2e8f0;
}
.ai-tabs :deep(.n-tabs-tab) {
  color: #64748b !important;
  font-weight: 500;
}
.ai-tabs :deep(.n-tabs-tab svg) {
  color: inherit;
}
.ai-tabs :deep(.n-tabs-tab:hover) {
  color: #475569 !important;
}
.ai-tabs :deep(.n-tabs-tab--active) {
  color: #4f46e5 !important;
}
.ai-tabs :deep(.n-tabs-bar) {
  background-color: #4f46e5 !important;
}
.ai-tabs :deep(.n-tabs-tab--active .n-tabs-tab__label) {
  color: #4f46e5 !important;
}
</style>
