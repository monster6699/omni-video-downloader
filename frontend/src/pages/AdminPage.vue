<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Shield, Users, Download, Sparkles, Search, Crown,
  Loader2, ChevronLeft, ChevronRight, Pencil, X, Check, Banknote,
} from 'lucide-vue-next'
import {
  fetchAdminUsers,
  fetchAdminStats,
  fetchAdminVipPricing,
  updateAdminVipPricing,
  updateAdminUser,
  type AdminUserItem,
  type AdminStats,
  type AdminUserUpdate,
} from '../api/admin'
import { useAuth } from '../composables/useAuth'
import { formatVipExpireAt, isVipExpireInPast, toDatetimeLocalInputValue } from '../utils/format'

const router = useRouter()
const { isAdmin, waitForSession } = useAuth()

const users = ref<AdminUserItem[]>([])
const total = ref(0)
const page = ref(1)
const keyword = ref('')
const loading = ref(false)
const stats = ref<AdminStats | null>(null)

const editModal = ref(false)
const editUser = ref<AdminUserItem | null>(null)
const editForm = ref<AdminUserUpdate>({})
/** datetime-local 字符串，与 editForm.vip_expire_at 同步提交 */
const editVipExpireLocal = ref('')
const saving = ref(false)

const vipMonthlyYuan = ref<number | string>('')
const vipYearlyYuan = ref<number | string>('')
const vipPricingUpdatedAt = ref<string | null>(null)
const vipPricingLoading = ref(false)
const vipPricingSaving = ref(false)
const vipPricingError = ref('')

const aiTypeLabels: Record<string, string> = {
  summary: '总结',
  mindmap: '导图',
  chat: '问答',
  translate: '翻译',
}

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / 20)))

async function loadUsers(p = 1) {
  loading.value = true
  try {
    const data = await fetchAdminUsers(p, 20, keyword.value)
    users.value = data.items
    total.value = data.total
    page.value = p
  } catch {
    /* silent */
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    stats.value = await fetchAdminStats()
  } catch {
    /* silent */
  }
}

async function loadVipPricing() {
  vipPricingLoading.value = true
  vipPricingError.value = ''
  try {
    const d = await fetchAdminVipPricing()
    vipMonthlyYuan.value = d.monthly_fen / 100
    vipYearlyYuan.value = d.yearly_fen / 100
    vipPricingUpdatedAt.value = d.updated_at
  } catch {
    vipPricingError.value = 'VIP 定价加载失败'
  } finally {
    vipPricingLoading.value = false
  }
}

async function saveVipPricing() {
  const m = Number(vipMonthlyYuan.value)
  const y = Number(vipYearlyYuan.value)
  const mf = Math.round(m * 100)
  const yf = Math.round(y * 100)
  if (!Number.isFinite(m) || !Number.isFinite(y) || mf < 1 || yf < 1) {
    vipPricingError.value = '请输入有效的价格（元），最低 ¥0.01'
    return
  }
  vipPricingSaving.value = true
  vipPricingError.value = ''
  try {
    const d = await updateAdminVipPricing({ monthly_fen: mf, yearly_fen: yf })
    vipMonthlyYuan.value = d.monthly_fen / 100
    vipYearlyYuan.value = d.yearly_fen / 100
    vipPricingUpdatedAt.value = d.updated_at
  } catch (e: unknown) {
    const d = (e as { response?: { data?: { detail?: string | string[] } } })?.response?.data
      ?.detail
    const msg = Array.isArray(d) ? d.join('；') : d
    vipPricingError.value = typeof msg === 'string' && msg ? msg : '保存失败'
  } finally {
    vipPricingSaving.value = false
  }
}

function openEdit(u: AdminUserItem) {
  editUser.value = u
  editForm.value = {
    nickname: u.nickname ?? undefined,
    is_vip: u.is_vip,
    ai_quota: u.ai_quota,
    is_admin: u.is_admin,
  }
  editVipExpireLocal.value = toDatetimeLocalInputValue(u.vip_expire_at)
  editModal.value = true
}

function closeEdit() {
  editModal.value = false
  editUser.value = null
  editVipExpireLocal.value = ''
}

