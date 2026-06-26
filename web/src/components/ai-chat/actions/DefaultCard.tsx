/** 默认 Action 卡片 — 未注册 action 类型的兜底展示 */
import { colors } from '../../../theme/tokens'

interface Props {
  data: Record<string, any>
  /** 可选: action 类型名称 */
  type?: string
}

export default function DefaultCard({ data, type }: Props) {
  return (
    <div>
      <div style={{ fontSize: 13, color: colors.textPrimary, fontWeight: 600 }}>
        动作: {type || '未知'}
      </div>
      <pre style={{ fontSize: 11, color: colors.textMuted, marginTop: 4, overflow: 'auto' }}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  )
}
