/** 加入自选股卡片 */
import { colors } from '../../../theme/tokens'

interface Props {
  data: Record<string, any>
}

export default function AddWatchlistCard({ data }: Props) {
  return (
    <div>
      <div style={{ fontSize: 13, color: colors.textPrimary, fontWeight: 600 }}>
        加入自选股: {data.stock_code}
      </div>
    </div>
  )
}
