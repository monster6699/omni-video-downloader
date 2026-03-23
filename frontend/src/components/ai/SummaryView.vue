<script setup lang="ts">
import { NSkeleton } from 'naive-ui'
import type { SummaryResponse } from '../../api/ai'

defineProps<{
  data: SummaryResponse | null
  loading: boolean
  error: string
}>()
</script>

<template>
  <div class="py-4">
    <!-- Loading -->
    <div v-if="loading" class="space-y-4 py-4">
      <div class="flex items-center gap-2 text-sm text-indigo-600 mb-2">
        <svg class="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83"/>
        </svg>
        AI 正在生成总结...
      </div>
      <NSkeleton text :repeat="3" />
      <NSkeleton text style="width: 60%" />
      <div class="flex gap-3 mt-4">
        <NSkeleton :width="120" :height="32" :sharp="false" />
        <NSkeleton :width="120" :height="32" :sharp="false" />
        <NSkeleton :width="120" :height="32" :sharp="false" />
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="text-center py-6">
      <p class="text-sm text-red-500">{{ error }}</p>
    </div>

    <!-- Empty (waiting) -->
    <div v-else-if="!data" class="text-center py-8">
      <p class="text-sm text-slate-500">等待分析完成...</p>
    </div>

    <!-- Result -->
    <div v-else class="space-y-6">
      <!-- Summary -->
      <div>
        <h4 class="text-base font-bold text-slate-900 mb-3 flex items-center gap-2">
          <svg class="text-indigo-600 shrink-0" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/></svg>
          概述
        </h4>
        <p class="text-sm text-slate-600 leading-relaxed whitespace-pre-line">{{ data.summary }}</p>
      </div>

      <!-- Keypoints -->
      <div v-if="data.keypoints.length">
        <h4 class="text-base font-bold text-slate-900 mb-3 flex items-center gap-2">
          <svg class="text-indigo-600 shrink-0" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2 2 7l10 5 10-5-10-5Z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/></svg>
          核心要点
        </h4>
        <div class="grid grid-cols-1 gap-2">
          <div
            v-for="(point, i) in data.keypoints"
            :key="i"
            class="flex items-start gap-3 px-4 py-3 rounded-xl bg-indigo-50/60 border border-indigo-100"
          >
            <span class="shrink-0 w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold flex items-center justify-center mt-0.5">
              {{ i + 1 }}
            </span>
            <span class="text-sm text-slate-700 leading-relaxed">{{ point }}</span>
          </div>
        </div>
      </div>

      <!-- Timeline -->
      <div v-if="data.timeline.length">
        <h4 class="text-base font-bold text-slate-900 mb-3 flex items-center gap-2">
          <svg class="text-indigo-600 shrink-0" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          时间线
        </h4>
        <div class="relative pl-6 border-l-2 border-indigo-200 space-y-4">
          <div v-for="(item, i) in data.timeline" :key="i" class="relative">
            <div class="absolute -left-[25px] w-3 h-3 rounded-full bg-indigo-500 border-2 border-white"></div>
            <div class="text-xs font-mono text-indigo-600 mb-0.5">{{ item.time }}</div>
            <div class="text-sm text-slate-700">{{ item.content }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
