<script setup lang="ts">
import { ref, nextTick, inject } from 'vue'
import { NInput } from 'naive-ui'
import { streamChat, QuotaExhaustedError, type ChatMessage } from '../../api/ai'

const props = defineProps<{ url: string }>()

const refreshAiQuota = inject<(() => void) | undefined>('refreshAiQuota', undefined)

const question = ref('')
const messages = ref<ChatMessage[]>([])
const streaming = ref(false)
const chatContainer = ref<HTMLDivElement | null>(null)

const quickQuestions = [
  '这个视频主要讲了什么？',
  '视频的核心观点是什么？',
  '总结一下视频的要点',
]

async function scrollToBottom() {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

async function handleSend(q?: string) {
  const text = (q || question.value).trim()
  if (!text || streaming.value) return

  question.value = ''
  messages.value.push({ role: 'user', content: text })
  messages.value.push({ role: 'assistant', content: '' })
  streaming.value = true
  await scrollToBottom()

  const assistantIdx = messages.value.length - 1

  try {
    const history = messages.value.slice(0, -2).map((m) => ({
      role: m.role,
      content: m.content,
    }))

    await streamChat(props.url, text, history, (chunk) => {
      messages.value[assistantIdx].content += chunk
      scrollToBottom()
    })
    refreshAiQuota?.()
  } catch (e: any) {
    if (e instanceof QuotaExhaustedError) {
      messages.value[assistantIdx].content = e.message
    } else {
      messages.value[assistantIdx].content =
        messages.value[assistantIdx].content || `出错了: ${e?.message || '请求失败'}`
    }
  } finally {
    streaming.value = false
    await scrollToBottom()
  }
}
</script>

<template>
  <div class="py-4 flex flex-col" style="height: 480px">
    <!-- Messages -->
    <div ref="chatContainer" class="flex-1 overflow-y-auto space-y-4 mb-4 pr-1">
      <!-- Welcome -->
      <div v-if="messages.length === 0" class="text-center py-8">
        <div class="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center mx-auto mb-3">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
        </div>
        <p class="text-sm text-[var(--color-text-secondary)] mb-4">基于视频内容进行智能问答，试试以下问题：</p>
        <div class="flex flex-wrap gap-2 justify-center">
          <button
            v-for="q in quickQuestions"
            :key="q"
            class="px-3 py-1.5 rounded-full border border-purple-200 text-sm text-purple-600 hover:bg-purple-50 transition-colors cursor-pointer"
            @click="handleSend(q)"
          >
            {{ q }}
          </button>
        </div>
      </div>

      <!-- Chat Messages -->
      <template v-for="(msg, i) in messages" :key="i">
        <!-- User -->
        <div v-if="msg.role === 'user'" class="flex justify-end">
          <div class="max-w-[80%] px-4 py-2.5 rounded-2xl rounded-br-md bg-purple-600 text-white text-sm leading-relaxed">
            {{ msg.content }}
          </div>
        </div>
        <!-- Assistant -->
        <div v-else class="flex justify-start">
          <div class="max-w-[80%] px-4 py-2.5 rounded-2xl rounded-bl-md bg-gray-100 text-[var(--color-text)] text-sm leading-relaxed whitespace-pre-wrap">
            {{ msg.content }}
            <span v-if="streaming && i === messages.length - 1 && !msg.content" class="inline-flex gap-1">
              <span class="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce" style="animation-delay: 0s"></span>
              <span class="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce" style="animation-delay: 0.15s"></span>
              <span class="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce" style="animation-delay: 0.3s"></span>
            </span>
          </div>
        </div>
      </template>
    </div>

    <!-- Input -->
    <div class="shrink-0 flex items-center gap-2 pt-3 border-t border-[var(--color-border)]">
      <NInput
        v-model:value="question"
        placeholder="输入你的问题..."
        :disabled="streaming"
        class="flex-1"
        @keyup.enter="handleSend()"
      />
      <button
        class="shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all cursor-pointer"
        :class="streaming || !question.trim() ? 'bg-gray-100 text-gray-400' : 'bg-purple-600 text-white hover:bg-purple-700 active:scale-95'"
        :disabled="streaming || !question.trim()"
        @click="handleSend()"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>
        </svg>
      </button>
    </div>
  </div>
</template>
