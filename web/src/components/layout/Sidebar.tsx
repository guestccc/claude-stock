/** 侧边栏 — 56px 图标导航栏 */
import { NavLink } from 'react-router-dom'
import { colors } from '../../theme/tokens'

/** SVG 线条图标，与 style1-terminal demo 保持一致 */
const icons = {
  // 行情 — 折线图
  market: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  ),
  // 列表 — 表格
  stocks: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="8" y1="6" x2="21" y2="6" />
      <line x1="8" y1="12" x2="21" y2="12" />
      <line x1="8" y1="18" x2="21" y2="18" />
      <line x1="3" y1="6" x2="3.01" y2="6" />
      <line x1="3" y1="12" x2="3.01" y2="12" />
      <line x1="3" y1="18" x2="3.01" y2="18" />
    </svg>
  ),
  // 选股 — 放大镜
  screener: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="8" />
      <path d="M21 21l-4.35-4.35" />
    </svg>
  ),
  // 回测 — 柱状图
  backtest: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 3v18h18" />
      <path d="M18 17V9" />
      <path d="M13 17V5" />
      <path d="M8 17v-3" />
    </svg>
  ),
  // 持仓 — 公文包
  portfolio: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="2" y="7" width="20" height="14" rx="2" />
      <path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2" />
    </svg>
  ),
}

const navItems = [
  { path: '/market', label: '行情', icon: icons.market },
  { path: '/stocks', label: '列表', icon: icons.stocks },
  { path: '/screener', label: '选股', icon: icons.screener },
  { path: '/backtest', label: '回测', icon: icons.backtest },
  { path: '/portfolio', label: '持仓', icon: icons.portfolio },
]

const styles = {
  sidebar: {
    width: 56,
    background: colors.bgSecondary,
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    padding: '12px 0',
    gap: 4,
  },
  icon: {
    width: 36,
    height: 36,
    borderRadius: 8,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: colors.textMuted,
    transition: 'all 0.2s',
    textDecoration: 'none',
  },
  iconActive: {
    background: colors.accentBg,
    color: colors.accent,
  },
}

export default function Sidebar() {
  return (
    <div style={styles.sidebar}>
      {navItems.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          style={({ isActive }) => ({
            ...styles.icon,
            ...(isActive ? styles.iconActive : {}),
          })}
          title={item.label}
        >
          {item.icon}
        </NavLink>
      ))}
    </div>
  )
}
