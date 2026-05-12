<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Puzzle, Download, Wrench, Shield, Globe, AlertCircle } from 'lucide-vue-next'

const zipUrl = computed(() => `${import.meta.env.BASE_URL}downloads/omnivideo-extension.zip`)
const zipAvailable = ref<boolean | null>(null)

onMounted(async () => {
  try {
    const r = await fetch(zipUrl.value, { method: 'HEAD' })
    zipAvailable.value = r.ok
  } catch {
    zipAvailable.value = false
  }
})
</script>

<template>
  <div class="max-w-3xl mx-auto px-4 py-10 sm:py-14">
    <div class="flex items-center gap-3 mb-2">
      <div class="w-11 h-11 rounded-xl bg-indigo-100 flex items-center justify-center text-indigo-600">
        <Puzzle class="w-6 h-6" />
      </div>
      <div>
        <h1 class="text-2xl sm:text-3xl font-bold text-slate-900">浏览器插件</h1>
        <p class="text-sm text-slate-500 mt-0.5">下载安装包与使用说明</p>
      </div>
    </div>

    <section class="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 class="text-lg font-semibold text-slate-800 flex items-center gap-2">
        <Download class="w-5 h-5 text-indigo-500" />
        下载
      </h2>
      <p class="mt-3 text-sm text-slate-600">
        当前为 Chrome / Edge 等 Chromium 内核浏览器的扩展（Manifest V3）。安装前请确认已允许「开发者模式」加载未上架扩展。
      </p>

      <div v-if="zipAvailable === null" class="mt-4 h-10 rounded-lg bg-slate-100 animate-pulse" />
      <template v-else-if="zipAvailable">
        <a
          :href="zipUrl"
          download="omnivideo-extension.zip"
          class="mt-4 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 transition-colors"
        >
          <Download class="w-4 h-4" />
          下载 omnivideo-extension.zip
        </a>
        <p class="mt-3 text-xs text-slate-500">解压后得到扩展根目录（含 manifest.json），按下方「安装步骤」加载即可。</p>
      </template>
      <template v-else>
        <p class="mt-4 flex items-start gap-2 text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          <AlertCircle class="w-4 h-4 shrink-0 mt-0.5" />
          站点暂未提供预构建安装包。请在项目根目录执行构建脚本生成 ZIP，或按「自行构建」从源码打包。
        </p>
        <pre class="mt-4 text-xs bg-slate-900 text-slate-100 rounded-xl p-4 overflow-x-auto leading-relaxed">cd extension &amp;&amp; npm ci &amp;&amp; npm run build
