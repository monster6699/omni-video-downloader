<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  BookOpen,
  Link2,
  Search,
  Download,
  Sparkles,
  MessageCircle,
  Crown,
  Loader2,
  AlertCircle,
} from 'lucide-vue-next'
import { fetchAiUsageRules, type UsageRules } from '../api/ai'

const router = useRouter()
const rules = ref<UsageRules | null>(null)
const loadError = ref('')

onMounted(async () => {
  try {
    rules.value = await fetchAiUsageRules()
  } catch {
    loadError.value = '无法加载额度配置，以下为默认说明（匿名每日 5 次 AI）。'
    rules.value = {
      anon_ai_daily_limit: 5,
      registered_default_ai_quota: 5,
      vip_ai_unlimited: true,
      subtitle_public_no_llm_quota: true,
      anon_limit_scope: 'summary, mindmap, translate, chat (per IP, UTC day)',
    }
  }
})
</script>

<template>
  <div class="max-w-3xl mx-auto px-4 py-10 sm:py-14">
    <div class="flex items-center gap-3 mb-2">
      <div class="w-11 h-11 rounded-xl bg-indigo-100 flex items-center justify-center text-indigo-600">
        <BookOpen class="w-6 h-6" />
      </div>
      <div>
        <h1 class="text-2xl sm:text-3xl font-bold text-slate-900">使用说明</h1>
        <p class="text-sm text-slate-500 mt-0.5">规则、额度与基本操作</p>
      </div>
    </div>

    <p class="mt-4 text-sm text-slate-600">
      需要在本站外解析视频？可安装
      <router-link to="/extension" class="text-indigo-600 hover:text-indigo-800 font-medium">浏览器插件</router-link>
      ，查看下载与安装说明。
    </p>

    <p v-if="loadError" class="mt-4 flex items-start gap-2 text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
      <AlertCircle class="w-4 h-4 shrink-0 mt-0.5" />
      {{ loadError }}
    </p>

    <section class="mt-10">
      <h2 class="text-lg font-semibold text-slate-800 mb-4">一、快速上手</h2>
      <ol class="space-y-4 text-slate-700">
        <li class="flex gap-3">
          <span class="shrink-0 w-8 h-8 rounded-full bg-indigo-600 text-white text-sm font-bold flex items-center justify-center">1</span>
          <div>
            <p class="font-medium flex items-center gap-2">
              <Link2 class="w-4 h-4 text-indigo-500" />
              粘贴视频链接
            </p>
            <p class="text-sm text-slate-600 mt-1">支持常见平台链接，在首页输入框粘贴后点击解析。</p>
          </div>
        </li>
        <li class="flex gap-3">
          <span class="shrink-0 w-8 h-8 rounded-full bg-indigo-600 text-white text-sm font-bold flex items-center justify-center">2</span>
          <div>
            <p class="font-medium flex items-center gap-2">
              <Search class="w-4 h-4 text-indigo-500" />
              解析与选清晰度
            </p>
            <p class="text-sm text-slate-600 mt-1">等待解析完成，在结果中选择需要的格式与清晰度。</p>
          </div>
        </li>
        <li class="flex gap-3">
          <span class="shrink-0 w-8 h-8 rounded-full bg-indigo-600 text-white text-sm font-bold flex items-center justify-center">3</span>
          <div>
            <p class="font-medium flex items-center gap-2">
              <Download class="w-4 h-4 text-indigo-500" />
              下载
            </p>
            <p class="text-sm text-slate-600 mt-1">登录用户可在「下载记录」中查看历史任务（若已开启该功能）。</p>
          </div>
        </li>
        <li class="flex gap-3">
          <span class="shrink-0 w-8 h-8 rounded-full bg-indigo-600 text-white text-sm font-bold flex items-center justify-center">4</span>
          <div>
            <p class="font-medium flex items-center gap-2">
              <Sparkles class="w-4 h-4 text-indigo-500" />
              AI 面板
            </p>
            <p class="text-sm text-slate-600 mt-1">解析成功后打开 AI 区域：总结、思维导图、字幕、翻译、视频问答等。</p>
          </div>
        </li>
      </ol>
    </section>

    <section class="mt-12">
      <h2 class="text-lg font-semibold text-slate-800 mb-4">二、账号与 AI 额度规则</h2>
      <div v-if="!rules" class="flex items-center gap-2 text-slate-500 py-6">
        <Loader2 class="w-5 h-5 animate-spin" />
        加载规则…
      </div>
      <ul v-else class="space-y-3 text-slate-700">
        <li class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p class="font-medium text-slate-800">未登录（访客）</p>
          <ul class="mt-2 text-sm text-slate-600 list-disc list-inside space-y-1">
            <li>
              每日可使用 <strong class="text-indigo-600">{{ rules.anon_ai_daily_limit }}</strong> 次
              <strong>大模型 AI 功能</strong>（总结、思维导图、字幕翻译、问答），按公网 IP 统计，统计日为 <strong>UTC 自然日</strong>。
            </li>
            <li>超出后需 <strong>登录</strong> 以使用账号内免费额度，或 <strong>开通 VIP</strong> 享受无限次 AI。</li>
            <li v-if="rules.subtitle_public_no_llm_quota">
              <strong>提取字幕</strong>一般不占用上述「每日 AI 次数」（仅为拉取/解析字幕，不走大模型）。
            </li>
          </ul>
        </li>
        <li class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p class="font-medium text-slate-800">已登录（普通用户）</p>
          <ul class="mt-2 text-sm text-slate-600 list-disc list-inside space-y-1">
            <li>
              账号默认带有 <strong class="text-indigo-600">{{ rules.registered_default_ai_quota }}</strong> 次
              免费 AI 额度（每次调用总结/导图/翻译/问答会扣减 1 次，具体以服务端为准）。
            </li>
            <li>VIP 有效期内：<strong>AI 不限次数</strong>（仍以公平使用与系统稳定性为限）。</li>
          </ul>
        </li>
        <li class="rounded-xl border border-amber-200 bg-amber-50/80 p-4">
          <p class="font-medium text-amber-900 flex items-center gap-2">
            <Crown class="w-4 h-4" />
            翻译结果缓存
          </p>
          <p class="mt-2 text-sm text-amber-900/90">
            同一视频、同一目标语言的翻译若命中缓存，通常<strong>不会再次扣减</strong>额度。
          </p>
        </li>
      </ul>
    </section>

    <section class="mt-12">
      <h2 class="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
        <MessageCircle class="w-5 h-5 text-indigo-500" />
        三、常见问题
      </h2>
      <dl class="space-y-4 text-sm text-slate-600">
        <div>
          <dt class="font-medium text-slate-800">提示「今日已用尽」或 403？</dt>
          <dd class="mt-1">访客说明当日匿名额度用完；登录用户说明免费次数用完或 VIP 已过期。可前往定价页开通 VIP。</dd>
        </div>
        <div>
          <dt class="font-medium text-slate-800">提示服务暂不可用（503）？</dt>
          <dd class="mt-1">匿名限流依赖缓存服务；若后端暂时无法连接限流服务，请先尝试登录后再使用 AI。</dd>
        </div>
        <div>
          <dt class="font-medium text-slate-800">IP 统计说明</dt>
          <dd class="mt-1">若经 CDN/反代访问，系统按常见 <code class="text-xs bg-slate-100 px-1 rounded">X-Forwarded-For</code> 取客户端 IP；共享网络下多人可能共用额度。</dd>
        </div>
      </dl>
    </section>

    <div class="mt-12 flex flex-wrap gap-3">
      <button
        type="button"
        class="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
        @click="router.push('/')"
      >
        返回首页
      </button>
      <button
        type="button"
        class="px-4 py-2 rounded-lg border border-slate-200 bg-white text-slate-700 text-sm font-medium hover:bg-slate-50"
        @click="router.push('/pricing')"
      >
        查看 VIP 方案
      </button>
    </div>
  </div>
</template>
