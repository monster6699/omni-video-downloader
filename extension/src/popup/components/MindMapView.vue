<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'

const props = defineProps<{ markdown: string; loading: boolean; error: string }>()

const svgContainer = ref<HTMLDivElement | null>(null)
const renderError = ref('')
let markmapInstance: any = null

async function renderMindMap() {
  if (!svgContainer.value || !props.markdown) return
  renderError.value = ''
  try {
    const { Transformer } = await import('markmap-lib')
    const { Markmap } = await import('markmap-view')
    const transformer = new Transformer()
    const { root } = transformer.transform(props.markdown)
    svgContainer.value.innerHTML = ''
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
    svg.setAttribute('width', '100%'); svg.setAttribute('height', '280')
    svg.style.width = '100%'; svg.style.minHeight = '280px'
    svgContainer.value.appendChild(svg)
    if (markmapInstance) { try { markmapInstance.destroy() } catch {} }
    markmapInstance = Markmap.create(svg, { autoFit: true, duration: 300, maxWidth: 200 }, root)
    setTimeout(() => { try { markmapInstance?.fit() } catch {} }, 150)
  } catch (e: any) {
    console.error('Mindmap render error:', e)
    renderError.value = '渲染失败: ' + (e?.message || '')
  }
}

onMounted(async () => { if (props.markdown) { await nextTick(); await renderMindMap() } })
watch(() => props.markdown, async (val) => { if (val) { await nextTick(); await renderMindMap() } }, { flush: 'post' })
onUnmounted(() => { if (markmapInstance) { try { markmapInstance.destroy() } catch {}; markmapInstance = null } })
</script>

<template>
  <div>
    <div v-if="loading" class="flex items-center gap-2 text-sm text-indigo-500 py-8 justify-center">
      <div class="w-4 h-4 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" /><span>正在生成导图…</span>
    </div>
    <p v-else-if="error || renderError" class="text-red-500 text-sm text-center py-4">{{ error || renderError }}</p>
    <div v-else-if="!markdown" class="text-center py-6 text-sm text-slate-400">等待分析完成…</div>
    <div v-else>
      <div ref="svgContainer" class="w-full rounded-xl border border-slate-200 bg-slate-50/50 overflow-hidden" />
      <p class="text-[10px] text-slate-400 mt-1.5 text-center">可拖拽缩放，点击节点展开/折叠</p>
    </div>
  </div>
</template>
