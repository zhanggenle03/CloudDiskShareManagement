/**
 * 工具函数
 */

// ── 预设颜色 ──
export const PRESET_COLORS = [
  '#4F6EF7', '#7B5EA7', '#EC4899', '#EF4444', '#F97316', '#F59E0B',
  '#10B981', '#06B6D4', '#3B82F6', '#8B5CF6', '#6366F1', '#14B8A6',
  '#84CC16', '#22C55E', '#0EA5E9', '#A855F7', '#D946EF', '#F43F5E',
  '#78716C', '#64748B', '#94A3B8', '#A3A3A3', '#737373', '#525252'
]

// ── HTML 转义 ──
export function escHtml(str) {
  if (!str) return ''
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

// ── 有效期样式 ──
export function getExpireClass(expire) {
  if (!expire) return 'unknown'
  if (expire === '永久有效') return 'permanent'
  if (expire === '已失效') return 'expired'
  if (expire.includes('后') || expire.includes('有效')) return 'expiring'
  return 'unknown'
}

// ── 获取平台信息 ──
export function getPlatformInfo(source) {
  const platform = source && source.includes(':') ? source.split(':')[0] : source
  return {
    platform,
    sourceClass: platform === 'baidu' ? 'baidu' : 'quark',
    sourceName: platform === 'baidu' ? '百度网盘' : '夸克网盘',
    sourceNameShort: platform === 'baidu' ? '百度' : '夸克'
  }
}

// ── 标签样式 ──
export function getTagStyle(tagName, tagColors) {
  const color = tagColors[tagName]
  if (!color) return { cls: 'no-color', style: '' }
  return { cls: 'has-color', style: `background:${color}18;color:${color};border:1px solid ${color}30;` }
}

// ── 格式化时间 ──
export function formatTime(timeStr) {
  if (!timeStr) return '--'
  return timeStr.replace(/\.\d+$/, '').slice(0, 16).replace('T', ' ')
}

// ── 复制到剪贴板 ──
export function copyToClipboard(text) {
  return navigator.clipboard.writeText(text)
}

// ── Toast 系统 ──
const toastListeners = []

export function onToast(listener) {
  toastListeners.push(listener)
  return () => {
    const idx = toastListeners.indexOf(listener)
    if (idx >= 0) toastListeners.splice(idx, 1)
  }
}

export function toast(msg, type = 'info') {
  toastListeners.forEach(fn => fn(msg, type))
}
