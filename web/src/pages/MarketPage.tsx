/** 行情页 */
import { useParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { colors } from '../theme/tokens'
import { getDaily, type DailyBar } from '../api/market'
import KlineChart from '../components/charts/KlineChart'

export default function MarketPage() {
  const { code: urlCode } = useParams()
  const [code, setCode] = useState(urlCode || '600584')
  const [name, setName] = useState('')
  const [dailyData, setDailyData] = useState<DailyBar[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (urlCode) setCode(urlCode)
  }, [urlCode])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getDaily(code, { limit: 120 })
      .then((res) => {
        if (!cancelled) {
          setDailyData(res.data)
          setName(res.name)
        }
      })
      .catch(() => {
        if (!cancelled) setDailyData([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [code])

  // 最新数据
  const latest = dailyData.length > 0 ? dailyData[dailyData.length - 1] : null
  const prev = dailyData.length > 1 ? dailyData[dailyData.length - 2] : null

  return (
    <div>
      {/* 指标卡片 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
        <StatCard label="最新价" value={latest?.close?.toFixed(2) ?? '-'} />
        <StatCard label="今开 / 昨收" value={latest ? `${latest.open?.toFixed(2) ?? '-'} / ${prev?.close?.toFixed(2) ?? '-'}` : '-'} sub="成交额" />
        <StatCard label="最高 / 最低" value={latest ? `${latest.high?.toFixed(2) ?? '-'} / ${latest.low?.toFixed(2) ?? '-'}` : '-'} sub="换手率" />
        <StatCard label="代码" value={`${code} ${name}`} sub="涨跌幅" />
      </div>

      {/* K线图 */}
      {loading ? (
        <div style={{ height: 360, display: 'flex', alignItems: 'center', justifyContent: 'center', color: colors.textMuted }}>
          加载中...
        </div>
      ) : dailyData.length > 0 ? (
        <KlineChart data={dailyData} height={360} />
      ) : (
        <div style={{ height: 360, display: 'flex', alignItems: 'center', justifyContent: 'center', color: colors.textMuted }}>
          搜索股票查看 K 线图
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div style={{
      background: colors.bgCard,
      borderRadius: 8,
      padding: 14,
    }}>
      <div style={{ fontSize: 10, color: colors.textLabel, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ fontSize: 18, color: colors.textPrimary, fontWeight: 600, fontFamily: 'inherit' }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 11, color: colors.textMuted, marginTop: 4 }}>{sub}</div>}
    </div>
  )
}
