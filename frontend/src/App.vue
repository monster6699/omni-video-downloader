<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NMessageProvider } from 'naive-ui'
import {
  Play,
  Crown,
  LogOut,
  LogIn,
  ChevronDown,
  Download,
  Shield,
  BookOpen,
  House,
  Tags,
} from 'lucide-vue-next'
import LoginModal from './components/LoginModal.vue'
import VipModal from './components/VipModal.vue'
import { useAuth } from './composables/useAuth'

const router = useRouter()
const showLogin = ref(false)
const showVip = ref(false)
const showUserMenu = ref(false)
const { user, isLoggedIn, isVip, isAdmin, logout, restoreSession } = useAuth()

onMounted(() => {
  restoreSession()
})

function handleLogout() {
  logout()
  showUserMenu.value = false
  router.push('/')
}

function goHistory() {
  showUserMenu.value = false
  router.push('/history')
}

function goAdmin() {
  showUserMenu.value = false
  router.push('/admin')
}

function goHome() {
  router.push('/')
}
</script>

<template>
  <NMessageProvider>
    <div class="min-h-screen bg-slate-50 font-sans text-slate-900 pb-20 flex flex-col">
      <!-- 顶部导航栏 -->
      <nav class="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div class="flex items-center gap-2 cursor-pointer" @click="goHome">
            <div class="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
              <Play class="w-5 h-5 text-white fill-white" />
            </div>
            <span class="font-bold text-xl tracking-tight">OmniVideo</span>
            <span class="hidden sm:inline-block ml-2 text-xs font-medium px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-600 border border-indigo-100">
              万能视频下载
            </span>
          </div>
          
          <div class="hidden md:flex items-center gap-8 text-sm font-medium text-slate-600">
            <router-link
              to="/"
              class="hover:text-indigo-600 transition-colors inline-flex items-center gap-1.5"
              active-class="text-indigo-600 font-semibold"
            >
              <House class="w-3.5 h-3.5 shrink-0 opacity-90" stroke-width="2" />
              首页
            </router-link>
            <router-link
              to="/guide"
              class="hover:text-indigo-600 transition-colors inline-flex items-center gap-1.5"
              active-class="text-indigo-600 font-semibold"
            >
              <BookOpen class="w-3.5 h-3.5 shrink-0 opacity-90" stroke-width="2" />
              使用说明
            </router-link>
            <router-link
              v-if="isLoggedIn"
              to="/history"
              class="hover:text-indigo-600 transition-colors inline-flex items-center gap-1.5"
              active-class="text-indigo-600 font-semibold"
            >
              <Download class="w-3.5 h-3.5 shrink-0 opacity-90" stroke-width="2" />
              下载记录
            </router-link>
            <router-link
              v-if="isAdmin"
              to="/admin"
              class="hover:text-indigo-600 transition-colors inline-flex items-center gap-1.5"
              active-class="text-indigo-600 font-semibold"
            >
              <Shield class="w-3.5 h-3.5 shrink-0 opacity-90" stroke-width="2" />
              管理后台
            </router-link>
          </div>

          <div class="flex items-center gap-3 sm:gap-4">
            <router-link
              to="/"
              class="md:hidden inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-indigo-600"
            >
              <House class="w-3.5 h-3.5 shrink-0" stroke-width="2" />
              首页
            </router-link>
            <router-link
              to="/guide"
              class="md:hidden inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-indigo-600"
            >
              <BookOpen class="w-3.5 h-3.5 shrink-0" stroke-width="2" />
              说明
            </router-link>
            <!-- 未登录 -->
            <template v-if="!isLoggedIn">
              <button
                type="button"
                @click="showLogin = true"
                class="text-sm font-medium text-slate-600 hover:text-indigo-600 transition-colors inline-flex items-center gap-1.5"
              >
                <LogIn class="w-3.5 h-3.5 shrink-0" stroke-width="2" />
                登录 / 注册
              </button>
            </template>

            <!-- 已登录 -->
            <template v-else>
              <div class="relative">
                <button
                  @click="showUserMenu = !showUserMenu"
                  class="flex items-center gap-2 text-sm font-medium text-slate-700 hover:text-indigo-600 transition-colors"
                >
                  <div class="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-bold text-xs overflow-hidden">
                    <img v-if="user?.avatar_url" :src="user.avatar_url" class="w-full h-full object-cover" />
                    <span v-else>{{ (user?.nickname || '用户')[0] }}</span>
                  </div>
                  <span class="max-w-[80px] truncate">{{ user?.nickname || user?.phone }}</span>
                  <span v-if="isVip" class="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-gradient-to-r from-amber-400 to-orange-400 text-white leading-none">VIP</span>
                  <ChevronDown class="w-3.5 h-3.5 text-slate-400" />
                </button>
                <!-- 下拉菜单 -->
                <div
                  v-if="showUserMenu"
                  class="absolute right-0 top-full mt-2 w-48 bg-white rounded-xl shadow-lg border border-slate-200 py-1 z-50"
                >
                  <div class="px-4 py-2.5 border-b border-slate-100">
                    <p class="text-sm font-medium text-slate-800 truncate">{{ user?.nickname }}</p>
                    <p class="text-xs text-slate-400 truncate">{{ user?.phone || user?.google_email }}</p>
                  </div>
                  <button
                    @click="goHistory"
                    class="w-full px-4 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2 transition-colors md:hidden"
                  >
                    <Download class="w-4 h-4" />
                    下载记录
                  </button>
                  <button
                    v-if="isAdmin"
                    @click="goAdmin"
                    class="w-full px-4 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2 transition-colors md:hidden"
                  >
                    <Shield class="w-4 h-4" />
                    管理后台
                  </button>
                  <button
                    @click="handleLogout"
                    class="w-full px-4 py-2.5 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2 transition-colors border-t border-slate-100"
                  >
                    <LogOut class="w-4 h-4" />
                    退出登录
                  </button>
                </div>
              </div>
            </template>

            <button
              type="button"
              @click="isLoggedIn ? showVip = true : showLogin = true"
              class="flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-full bg-gradient-to-r from-amber-100 to-orange-100 text-amber-900 hover:from-amber-200 hover:to-orange-200 transition-all border border-amber-200 shadow-sm"
            >
              <Crown class="w-4 h-4 shrink-0" stroke-width="2" />
              <span class="leading-none">{{ isLoggedIn ? (isVip ? 'VIP 套餐' : '开通 VIP') : '开通 VIP' }}</span>
            </button>
            <router-link
              to="/pricing"
              class="hidden md:inline-flex items-center gap-1 text-xs font-medium text-amber-700 hover:text-amber-900 transition-colors"
            >
              <Tags class="w-3.5 h-3.5 shrink-0" stroke-width="2" />
              {{ isLoggedIn && isVip ? '套餐与续费' : '查看方案' }}
            </router-link>
          </div>
        </div>
      </nav>

      <!-- Main -->
      <main class="flex-1">
        <router-view />
      </main>

      <LoginModal v-model:show="showLogin" />
      <VipModal v-model:show="showVip" />

      <!-- 点击其他区域关闭用户菜单 -->
      <div v-if="showUserMenu" class="fixed inset-0 z-40" @click="showUserMenu = false"></div>
    </div>
  </NMessageProvider>
</template>
