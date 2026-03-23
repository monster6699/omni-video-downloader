<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onUnmounted, computed } from 'vue'
import { X, User, Eye, EyeOff, Loader2 } from 'lucide-vue-next'
import { useMessage } from 'naive-ui'
import { login, register, googleLogin } from '../api/auth'
import { useAuth } from '../composables/useAuth'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void
}>()

const message = useMessage()
const { setUser } = useAuth()

const mode = ref<'login' | 'register'>('login')
const phone = ref('')
const password = ref('')
const nickname = ref('')
const submitting = ref(false)
const agreed = ref(false)

const mousePos = ref({ x: 0, y: 0 })
const focusedField = ref<'phone' | 'password' | 'nickname' | null>(null)
const showPassword = ref(false)

const handleMouseMove = (e: MouseEvent) => {
  if (!props.show) return
  const x = (e.clientX / window.innerWidth) * 2 - 1
  const y = (e.clientY / window.innerHeight) * 2 - 1
  mousePos.value = { x, y }
}

onMounted(() => {
  window.addEventListener('mousemove', handleMouseMove)
})

onUnmounted(() => {
  window.removeEventListener('mousemove', handleMouseMove)
})

const activePos = computed(() => {
  if (focusedField.value === 'phone' || focusedField.value === 'nickname') {
    return { x: 0.7, y: -0.3 }
  } else if (focusedField.value === 'password') {
    return { x: -0.8, y: 0.15 }
  }
  return mousePos.value
})

function close() {
  emit('update:show', false)
}

async function handleSubmit() {
  if (!phone.value.trim()) {
    message.warning('请输入手机号')
    return
  }
  if (!password.value.trim() || password.value.length < 6) {
    message.warning('密码至少 6 位')
    return
  }
  if (!agreed.value) {
    message.warning('请先同意用户协议')
    return
  }

  submitting.value = true
  try {
    const res =
      mode.value === 'login'
        ? await login(phone.value, password.value)
        : await register(phone.value, password.value, nickname.value || undefined)

    setUser(res.user, res.access_token)
    message.success(mode.value === 'login' ? '登录成功' : '注册成功')
    close()
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err.message || '操作失败'
    message.error(detail)
  } finally {
    submitting.value = false
  }
}

async function handleGoogleLogin(response: any) {
  const idToken = response.credential
  if (!idToken) return
  submitting.value = true
  try {
    const res = await googleLogin(idToken)
    setUser(res.user, res.access_token)
    message.success('Google 登录成功')
    close()
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err.message || 'Google 登录失败'
    message.error(detail)
  } finally {
    submitting.value = false
  }
}

const GOOGLE_CLIENT_ID = '974412240771-t3e4fa0r3jj969dr2jb6i69mq1fqoa18.apps.googleusercontent.com'
const googleBtnRef = ref<HTMLElement | null>(null)

function renderGoogleButton() {
  const g = (window as any).google
  if (!g?.accounts?.id || !googleBtnRef.value) return
  g.accounts.id.initialize({
    client_id: GOOGLE_CLIENT_ID,
    callback: handleGoogleLogin,
  })
  g.accounts.id.renderButton(googleBtnRef.value, {
    theme: 'outline',
    size: 'large',
    width: googleBtnRef.value.offsetWidth,
    text: 'continue_with',
    shape: 'rectangular',
    logo_alignment: 'center',
  })
}

watch(() => props.show, async (val) => {
  if (val) {
    await nextTick()
    renderGoogleButton()
  }
})
</script>

