<script setup lang="ts">
import { ref, onUnmounted, computed, watch } from 'vue'
import { Crown, Check, Loader2, X, RefreshCw } from 'lucide-vue-next'
import { LogoWechat, LogoAlipay } from '@vicons/ionicons5'
import QRCode from 'qrcode'
import { getPlans, createOrder, getOrderStatus, type PlanInfo } from '../api/pay'
import { useAuth } from '../composables/useAuth'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ (e: 'update:show', v: boolean): void }>()

const { user, isVip, vipExpireLabel, restoreSession } = useAuth()

function isCurrentPlan(planId: string) {
  return isVip.value && user.value?.vip_plan_id === planId
}

const plans = ref<PlanInfo[]>([])
const selectedPlan = ref('monthly')
const payMethod = ref<'wechat' | 'alipay'>('wechat')
const loading = ref(false)
const qrDataUrl = ref('')
const orderNo = ref('')
const payStatus = ref<'idle' | 'paying' | 'success' | 'failed'>('idle')
const pollTimer = ref<ReturnType<typeof setInterval> | null>(null)

const selectedPlanInfo = computed(() => plans.value.find(p => p.id === selectedPlan.value))

function formatPrice(fen: number) {
  return (fen / 100).toFixed(fen % 100 === 0 ? 0 : 2)
}

function close() {
  resetPay()
  emit('update:show', false)
}

async function handlePay() {
  loading.value = true
  payStatus.value = 'paying'
  try {
    const resp = await createOrder(selectedPlan.value, payMethod.value)
    orderNo.value = resp.order_no
    qrDataUrl.value = await QRCode.toDataURL(resp.qr_url, {
      width: 240,
      margin: 2,
      color: { dark: '#1e293b', light: '#ffffff' },
    })
    startPolling()
  } catch {
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
    if (count > 150) { stopPolling(); payStatus.value = 'failed'; return }
    try {
      const s = await getOrderStatus(orderNo.value)
      if (s.status === 'paid') { stopPolling(); payStatus.value = 'success'; await restoreSession() }
    } catch { /* ignore */ }
  }, 2000)
}

function stopPolling() {
  if (pollTimer.value) { clearInterval(pollTimer.value); pollTimer.value = null }
}

function resetPay() {
  stopPolling()
  payStatus.value = 'idle'
  qrDataUrl.value = ''
  orderNo.value = ''
}

watch(() => props.show, async (v) => {
  if (!v) return
  await restoreSession()
  if (plans.value.length === 0) {
    try {
      plans.value = await getPlans()
    } catch { /* silent */ }
  }
  const pid = user.value?.vip_plan_id
  if (pid === 'monthly' || pid === 'yearly') {
    selectedPlan.value = pid
  }
})

