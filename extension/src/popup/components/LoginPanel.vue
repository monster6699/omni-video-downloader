<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { login as apiLogin, getMe } from '../../shared/api'
import { setToken, setUser, getToken, clearAuth } from '../../shared/storage'
import type { UserProfile } from '../../shared/types'

const SITE_URL = 'http://localhost:5173'

const props = defineProps<{ user: UserProfile | null }>()
const emit = defineEmits<{ login: [user: UserProfile]; logout: [] }>()

const showPanel = ref(false)
const phone = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  if (!phone.value || !password.value) return
  loading.value = true; error.value = ''
  try {
    const res = await apiLogin(phone.value, password.value)
    await setToken(res.access_token)
    await setUser(res.user)
    emit('login', res.user)
    showPanel.value = false; phone.value = ''; password.value = ''
  } catch (e: unknown) { error.value = (e as Error).message || '登录失败' }
  finally { loading.value = false }
}

async function handleLogout() { await clearAuth(); emit('logout') }

function openRegister() { chrome.tabs.create({ url: SITE_URL }) }

onMounted(async () => {
  if (props.user) return
  const token = await getToken()
  if (!token) return
  try { const p = await getMe(); await setUser(p); emit('login', p) }
  catch { await clearAuth() }
})
</script>

<template>
  <div class="relative">
    <div v-if="user" class="flex items-center gap-2">
      <div class="flex items-center gap-1.5">
        <div class="w-6 h-6 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-bold text-[10px]">
          {{ (user.nickname || user.phone || '?')[0] }}
        </div>
        <span class="text-xs text-slate-600 max-w-15 truncate">{{ user.nickname || user.phone }}</span>
        <span v-if="user.is_vip" class="text-[9px] font-bold px-1 py-0.5 rounded-full bg-amber-100 text-amber-700 leading-none">VIP</span>
      </div>
      <button class="text-[10px] text-slate-400 hover:text-red-500 transition" @click="handleLogout">退出</button>
    </div>
    <button v-else class="text-xs font-medium text-slate-600 hover:text-indigo-600 transition flex items-center gap-1" @click="showPanel = !showPanel">
      <span>登录</span>
    </button>
    <div v-if="showPanel && !user" class="absolute right-0 top-full mt-2 w-72 bg-white border border-slate-200 rounded-2xl p-5 shadow-xl z-50">
      <h4 class="text-sm font-bold text-slate-900 mb-3">登录账号</h4>
      <div class="space-y-2.5">
        <input v-model="phone" type="tel" placeholder="手机号"
          class="w-full bg-slate-50 border border-slate-200 text-sm text-slate-900 rounded-xl px-3 py-2.5 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
          @keyup.enter="handleLogin" />
        <input v-model="password" type="password" placeholder="密码"
          class="w-full bg-slate-50 border border-slate-200 text-sm text-slate-900 rounded-xl px-3 py-2.5 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
          @keyup.enter="handleLogin" />
        <button class="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl transition disabled:opacity-50 shadow-sm"
          :disabled="loading" @click="handleLogin">{{ loading ? '登录中…' : '登录' }}</button>
        <p v-if="error" class="text-red-500 text-xs text-center">{{ error }}</p>
      </div>
      <div class="mt-3 pt-3 border-t border-slate-100 text-center">
        <button class="text-xs text-indigo-600 hover:text-indigo-700 font-medium transition" @click="openRegister">
          还没有账号？去网站注册 →
        </button>
      </div>
    </div>
  </div>
</template>
