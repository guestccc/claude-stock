/** 基金详情页 */
import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getFundDetail, getFundNavHistory, type FundDetail, type FundNavPoint } from '../api/fund'
import FundNavChart from '../components/charts/FundNavChart'
import FundBacktestPanel from '../components/fund/FundBacktestPanel'
import { colors, fonts, changeColor, changeSign } from '../theme/tokens'

const PERIODS = ['1月', '3月', '6月', '1年', '3年', '成立来'] as const

const S = {
  page: { maxWidth: 900, margin: '0 auto' },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    marginBottom: 24,
  },
  backBtn: {
    background: 'transparent',
    border: `1px solid ${colors.border}`,
    borderRadius: 6,
    color: colors.textSecondary,
    cursor: 'pointer',
    fontSize: 13,
    fontFamily: fonts.mono,
    padding: '6px 12px',
  },
  nameWrap: { flex: 1, minWidth: 0 },
  name: {
    fontFamily: fonts.mono,
    fontSize: 16,
    color: colors.textPrimary,
    fontWeight: 600,
  },
  code: {
    fontFamily: fonts.mono,
    fontSize: 11,
    color: colors.textMuted,
    marginLeft: 8,
  },
  typeTag: (type: string) => {
    const map: Record<string, string> = {
      '混合型': '#7aa4f5', '股票型': '#e06666', '债券型': '#5cb85c',
      '指数型': '#f0ad4e', '货币型': '#5bc0de', 'QDII': '#9b59b6',
    }
    const color = map[type] || colors.accent
    return {
      display: 'inline-block',
      fontFamily: fonts.mono,
      fontSize: 10,
      color,
      background: color + '22',
      borderRadius: 4,
      padding: '2px 6px',
      marginLeft: 8,
    }
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
    gap: 10,
    marginBottom: 24,
  },
  statCard: {
    background: colors.bgSecondary,
    borderRadius: 8,
    padding: '12px 14px',
  },
  statLabel: {
    fontFamily: fonts.mono,
    fontSize: 10,
    color: colors.textLabel,
    marginBottom: 4,
  },
  statValue: {
    fontFamily: fonts.mono,
    fontSize: 14,
    color: colors.textPrimary,
    fontWeight: 600,
  },
  periodBar: {
    display: 'flex',
    gap: 6,
    marginBottom: 12,
  },
  periodBtn: (active: boolean) => ({
    padding: '6px 14px',
    borderRadius: 6,
    border: 'none',
    cursor: 'pointer',
    fontSize: 12,
    fontFamily: fonts.mono,
    fontWeight: 600,
    background: active ? colors.accent : colors.bgSecondary,
    color: active ? '#fff' : colors.textSecondary,
    transition: 'all 0.15s',
  }),
  chartWrap: {
    background: colors.bgSecondary,
    borderRadius: 8,
    padding: 12,
    marginBottom: 24,
  },
  sectionTitle: {
    fontFamily: fonts.mono,
    fontSize: 12,
    color: colors.textMuted,
    fontWeight: 600,
    marginBottom: 10,
    paddingLeft: 8,
    borderLeft: `3px solid ${colors.accent}`,
  },
  tabBar: {
    display: 'flex',
    gap: 0,
    marginBottom: 20,
    borderBottom: `1px solid ${colors.border}`,
  },
  tab: (active: boolean) => ({
    padding: '8px 20px',
    fontFamily: fonts.mono,
    fontSize: 13,
    fontWeight: 600,
    color: active ? colors.accent : colors.textMuted,
    background: 'transparent',
    border: 'none',
    borderBottom: active ? `2px solid ${colors.accent}` : '2px solid transparent',
    cursor: 'pointer',
    transition: 'all 0.15s',
  }),
  infoGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: 10,
  },
  infoItem: {
    background: colors.bgSecondary,
    borderRadius: 8,
    padding: '10px 14px',
  },
  infoLabel: {
    fontFamily: fonts.mono,
    fontSize: 10,
    color: colors.textLabel,
    marginBottom: 4,
  },
  infoValue: {
    fontFamily: fonts.mono,
    fontSize: 12,
    color: colors.textSecondary,
    wordBreak: 'break-all' as const,
  },
  loading: {
    textAlign: 'center' as const,
    padding: 48,
    color: colors.textMuted,
    fontFamily: fonts.mono,
    fontSize: 13,
  },
  error: {
    textAlign: 'center' as const,
    padding: 48,
    color: colors.fall,
    fontFamily: fonts.mono,
    fontSize: 13,
  },
}

