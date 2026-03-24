/**
 * 与后端 parse 能力对齐：抖音除 /video/ 外还有精选/弹层 modal_id、短链等。
 */
export const VIDEO_URL_PATTERNS: RegExp[] = [
  /youtube\.com\/watch/,
  /youtu\.be\//,
  /bilibili\.com\/video/,
  /douyin\.com\/video\//,
  // 精选、关注流等：?modal_id= 或 &modal_id=
  /douyin\.com\/[^#]*[?&]modal_id=\d+/,
  /douyin\.com\/[^#]*[?&]aweme_id=\d+/,
  /v\.douyin\.com\//,
  /tiktok\.com\/@.+\/video/,
  /twitter\.com\/.+\/status/,
  /x\.com\/.+\/status/,
  /instagram\.com\/(p|reel)\//,
]

export function isLikelyVideoPageUrl(url: string): boolean {
  return VIDEO_URL_PATTERNS.some((p) => p.test(url))
}
