/** 色彩 Token — 纯黑终端风格
 *
 * 【颜色规范 — A股红涨绿跌，全 App 强制执行】
 *
 *   正数（涨/盈）→ 红色  rise
 *   负数（跌/亏）→ 绿色  fall
 *
 * 实现：changeColor(v)  > 0 ? red : green
 * 禁止：任何页面自行写颜色逻辑，全部调用 changeColor()
 *
 * 为什么用 rise/fall 命名而非 up/down？
 *   rise = 红（涨），fall = 绿（跌）— 描述动作，不描述方向
 *   这样 ai 和人类都容易记住：涨=红，跌=绿
 *
 * 色值：
 *   rise = #e06666  红色（涨、盈、正收益）
 *   fall = #5cb85c  绿色（跌、亏、负收益）
 */
export const colors = {
  bg: '#000000',
  bgSecondary: '#2d2d2d',
  bgHover: '#1a1a1a',
  bgCard: '#2d2d2d',

  textPrimary: '#e5e7eb',
  textSecondary: '#c4c9d4',
  textMuted: '#7a8099',
  textLabel: '#6b7280',

  accent: '#7aa4f5',
  accentBg: '#1a2d5c',

  // A股红涨绿跌
  rise: '#e06666',      // 正数 → 红色（涨）
  riseBg: '#1a0d0d',
  fall: '#5cb85c',       // 负数 → 绿色（跌）
  fallBg: '#0d1a0d',

  watch: '#7aa4f5',
  watchBg: '#0d1420',

  border: '#1a1a1a',
  progress: '#4a6fa5',
} as const

/** 字体 */
export const fonts = {
  mono: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace",
} as const

// ---------- 全局颜色工具函数 ----------
// changeColor: A股红涨绿跌 — 全 App 唯一颜色逻辑
export function changeColor(v: number | null): string {
  if (v == null) return colors.textMuted
  return v >= 0 ? colors.rise : colors.fall
}

export function changeSign(v: number | null): string {
  if (v == null) return '-'
  return (v >= 0 ? '+' : '') + v.toFixed(2) + '%'
}

export function changeSignRaw(v: number | null, decimals = 2): string {
  if (v == null) return '-'
  return (v >= 0 ? '+' : '') + v.toFixed(decimals)
}