<template>
  <div v-if="show" class="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 font-sans text-slate-900 transition-opacity">
    <div class="absolute inset-0" @click="close"></div>
    
    <div class="w-full max-w-[900px] max-h-[90vh] bg-white rounded-2xl shadow-2xl flex overflow-hidden relative z-10 animate-in fade-in zoom-in-95 duration-300">
      
      <!-- 左侧：互动插画区域 -->
      <div class="w-[45%] min-h-0 bg-[#F5F7F9] relative overflow-hidden hidden md:flex items-end justify-center pointer-events-none flex-shrink-0">
        <div class="absolute bottom-16 w-full h-[1px] bg-transparent"></div>

        <!-- 1. 紫色小怪兽 -->
        <div class="absolute bottom-16 left-[15%] z-10 breathe-1">
          <div 
            class="w-[100px] h-[220px] bg-[#6B38FB] rounded-t-xl flex flex-col items-center pt-8 jelly-body origin-bottom"
            :style="{ transform: `translateX(${activePos.x * 6}px) skewX(${-activePos.x * 12}deg)` }"
          >
            <div class="flex gap-4 blink-1">
              <div class="w-[14px] h-[14px] bg-white rounded-full flex items-center justify-center overflow-hidden">
                <div 
                  class="w-[6px] h-[6px] bg-black rounded-full jelly-eye"
                  :style="{ transform: `translate(${activePos.x * 4}px, ${activePos.y * 4}px)` }"
                ></div>
              </div>
              <div class="w-[14px] h-[14px] bg-white rounded-full flex items-center justify-center overflow-hidden">
                <div 
                  class="w-[6px] h-[6px] bg-black rounded-full jelly-eye"
                  :style="{ transform: `translate(${activePos.x * 4}px, ${activePos.y * 4}px)` }"
                ></div>
              </div>
            </div>
            <div class="relative w-4 h-3 mt-4">
              <div :class="`absolute inset-0 border-b-[2.5px] border-white rounded-b-full jelly-eye ${focusedField === 'password' ? 'opacity-0 scale-50' : 'opacity-100 scale-100'}`"></div>
              <div :class="`absolute top-1/2 left-0 w-full h-[2.5px] bg-white/90 rounded-full jelly-eye -translate-y-1/2 ${focusedField === 'password' ? 'opacity-100 scale-100' : 'opacity-0 scale-50'}`"></div>
            </div>
          </div>
        </div>

        <!-- 2. 橙色小怪兽 -->
        <div class="absolute bottom-16 left-[-5%] z-20 breathe-2">
          <div 
            class="w-[180px] h-[100px] bg-[#FF7124] rounded-t-[100px] flex flex-col items-center pt-6 jelly-body origin-bottom"
            :style="{ transform: `translateX(${activePos.x * 12}px) skewX(${-activePos.x * 15}deg)` }"
          >
            <div :class="`flex gap-6 ${focusedField === 'password' ? '' : 'blink-2'}`">
              <div 
                class="bg-black rounded-full jelly-eye"
                :style="{ 
                  width: focusedField === 'password' ? '14px' : '10px',
                  height: focusedField === 'password' ? '2.5px' : '10px',
                  transform: `translate(${activePos.x * 5}px, ${activePos.y * 5}px)`
                }"
              ></div>
              <div 
                class="bg-black rounded-full jelly-eye"
                :style="{ 
                  width: focusedField === 'password' ? '14px' : '10px',
                  height: focusedField === 'password' ? '2.5px' : '10px',
                  transform: `translate(${activePos.x * 5}px, ${activePos.y * 5}px)`
                }"
              ></div>
            </div>
            <div class="mt-4 w-6 h-3 bg-black rounded-b-full jelly-eye"></div>
          </div>
        </div>

        <!-- 3. 黑色小怪兽 -->
        <div class="absolute bottom-16 right-[35%] z-10 breathe-3">
          <div 
            class="w-[60px] h-[160px] bg-[#1A1A1A] rounded-t-xl flex flex-col items-center pt-8 jelly-body origin-bottom"
            :style="{ transform: `translateX(${activePos.x * 4}px) skewX(${-activePos.x * 18}deg)` }"
          >
            <div class="flex gap-2 blink-3">
              <div class="w-[12px] h-[12px] bg-white rounded-full flex items-center justify-center overflow-hidden">
                <div 
                  class="w-[5px] h-[5px] bg-black rounded-full jelly-eye"
                  :style="{ transform: `translate(${activePos.x * 3}px, ${activePos.y * 3}px)` }"
                ></div>
              </div>
              <div class="w-[12px] h-[12px] bg-white rounded-full flex items-center justify-center overflow-hidden">
                <div 
                  class="w-[5px] h-[5px] bg-black rounded-full jelly-eye"
                  :style="{ transform: `translate(${activePos.x * 3}px, ${activePos.y * 3}px)` }"
                ></div>
              </div>
            </div>
            <div class="mt-3 w-3 h-1.5 border-t-[2.5px] border-white/90 rounded-t-full"></div>
          </div>
        </div>

        <!-- 4. 黄色小怪兽 -->
        <div class="absolute bottom-16 right-[10%] z-20 breathe-4">
          <div 
            class="w-[100px] h-[140px] bg-[#EBB100] rounded-t-[60px] flex flex-col items-center pt-8 jelly-body origin-bottom"
            :style="{ transform: `translateX(${activePos.x * 10}px) skewX(${-activePos.x * 10}deg)` }"
          >
            <div class="flex gap-3 blink-4">
              <div class="w-[12px] h-[12px] bg-white rounded-full flex items-center justify-center overflow-hidden">
                <div 
                  class="w-[5px] h-[5px] bg-black rounded-full jelly-eye"
                  :style="{ transform: `translate(${activePos.x * 4}px, ${activePos.y * 4}px)` }"
                ></div>
              </div>
              <div class="w-[12px] h-[12px] bg-white rounded-full flex items-center justify-center overflow-hidden">
                <div 
                  class="w-[5px] h-[5px] bg-black rounded-full jelly-eye"
                  :style="{ transform: `translate(${activePos.x * 4}px, ${activePos.y * 4}px)` }"
                ></div>
              </div>
            </div>
            <div class="mt-4 w-6 h-[3px] bg-black/90 rounded-full"></div>
          </div>
        </div>
      </div>

      <!-- 右侧：表单区域 -->
      <div class="w-full md:w-[55%] flex flex-col overflow-hidden">
        <button @click="close" class="absolute top-4 right-4 z-10 text-slate-400 hover:text-slate-600 transition-colors">
          <X class="w-5 h-5" />
        </button>

        <!-- 滚动区域：flex-1 + overflow-y-auto 即可滚动 -->
        <div class="flex-1 min-h-0 overflow-y-auto p-6 lg:p-8">

          <div class="mb-6">
            <h1 class="text-2xl font-bold text-slate-900 mb-1">
              {{ mode === 'login' ? '欢迎回来' : '创建账号' }}
            </h1>
            <p class="text-slate-500 text-sm">
              {{ mode === 'login' ? '登录以使用完整功能' : '注册后即可体验全部功能' }}
            </p>
          </div>

          <div class="flex bg-slate-50 p-1 rounded-xl mb-5">
            <button
              type="button"
              :class="[
                'flex-1 flex items-center justify-center gap-2 py-2.5 font-medium text-sm rounded-lg transition-all',
                mode === 'login'
                  ? 'bg-white text-indigo-900 shadow-sm border border-indigo-100'
                  : 'text-slate-500 hover:text-slate-700',
              ]"
              @click="mode = 'login'"
            >
              <User class="w-4 h-4" :class="mode === 'login' ? 'text-indigo-600' : ''" />
              登录
            </button>
            <button
              type="button"
              :class="[
                'flex-1 flex items-center justify-center gap-2 py-2.5 font-medium text-sm rounded-lg transition-all',
                mode === 'register'
                  ? 'bg-white text-indigo-900 shadow-sm border border-indigo-100'
                  : 'text-slate-500 hover:text-slate-700',
              ]"
              @click="mode = 'register'"
            >
              注册
            </button>
          </div>

          <form @submit.prevent="handleSubmit" class="space-y-4">
          <!-- 昵称（仅注册） -->
          <div v-if="mode === 'register'">
            <label class="block text-sm font-medium text-slate-700 mb-1.5">昵称（选填）</label>
            <input
              v-model="nickname"
              type="text"
              placeholder="给自己起个名字"
              @focus="focusedField = 'nickname'"
              @blur="focusedField = null"
              class="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/25 focus:border-indigo-500 transition-all placeholder-slate-400 text-sm"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1.5">手机号</label>
            <input
              v-model="phone"
              type="text"
              placeholder="请输入手机号"
              @focus="focusedField = 'phone'"
              @blur="focusedField = null"
              class="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/25 focus:border-indigo-500 transition-all placeholder-slate-400 text-sm"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1.5">密码</label>
            <div class="relative">
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                placeholder="请输入密码（至少 6 位）"
                @focus="focusedField = 'password'"
                @blur="focusedField = null"
                class="w-full pl-4 pr-12 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/25 focus:border-indigo-500 transition-all placeholder-slate-400 text-sm"
              />
              <button 
                type="button"
                @click="showPassword = !showPassword"
                class="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
              >
                <EyeOff v-if="showPassword" class="w-4 h-4" />
                <Eye v-else class="w-4 h-4" />
              </button>
            </div>
          </div>

          <div v-if="mode === 'login'" class="flex items-center justify-end">
            <a href="#" class="text-sm text-slate-500 hover:text-slate-700">忘记密码？</a>
          </div>

          <button
            type="submit"
            :disabled="submitting"
            class="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-medium py-3.5 rounded-xl transition-colors shadow-sm flex items-center justify-center gap-2"
          >
            <Loader2 v-if="submitting" class="w-4 h-4 animate-spin" />
            {{ submitting ? '处理中...' : mode === 'login' ? '登录' : '注册' }}
          </button>

          <div class="flex items-center gap-4 my-2">
            <div class="flex-1 h-px bg-slate-200"></div>
            <span class="text-xs text-slate-400">或</span>
            <div class="flex-1 h-px bg-slate-200"></div>
          </div>

          <!-- Google 登录按钮（由 GIS SDK 动态渲染） -->
          <div ref="googleBtnRef" class="w-full flex justify-center"></div>

          <label class="mt-auto flex items-center justify-center gap-2 pt-2 cursor-pointer select-none">
            <input
              v-model="agreed"
              type="checkbox"
              class="w-4 h-4 rounded accent-indigo-600 cursor-pointer"
            />
            <span class="text-xs text-slate-500">
              我已阅读并同意 <a href="#" class="text-indigo-600 hover:underline">《用户服务协议》</a> 和 <a href="#" class="text-indigo-600 hover:underline">《隐私政策》</a>
            </span>
          </label>
        </form>

        </div><!-- /scroll -->

      </div><!-- /右侧表单 -->
    </div><!-- /main card -->
  </div><!-- /overlay -->
