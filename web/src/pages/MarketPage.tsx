/** 行情页 — 左侧 K 线详情 + 右侧自选股 */
import { useParams } from 'react-router-dom'
import { useState, useEffect, useCallback } from 'react'
import WatchlistPanel from '../components/stock/WatchlistPanel'
import StockDetailPanel from '../components/stock/StockDetailPanel'

export default function MarketPage() {
  const { code: urlCode } = useParams()
  const [code, setCode] = useState(urlCode || '600584')
  const [wlRefresh, setWlRefresh] = useState(0)

  useEffect(() => {
    if (urlCode) setCode(urlCode)
  }, [urlCode])

  const handleWatchlistChange = useCallback(() => {
    setWlRefresh((k) => k + 1)
  }, [])

  return (
    <div style={{ display: 'flex', gap: 16, height: '100%' }}>
      {/* 左侧：指标卡片 + K 线图（复用 StockDetailPanel） */}
      <StockDetailPanel code={code} onWatchlistChange={handleWatchlistChange} />

      {/* 右侧：自选股面板 */}
      <WatchlistPanel refreshKey={wlRefresh} />
    </div>
  )
}
