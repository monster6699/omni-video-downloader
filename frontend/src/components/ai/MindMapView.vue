<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'

const props = defineProps<{
  markdown: string
  loading: boolean
  error: string
}>()

const svgContainer = ref<HTMLDivElement | null>(null)
const renderError = ref('')
let markmapInstance: any = null
let assetsLoaded = false

async function loadMarkmapAssets(transformer: any) {
  if (assetsLoaded) return
  try {
    const { loadCSS, loadJS } = await import('markmap-common')
    const assets = transformer.getAssets()
    if (assets.styles) loadCSS(assets.styles)
    if (assets.scripts) {
      const { Markmap } = await import('markmap-view')
      await loadJS(assets.scripts, { getMarkmap: () => ({ Markmap }) })
    }
    assetsLoaded = true
  } catch (e) {
    console.warn('Failed to load markmap assets:', e)
  }
}

async function renderMindMap() {
  if (!svgContainer.value || !props.markdown) return

  renderError.value = ''

  try {
    const { Transformer } = await import('markmap-lib')
    const { Markmap } = await import('markmap-view')

    const transformer = new Transformer()
    await loadMarkmapAssets(transformer)
    const { root } = transformer.transform(props.markdown)

    svgContainer.value.innerHTML = ''
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
    svg.setAttribute('width', '100%')
    svg.setAttribute('height', '500')
    svg.style.width = '100%'
    svg.style.minHeight = '500px'
    svgContainer.value.appendChild(svg)

    if (markmapInstance) {
      try { markmapInstance.destroy() } catch {}
    }

    markmapInstance = Markmap.create(svg, { autoFit: true }, root)

    setTimeout(() => {
      if (markmapInstance) {
        try { markmapInstance.fit() } catch {}
      }
    }, 100)
  } catch (e: any) {
    console.error('Mindmap render error:', e)
    renderError.value = '思维导图渲染失败: ' + (e?.message || '')
  }
}

onMounted(async () => {
  if (props.markdown) {
    await nextTick()
    await renderMindMap()
  }
})

watch(
  () => props.markdown,
  async (val) => {
    if (val) {
      await nextTick()
      await renderMindMap()
    }
  },
  { flush: 'post' },
)

onUnmounted(() => {
  if (markmapInstance) {
    try { markmapInstance.destroy() } catch {}
    markmapInstance = null
  }
})
</script>

<template>
  <div class="py-4">
    <!-- Loading -->
    <div v-if="loading" class="py-8 text-center">
      <div class="inline-flex items-center gap-2 text-sm text-purple-600">
        <svg class="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83"/>
        </svg>
        AI 正在生成思维导图...
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error || renderError" class="text-center py-6">
      <p class="text-sm text-red-500">{{ error || renderError }}</p>
    </div>

    <!-- Empty (waiting) -->
    <div v-else-if="!markdown" class="text-center py-8">
      <p class="text-sm text-[var(--color-text-secondary)]">等待分析完成...</p>
    </div>

    <!-- Mind Map -->
    <div v-else>
      <div ref="svgContainer" class="w-full rounded-xl border border-[var(--color-border)] bg-gray-50 overflow-hidden"></div>
      <div class="mt-3">
        <span class="text-xs text-[var(--color-text-secondary)]">可拖拽缩放，点击节点展开/折叠</span>
      </div>
    </div>
  </div>
</template>
