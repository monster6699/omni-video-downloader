/** 后端可能返回无时区的 ISO（存的是 UTC），按 UTC 解析再格式化为本地展示 */

function parseBackendDate(iso: string): Date {
  const s = iso.trim()
  if (/[zZ]$|[+-]\d{2}:?\d{2}$/.test(s)) return new Date(s)
  return new Date(s.includes('T') ? `${s}Z` : `${s.replace(' ', 'T')}Z`)
}

/** VIP 到期时间展示，例如：2026年3月25日 20:30 */
export function formatVipExpireAt(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = parseBackendDate(iso)
  if (Number.isNaN(d.getTime())) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(d)
}

const pad2 = (n: number) => n.toString().padStart(2, '0')

/** 供 `<input type="datetime-local">` 绑定（本地时区） */
export function toDatetimeLocalInputValue(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = parseBackendDate(iso)
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}T${pad2(d.getHours())}:${pad2(d.getMinutes())}`
}

/** VIP 到期是否早于当前时间（用于列表标红） */
export function isVipExpireInPast(iso: string | null | undefined): boolean {
  if (!iso) return false
  const d = parseBackendDate(iso)
  return !Number.isNaN(d.getTime()) && d.getTime() < Date.now()
}
