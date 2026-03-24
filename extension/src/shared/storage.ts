const KEY_TOKEN = 'omni_token'
const KEY_USER = 'omni_user'

export async function getToken(): Promise<string | null> {
  try {
    const r = await chrome.storage.local.get(KEY_TOKEN)
    return r[KEY_TOKEN] || null
  } catch (e) {
    console.warn('[OmniDL] getToken failed:', e)
    return null
  }
}

export async function setToken(token: string): Promise<void> {
  await chrome.storage.local.set({ [KEY_TOKEN]: token })
  console.log('[OmniDL] token saved, length:', token.length)
}

export async function removeToken(): Promise<void> {
  await chrome.storage.local.remove(KEY_TOKEN)
}

export async function getUser(): Promise<unknown> {
  try {
    const r = await chrome.storage.local.get(KEY_USER)
    return r[KEY_USER] || null
  } catch {
    return null
  }
}

export async function setUser(user: unknown): Promise<void> {
  await chrome.storage.local.set({ [KEY_USER]: user })
}

export async function clearAuth(): Promise<void> {
  await chrome.storage.local.remove([KEY_TOKEN, KEY_USER])
  console.log('[OmniDL] auth cleared')
}
