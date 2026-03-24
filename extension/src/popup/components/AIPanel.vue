<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { fetchSubtitle, fetchSummary, fetchMindMap, streamChat, translateSubtitles, ApiError } from '../../shared/api'
import { getToken } from '../../shared/storage'
import type { SummaryResponse, SubtitleResponse } from '../../shared/types'
import MindMapView from './MindMapView.vue'

const props = defineProps<{ url: string }>()

type Tab = 'summary' | 'subtitle' | 'mindmap' | 'qa'
const activeTab = ref<Tab>('summary')
const tabs: { key: Tab; label: string; icon: string }[] = [
  { key: 'summary', label: '总结摘要', icon: '📝' },
  { key: 'subtitle', label: '字幕文本', icon: '💬' },
  { key: 'mindmap', label: '思维导图', icon: '🧠' },
  { key: 'qa', label: 'AI 问答', icon: '✨' },
]

const isLoggedIn = ref(false)
getToken().then(t => { isLoggedIn.value = !!t })

const summaryData = ref<SummaryResponse | null>(null)
const summaryLoading = ref(false)
const summaryError = ref('')

const subtitleData = ref<SubtitleResponse | null>(null)
const subtitleLoading = ref(false)
const subtitleError = ref('')

const targetLang = ref('zh')
const translating = ref(false)
const translateError = ref('')
const translations = ref<string[]>([])

const langOptions = [
  { label: '中文', value: 'zh' },
  { label: 'English', value: 'en' },
  { label: '日本語', value: 'ja' },
  { label: '한국어', value: 'ko' },
  { label: 'Français', value: 'fr' },
  { label: 'Español', value: 'es' },
  { label: 'Deutsch', value: 'de' },
]

/** 与后端每批约 24 条同级估算，仅作提示 */
const translateBatchHint = computed(() => {
  const n = subtitleData.value?.subtitles.length ?? 0
  if (n <= 0) return ''
  const batches = Math.max(1, Math.ceil(n / 24))
  return batches > 1
    ? `约 ${batches} 批请求（服务端并行），可能需要 1～5 分钟，请勿关闭弹窗`
    : '通常很快完成'
})

const mindmapMarkdown = ref('')
const mindmapLoading = ref(false)
const mindmapError = ref('')

const qaQuestion = ref('')
const qaMessages = ref<{ role: string; content: string }[]>([])
const qaStreaming = ref(false)
const chatBox = ref<HTMLDivElement | null>(null)
const quickQs = ['这个视频主要讲了什么？', '视频的核心观点是什么？', '总结一下要点']

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

function handleError(e: unknown): string {
  if (e instanceof ApiError) return e.message
  return (e as Error).message || '请求失败'
}

