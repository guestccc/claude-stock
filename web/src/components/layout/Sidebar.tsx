/** 侧边栏 — 56px 图标导航栏 */
import { NavLink } from 'react-router-dom'
import { colors } from '../../theme/tokens'

const navItems = [
  { path: '/market', label: '行情', icon: '📊' },
  { path: '/screener', label: '选股', icon: '🔍' },
  { path: '/backtest', label: '回测', icon: '📈' },
  { path: '/portfolio', label: '持仓', icon: '💼' },
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
    fontSize: 16,
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