async function saveEdit() {
  if (!editUser.value) return
  saving.value = true
  try {
    const vipExpirePayload =
      editVipExpireLocal.value.trim() === ''
        ? null
        : new Date(editVipExpireLocal.value).toISOString()
    await updateAdminUser(editUser.value.id, {
      ...editForm.value,
      vip_expire_at: vipExpirePayload,
    })
    const u = editUser.value
    if (editForm.value.nickname !== undefined) u.nickname = editForm.value.nickname!
    if (editForm.value.is_vip !== undefined) u.is_vip = editForm.value.is_vip!
    if (editForm.value.ai_quota !== undefined) u.ai_quota = editForm.value.ai_quota!
    if (editForm.value.is_admin !== undefined) u.is_admin = editForm.value.is_admin!
    u.vip_expire_at = vipExpirePayload
    closeEdit()
  } catch {
    /* silent */
  } finally {
    saving.value = false
  }
}

function handleSearch() {
  loadUsers(1)
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

onMounted(async () => {
  await waitForSession()
  if (!isAdmin.value) {
    router.replace('/')
    return
  }
  loadUsers()
  loadStats()
  loadVipPricing()
})
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 sm:px-6 py-10">
    <!-- Header -->
    <div class="flex items-center gap-4 mb-8">
      <div class="w-10 h-10 rounded-xl bg-violet-100 flex items-center justify-center">
        <Shield class="w-5 h-5 text-violet-600" />
      </div>
      <div>
        <h1 class="text-2xl font-bold text-slate-900">管理后台</h1>
        <p class="text-sm text-slate-500 mt-0.5">用户管理与系统统计</p>
      </div>
    </div>

    <!-- Stats Cards -->
    <div v-if="stats" class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <div class="bg-gradient-to-br from-blue-50 to-blue-100/50 rounded-2xl p-5 border border-blue-200/50">
        <div class="flex items-center gap-2 text-blue-600 mb-2">
          <Users class="w-4 h-4" />
          <span class="text-xs font-medium">总用户</span>
        </div>
        <p class="text-3xl font-bold text-blue-900">{{ stats.total_users }}</p>
      </div>
      <div class="bg-gradient-to-br from-amber-50 to-amber-100/50 rounded-2xl p-5 border border-amber-200/50">
        <div class="flex items-center gap-2 text-amber-600 mb-2">
          <Crown class="w-4 h-4" />
          <span class="text-xs font-medium">VIP 用户</span>
        </div>
        <p class="text-3xl font-bold text-amber-900">{{ stats.vip_users }}</p>
      </div>
      <div class="bg-gradient-to-br from-green-50 to-green-100/50 rounded-2xl p-5 border border-green-200/50">
        <div class="flex items-center gap-2 text-green-600 mb-2">
          <Download class="w-4 h-4" />
          <span class="text-xs font-medium">今日下载</span>
        </div>
        <p class="text-3xl font-bold text-green-900">{{ stats.today_downloads }}</p>
      </div>
      <div class="bg-gradient-to-br from-purple-50 to-purple-100/50 rounded-2xl p-5 border border-purple-200/50">
        <div class="flex items-center gap-2 text-purple-600 mb-2">
          <Sparkles class="w-4 h-4" />
          <span class="text-xs font-medium">今日 AI 调用</span>
        </div>
        <p class="text-3xl font-bold text-purple-900">{{ stats.today_ai_tasks }}</p>
        <div v-if="Object.keys(stats.ai_type_distribution).length" class="flex gap-2 mt-2 flex-wrap">
          <span
            v-for="(count, type) in stats.ai_type_distribution"
            :key="type"
            class="text-[10px] px-1.5 py-0.5 rounded bg-purple-100 text-purple-700"
          >
            {{ aiTypeLabels[type] || type }}: {{ count }}
          </span>
        </div>
      </div>
    </div>

    <!-- VIP 定价 -->
    <div class="bg-white border border-slate-200 rounded-2xl p-6 mb-8">
      <div class="flex items-center gap-2 mb-1">
        <Banknote class="w-5 h-5 text-amber-600" />
        <h2 class="text-lg font-semibold text-slate-900">VIP 定价</h2>
      </div>
      <p class="text-sm text-slate-500 mb-4">
        月度 / 年度套餐在定价页与支付弹窗中展示的价格（单位：元）。保存后立即对<strong>新订单</strong>生效；已创建的待支付订单金额不变。
      </p>
      <div v-if="vipPricingLoading" class="py-8 flex justify-center">
        <Loader2 class="w-6 h-6 text-violet-500 animate-spin" />
      </div>
      <template v-else>
        <div class="grid sm:grid-cols-2 gap-4 max-w-xl">
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1.5">月度 VIP（元）</label>
            <input
              v-model.number="vipMonthlyYuan"
              type="number"
              min="0.01"
              step="0.01"
              class="w-full px-3.5 py-2.5 text-sm bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 tabular-nums"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1.5">年度 VIP（元）</label>
            <input
              v-model.number="vipYearlyYuan"
              type="number"
              min="0.01"
              step="0.01"
              class="w-full px-3.5 py-2.5 text-sm bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 tabular-nums"
            />
          </div>
        </div>
        <p v-if="vipPricingUpdatedAt" class="text-xs text-slate-400 mt-3">
          最近更新：{{ new Date(vipPricingUpdatedAt).toLocaleString('zh-CN') }}
        </p>
        <p v-if="vipPricingError" class="text-sm text-red-600 mt-3">{{ vipPricingError }}</p>
        <button
          type="button"
          :disabled="vipPricingSaving"
          class="mt-4 inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-60 rounded-xl transition-colors"
          @click="saveVipPricing"
        >
          <Loader2 v-if="vipPricingSaving" class="w-4 h-4 animate-spin" />
          <Check v-else class="w-4 h-4" />
          保存定价
        </button>
      </template>
    </div>

    <!-- Search -->
    <div class="flex items-center gap-3 mb-6">
      <div class="relative flex-1 max-w-md">
        <Search class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          v-model="keyword"
          type="text"
          placeholder="搜索手机号 / 昵称 / 邮箱"
          class="w-full pl-10 pr-4 py-2.5 text-sm bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400"
          @keyup.enter="handleSearch"
        />
      </div>
      <button
        @click="handleSearch"
        class="px-5 py-2.5 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 rounded-xl transition-colors"
      >
        搜索
      </button>
    </div>

    <!-- User Table -->
    <div class="bg-white border border-slate-200 rounded-2xl overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-slate-50/80 text-slate-500 text-left">
              <th class="px-5 py-3.5 font-medium">ID</th>
              <th class="px-5 py-3.5 font-medium">用户</th>
              <th class="px-5 py-3.5 font-medium">VIP</th>
              <th class="px-5 py-3.5 font-medium">VIP 到期</th>
              <th class="px-5 py-3.5 font-medium">AI 配额</th>
              <th class="px-5 py-3.5 font-medium">下载数</th>
              <th class="px-5 py-3.5 font-medium">AI 调用</th>
              <th class="px-5 py-3.5 font-medium">注册时间</th>
              <th class="px-5 py-3.5 font-medium">操作</th>
            </tr>
          </thead>
          <tbody v-if="loading">
            <tr>
              <td colspan="9" class="text-center py-16">
                <Loader2 class="w-6 h-6 text-violet-500 animate-spin mx-auto" />
              </td>
            </tr>
          </tbody>
          <tbody v-else class="divide-y divide-slate-100">
            <tr v-for="u in users" :key="u.id" class="hover:bg-slate-50/50 transition-colors">
              <td class="px-5 py-4 text-slate-400 tabular-nums">{{ u.id }}</td>
              <td class="px-5 py-4">
                <div class="flex flex-col">
                  <span class="font-medium text-slate-800">
                    {{ u.nickname || '未命名' }}
                    <span v-if="u.is_admin" class="text-[10px] px-1.5 py-0.5 rounded bg-violet-100 text-violet-700 ml-1">管理员</span>
                  </span>
                  <span class="text-xs text-slate-400 mt-0.5">{{ u.phone || u.google_email || '-' }}</span>
                </div>
              </td>
              <td class="px-5 py-4">
                <span
                  :class="u.is_vip
                    ? 'bg-amber-100 text-amber-700 border-amber-200'
                    : 'bg-slate-100 text-slate-400 border-slate-200'"
                  class="inline-block px-2.5 py-1 text-xs font-medium rounded-full border"
                >
                  {{ u.is_vip ? 'VIP' : '普通' }}
                </span>
              </td>
              <td class="px-5 py-4 text-xs">
                <template v-if="!u.is_vip">
                  <span class="text-slate-300">—</span>
                </template>
                <template v-else-if="!u.vip_expire_at">
                  <span class="text-slate-500">未设置</span>
                </template>
                <template v-else>
                  <div
                    :class="isVipExpireInPast(u.vip_expire_at) ? 'text-red-600' : 'text-slate-700'"
                    class="leading-snug"
                  >
                    {{ formatVipExpireAt(u.vip_expire_at) }}
                  </div>
                  <span
                    v-if="isVipExpireInPast(u.vip_expire_at)"
                    class="inline-block mt-0.5 text-[10px] font-medium text-red-500"
                  >
                    已过期
                  </span>
                </template>
              </td>
              <td class="px-5 py-4 text-slate-700 tabular-nums">{{ u.ai_quota }}</td>
              <td class="px-5 py-4 text-slate-600 tabular-nums">{{ u.download_count }}</td>
              <td class="px-5 py-4 text-slate-600 tabular-nums">{{ u.ai_task_count }}</td>
              <td class="px-5 py-4 text-slate-400 text-xs">{{ formatDate(u.created_at) }}</td>
              <td class="px-5 py-4">
                <button
                  @click="openEdit(u)"
                  class="p-2 rounded-lg hover:bg-violet-50 text-slate-400 hover:text-violet-600 transition-colors"
                  title="编辑"
                >
                  <Pencil class="w-4 h-4" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="total > 20" class="flex items-center justify-between mt-6">
      <span class="text-sm text-slate-400">共 {{ total }} 位用户</span>
      <div class="flex items-center gap-2">
        <button
          :disabled="page <= 1"
          @click="loadUsers(page - 1)"
          class="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40 transition-colors"
        >
          <ChevronLeft class="w-4 h-4" />
        </button>
        <span class="text-sm text-slate-600 px-3 tabular-nums">{{ page }} / {{ totalPages }}</span>
        <button
          :disabled="page >= totalPages"
          @click="loadUsers(page + 1)"
          class="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40 transition-colors"
        >
          <ChevronRight class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Edit Modal -->
    <Teleport to="body">
      <div v-if="editModal && editUser" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="closeEdit" />
        <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
          <!-- Modal Header -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
            <h3 class="text-lg font-bold text-slate-900">编辑用户</h3>
            <button @click="closeEdit" class="p-1.5 rounded-lg hover:bg-slate-100 transition-colors">
              <X class="w-5 h-5 text-slate-400" />
            </button>
          </div>

          <!-- Modal Body -->
          <div class="px-6 py-5 space-y-5">
            <!-- User Info -->
            <div class="flex items-center gap-3 p-3 bg-slate-50 rounded-xl">
              <div class="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-bold text-sm">
                {{ (editUser.nickname || '用户')[0] }}
              </div>
              <div>
                <p class="font-medium text-slate-800">{{ editUser.nickname || '未命名' }}</p>
                <p class="text-xs text-slate-400">ID: {{ editUser.id }} · {{ editUser.phone || editUser.google_email }}</p>
              </div>
            </div>

            <!-- Nickname -->
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1.5">昵称</label>
              <input
                v-model="editForm.nickname"
                type="text"
                class="w-full px-3.5 py-2.5 text-sm bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400"
              />
            </div>

            <!-- VIP Toggle -->
            <div class="flex items-center justify-between">
              <label class="text-sm font-medium text-slate-700">VIP 会员</label>
              <button
                @click="editForm.is_vip = !editForm.is_vip"
                :class="editForm.is_vip ? 'bg-amber-500' : 'bg-slate-300'"
                class="relative w-11 h-6 rounded-full transition-colors"
              >
                <span
                  :class="editForm.is_vip ? 'translate-x-5' : 'translate-x-0.5'"
                  class="absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform"
                />
              </button>
            </div>

            <!-- VIP 到期 -->
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1.5">VIP 到期时间</label>
              <input
                v-model="editVipExpireLocal"
                type="datetime-local"
                class="w-full px-3.5 py-2.5 text-sm bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400"
              />
              <p class="text-[11px] text-slate-400 mt-1.5">留空保存将清空到期时间（未设置）</p>
            </div>

            <!-- AI Quota -->
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1.5">AI 配额</label>
              <input
                v-model.number="editForm.ai_quota"
                type="number"
                min="0"
                class="w-full px-3.5 py-2.5 text-sm bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400"
              />
            </div>

            <!-- Admin Toggle -->
            <div class="flex items-center justify-between">
              <label class="text-sm font-medium text-slate-700">管理员权限</label>
              <button
                @click="editForm.is_admin = !editForm.is_admin"
                :class="editForm.is_admin ? 'bg-violet-500' : 'bg-slate-300'"
                class="relative w-11 h-6 rounded-full transition-colors"
              >
                <span
                  :class="editForm.is_admin ? 'translate-x-5' : 'translate-x-0.5'"
                  class="absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform"
                />
              </button>
            </div>
          </div>

          <!-- Modal Footer -->
          <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-100 bg-slate-50/50">
            <button
              @click="closeEdit"
              class="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 transition-colors"
            >
              取消
            </button>
            <button
              @click="saveEdit"
              :disabled="saving"
              class="flex items-center gap-2 px-5 py-2 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 disabled:opacity-60 rounded-xl transition-colors"
            >
              <Loader2 v-if="saving" class="w-4 h-4 animate-spin" />
              <Check v-else class="w-4 h-4" />
              保存
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
