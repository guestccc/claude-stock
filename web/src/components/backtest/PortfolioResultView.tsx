/** 组合回测结果展示组件 */
import React, { useMemo, useState, useEffect } from 'react'
import ReactECharts from 'echarts-for-react'
import { colors, fonts, changeColor, changeSignRaw } from '../../theme/tokens'
import KlineChart from '../charts/KlineChart'
import { getDaily, type DailyBar } from '../../api/market'
import type { PortfolioBacktestResponse, TradeResult } from '../../api/backtest'

// ---------- 工具 ----------
function fmt(v: number | null | undefined, d = 2): string {
  if (v == null || v === undefined) return '-'
  return v.toLocaleString('zh-CN', { minimumFractionDigits: d, maximumFractionDigits: d })
}

// ---------- 样式 ----------
const S = {
  card: {
    background: colors.bgSecondary,
    borderRadius: 8,
    padding: 20,
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: colors.textPrimary,
    marginBottom: 12,
    fontFamily: fonts.mono,
    borderLeft: `3px solid ${colors.accent}`,
    paddingLeft: 10,
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
    gap: 12,
  },
  statItem: {
    textAlign: 'center' as const,
    padding: '10px',
    background: colors.bg,
    borderRadius: 6,
  },
  statLabel: {
    fontSize: 11,
    color: colors.textLabel,
    fontFamily: fonts.mono,
    marginBottom: 4,
  },
  statValue: {
    fontSize: 18,
    fontFamily: fonts.mono,
    fontWeight: 600,
    color: colors.textPrimary,
  },
  statSub: {
    fontSize: 11,
    color: colors.textMuted,
    fontFamily: fonts.mono,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    fontSize: 12,
    fontFamily: fonts.mono,
  },
  th: {
    padding: '6px 10px',
    textAlign: 'left' as const,
    color: colors.textLabel,
    fontSize: 11,
    borderBottom: `1px solid ${colors.border}`,
    whiteSpace: 'nowrap' as const,
    cursor: 'pointer',
  },
  thRight: { textAlign: 'right' as const },
  td: {
    padding: '8px 10px',
    borderBottom: `1px solid ${colors.border}`,
    color: colors.textPrimary,
  },
  tdRight: { textAlign: 'right' as const },
  tr: {
    transition: 'background 0.1s',
    cursor: 'pointer',
  },
  badge: (win: boolean) => ({
    display: 'inline-block',
    padding: '2px 6px',
    borderRadius: 3,
    fontSize: 11,
    fontWeight: 600,
    background: win ? colors.riseBg : colors.fallBg,
    color: win ? colors.rise : colors.fall,
    fontFamily: fonts.mono,
  }),
}

const reasonMap: Record<string, string> = {
  stop_loss: '止损',
  take_profit: '止盈',
  force_close: '强平',
  breakout: '突破',
}

interface Props {
  result: PortfolioBacktestResponse
}

