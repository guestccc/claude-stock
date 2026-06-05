/** Action 执行卡片 — 确认/取消 AI 建议的操作 */
import { useState } from 'react'
import { colors, fonts } from '../../theme/tokens'
import { executeAction } from '../../api/chat'
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

  // 根据 action 类型渲染不同的卡片内容
  const renderContent = () => {
    const d = action.data
    switch (action.type) {
      case 'set_tp_sl':
        return (
          <div>
            <div style={{ fontSize: 13, color: colors.textPrimary, fontWeight: 600, marginBottom: 8 }}>
              AI 建议设置止盈止损
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
              <div style={{ background: '#1a0d0d', border: `1px solid ${colors.rise}`, borderRadius: 6, padding: 8 }}>
                <div style={{ color: colors.textMuted, fontSize: 10 }}>止盈价</div>
                <div style={{ color: colors.rise, fontSize: 16, fontWeight: 700 }}>{d.tp_price}</div>
              </div>
              <div style={{ background: '#0d1a0d', border: `1px solid ${colors.fall}`, borderRadius: 6, padding: 8 }}>
                <div style={{ color: colors.textMuted, fontSize: 10 }}>止损价</div>
                <div style={{ color: colors.fall, fontSize: 16, fontWeight: 700 }}>{d.sl_price}</div>
              </div>
            </div>
            {d.strategy && (
              <div style={{ fontSize: 11, color: colors.textMuted, marginTop: 6 }}>
                策略: {d.strategy}
              </div>
            )}
          </div>
        )
      case 'add_watchlist':
        return (
          <div>
            <div style={{ fontSize: 13, color: colors.textPrimary, fontWeight: 600 }}>
              加入自选股: {d.stock_code}
            </div>
          </div>
        )
      default:
        return (
          <div>
            <div style={{ fontSize: 13, color: colors.textPrimary, fontWeight: 600 }}>
              动作: {action.type}
            </div>
            <pre style={{ fontSize: 11, color: colors.textMuted, marginTop: 4, overflow: 'auto' }}>
              {JSON.stringify(action.data, null, 2)}
            </pre>
          </div>
        )
    }
  }

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
      {renderContent()}

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
