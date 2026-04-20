/** 股票详情面板 — 指标卡 + K线图（从 MarketPage 提取，供复用） */
import { useState, useEffect, useCallback } from 'react'
import { colors } from '../../theme/tokens'
import { getDaily, type DailyBar } from '../../api/market'
import { getWatchlist, addWatchlist, removeWatchlist } from '../../api/watchlist'
import KlineChart from '../charts/KlineChart'

interface Props {
  code: string
  /** 自选股变更回调，通知父组件刷新 WatchlistPanel */
  onWatchlistChange?: () => void
}

export default function StockDetailPanel({ code, onWatchlistChange }: Props) {
  const [name, setName] = useState('')
  const [allData, setAllData] = useState<DailyBar[]>([])
  const [loading, setLoading] = useState(false)
  const [hasMore, setHasMore] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)

  // 自选股状态
  const [inList, setInList] = useState(false)
  const [watchlistId, setWatchlistId] = useState<number | null>(null)

  // 首次加载：拉最近 500 条（约 2 年）
  useEffect(() => {
    if (!code) return
    let cancelled = false
    setLoading(true)
    setAllData([])
    setHasMore(true)
    getDaily(code, { limit: 500 })
      .then((res) => {
        if (!cancelled) {
          setAllData(res.data)
          setHasMore(res.data.length === 500)
          setName(res.name)
        }
      })
      .catch(() => { if (!cancelled) setAllData([]) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [code])

  // 加载更早数据（滚动到最左侧触发）
  const handleLoadMore = useCallback(async () => {
    if (!hasMore || isLoadingMore || allData.length === 0) return
    setIsLoadingMore(true)
    const earliestDate = allData[0].date
    try {
      const res = await getDaily(code, { end: earliestDate, limit: 500 })
      // 后端 end 是 <=，过滤掉等于 earliestDate 的（避免重复）
      const newData = res.data.filter((d) => d.date < earliestDate)
      if (newData.length === 0) {
        setHasMore(false)
      } else {
        setAllData((prev) => [...newData, ...prev])
      }
    } catch {
      // ignore
    } finally {
      setIsLoadingMore(false)
    }
  }, [code, allData, hasMore, isLoadingMore])

  // 检查当前股票是否在自选股中
  const checkWatchlist = useCallback(async () => {
    if (!code) return
    try {
      const items = await getWatchlist()
      const found = items.find((i) => i.code === code)
      setInList(!!found)
      setWatchlistId(found ? found.id : null)
    } catch {
      // ignore
    }
  }, [code])

  useEffect(() => {
    checkWatchlist()
  }, [checkWatchlist])

  // 切换自选股
  const toggleWatchlist = async () => {
    try {
      if (inList && watchlistId != null) {
        await removeWatchlist(watchlistId)
      } else {
        await addWatchlist(code)
      }
      await checkWatchlist()
      onWatchlistChange?.()
    } catch {
      // ignore
    }
  }

  const latest = allData.length > 0 ? allData[allData.length - 1] : null
  const prev = allData.length > 1 ? allData[allData.length - 2] : null

  return (
    <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* 指标卡片 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
        <StatCard label="代码" value={`${code} ${name}`} accent extra={
          <button
            onClick={toggleWatchlist}
            title={inList ? '移出自选' : '加入自选'}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: 0,
              fontSize: 16,
              color: inList ? '#f5a742' : colors.textMuted,
              lineHeight: 1,
              transition: 'color 0.2s',
            }}
          >
            {inList ? '★' : '☆'}
          </button>
        } />
        <StatCard label="最新价" value={latest?.close?.toFixed(2) ?? '-'} />
        <ChangeCard pctChange={latest?.pct_change} close={latest?.close} prevClose={prev?.close} />
        <StatCard
          label="今开 / 昨收"
          value={latest ? `${latest.open?.toFixed(2) ?? '-'} / ${prev?.close?.toFixed(2) ?? '-'}` : '-'}
        />
        <StatCard
          label="最高 / 最低"
          value={latest ? `${latest.high?.toFixed(2) ?? '-'} / ${latest.low?.toFixed(2) ?? '-'}` : '-'}
        />
      </div>

      {/* K线图 */}
      {loading ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: colors.textMuted }}>
          加载中...
        </div>
      ) : allData.length > 0 ? (
        <KlineChart
          data={allData}
          height={580}
          onLoadMore={handleLoadMore}
          isLoadingMore={isLoadingMore}
          hasMore={hasMore}
        />
      ) : (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: colors.textMuted }}>
          点击左侧股票查看 K 线图
        </div>
      )}
    </div>
  )
}

// ---------- 子组件 ----------

function ChangeCard({ pctChange, close, prevClose }: {
  pctChange: number | null | undefined
  close: number | null | undefined
  prevClose: number | null | undefined
}) {
  const pct = pctChange ?? (close != null && prevClose ? ((close - prevClose) / prevClose) * 100 : null)
  const isUp = pct != null && pct >= 0
  const color = pct == null ? colors.textMuted : isUp ? '#e06666' : '#5cb85c'
  const text = pct != null ? `${isUp ? '+' : ''}${pct.toFixed(2)}%` : '-'
  return (
    <div style={{ background: colors.bgCard, borderRadius: 8, padding: 14 }}>
      <div style={{ fontSize: 10, color: colors.textLabel, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>涨跌幅</div>
      <div style={{ fontSize: 18, color, fontWeight: 700 }}>{text}</div>
    </div>
  )
}

function StatCard({ label, value, accent = false, extra }: {
  label: string
  value: string
  accent?: boolean
  extra?: React.ReactNode
}) {
  return (
    <div style={{
      background: accent ? colors.accentBg : colors.bgCard,
      borderRadius: 8,
      padding: 14,
      border: accent ? `1px solid ${colors.accent}` : '1px solid transparent',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <div style={{ fontSize: 10, color: accent ? colors.accent : colors.textLabel, textTransform: 'uppercase', letterSpacing: 0.5 }}>
          {label}
        </div>
        {extra}
      </div>
      <div style={{ fontSize: 18, color: accent ? colors.accent : colors.textPrimary, fontWeight: accent ? 700 : 600 }}>
        {value}
      </div>
    </div>
  )
}
