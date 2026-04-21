/** 侧边栏 — 图标+文字导航 */
import { NavLink } from 'react-router-dom'
import { colors, fonts } from '../../theme/tokens'

const icons = {
  market: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  ),
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
  screener: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="8" />
      <path d="M21 21l-4.35-4.35" />
    </svg>
  ),
  backtest: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 3v18h18" />
      <path d="M18 17V9" />
      <path d="M13 17V5" />
      <path d="M8 17v-3" />
    </svg>
  ),
  portfolio: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="2" y="7" width="20" height="14" rx="2" />
      <path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2" />
    </svg>
  ),
  fund: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
      <polyline points="16 7 22 7 22 13" />
    </svg>
  ),
}

const navItems = [
  { path: '/market', label: '行情', icon: icons.market },
  { path: '/stocks', label: '列表', icon: icons.stocks },
  { path: '/screener', label: '选股', icon: icons.screener },
  { path: '/backtest', label: '回测', icon: icons.backtest },
  { path: '/portfolio', label: '持仓', icon: icons.portfolio },
  { path: '/fund', label: '基金', icon: icons.fund },
]

const S = {
  sidebar: {
    width: 72,
    background: colors.bgSecondary,
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    padding: '12px 0',
    gap: 2,
  },
  item: {
    width: 64,
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 3,
    padding: '6px 4px',
    borderRadius: 8,
    cursor: 'pointer',
    transition: 'all 0.15s',
    textDecoration: 'none',
    color: colors.textMuted,
  },
  itemActive: {
    background: colors.accentBg,
    color: colors.accent,
  },
  label: {
    fontSize: 10,
    fontFamily: fonts.mono,
    lineHeight: 1,
  },
}

export default function Sidebar() {
  return (
    <div style={S.sidebar}>
      {navItems.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          style={({ isActive }) => ({
            ...S.item,
            ...(isActive ? S.itemActive : {}),
          })}
        >
          {item.icon}
          <span style={S.label}>{item.label}</span>
        </NavLink>
      ))}
    </div>
  )
}
