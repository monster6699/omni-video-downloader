import { ref, computed } from 'vue'
import { getMe, type UserProfile } from '../api/auth'
import { formatVipExpireAt } from '../utils/format'

const user = ref<UserProfile | null>(null)
const loading = ref(false)

let _restorePromise: Promise<void> | null = null

export function useAuth() {
  const isLoggedIn = computed(() => !!user.value)
  const isVip = computed(
    () =>
      !!user.value?.is_vip &&
      (!user.value.vip_expire_at || new Date(user.value.vip_expire_at) > new Date()),
  )
  const isAdmin = computed(() => !!user.value?.is_admin)

  /** 供导航/定价页等展示，例如「有效期至 2026年3月25日 20:30」 */
  const vipExpireLabel = computed(() => {
    const u = user.value
    if (!u?.is_vip) return ''
    if (!u.vip_expire_at) return '会员权益已开通'
    const text = formatVipExpireAt(u.vip_expire_at)
    return text ? `有效期至 ${text}` : ''
  })

  function setUser(u: UserProfile, token: string) {
    user.value = u
    localStorage.setItem('token', token)
  }

  function logout() {
    user.value = null
    localStorage.removeItem('token')
  }

  async function tryRestoreSession() {
    const token = localStorage.getItem('token')
    if (!token || user.value) return
    loading.value = true
    try {
      user.value = await getMe()
    } catch {
      localStorage.removeItem('token')
      user.value = null
    } finally {
      loading.value = false
    }
  }

  function restoreSession() {
    if (!_restorePromise) {
      _restorePromise = tryRestoreSession()
    }
    return _restorePromise
  }

  async function waitForSession() {
    if (_restorePromise) await _restorePromise
  }

  return {
    user,
    loading,
    isLoggedIn,
    isVip,
    isAdmin,
    vipExpireLabel,
    setUser,
    logout,
    tryRestoreSession,
    restoreSession,
    waitForSession,
  }
}