function renderMd(text: string): string {
  let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="md-pre"><code>$2</code></pre>')
  html = html.replace(/`([^`]+)`/g, '<code class="md-code">$1</code>')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/^### (.+)$/gm, '<div class="md-h3">$1</div>')
  html = html.replace(/^## (.+)$/gm, '<div class="md-h2">$1</div>')
  html = html.replace(/^[-*] (.+)$/gm, '<div class="md-li">• $1</div>')
  html = html.replace(/^(\d+)\. (.+)$/gm, '<div class="md-li">$1. $2</div>')
  html = html.replace(/\n{2,}/g, '<br/><br/>')
  html = html.replace(/\n/g, '<br/>')
  return html
}

async function runAnalysis() {
  subtitleData.value = null; summaryData.value = null; mindmapMarkdown.value = ''
  translations.value = []; translateError.value = ''
  subtitleLoading.value = true; summaryLoading.value = true; mindmapLoading.value = true
  subtitleError.value = ''; summaryError.value = ''; mindmapError.value = ''

  try {
    const sub = await fetchSubtitle(props.url)
    subtitleData.value = sub
    subtitleLoading.value = false

    const text = sub.full_text?.trim() ? sub.full_text : undefined
    const source = sub.source !== 'none' ? sub.source : undefined

    fetchSummary(props.url, text, source)
      .then(r => { summaryData.value = r })
      .catch(e => { summaryError.value = handleError(e) })
      .finally(() => { summaryLoading.value = false })

    fetchMindMap(props.url, text, source)
      .then(r => { mindmapMarkdown.value = r.markdown })
      .catch(e => { mindmapError.value = handleError(e) })
      .finally(() => { mindmapLoading.value = false })
  } catch (e) {
    subtitleError.value = (e as Error).message || '字幕提取失败'
    subtitleLoading.value = false; summaryLoading.value = false; mindmapLoading.value = false
  }
}

async function sendChat(q?: string) {
  const text = (q || qaQuestion.value).trim()
  if (!text || qaStreaming.value) return
  qaQuestion.value = ''
  qaMessages.value.push({ role: 'user', content: text })
  qaMessages.value.push({ role: 'assistant', content: '' })
  qaStreaming.value = true
  await scrollChat()

  const idx = qaMessages.value.length - 1
  try {
    const history = qaMessages.value.slice(0, -2).map(m => ({ role: m.role, content: m.content }))
    await streamChat(props.url, text, history, (chunk) => {
      qaMessages.value[idx].content += chunk
      scrollChat()
    })
  } catch (e) {
    qaMessages.value[idx].content = qaMessages.value[idx].content || handleError(e)
  } finally { qaStreaming.value = false }
}

async function scrollChat() {
  await nextTick()
  if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
}

async function handleTranslate() {
  if (!subtitleData.value?.subtitles.length || translating.value) return
  translating.value = true
  translateError.value = ''
  try {
    const texts = subtitleData.value.subtitles.map((s) => s.text)
    const res = await translateSubtitles(props.url, texts, targetLang.value)
    translations.value = res.translations
  } catch (e) {
    translateError.value = handleError(e)
  } finally {
    translating.value = false
  }
}

function copySubtitleAll() {
  const sub = subtitleData.value
  if (!sub) return
  let text = sub.full_text
  if (translations.value.length === sub.subtitles.length) {
    text = sub.subtitles
      .map((s, i) => `${s.text}\n${translations.value[i] || ''}`)
      .join('\n\n')
  }
  void navigator.clipboard.writeText(text)
}

function copySubtitleLine(original: string, translation: string | undefined) {
  const payload = translation ? `${original}\n${translation}` : original
  void navigator.clipboard.writeText(payload)
}

watch(() => props.url, () => { if (props.url) runAnalysis() }, { immediate: true })
</script>

<template>
  <div class="mt-3 rounded-2xl bg-white border border-slate-200 shadow-sm overflow-hidden">
    <div class="flex border-b border-slate-100 px-1 bg-slate-50/50">
      <button v-for="tab in tabs" :key="tab.key"
        class="flex-1 py-2.5 text-xs font-medium transition-colors text-center relative"
        :class="activeTab === tab.key ? 'text-indigo-600' : 'text-slate-500 hover:text-slate-700'"
        @click="activeTab = tab.key">
        <span class="inline-flex items-center gap-1"><span>{{ tab.icon }}</span><span>{{ tab.label }}</span></span>
        <div v-if="activeTab === tab.key" class="absolute bottom-0 left-2 right-2 h-0.5 bg-indigo-600 rounded-full" />
      </button>
    </div>

    <div class="p-4 max-h-80 overflow-y-auto">
      <!-- Summary -->
      <div v-if="activeTab === 'summary'">
        <div v-if="summaryLoading" class="flex items-center gap-2 text-sm text-indigo-500 py-6 justify-center">
          <div class="w-4 h-4 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" /><span>正在生成摘要…</span>
        </div>
        <div v-else-if="summaryError" class="text-center py-4">
          <p class="text-red-500 text-sm">{{ summaryError }}</p>
          <p v-if="!isLoggedIn" class="text-xs text-slate-400 mt-1">提示：请在右上角登录插件账号</p>
        </div>
        <div v-else-if="summaryData" class="space-y-3">
          <p class="text-sm text-slate-700 leading-relaxed">{{ summaryData.summary }}</p>
          <div v-if="summaryData.keypoints.length">
            <h5 class="text-xs font-bold text-slate-500 mb-1.5 uppercase tracking-wider">要点</h5>
            <ul class="space-y-1">
              <li v-for="(pt, i) in summaryData.keypoints" :key="i" class="text-xs text-slate-600 flex gap-1.5">
                <span class="text-indigo-500 shrink-0">•</span><span>{{ pt }}</span>
              </li>
            </ul>
          </div>
          <div v-if="summaryData.timeline.length">
            <h5 class="text-xs font-bold text-slate-500 mb-1.5 uppercase tracking-wider">时间线</h5>
            <div class="space-y-1">
              <div v-for="(item, i) in summaryData.timeline" :key="i" class="text-xs flex gap-2">
                <span class="text-indigo-500 font-mono shrink-0">{{ item.time }}</span>
                <span class="text-slate-600">{{ item.text }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Subtitles -->
      <div v-if="activeTab === 'subtitle'">
        <div v-if="subtitleLoading" class="flex items-center gap-2 text-sm text-indigo-500 py-6 justify-center">
          <div class="w-4 h-4 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" /><span>正在提取字幕…</span>
        </div>
        <p v-else-if="subtitleError" class="text-red-500 text-sm text-center py-4">{{ subtitleError }}</p>
        <div v-else-if="!subtitleData || subtitleData.subtitles.length === 0" class="text-center py-6">
          <p class="text-sm text-slate-400">当前视频无字幕</p>
        </div>
        <div v-else>
          <div class="flex flex-wrap items-center gap-2 mb-2">
            <span class="text-xs text-slate-400 shrink-0">共 {{ subtitleData.subtitles.length }} 条</span>
            <select
              v-model="targetLang"
              class="h-7 px-2 rounded-lg text-[11px] font-medium bg-slate-50 border border-slate-200 text-slate-700 cursor-pointer focus:outline-none focus:ring-1 focus:ring-indigo-400"
              @change="translations = []"
            >
              <option v-for="opt in langOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
            <button
              type="button"
              class="h-7 px-2.5 rounded-lg text-[11px] font-semibold bg-indigo-50 text-indigo-600 hover:bg-indigo-100 disabled:opacity-50 transition shrink-0"
              :disabled="translating"
              @click="handleTranslate"
            >
              {{ translating ? '翻译中…' : '翻译' }}
            </button>
            <button type="button" class="text-xs text-indigo-600 hover:text-indigo-700 font-medium ml-auto" @click="copySubtitleAll">
              复制全部
            </button>
          </div>
          <p v-if="translating" class="text-[10px] text-slate-500 mb-2 leading-snug">{{ translateBatchHint }}</p>
          <p v-if="translateError" class="text-red-500 text-[11px] mb-2">{{ translateError }}</p>
          <p v-else-if="translations.length" class="text-[10px] text-indigo-600 mb-2">已翻译为 {{ langOptions.find(o => o.value === targetLang)?.label }}</p>
          <div class="space-y-0.5 max-h-60 overflow-y-auto">
            <div
              v-for="(s, i) in subtitleData.subtitles"
              :key="i"
              class="flex gap-2.5 px-2 py-1.5 rounded-lg hover:bg-slate-50 cursor-pointer transition-colors"
              @click="copySubtitleLine(s.text, translations[i])"
            >
              <span class="text-[11px] font-mono text-indigo-500 shrink-0 pt-0.5 min-w-10">{{ formatTime(s.start) }}</span>
              <div class="min-w-0 flex-1">
                <span class="text-xs text-slate-700 leading-relaxed block">{{ s.text }}</span>
                <template v-if="translations.length > i">
                  <span v-if="translations[i]" class="text-[11px] text-indigo-600/90 leading-relaxed block mt-0.5">{{ translations[i] }}</span>
                  <span v-else-if="s.text.trim()" class="text-[11px] text-amber-600/90 leading-relaxed block mt-0.5">（本行无译文，多为模型输出截断，可再点「翻译」重试）</span>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Mindmap -->
      <div v-if="activeTab === 'mindmap'">
        <MindMapView :markdown="mindmapMarkdown" :loading="mindmapLoading" :error="mindmapError" />
      </div>

      <!-- QA Chat -->
      <div v-if="activeTab === 'qa'">
        <div v-if="qaMessages.length === 0" class="py-4">
          <p class="text-xs text-slate-400 mb-3 text-center">向 AI 提问关于视频的任何问题</p>
          <div class="flex flex-wrap gap-1.5 justify-center">
            <button v-for="q in quickQs" :key="q"
              class="text-xs px-3 py-1.5 bg-indigo-50 text-indigo-600 rounded-full hover:bg-indigo-100 transition"
              @click="sendChat(q)">{{ q }}</button>
          </div>
        </div>
        <div v-else ref="chatBox" class="space-y-3 max-h-50 overflow-y-auto mb-3">
          <div v-for="(msg, i) in qaMessages" :key="i" :class="msg.role === 'user' ? 'text-right' : ''">
            <div class="inline-block max-w-[85%] px-3 py-2 rounded-xl text-xs leading-relaxed"
              :class="msg.role === 'user' ? 'bg-indigo-600 text-white rounded-br-sm' : 'bg-slate-100 text-slate-700 rounded-bl-sm md-content'">
              <span v-if="!msg.content && qaStreaming && i === qaMessages.length - 1" class="inline-block w-2 h-2 bg-indigo-400 rounded-full animate-pulse" />
              <span v-else-if="msg.role === 'user'">{{ msg.content }}</span>
              <span v-else v-html="renderMd(msg.content)" />
            </div>
          </div>
        </div>
        <div class="flex gap-2">
          <input v-model="qaQuestion" placeholder="输入问题…"
            class="flex-1 bg-slate-50 border border-slate-200 text-xs text-slate-900 rounded-xl px-3 py-2 focus:border-indigo-500 focus:outline-none"
            @keyup.enter="sendChat()" />
          <button class="px-3 py-2 bg-indigo-600 text-white text-xs font-semibold rounded-xl hover:bg-indigo-700 transition disabled:opacity-50 shrink-0"
            :disabled="qaStreaming || !qaQuestion.trim()" @click="sendChat()">发送</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
:deep(.md-content strong) { font-weight: 700; }
:deep(.md-content .md-h2) { font-weight: 700; font-size: 13px; margin: 8px 0 4px; }
:deep(.md-content .md-h3) { font-weight: 600; font-size: 12px; margin: 6px 0 2px; }
:deep(.md-content .md-li) { padding-left: 8px; }
:deep(.md-content .md-code) { background: #e2e8f0; padding: 1px 4px; border-radius: 3px; font-family: monospace; font-size: 11px; }
:deep(.md-content .md-pre) { background: #1e293b; color: #e2e8f0; padding: 8px 10px; border-radius: 8px; margin: 6px 0; overflow-x: auto; font-size: 11px; font-family: monospace; white-space: pre-wrap; }
</style>
