/** 持仓面板 — 右侧列表，点击切换股票 */
import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { colors, fonts, changeColor, changeSign } from '../../theme/tokens'
import {
  getHoldings,
  type HoldingItem,
  type HoldingSummary,
} from '../../api/portfolio'

const S = {
  panel: {
    width: 240,
    background: colors.bgCard,
    borderRadius: '0 0 8px 8px',
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden',
    alignSelf: 'flex-start',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 12px',
    borderBottom: `1px solid ${colors.bgHover}`,
  },
  title: {
    fontSize: 12,
    fontWeight: 600,
    color: colors.textSecondary,
    letterSpacing: 0.5,
  },
  count: {
    fontSize: 10,
    color: colors.textMuted,
  },
  list: {
    flex: 1,
    overflowY: 'auto' as const,
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 12px',
    cursor: 'pointer',
    transition: 'background 0.15s',
  },
  rowActive: {
    background: colors.accentBg,
  },
  codeText: {
    fontSize: 12,
    fontWeight: 600,
    color: colors.textSecondary,
    fontFamily: 'inherit',
  },
  nameText: {
    fontSize: 10,
    color: colors.textMuted,
    marginTop: 2,
  },
  priceText: {
    fontSize: 12,
    fontWeight: 600,
    fontFamily: 'inherit',
    textAlign: 'right' as const,
  },
  changeText: {
    fontSize: 10,
    textAlign: 'right' as const,
    marginTop: 2,
  },
  empty: {
    padding: '24px 12px',
    textAlign: 'center' as const,
    color: colors.textMuted,
    fontSize: 11,
  },
  summary: {
    padding: '10px 12px',
    borderTop: `1px solid ${colors.bgHover}`,
    fontSize: 10,
    color: colors.textMuted,
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
}

export default function HoldingsPanel() {
  const { code: currentCode } = useParams()
  const navigate = useNavigate()
  const [holdings, setHoldings] = useState<HoldingItem[]>([])
  const [summary, setSummary] = useState<HoldingSummary | null>(null)

  const loadData = useCallback(async () => {
    try {
      const data = await getHoldings()
      setHoldings(data.holdings)
      setSummary(data.summary)
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  return (
    <div style={S.panel}>
      <div style={S.header}>
        <span style={S.title}>持仓</span>
        <span style={S.count}>{holdings.length}只</span>
      </div>
      <div style={S.list}>
        {holdings.length === 0 ? (
          <div style={S.empty}>暂无持仓</div>
        ) : (
          holdings.map((h) => {
            const isActive = h.code === currentCode
            const profitPct = h.profit_pct
            return (
              <div
                key={h.code}
                style={{ ...S.row, ...(isActive ? S.rowActive : {}) }}
                onMouseEnter={(e) => {
                  if (!isActive) (e.currentTarget as HTMLElement).style.background = colors.bgHover
                }}
                onMouseLeave={(e) => {
                  if (!isActive) (e.currentTarget as HTMLElement).style.background = 'transparent'
                }}
                onClick={() => navigate(`/market/${h.code}`)}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={S.codeText}>{h.code}</div>
                  <div style={S.nameText}>{h.name}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  {h.current_price != null && (
                    <div style={{ ...S.priceText, color: changeColor(profitPct) }}>
                      {h.current_price.toFixed(2)}
                    </div>
                  )}
                  {profitPct != null && (
                    <div style={{ ...S.changeText, color: changeColor(profitPct) }}>
                      {changeSign(profitPct)}
                    </div>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>
      {summary && holdings.length > 0 && (
        <div style={S.summary}>
          <span>总市值 {(summary.total_market_value ?? 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })}</span>
          <span style={{ color: changeColor(summary.total_profit_pct) }}>
            {changeSign(summary.total_profit_pct)}
          </span>
        </div>
      )}
    </div>
  )
}