export default function PortfolioResultView({ result }: Props) {
  const { portfolio_stats, overall_equity, stock_results } = result
  const [expandedStock, setExpandedStock] = useState<string | null>(null)
  const [tradeFilter, setTradeFilter] = useState<string>('ALL')

  // 回测日期范围（用于懒加载 K 线）
  const btStartDate = overall_equity.length > 0 ? overall_equity[0].date : undefined
  const btEndDate = overall_equity.length > 0 ? overall_equity[overall_equity.length - 1].date : undefined

  // ---------- 组合总览卡片 ----------
  const statCards = [
    { label: '总收益率', value: `${portfolio_stats.total_return_pct >= 0 ? '+' : ''}${portfolio_stats.total_return_pct.toFixed(1)}%`, color: changeColor(portfolio_stats.total_return_pct), sub: `¥${fmt(portfolio_stats.total_return)}` },
    { label: '最终资金', value: `¥${fmt(portfolio_stats.final_capital, 0)}`, color: changeColor(portfolio_stats.total_return), sub: `本金 ¥${fmt(portfolio_stats.initial_capital, 0)}` },
    { label: '交易次数', value: String(portfolio_stats.num_trades), color: colors.textPrimary, sub: `盈${portfolio_stats.win_trades} 亏${portfolio_stats.loss_trades}` },
    { label: '胜率', value: `${portfolio_stats.win_rate.toFixed(0)}%`, color: changeColor(portfolio_stats.win_rate - 50), sub: `盈¥${fmt(portfolio_stats.avg_win)} / 亏¥${fmt(portfolio_stats.avg_loss)}` },
    { label: '盈亏比', value: portfolio_stats.rr_ratio < 0 ? '∞' : portfolio_stats.rr_ratio.toFixed(2), color: colors.textPrimary, sub: `均持仓${portfolio_stats.avg_holding_days.toFixed(0)}天` },
    { label: '最大回撤', value: `-${portfolio_stats.max_drawdown_pct.toFixed(1)}%`, color: colors.fall, sub: `¥${fmt(portfolio_stats.max_drawdown)}` },
    { label: '夏普比率', value: portfolio_stats.sharpe_ratio.toFixed(2), color: portfolio_stats.sharpe_ratio >= 1 ? colors.rise : portfolio_stats.sharpe_ratio >= 0 ? colors.textMuted : colors.fall, sub: '年化' },
    { label: '日均收益', value: `${portfolio_stats.daily_return_pct >= 0 ? '+' : ''}${portfolio_stats.daily_return_pct.toFixed(4)}%`, color: changeColor(portfolio_stats.daily_return_pct), sub: '总收益/交易日' },
  ]

  // ---------- 组合资金曲线 ----------
  const equityOption = useMemo(() => {
    if (!overall_equity || overall_equity.length === 0) return null
    const dates = overall_equity.map(e => e.date)
    const totals = overall_equity.map(e => Number(e.total.toFixed(2)))
    const peaks = overall_equity.map(e => Number(e.peak.toFixed(2)))
    const ddPcts = overall_equity.map(e => -Number(e.dd_pct.toFixed(2)))
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['总净值', '峰值', '回撤%'], top: 0, textStyle: { color: '#fff' } },
      grid: { left: 60, right: 60, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: dates },
      yAxis: [
        { type: 'value', name: '净值', scale: true },
        { type: 'value', name: '回撤%', position: 'right' },
      ],
      series: [
        { name: '总净值', type: 'line', data: totals, smooth: true, lineStyle: { width: 2 }, itemStyle: { color: colors.accent } },
        { name: '峰值', type: 'line', data: peaks, smooth: true, lineStyle: { width: 1, type: 'dashed' }, itemStyle: { color: colors.textMuted } },
        { name: '回撤%', type: 'line', data: ddPcts, yAxisIndex: 1, smooth: true, lineStyle: { width: 1 }, itemStyle: { color: colors.fall }, areaStyle: { opacity: 0.1 } },
      ],
    }
  }, [overall_equity])

  // ---------- 各股对比资金曲线 ----------
  const compareOption = useMemo(() => {
    if (!stock_results || stock_results.length === 0) return null
    // 统一日期轴
    const allDates = new Set<string>()
    stock_results.forEach(s => s.equity_curve.forEach(e => allDates.add(e.date)))
    const dates = Array.from(allDates).sort()
    const palette = [colors.accent, colors.rise, colors.fall, '#9b59b6', '#3498db', '#e67e22', '#1abc9c', '#f39c12']
    const series = stock_results.map((s, idx) => {
      const map = new Map(s.equity_curve.map(e => [e.date, e.total]))
      return {
        name: `${s.name}(${s.code})`,
        type: 'line',
        data: dates.map(d => { const v = map.get(d); return v != null ? Number(v.toFixed(2)) : null }),
        smooth: true,
        connectNulls: true,
        lineStyle: { width: 1.5 },
        itemStyle: { color: palette[idx % palette.length] },
      }
    })
    return {
      tooltip: { trigger: 'axis' },
      legend: { top: 0, type: 'scroll', textStyle: { color: '#fff' } },
      grid: { left: 60, right: 30, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: dates },
      yAxis: { type: 'value', name: '净值', scale: true },
      series,
    }
  }, [stock_results])

  // ---------- 全部交易明细（带股票筛选） ----------
  const allTrades: (TradeResult & { code: string; name: string })[] = useMemo(() => {
    const list: (TradeResult & { code: string; name: string })[] = []
    stock_results.forEach(s => {
      s.trades.forEach(t => list.push({ ...t, code: s.code, name: s.name }))
    })
    list.sort((a, b) => a.entry_date.localeCompare(b.entry_date))
    return list
  }, [stock_results])

  const filteredTrades = tradeFilter === 'ALL'
    ? allTrades
    : allTrades.filter(t => t.code === tradeFilter)

  return (
    <div>
      {/* 组合总览 */}
      <div style={S.card}>
        <div style={S.sectionTitle}>组合总览</div>
        <div style={S.statsGrid}>
          {statCards.map((c, i) => (
            <div key={i} style={S.statItem}>
              <div style={S.statLabel}>{c.label}</div>
              <div style={{ ...S.statValue, color: c.color }}>{c.value}</div>
              <div style={S.statSub}>{c.sub}</div>
            </div>
          ))}
        </div>
      </div>

      {/* 组合资金曲线 */}
      {equityOption && (
        <div style={S.card}>
          <div style={S.sectionTitle}>组合资金曲线</div>
          <ReactECharts option={equityOption} style={{ height: 320 }} />
        </div>
      )}

      {/* 股票列表 */}
      <div style={S.card}>
        <div style={S.sectionTitle}>各股票明细</div>
        <table style={S.table}>
          <thead>
            <tr>
              <th style={S.th}>股票</th>
              <th style={{ ...S.th, ...S.thRight }}>收益率</th>
              <th style={{ ...S.th, ...S.thRight }}>交易数</th>
              <th style={{ ...S.th, ...S.thRight }}>胜率</th>
              <th style={{ ...S.th, ...S.thRight }}>盈亏比</th>
              <th style={{ ...S.th, ...S.thRight }}>最大回撤</th>
              <th style={{ ...S.th, ...S.thRight }}>夏普</th>
              <th style={S.th}>操作</th>
            </tr>
          </thead>
          <tbody>
            {stock_results.map(s => {
              const st = s.stats
              const winRate = st.num_trades > 0 ? (st.win_trades / st.num_trades * 100) : 0
              return (
                <React.Fragment key={s.code}>
                  <tr
                    style={S.tr}
                    onMouseEnter={e => (e.currentTarget.style.background = colors.bgHover)}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                    onClick={() => setExpandedStock(expandedStock === s.code ? null : s.code)}
                  >
                    <td style={{ ...S.td, color: colors.accent, fontWeight: 600 }}>{s.name}({s.code})</td>
                    <td style={{ ...S.td, ...S.tdRight, color: changeColor(st.total_return_pct), fontWeight: 600 }}>
                      {st.total_return_pct >= 0 ? '+' : ''}{st.total_return_pct.toFixed(1)}%
                    </td>
                    <td style={{ ...S.td, ...S.tdRight }}>{st.num_trades}</td>
                    <td style={{ ...S.td, ...S.tdRight, color: changeColor(winRate - 50) }}>{winRate.toFixed(0)}%</td>
                    <td style={{ ...S.td, ...S.tdRight }}>{st.rr_ratio < 0 ? '∞' : st.rr_ratio.toFixed(2)}</td>
                    <td style={{ ...S.td, ...S.tdRight, color: colors.fall }}>-{st.max_drawdown_pct.toFixed(1)}%</td>
                    <td style={{ ...S.td, ...S.tdRight, color: st.sharpe_ratio >= 1 ? colors.rise : st.sharpe_ratio >= 0 ? colors.textMuted : colors.fall }}>{st.sharpe_ratio.toFixed(2)}</td>
                    <td style={S.td}>
                      <span style={{ color: colors.accent, fontSize: 11 }}>
                        {expandedStock === s.code ? '收起 ▲' : '展开 ▼'}
                      </span>
                    </td>
                  </tr>
                  {expandedStock === s.code && (
                    <tr>
                      <td colSpan={8} style={{ padding: '8px 16px 16px', background: colors.bg, borderBottom: `1px solid ${colors.border}` }}>
                        <StockDetailPanel
                          code={s.code}
                          trades={s.trades}
                          startDate={btStartDate}
                          endDate={btEndDate}
                        />
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* 全部交易明细 */}
      {allTrades.length > 0 && (
        <div style={S.card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={S.sectionTitle}>全部交易明细</div>
            <select
              value={tradeFilter}
              onChange={e => setTradeFilter(e.target.value)}
              style={{
                padding: '4px 8px',
                background: colors.bg,
                color: colors.textPrimary,
                border: `1px solid ${colors.border}`,
                borderRadius: 4,
                fontSize: 12,
                fontFamily: fonts.mono,
              }}
            >
              <option value="ALL">全部股票</option>
              {stock_results.map(s => (
                <option key={s.code} value={s.code}>{s.name}({s.code})</option>
              ))}
            </select>
          </div>
          <AllTradesTable trades={filteredTrades} />
        </div>
      )}

      {/* 各股对比资金曲线 */}
      {compareOption && (
        <div style={S.card}>
          <div style={S.sectionTitle}>各股票净值对比</div>
          <ReactECharts option={compareOption} style={{ height: 320 }} />
        </div>
      )}
    </div>
  )
}

// ---------- 子组件：单只股票交易明细表 ----------
function StockTradeTable({ trades }: { trades: TradeResult[] }) {
  if (trades.length === 0) {
    return <div style={{ color: colors.textMuted, fontSize: 12, padding: 8 }}>无交易记录</div>
  }
  return (
    <table style={S.table}>
      <thead>
        <tr>
          <th style={S.th}>序号</th>
          <th style={S.th}>买入日</th>
          <th style={S.th}>卖出日</th>
          <th style={{ ...S.th, ...S.thRight }}>天数</th>
          <th style={{ ...S.th, ...S.thRight }}>买入价</th>
          <th style={{ ...S.th, ...S.thRight }}>卖出价</th>
          <th style={{ ...S.th, ...S.thRight }}>股数</th>
          <th style={{ ...S.th, ...S.thRight }}>盈亏</th>
          <th style={{ ...S.th, ...S.thRight }}>收益率</th>
          <th style={S.th}>原因</th>
        </tr>
      </thead>
      <tbody>
        {(() => {
          // 按 entry_date 分组序号
          const egm = new Map<string, number>()
          let gs = 0
          trades.forEach(t => {
            if (!egm.has(t.entry_date)) { gs++; egm.set(t.entry_date, gs) }
          })
          return trades.map((t, i) => {
            const isWin = t.pnl > 0
            return (
              <tr key={i}>
                <td style={{ ...S.td, color: colors.textMuted, fontWeight: 600 }}>{egm.get(t.entry_date) || (i + 1)}</td>
                <td style={{ ...S.td, color: colors.accent }}>{t.entry_date}</td>
                <td style={{ ...S.td, color: colors.accent }}>{t.exit_date}</td>
                <td style={{ ...S.td, ...S.tdRight }}>{t.holding_days}</td>
                <td style={{ ...S.td, ...S.tdRight }}>{fmt(t.entry_price)}</td>
                <td style={{ ...S.td, ...S.tdRight }}>{fmt(t.exit_price)}</td>
                <td style={{ ...S.td, ...S.tdRight }}>{t.shares}</td>
                <td style={{ ...S.td, ...S.tdRight, color: changeColor(t.pnl), fontWeight: 600 }}>{changeSignRaw(t.pnl)}</td>
                <td style={{ ...S.td, ...S.tdRight, color: changeColor(t.pnl), fontWeight: 600 }}>
                  {t.entry_price > 0 ? `${t.pnl >= 0 ? '+' : ''}${((t.exit_price - t.entry_price) / t.entry_price * 100).toFixed(2)}%` : '-'}
                </td>
                <td style={S.td}>
                  <span style={S.badge(isWin)}>{reasonMap[t.reason] || t.reason}</span>
                </td>
              </tr>
            )
          })
        })()}
      </tbody>
    </table>
  )
}

// ---------- 子组件：全部交易明细表（带股票代码列）----------
function AllTradesTable({ trades }: { trades: (TradeResult & { code: string; name: string })[] }) {
  return (
    <table style={S.table}>
      <thead>
        <tr>
          <th style={S.th}>序号</th>
          <th style={S.th}>股票</th>
          <th style={S.th}>买入日</th>
          <th style={S.th}>卖出日</th>
          <th style={{ ...S.th, ...S.thRight }}>天数</th>
          <th style={{ ...S.th, ...S.thRight }}>买入价</th>
          <th style={{ ...S.th, ...S.thRight }}>卖出价</th>
          <th style={{ ...S.th, ...S.thRight }}>股数</th>
          <th style={{ ...S.th, ...S.thRight }}>盈亏</th>
          <th style={{ ...S.th, ...S.thRight }}>收益率</th>
          <th style={S.th}>原因</th>
        </tr>
      </thead>
      <tbody>
        {(() => {
          // 按 code+entry_date 分组序号（跨股票）
          const egm = new Map<string, number>()
          let gs = 0
          trades.forEach(t => {
            const key = `${t.code}_${t.entry_date}`
            if (!egm.has(key)) { gs++; egm.set(key, gs) }
          })
          return trades.map((t, i) => {
            const isWin = t.pnl > 0
            return (
              <tr key={i}>
                <td style={{ ...S.td, color: colors.textMuted, fontWeight: 600 }}>{egm.get(`${t.code}_${t.entry_date}`) || (i + 1)}</td>
                <td style={{ ...S.td, color: colors.accent, whiteSpace: 'nowrap' }}>{t.name}({t.code})</td>
                <td style={{ ...S.td, color: colors.textSecondary }}>{t.entry_date}</td>
                <td style={{ ...S.td, color: colors.textSecondary }}>{t.exit_date}</td>
                <td style={{ ...S.td, ...S.tdRight }}>{t.holding_days}</td>
                <td style={{ ...S.td, ...S.tdRight }}>{fmt(t.entry_price)}</td>
                <td style={{ ...S.td, ...S.tdRight }}>{fmt(t.exit_price)}</td>
                <td style={{ ...S.td, ...S.tdRight }}>{t.shares}</td>
                <td style={{ ...S.td, ...S.tdRight, color: changeColor(t.pnl), fontWeight: 600 }}>{changeSignRaw(t.pnl)}</td>
                <td style={{ ...S.td, ...S.tdRight, color: changeColor(t.pnl), fontWeight: 600 }}>
                  {t.entry_price > 0 ? `${t.pnl >= 0 ? '+' : ''}${((t.exit_price - t.entry_price) / t.entry_price * 100).toFixed(2)}%` : '-'}
                </td>
                <td style={S.td}>
                  <span style={S.badge(isWin)}>{reasonMap[t.reason] || t.reason}</span>
                </td>
              </tr>
            )
          })
        })()}
      </tbody>
    </table>
  )
}

// ---------- 子组件：股票详情（K 线 + 买卖点 + 交易表） ----------
function StockDetailPanel({ code, trades, startDate, endDate }: {
  code: string
  trades: TradeResult[]
  startDate?: string
  endDate?: string
}) {
  const [klineData, setKlineData] = useState<DailyBar[]>([])
  const [loading, setLoading] = useState(false)

  // 懒加载 K 线数据
  useEffect(() => {
    if (!startDate || !endDate) return
    let cancelled = false
    setLoading(true)
    getDaily(code, { start: startDate, end: endDate, limit: 2000 })
      .then(resp => {
        if (!cancelled) setKlineData(resp.data || [])
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [code, startDate, endDate])

  // 构建买卖标记：白色圆形 + 彩色文字(买N/卖N)
  // 按 entry_date 分组：同一笔买入分多次卖出时，序号一致
  const buySellMarks = useMemo(() => {
    if (klineData.length === 0 || trades.length === 0) return []
    const dateIndexMap = new Map(klineData.map((d, i) => [d.date, i]))
    const entryGroupMap = new Map<string, number>()
    let groupSeq = 0
    for (const t of trades) {
      if (!entryGroupMap.has(t.entry_date)) {
        groupSeq++
        entryGroupMap.set(t.entry_date, groupSeq)
      }
    }
    const marks: any[] = []
    const addedBuySet = new Set<string>()
    trades.forEach(t => {
      const seq = entryGroupMap.get(t.entry_date) || 1
      const buyKey = `${t.entry_date}_${t.entry_price}`
      const buyIdx = dateIndexMap.get(t.entry_date)
      if (buyIdx != null && !addedBuySet.has(buyKey)) {
        addedBuySet.add(buyKey)
        marks.push({
          coord: [buyIdx, t.entry_price],
          value: `买${seq}`,
          // symbol: BUY_SYMBOL, // 旧 SVG 图标
          symbol: 'circle',
          symbolSize: 26,
          symbolOffset: [0, -20],
          itemStyle: { color: '#fff', borderColor: '#f1a740', borderWidth: 2 },
          label: { show: true, formatter: `买${seq}`, color: '#f1a740', fontSize: 10, fontWeight: 600 },
        })
      }
      const sellIdx = dateIndexMap.get(t.exit_date)
      if (sellIdx != null) {
        marks.push({
          coord: [sellIdx, t.exit_price],
          value: `卖${seq}`,
          // symbol: SELL_SYMBOL, // 旧 SVG 图标
          symbol: 'circle',
          symbolSize: 26,
          symbolOffset: [0, 20],
          itemStyle: { color: '#fff', borderColor: '#2966C1', borderWidth: 2 },
          label: { show: true, formatter: `卖${seq}`, color: '#2966C1', fontSize: 10, fontWeight: 600 },
        })
      }
    })
    return marks
  }, [klineData, trades])

  return (
    <div>
      {loading && (
        <div style={{ textAlign: 'center', padding: 24, color: colors.textMuted, fontFamily: fonts.mono, fontSize: 12 }}>
          加载 K 线数据...
        </div>
      )}
      {!loading && klineData.length > 0 && (
        <KlineChart data={klineData} height={400} extraMarkPoints={buySellMarks} />
      )}
      {!loading && klineData.length === 0 && (
        <div style={{ textAlign: 'center', padding: 16, color: colors.textMuted, fontFamily: fonts.mono, fontSize: 12 }}>
          暂无 K 线数据
        </div>
      )}
      <div style={{ marginTop: 12 }}>
        <StockTradeTable trades={trades} />
      </div>
    </div>
  )
}