</template>

<style scoped>
.jelly-body {
  transition: transform 0.45s cubic-bezier(0.25, 1.2, 0.5, 1);
}
.jelly-eye {
  transition: all 0.35s cubic-bezier(0.25, 1.2, 0.5, 1);
}
.breathe-1 { animation: breathe 3.2s ease-in-out infinite; transform-origin: bottom; }
.breathe-2 { animation: breathe 4.0s ease-in-out infinite 0.5s; transform-origin: bottom; }
.breathe-3 { animation: breathe 3.5s ease-in-out infinite 1.0s; transform-origin: bottom; }
.breathe-4 { animation: breathe 4.2s ease-in-out infinite 1.5s; transform-origin: bottom; }
@keyframes breathe {
  0%, 100% { transform: scaleY(1) translateY(0); }
  50% { transform: scaleY(0.98) translateY(2px); }
}

.blink-1 { animation: blink 4.5s infinite 0s; transform-origin: center; }
.blink-2 { animation: blink 5.5s infinite 1.2s; transform-origin: center; }
.blink-3 { animation: blink 3.2s infinite 2.5s; transform-origin: center; }
.blink-4 { animation: double-blink 6s infinite 0.8s; transform-origin: center; }

@keyframes blink {
  0%, 94%, 100% { transform: scaleY(1); }
  97% { transform: scaleY(0.05); }
}
@keyframes double-blink {
  0%, 88%, 100% { transform: scaleY(1); }
  91%, 97% { transform: scaleY(0.05); }
  94% { transform: scaleY(1); }
}
</style>