cd ../frontend &amp;&amp; npm run zip-extension</pre>
        <p class="mt-2 text-xs text-slate-500">生成文件：<code class="text-slate-700 bg-slate-100 px-1 rounded">frontend/public/downloads/omnivideo-extension.zip</code>，重新部署前端后即可在此页下载。</p>
      </template>
    </section>

    <section class="mt-10">
      <h2 class="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
        <Wrench class="w-5 h-5 text-indigo-500" />
        安装步骤
      </h2>
      <ol class="space-y-4 text-slate-700">
        <li class="flex gap-3">
          <span class="shrink-0 w-8 h-8 rounded-full bg-indigo-600 text-white text-sm font-bold flex items-center justify-center">1</span>
          <div>
            <p class="font-medium">解压 ZIP（或直接使用构建目录）</p>
            <p class="text-sm text-slate-600 mt-1">解压后应能看到 <code class="text-sm bg-slate-100 px-1 rounded">manifest.json</code>、<code class="text-sm bg-slate-100 px-1 rounded">popup</code>、<code class="text-sm bg-slate-100 px-1 rounded">background</code> 等文件与文件夹。</p>
          </div>
        </li>
        <li class="flex gap-3">
          <span class="shrink-0 w-8 h-8 rounded-full bg-indigo-600 text-white text-sm font-bold flex items-center justify-center">2</span>
          <div>
            <p class="font-medium">打开扩展管理页</p>
            <p class="text-sm text-slate-600 mt-1">Chrome：地址栏输入 <code class="text-sm bg-slate-100 px-1 rounded">chrome://extensions</code>；Edge：<code class="text-sm bg-slate-100 px-1 rounded">edge://extensions</code>。</p>
          </div>
        </li>
        <li class="flex gap-3">
          <span class="shrink-0 w-8 h-8 rounded-full bg-indigo-600 text-white text-sm font-bold flex items-center justify-center">3</span>
          <div>
            <p class="font-medium">开启「开发者模式」</p>
            <p class="text-sm text-slate-600 mt-1">在页面右上角打开开发者模式开关。</p>
          </div>
        </li>
        <li class="flex gap-3">
          <span class="shrink-0 w-8 h-8 rounded-full bg-indigo-600 text-white text-sm font-bold flex items-center justify-center">4</span>
          <div>
            <p class="font-medium">加载已解压的扩展程序</p>
            <p class="text-sm text-slate-600 mt-1">点击「加载已解压的扩展程序」，选择解压后的文件夹（与 manifest 同级的那一层）。不要只选到 zip 内的子目录导致找不到 manifest。</p>
          </div>
        </li>
        <li class="flex gap-3">
          <span class="shrink-0 w-8 h-8 rounded-full bg-indigo-600 text-white text-sm font-bold flex items-center justify-center">5</span>
          <div>
            <p class="font-medium">固定图标（可选）</p>
            <p class="text-sm text-slate-600 mt-1">点击工具栏拼图图标，将 Omni Video Downloader 固定到工具栏，便于在支持站点上打开弹窗。</p>
          </div>
        </li>
      </ol>
    </section>

    <section class="mt-10">
      <h2 class="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
        <Globe class="w-5 h-5 text-indigo-500" />
        使用说明
      </h2>
      <ul class="space-y-3 text-sm text-slate-700">
        <li class="flex gap-2">
          <span class="text-indigo-500 font-bold">·</span>
          <span>在 <strong>YouTube、Bilibili、抖音、TikTok</strong> 等匹配页面，扩展会注入内容脚本；点击工具栏图标打开弹窗，可解析当前页或配合站点内操作使用（与网页版账号体系一致时需先在本站登录）。</span>
        </li>
        <li class="flex gap-2">
          <span class="text-indigo-500 font-bold">·</span>
          <span>下载任务由浏览器通过 <code class="text-xs bg-slate-100 px-1 rounded">downloads</code> 权限保存到本机默认下载目录。</span>
        </li>
        <li class="flex gap-2">
          <span class="text-indigo-500 font-bold">·</span>
          <span>若解析失败，请确认视频页已完全加载，或尝试刷新页面后再打开弹窗。</span>
        </li>
      </ul>
    </section>

    <section class="mt-10 rounded-2xl border border-slate-200 bg-slate-50 p-5">
      <h2 class="text-lg font-semibold text-slate-800 mb-3 flex items-center gap-2">
        <Shield class="w-5 h-5 text-indigo-500" />
        权限与后端地址
      </h2>
      <p class="text-sm text-slate-600">
        扩展声明了 <code class="text-xs bg-white px-1 rounded border border-slate-200">activeTab</code>、<code class="text-xs bg-white px-1 rounded border border-slate-200">storage</code>、<code class="text-xs bg-white px-1 rounded border border-slate-200">downloads</code>，以及访问后端 API 的 host 权限。默认构建面向本地开发（如 <code class="text-xs bg-white px-1 rounded border border-slate-200">http://localhost:8000</code>）。若需连接线上 API，需修改扩展源码中的 API 与 manifest 中的 host_permissions 后重新打包。
      </p>
    </section>

    <p class="mt-10 text-sm text-slate-500">
      <router-link to="/guide" class="text-indigo-600 hover:text-indigo-800 font-medium">返回网站使用说明</router-link>
      <span class="mx-2 text-slate-300">|</span>
      <router-link to="/" class="text-indigo-600 hover:text-indigo-800 font-medium">回到首页</router-link>
    </p>
  </div>
</template>
