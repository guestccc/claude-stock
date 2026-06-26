/** Action 执行卡片 — 通过注册表路由到对应卡片组件 */
import { useState } from 'react'
import { colors, fonts } from '../../theme/tokens'
import { executeAction } from '../../api/chat'
import { getActionEntry } from './actions/registry'
import type { ChatAction } from '../../types/chat'

interface Props {
  action: ChatAction
  onExecuted?: (action: ChatAction, result: { success: boolean; message: string; data?: any }) => void
}

export default function ActionCard({ action, onExecuted }: Props) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null)

  const handleExecute = async () => {
    setLoading(true)
    try {
      const res = await executeAction(action.type, action.data)
      setResult({ success: res.success, message: res.message })
      onExecuted?.(action, res)
    } catch (err: any) {
      setResult({ success: false, message: `执行失败: ${err.message}` })
    } finally {
      setLoading(false)
    }
  }

  // 从注册表获取对应的卡片组件
  const entry = getActionEntry(action.type)
  const CardComponent = entry.card

  return (
    <div
      style={{
        background: colors.bgHover,
        border: `1px solid ${colors.border}`,
        borderRadius: 8,
        padding: 12,
        marginTop: 10,
        fontFamily: fonts.mono,
      }}
    >
      <CardComponent data={action.data} />

      {!result ? (
        <div style={{ display: 'flex', gap: 8, marginTop: 10, justifyContent: 'flex-end' }}>
          <button
            onClick={handleExecute}
            disabled={loading}
            style={{
              padding: '5px 14px',
              fontSize: 12,
              borderRadius: 4,
              border: 'none',
              background: colors.accent,
              color: '#fff',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.6 : 1,
              fontFamily: fonts.mono,
            }}
          >
            {loading ? '执行中...' : '确认执行'}
          </button>
        </div>
      ) : (
        <div
          style={{
            marginTop: 10,
            padding: '6px 10px',
            borderRadius: 4,
            fontSize: 12,
            background: result.success ? '#0d1a0d' : '#1a0d0d',
            color: result.success ? colors.fall : colors.rise,
            border: `1px solid ${result.success ? colors.fall : colors.rise}`,
          }}
        >
          {result.message}
        </div>
      )}
    </div>
  )
}
