/** 止盈止损卡片 — 展示 AI 建议的止盈/止损/成本价格 */
import { colors, fonts } from '../../../theme/tokens'

interface Props {
  data: Record<string, any>
}

export default function SetTpSlCard({ data }: Props) {
  const d = data
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
}
