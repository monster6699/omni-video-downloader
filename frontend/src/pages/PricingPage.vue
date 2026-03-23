<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Crown, Check, Sparkles, Download, Zap, Shield,
  Loader2, X, RefreshCw,
} from 'lucide-vue-next'
import { LogoWechat, LogoAlipay } from '@vicons/ionicons5'
import QRCode from 'qrcode'
import { getPlans, createOrder, getOrderStatus, type PlanInfo } from '../api/pay'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const { user, isLoggedIn, isVip, vipExpireLabel, waitForSession, restoreSession } = useAuth()

function isCurrentPlan(planId: string) {
  return isVip.value && user.value?.vip_plan_id === planId
}

const plans = ref<PlanInfo[]>([])
const selectedPlan = ref<string>('monthly')
const payMethod = ref<'wechat' | 'alipay'>('wechat')
const loading = ref(false)
const qrDataUrl = ref('')
const orderNo = ref('')
const payStatus = ref<'idle' | 'paying' | 'success' | 'failed'>('idle')
const pollTimer = ref<ReturnType<typeof setInterval> | null>(null)

const vipFeatures = [
  { icon: Download, text: '高清视频无限下载' },
  { icon: Sparkles, text: 'AI 分析无限次' },
  { icon: Zap, text: '极速下载通道' },
  { icon: Shield, text: '专属客服支持' },
]

const selectedPlanInfo = computed(() => plans.value.find(p => p.id === selectedPlan.value))

function formatPrice(fen: number) {
  return (fen / 100).toFixed(fen % 100 === 0 ? 0 : 2)
}

function pricePerMonth(plan: PlanInfo) {
  const months = Math.round(plan.duration_days / 30)
  return formatPrice(Math.round(plan.price / months))
}

async function handlePay() {
  if (!isLoggedIn.value) {
    router.push('/')
    return
  }
  loading.value = true
  payStatus.value = 'paying'
  try {
    const resp = await createOrder(selectedPlan.value, payMethod.value)
    orderNo.value = resp.order_no
    qrDataUrl.value = await QRCode.toDataURL(resp.qr_url, {
      width: 280,
      margin: 2,
      color: { dark: '#1e293b', light: '#ffffff' },
    })
    startPolling()
  } catch (e: any) {
    payStatus.value = 'failed'
  } finally {
    loading.value = false
  }
}

function startPolling() {
  stopPolling()
  let count = 0
  pollTimer.value = setInterval(async () => {
    count++
    if (count > 150) {
      stopPolling()
      payStatus.value = 'failed'
      return
    }
    try {
      const status = await getOrderStatus(orderNo.value)
      if (status.status === 'paid') {
        stopPolling()
        payStatus.value = 'success'
        await restoreSession()
      }
    } catch { /* ignore */ }
  }, 2000)
}

