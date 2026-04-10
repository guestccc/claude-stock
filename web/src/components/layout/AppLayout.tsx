/** 应用布局 — 侧边栏 + 顶栏 + 内容区 */
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Topbar from './Topbar'
import { colors } from '../../theme/tokens'

const styles = {
  layout: {
    display: 'flex',
    height: '100vh',
  },
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden',
  },
  content: {
    flex: 1,
    padding: 16,
    overflowY: 'auto' as const,
    background: colors.bg,
  },
}

export default function AppLayout() {
  return (
    <div style={styles.layout}>
      <Sidebar />
      <div style={styles.main}>
        <Topbar />
        <div style={styles.content}>
          <Outlet />
        </div>
      </div>
    </div>
  )
}
