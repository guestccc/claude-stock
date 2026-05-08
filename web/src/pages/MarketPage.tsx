/** 行情页 — 左侧 K 线详情 + 右侧自选股/持仓 */
import { useParams } from 'react-router-dom'
import { useState, useEffect, useCallback } from 'react'
import WatchlistPanel from '../components/stock/WatchlistPanel'
import HoldingsPanel from '../components/stock/HoldingsPanel'
import StockDetailPanel from '../components/stock/StockDetailPanel'
import { colors, fonts } from '../theme/tokens'

type RightTab = 'watchlist' | 'holdings'

const tabItems: { key: RightTab; label: string }[] = [
  { key: 'watchlist', label: '自选股' },
  { key: 'holdings', label: '持仓' },
]

const S = {
  tabBar: {
    display: 'flex',
    background: colors.bgCard,
    borderRadius: '8px 8px 0 0',
    borderBottom: `1px solid ${colors.bgHover}`,
  },
  tab: (active: boolean) => ({
    flex: 1,
    padding: '8px 0',
    textAlign: 'center' as const,
    fontSize: 11,
    fontFamily: fonts.mono,
    fontWeight: 600,
    color: active ? colors.accent : colors.textMuted,
    cursor: 'pointer',
    borderBottom: active ? `2px solid ${colors.accent}` : '2px solid transparent',
    transition: 'color 0.15s, border-color 0.15s',
  }),
}

export default function MarketPage() {
  const { code: urlCode } = useParams()
  const [code, setCode] = useState(urlCode || '600584')
  const [wlRefresh, setWlRefresh] = useState(0)
  const [activeTab, setActiveTab] = useState<RightTab>('watchlist')

  useEffect(() => {
    if (urlCode) setCode(urlCode)
  }, [urlCode])

  const handleWatchlistChange = useCallback(() => {
    setWlRefresh((k) => k + 1)
  }, [])

  return (
    <div style={{ display: 'flex', gap: 16, height: '100%' }}>
      {/* 左侧：指标卡片 + K 线图 */}
      <StockDetailPanel code={code} onWatchlistChange={handleWatchlistChange} />

      {/* 右侧：自选股 / 持仓 Tab */}
      <div style={{ width: 240, alignSelf: 'flex-start', display: 'flex', flexDirection: 'column' }}>
        <div style={S.tabBar}>
          {tabItems.map((t) => (
            <div key={t.key} style={S.tab(activeTab === t.key)} onClick={() => setActiveTab(t.key)}>
              {t.label}
            </div>
          ))}
        </div>
        {activeTab === 'watchlist' ? (
          <WatchlistPanel refreshKey={wlRefresh} />
        ) : (
          <HoldingsPanel />
        )}
      </div>
    </div>
  )
}