onUnmounted(() => stopPolling())
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="close" />
      <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
        <!-- Header -->
        <div class="px-6 py-4 border-b border-slate-100">
          <div class="flex items-center justify-between gap-3">
            <div class="flex items-center gap-2 min-w-0">
              <Crown class="w-5 h-5 shrink-0 text-amber-500" stroke-width="2" />
              <h3 class="text-lg font-bold text-slate-900 leading-none truncate">{{ isVip ? 'VIP 套餐' : '开通 VIP' }}</h3>
            </div>
            <button type="button" @click="close" class="shrink-0 p-1.5 rounded-lg hover:bg-slate-100 transition-colors inline-flex items-center justify-center">
              <X class="w-5 h-5 text-slate-400 shrink-0" stroke-width="2" />
            </button>
          </div>
          <p
            v-if="isVip && vipExpireLabel"
            class="text-xs text-amber-800 mt-2.5 leading-snug pl-7"
          >
            {{ vipExpireLabel }}
          </p>
        </div>

        <!-- IDLE: select plan + pay -->
        <div v-if="payStatus === 'idle'" class="px-6 py-5 space-y-5">
          <!-- Plan pills -->
          <div class="flex gap-3">
            <button
              v-for="plan in plans"
              :key="plan.id"
              type="button"
              @click="selectedPlan = plan.id"
              :class="selectedPlan === plan.id
                ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                : 'border-slate-200 text-slate-600 hover:border-slate-300'"
              class="relative flex-1 rounded-xl border-2 p-3.5 text-center transition-all"
            >
              <p class="text-lg font-extrabold">¥{{ formatPrice(plan.price) }}</p>
              <p class="text-xs mt-0.5">{{ plan.name }}</p>
              <p
                v-if="isCurrentPlan(plan.id)"
                class="mt-2 text-[10px] font-semibold text-emerald-600 leading-tight"
              >
                已是当前套餐
              </p>
            </button>
          </div>

          <!-- Pay method -->
          <div class="flex gap-3">
            <button
              type="button"
              @click="payMethod = 'wechat'"
              :class="payMethod === 'wechat' ? 'border-green-500 bg-green-50 text-green-700' : 'border-slate-200 text-slate-500'"
              class="flex flex-1 min-w-0 items-center justify-center gap-2 py-2.5 rounded-xl border-2 text-sm font-medium transition-all"
            >
              <LogoWechat class="w-5 h-5 shrink-0" aria-hidden="true" />
              <span class="leading-none">微信支付</span>
            </button>
            <button
              type="button"
              @click="payMethod = 'alipay'"
              :class="payMethod === 'alipay' ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-slate-200 text-slate-500'"
              class="flex flex-1 min-w-0 items-center justify-center gap-2 py-2.5 rounded-xl border-2 text-sm font-medium transition-all"
            >
              <LogoAlipay class="w-5 h-5 shrink-0" aria-hidden="true" />
              <span class="leading-none">支付宝</span>
            </button>
          </div>

          <button
            type="button"
            @click="handlePay"
            :disabled="loading"
            class="w-full py-3.5 rounded-xl font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 transition-colors flex items-center justify-center gap-2"
          >
            <Loader2 v-if="loading" class="w-4 h-4 shrink-0 animate-spin" stroke-width="2" />
            <Crown v-else class="w-4 h-4 shrink-0" stroke-width="2" />
            <span class="leading-none">{{ loading ? '创建订单...' : `¥${selectedPlanInfo ? formatPrice(selectedPlanInfo.price) : ''} 立即开通` }}</span>
          </button>
        </div>

        <!-- PAYING: QR code -->
        <div v-if="payStatus === 'paying'" class="px-6 py-8 text-center">
          <div class="inline-block p-2 bg-white rounded-xl border border-slate-100 shadow-sm mb-4">
            <img v-if="qrDataUrl" :src="qrDataUrl" alt="支付二维码" class="w-[200px] h-[200px]" />
          </div>
          <p class="text-sm text-slate-500 mb-1">
            使用 <span class="font-medium" :class="payMethod === 'wechat' ? 'text-green-600' : 'text-blue-600'">{{ payMethod === 'wechat' ? '微信' : '支付宝' }}</span> 扫码
          </p>
          <p class="text-xl font-bold text-slate-900 mb-4">¥{{ selectedPlanInfo ? formatPrice(selectedPlanInfo.price) : '' }}</p>
          <div class="flex items-center justify-center gap-2 text-sm text-slate-400">
            <Loader2 class="w-4 h-4 shrink-0 animate-spin" stroke-width="2" />
            <span class="leading-none">等待支付...</span>
          </div>
        </div>

        <!-- SUCCESS -->
        <div v-if="payStatus === 'success'" class="px-6 py-8 text-center">
          <div class="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-3">
            <Check class="w-7 h-7 text-green-600 shrink-0" stroke-width="2" />
          </div>
          <h4 class="text-lg font-bold text-slate-900 mb-1">支付成功</h4>
          <p class="text-sm text-slate-500 mb-5">欢迎成为 VIP 会员！</p>
          <button @click="close" class="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-medium transition-colors">
            开始使用
          </button>
        </div>

        <!-- FAILED -->
        <div v-if="payStatus === 'failed'" class="px-6 py-8 text-center">
          <div class="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-3">
            <X class="w-7 h-7 text-red-500 shrink-0" stroke-width="2" />
          </div>
          <h4 class="text-lg font-bold text-slate-900 mb-1">支付失败</h4>
          <p class="text-sm text-slate-500 mb-5">请重新尝试</p>
          <button type="button" @click="resetPay" class="w-full py-3 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium transition-colors flex items-center justify-center gap-2">
            <RefreshCw class="w-4 h-4 shrink-0" stroke-width="2" />
            <span class="leading-none">重新支付</span>
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