export default function FundDetailPage() {
  const { code } = useParams<{ code: string }>()
  const navigate = useNavigate()

  const [detail, setDetail] = useState<FundDetail | null>(null)
  const [navData, setNavData] = useState<FundNavPoint[]>([])
  const [period, setPeriod] = useState<string>('1年')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<'overview' | 'backtest'>('overview')

  // 加载详情
  useEffect(() => {
    if (!code) return
    getFundDetail(code)
      .then(setDetail)
      .catch(e => setError(e.message))
  }, [code])

  // 加载历史净值
  const loadNavHistory = useCallback(async (p: string) => {
    if (!code) return
    try {
      const res = await getFundNavHistory(code, p)
      setNavData(res.data)
    } catch {
      setNavData([])
    }
  }, [code])

  // 首次加载 + 切换周期
  useEffect(() => {
    setLoading(true)
    loadNavHistory(period).finally(() => setLoading(false))
  }, [period, loadNavHistory])

  if (error) return <div style={S.error}>加载失败: {error}</div>
  if (!detail) return <div style={S.loading}>加载中...</div>

  return (
    <div style={S.page}>
      {/* 顶部 */}
      <div style={S.header}>
        <button style={S.backBtn} onClick={() => navigate('/fund')}>
          ← 返回
        </button>
        <div style={S.nameWrap}>
          <span style={S.name}>{detail.name}</span>
          <span style={S.code}>{detail.code}</span>
          {detail.fund_type && <span style={S.typeTag(detail.fund_type)}>{detail.fund_type}</span>}
        </div>
      </div>

      {/* Tab 栏 */}
      <div style={S.tabBar}>
        <button style={S.tab(activeTab === 'overview')} onClick={() => setActiveTab('overview')}>
          概览
        </button>
        <button style={S.tab(activeTab === 'backtest')} onClick={() => setActiveTab('backtest')}>
          回测
        </button>
      </div>

      {activeTab === 'overview' ? (
      <>
      {/* 指标卡 */}
      <div style={S.sectionTitle}>实时数据</div>
      <div style={S.statsGrid}>
        <div style={S.statCard}>
          <div style={S.statLabel}>最新净值</div>
          <div style={S.statValue}>
            {detail.nav != null ? detail.nav.toFixed(4) : '-'}
            {detail.nav_date && <span style={{ fontSize: 10, color: colors.textMuted, marginLeft: 6 }}>{detail.nav_date}</span>}
          </div>
        </div>
        <div style={S.statCard}>
          <div style={S.statLabel}>估值涨跌</div>
          <div style={{ ...S.statValue, color: changeColor(detail.est_pct) }}>
            {detail.est_pct != null ? changeSign(detail.est_pct) : '-'}
          </div>
        </div>
        <div style={S.statCard}>
          <div style={S.statLabel}>基金公司</div>
          <div style={{ ...S.statValue, fontSize: 12 }}>{detail.company || '-'}</div>
        </div>
        <div style={S.statCard}>
          <div style={S.statLabel}>基金经理</div>
          <div style={{ ...S.statValue, fontSize: 12 }}>{detail.manager || '-'}</div>
        </div>
        <div style={S.statCard}>
          <div style={S.statLabel}>规模</div>
          <div style={S.statValue}>{detail.scale || '-'}</div>
        </div>
      </div>

      {/* 周期选择 + 折线图 */}
      <div style={S.sectionTitle}>净值走势</div>
      <div style={S.chartWrap}>
        <div style={S.periodBar}>
          {PERIODS.map(p => (
            <button
              key={p}
              style={S.periodBtn(period === p)}
              onClick={() => setPeriod(p)}
            >
              {p}
            </button>
          ))}
        </div>
        {loading ? (
          <div style={S.loading}>加载中...</div>
        ) : (
          <FundNavChart data={navData} height={380} />
        )}
      </div>

      {/* 历史净值列表 */}
      {!loading && navData.length > 0 && (
        <>
          <div style={S.sectionTitle}>历史净值</div>
          <div style={{
            background: colors.bgSecondary,
            borderRadius: 8,
            padding: 12,
            marginBottom: 24,
            maxHeight: 360,
            overflowY: 'auto',
          }}>
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: 12,
            fontFamily: fonts.mono,
          }}>
            <thead>
              <tr>
                <th style={S.th}>日期</th>
                <th style={{ ...S.th, textAlign: 'right' }}>单位净值</th>
                <th style={{ ...S.th, textAlign: 'right' }}>日增长率</th>
              </tr>
            </thead>
            <tbody>
              {[...navData].reverse().map((d, i) => (
                <tr key={i}>
                  <td style={{ padding: '5px 8px', borderBottom: `1px solid ${colors.border}`, color: colors.textSecondary }}>
                    {d.date}
                  </td>
                  <td style={{ padding: '5px 8px', borderBottom: `1px solid ${colors.border}`, color: colors.textSecondary, textAlign: 'right' }}>
                    {d.nav.toFixed(4)}
                  </td>
                  <td style={{
                    padding: '5px 8px',
                    borderBottom: `1px solid ${colors.border}`,
                    color: changeColor(d.pct_change),
                    textAlign: 'right',
                  }}>
                    {d.pct_change != null ? (d.pct_change >= 0 ? '+' : '') + d.pct_change.toFixed(2) + '%' : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </>
      )}

      {/* 基本信息 */}
      <div style={S.sectionTitle}>基本信息</div>
      <div style={S.infoGrid}>
        {detail.setup_date && (
          <div style={S.infoItem}>
            <div style={S.infoLabel}>成立日期</div>
            <div style={S.infoValue}>{detail.setup_date}</div>
          </div>
        )}
        {detail.benchmark && (
          <div style={S.infoItem}>
            <div style={S.infoLabel}>业绩基准</div>
            <div style={S.infoValue}>{detail.benchmark}</div>
          </div>
        )}
        {detail.strategy && (
          <div style={S.infoItem}>
            <div style={S.infoLabel}>投资策略</div>
            <div style={S.infoValue}>{detail.strategy}</div>
          </div>
        )}
        {detail.full_name && (
          <div style={S.infoItem}>
            <div style={S.infoLabel}>基金全称</div>
            <div style={S.infoValue}>{detail.full_name}</div>
          </div>
        )}
      </div>
      </>
      ) : (
        <FundBacktestPanel code={code!} />
      )}
    </div>
  )
}
