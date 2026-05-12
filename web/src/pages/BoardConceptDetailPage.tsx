/** 概念板块详情页 — 指数 K 线 */
import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { Segmented, Spin, Empty } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import KlineChart from '../components/charts/KlineChart'
import { getConceptKline } from '../api/board'
import type { DailyBar } from '../api/market'

const PERIOD_OPTIONS = [
  { label: '1年', value: 'Y1' },
  { label: '3年', value: 'Y3' },
  { label: '5年', value: 'Y5' },
  { label: '全部', value: 'ALL' },
]

export default function BoardConceptDetailPage() {
  const { name } = useParams<{ name: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const decodedName = decodeURIComponent(name || '')
  const code = searchParams.get('code') || ''

  const [period, setPeriod] = useState('Y1')
  const [loading, setLoading] = useState(true)
  const [rawData, setRawData] = useState<any[]>([])

  useEffect(() => {
    if (!decodedName) return
    setLoading(true)
    getConceptKline(decodedName, period, code)
      .then((res) => setRawData(res.data || []))
      .catch(() => setRawData([]))
      .finally(() => setLoading(false))
  }, [decodedName, period, code])

  // 转为 DailyBar 格式供 KlineChart 使用
  const bars: DailyBar[] = useMemo(() => (
    rawData.map((r) => ({
      date: r.date,
      open: r.open,
      close: r.close,
      high: r.high,
      low: r.low,
      volume: r.volume,
      turnover: r.turnover,
      pct_change: r.pct_change,
    }))
  ), [rawData])

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      {/* 顶部 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <ArrowLeftOutlined
            style={{ cursor: 'pointer', fontSize: 14, color: '#999' }}
            onClick={() => navigate('/board')}
          />
          <h2 style={{ margin: 0, fontSize: 16 }}>{decodedName}</h2>
          <span style={{ fontSize: 11, color: '#888' }}>概念板块指数</span>
        </div>
        <Segmented
          size="small"
          value={period}
          onChange={(v) => setPeriod(v as string)}
          options={PERIOD_OPTIONS}
        />
      </div>

      {/* K 线图 */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin tip="加载K线数据..." />
        </div>
      ) : bars.length > 0 ? (
        <KlineChart data={bars} height={580} />
      ) : (
        <div style={{ textAlign: 'center', padding: '80px 0' }}>
          <Empty description="暂无K线数据（该板块可能不在数据源中）" />
        </div>
      )}
    </div>
  )
}
