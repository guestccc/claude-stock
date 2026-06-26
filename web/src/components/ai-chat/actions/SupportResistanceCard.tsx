/** 压力支撑位卡片 — 展示 AI 识别的压力位/支撑位 */
import { colors } from '../../../theme/tokens'

interface Props {
  data: Record<string, any>
}

export default function SupportResistanceCard({ data }: Props) {
  return (
    <div>
      <div style={{ fontSize: 13, color: colors.textPrimary, fontWeight: 600, marginBottom: 8 }}>
        AI 识别压力支撑位
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
        <div style={{ background: '#1a0d0d', border: `1px solid ${colors.rise}`, borderRadius: 6, padding: 8 }}>
          <div style={{ color: colors.textMuted, fontSize: 10 }}>压力位</div>
          <div style={{ color: colors.rise, fontSize: 16, fontWeight: 700 }}>{data.pressure_price}</div>
        </div>
        <div style={{ background: '#0d1a0d', border: `1px solid ${colors.fall}`, borderRadius: 6, padding: 8 }}>
          <div style={{ color: colors.textMuted, fontSize: 10 }}>支撑位</div>
          <div style={{ color: colors.fall, fontSize: 16, fontWeight: 700 }}>{data.support_price}</div>
        </div>
      </div>
      {data.reason && (
        <div style={{ fontSize: 11, color: colors.textMuted, marginTop: 6 }}>
          分析: {data.reason}
        </div>
      )}
    </div>
  )
}