function stopPolling() {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

function resetPay() {
  stopPolling()
  payStatus.value = 'idle'
  qrDataUrl.value = ''
  orderNo.value = ''
}

onMounted(async () => {
  await waitForSession()
  try {
    plans.value = await getPlans()
  } catch { /* silent */ }
  const pid = user.value?.vip_plan_id
  if (pid === 'monthly' || pid === 'yearly') {
    selectedPlan.value = pid
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="max-w-5xl mx-auto px-4 sm:px-6 py-16">
    <!-- Header -->
    <div class="text-center mb-12">
      <div class="inline-flex items-center justify-center gap-2 px-4 py-1.5 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-sm font-medium mb-4">
        <Crown class="w-4 h-4 shrink-0 text-amber-700" stroke-width="2" />
        <span class="leading-none">升级 VIP，解锁全部功能</span>
      </div>
      <h1 class="text-4xl font-extrabold text-slate-900 tracking-tight">
        选择适合你的方案
      </h1>
      <p class="text-lg text-slate-500 mt-3 max-w-xl mx-auto">
        无限下载 + 无限 AI 分析，一次开通，畅享所有平台视频
      </p>
      <p
        v-if="isLoggedIn && isVip && vipExpireLabel"
        class="text-sm font-medium text-amber-900 mt-4 max-w-xl mx-auto px-4 py-2 rounded-xl bg-amber-50 border border-amber-200"
      >
        {{ vipExpireLabel }}
      </p>
      <p
        v-if="isLoggedIn && isVip && !user?.vip_plan_id"
        class="text-sm text-amber-700 mt-4 max-w-xl mx-auto px-4 py-2 rounded-lg bg-amber-50 border border-amber-100"
      >
        您已是 VIP 会员。续费任意套餐可延长有效期；若系统未记录套餐类型，支付成功后将会更新。
      </p>
    </div>

    <!-- Plan Cards -->
    <div class="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto mb-12">
      <div
        v-for="plan in plans"
        :key="plan.id"
        @click="selectedPlan = plan.id; payStatus === 'paying' && resetPay()"
        class="relative rounded-2xl border-2 p-6 cursor-pointer transition-all"
        :class="selectedPlan === plan.id
          ? 'border-indigo-500 bg-indigo-50/50 shadow-lg shadow-indigo-100'
          : 'border-slate-200 bg-white hover:border-slate-300'"
      >
        <div v-if="plan.id === 'yearly'" class="absolute -top-3 right-4 z-10 px-3 py-1 rounded-full bg-gradient-to-r from-amber-400 to-orange-400 text-white text-xs font-bold leading-none">
          推荐
        </div>

        <!-- 左侧勾选与价格同一行流式排版，避免 absolute 与价格重叠 -->
        <div class="flex items-start gap-3 mb-1">
          <div class="shrink-0 w-5 flex justify-center pt-1.5" aria-hidden="true">
            <div
              v-if="selectedPlan === plan.id"
              class="w-5 h-5 rounded-full bg-indigo-600 flex items-center justify-center"
            >
              <Check class="w-3 h-3 text-white shrink-0" stroke-width="2.5" />
            </div>
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-baseline gap-2">
              <span class="text-3xl font-extrabold text-slate-900 leading-none tabular-nums">¥{{ formatPrice(plan.price) }}</span>
              <span v-if="plan.id === 'yearly'" class="text-sm text-slate-400 line-through">¥{{ formatPrice(plans.find(p => p.id === 'monthly')!.price * 12) }}</span>
            </div>
            <p class="text-sm text-slate-500 mt-2 leading-snug">
              {{ plan.name }}
              <span v-if="plan.duration_days > 30" class="ml-1 text-amber-600 font-medium">
                ≈ ¥{{ pricePerMonth(plan) }}/月
              </span>
            </p>
            <p
              v-if="isCurrentPlan(plan.id)"
              class="mt-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-800 text-xs font-semibold leading-none"
            >
              <Check class="w-3 h-3 shrink-0" stroke-width="2.5" />
              已是当前套餐
            </p>
          </div>
        </div>

        <ul class="space-y-2.5 pl-8 mt-4">
          <li v-for="feat in vipFeatures" :key="feat.text" class="flex items-center gap-2.5 text-sm text-slate-700">
            <div
              class="shrink-0 w-5 h-5 rounded-full flex items-center justify-center"
              :class="selectedPlan === plan.id ? 'bg-indigo-100 text-indigo-600' : 'bg-slate-100 text-slate-400'"
            >
              <component :is="feat.icon" class="w-3 h-3 shrink-0" stroke-width="2.5" />
            </div>
            <span class="leading-snug">{{ feat.text }}</span>
          </li>
        </ul>
      </div>
    </div>

    <!-- Pay Method + Action (when not paying) -->
    <div v-if="payStatus === 'idle'" class="max-w-md mx-auto">
      <div class="flex items-center justify-center gap-4 mb-6">
        <button
          @click="payMethod = 'wechat'"
          :class="payMethod === 'wechat'
            ? 'border-green-500 bg-green-50 text-green-700'
            : 'border-slate-200 text-slate-500 hover:border-slate-300'"
          class="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl border-2 text-sm font-medium transition-all"
        >
          <LogoWechat class="w-5 h-5 shrink-0" aria-hidden="true" />
          <span class="leading-none">微信支付</span>
        </button>
        <button
          @click="payMethod = 'alipay'"
          :class="payMethod === 'alipay'
            ? 'border-blue-500 bg-blue-50 text-blue-700'
            : 'border-slate-200 text-slate-500 hover:border-slate-300'"
          class="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl border-2 text-sm font-medium transition-all"
        >
          <LogoAlipay class="w-5 h-5 shrink-0" aria-hidden="true" />
          <span class="leading-none">支付宝</span>
        </button>
      </div>

      <button
        @click="handlePay"
        :disabled="loading || !selectedPlanInfo"
        class="w-full py-4 rounded-2xl font-bold text-lg transition-all shadow-lg shadow-indigo-200 flex items-center justify-center gap-2.5"
        :class="loading
          ? 'bg-indigo-400 text-white cursor-wait'
          : 'bg-indigo-600 hover:bg-indigo-700 text-white'"
      >
        <Loader2 v-if="loading" class="w-5 h-5 shrink-0 animate-spin" stroke-width="2" />
        <Crown v-else class="w-5 h-5 shrink-0" stroke-width="2" />
        <span class="leading-none">{{ loading ? '正在创建订单...' : `立即开通 ¥${selectedPlanInfo ? formatPrice(selectedPlanInfo.price) : ''}` }}</span>
      </button>
    </div>

    <!-- QR Code payment modal overlay -->
    <div v-if="payStatus === 'paying'" class="max-w-sm mx-auto">
      <div class="bg-white rounded-2xl border border-slate-200 shadow-xl p-8 text-center">
        <div class="flex items-center justify-between gap-3 mb-6">
          <h3 class="text-lg font-bold text-slate-900 leading-none">扫码支付</h3>
          <button type="button" @click="resetPay" class="shrink-0 p-1.5 rounded-lg hover:bg-slate-100 inline-flex items-center justify-center">
            <X class="w-5 h-5 text-slate-400 shrink-0" stroke-width="2" />
          </button>
        </div>

        <div class="inline-block p-3 bg-white rounded-xl border border-slate-100 shadow-sm mb-4">
          <img v-if="qrDataUrl" :src="qrDataUrl" alt="支付二维码" class="w-[240px] h-[240px]" />
        </div>

        <p class="text-sm text-slate-500 mb-2">
          请使用 <span class="font-medium" :class="payMethod === 'wechat' ? 'text-green-600' : 'text-blue-600'">{{ payMethod === 'wechat' ? '微信' : '支付宝' }}</span> 扫码支付
        </p>
        <p class="text-2xl font-bold text-slate-900 mb-4">
          ¥{{ selectedPlanInfo ? formatPrice(selectedPlanInfo.price) : '' }}
        </p>

        <div class="flex items-center justify-center gap-2 text-sm text-slate-400">
          <Loader2 class="w-4 h-4 shrink-0 animate-spin" stroke-width="2" />
          <span class="leading-none">等待支付中...</span>
        </div>
      </div>
    </div>

    <!-- Success -->
    <div v-if="payStatus === 'success'" class="max-w-sm mx-auto text-center">
      <div class="bg-white rounded-2xl border border-slate-200 shadow-xl p-8">
        <div class="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
          <Check class="w-8 h-8 text-green-600 shrink-0" stroke-width="2" />
        </div>
        <h3 class="text-xl font-bold text-slate-900 mb-2">支付成功</h3>
        <p class="text-sm text-slate-500 mb-6">恭喜你成为 VIP 会员，尽情享受吧！</p>
        <button
          @click="router.push('/')"
          class="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-medium transition-colors"
        >
          开始使用
        </button>
      </div>
    </div>

    <!-- Failed -->
    <div v-if="payStatus === 'failed'" class="max-w-sm mx-auto text-center">
      <div class="bg-white rounded-2xl border border-slate-200 shadow-xl p-8">
        <div class="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-4">
          <X class="w-8 h-8 text-red-500 shrink-0" stroke-width="2" />
        </div>
        <h3 class="text-xl font-bold text-slate-900 mb-2">支付超时或失败</h3>
        <p class="text-sm text-slate-500 mb-6">请重新尝试</p>
        <button
          @click="resetPay"
          class="w-full py-3 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium transition-colors flex items-center justify-center gap-2"
        >
          <RefreshCw class="w-4 h-4 shrink-0" stroke-width="2" />
          <span class="leading-none">重新支付</span>
        </button>
      </div>
    </div>
  </div>
</template>
