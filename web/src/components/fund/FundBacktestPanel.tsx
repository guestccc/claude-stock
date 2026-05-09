/** 基金回测面板 — 策略选择 + 参数配置 + 结果展示 */
import { useState, useEffect } from 'react'
import ReactECharts from 'echarts-for-react'
import * as echarts from 'echarts'
import {
  getFundBacktestStrategies,
  runFundBacktest,
  type FundStrategyInfo,
  type FundBacktestResponse,
  type StrategyParams,
} from '../../api/fund'
import { colors, fonts, changeColor } from '../../theme/tokens'

const S = {
  sectionTitle: {
    fontFamily: fonts.mono,
    fontSize: 12,
    color: colors.textMuted,
    fontWeight: 600,
    marginBottom: 10,
    paddingLeft: 8,
    borderLeft: `3px solid ${colors.accent}`,
  },
  strategyBar: {
    display: 'flex',
    gap: 6,
    marginBottom: 16,
    flexWrap: 'wrap' as const,
  },
  strategyBtn: (active: boolean) => ({
    padding: '6px 12px',
    borderRadius: 6,
    border: 'none',
    cursor: 'pointer',
    fontSize: 11,
    fontFamily: fonts.mono,
    fontWeight: 600,
    background: active ? colors.accent : colors.bgSecondary,
    color: active ? '#fff' : colors.textSecondary,
    transition: 'all 0.15s',
  }),
  configGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: 10,
    marginBottom: 16,
  },
  fieldGroup: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 4,
  },
  label: {
    fontFamily: fonts.mono,
    fontSize: 10,
    color: colors.textLabel,
  },
  input: {
    background: colors.bg,
    border: `1px solid ${colors.border}`,
    borderRadius: 6,
    padding: '6px 10px',
    color: colors.textPrimary,
    fontSize: 12,
    fontFamily: fonts.mono,
    outline: 'none',
  },
  runBtn: (loading: boolean) => ({
    padding: '8px 20px',
    borderRadius: 6,
    border: 'none',
    cursor: loading ? 'wait' : 'pointer',
    fontSize: 12,
    fontFamily: fonts.mono,
    fontWeight: 600,
    background: loading ? colors.textMuted : colors.accent,
    color: '#fff',
    marginBottom: 20,
  }),
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
    gap: 10,
    marginBottom: 20,
  },
  statCard: {
    background: colors.bgSecondary,
    borderRadius: 8,
    padding: '10px 12px',
  },
  statLabel: {
    fontFamily: fonts.mono,
    fontSize: 10,
    color: colors.textLabel,
    marginBottom: 2,
  },
  statValue: {
    fontFamily: fonts.mono,
    fontSize: 14,
    color: colors.textPrimary,
    fontWeight: 600,
  },
  chartWrap: {
    background: colors.bgSecondary,
    borderRadius: 8,
    padding: 10,
    marginBottom: 20,
  },
  tableWrap: {
    background: colors.bgSecondary,
    borderRadius: 8,
    padding: 10,
    maxHeight: 400,
    overflowY: 'auto' as const,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    fontSize: 11,
    fontFamily: fonts.mono,
  },
  th: {
    padding: '6px 8px',
    textAlign: 'left' as const,
    color: colors.textLabel,
    fontSize: 10,
    borderBottom: `1px solid ${colors.border}`,
    whiteSpace: 'nowrap' as const,
  },
  td: {
    padding: '5px 8px',
    borderBottom: `1px solid ${colors.border}`,
    color: colors.textSecondary,
  },
  tdRight: { textAlign: 'right' as const },
  empty: {
    textAlign: 'center' as const,
    padding: 48,
    color: colors.textMuted,
    fontFamily: fonts.mono,
    fontSize: 13,
  },
  tagBuy: {
    display: 'inline-block',
    fontSize: 10,
    padding: '1px 6px',
    borderRadius: 3,
    background: colors.rise + '22',
    color: colors.rise,
  },
  tagSell: {
    display: 'inline-block',
    fontSize: 10,
    padding: '1px 6px',
    borderRadius: 3,
    background: colors.fall + '22',
    color: colors.fall,
  },
}

interface Props {
  code: string
}

// 策略规则说明
const STRATEGY_RULES: Record<string, { buy: string[]; sell: string[]; note?: string }> = {
  dca: {
    buy: ['每隔 N 天自动买入，金额固定'],
    sell: ['回测期间不卖出，持有到期末'],
    note: '适合长期看好的基金，用纪律性平摊成本',
  },
  equal_buy: {
    buy: ['当日净值相比上次买入跌幅达到阈值时，等额买入'],
    sell: ['持仓收益率达到止盈线时，全部卖出清仓'],
  },
  pyramid: {
    buy: [
      '首次建仓后，根据前一年最大回撤动态生成补仓梯度',
      '浮亏达到某档阈值时买入，档位越深金额越大（金字塔加仓）',
    ],
    sell: ['持仓收益率达到止盈线时，全部卖出清仓，梯度重置'],
    note: '越跌买越多，适合左侧建仓、底部收集筹码',
  },
  reverse_pyramid: {
    buy: [
      '首次建仓后，根据前一年最大回撤动态生成补仓梯度',
      '浮亏达到某档阈值时买入，档位越深金额越小（倒金字塔加仓）',
    ],
    sell: ['持仓收益率达到止盈线时，全部卖出清仓，梯度重置'],
    note: '越跌买越少，控制下行风险，适合保守型投资者',
  },
  constant_value: {
    buy: ['持仓市值低于目标值时，补仓到目标市值'],
    sell: ['持仓市值高于目标值时，卖出超出部分'],
    note: '本质是高抛低吸，自动保持持仓市值恒定',
  },
  grid: {
    buy: ['净值相对上次买入下跌 N% 时，按固定金额买入'],
    sell: ['净值相对上次买入上涨 N% 时，卖出对应份额'],
    note: '在震荡市中反复收割利润，适合波动较大的基金',
  },
}

// 每种策略需要的参数字段
const STRATEGY_PARAMS: Record<string, (keyof StrategyParams)[]> = {
  dca: ['interval_days', 'amount'],
  equal_buy: ['drop_pct', 'amount', 'take_profit_pct'],
  pyramid: ['take_profit_pct', 'level_interval_pct', 'min_levels'],
  reverse_pyramid: ['take_profit_pct', 'level_interval_pct', 'min_levels'],
  constant_value: ['target_value', 'rebalance_days'],
  grid: ['grid_pct', 'amount_per_grid'],
}

const PARAM_LABELS: Record<string, string> = {
  interval_days: '定投间隔(天)',
  amount: '每次金额',
  drop_pct: '跌幅阈值(%)',
  take_profit_pct: '止盈(%)',
  level_interval_pct: '每档间距(%)',
  min_levels: '最少档位',
  target_value: '目标市值',
  rebalance_days: '调仓间隔(天)',
  grid_pct: '每格涨跌(%)',
  amount_per_grid: '每格金额',
}

const PARAM_DEFAULTS: StrategyParams = {
  interval_days: 7,
  amount: 500,
  drop_pct: -2,
  take_profit_pct: 20,
  level_interval_pct: 4,
  min_levels: 3,
  target_value: 5000,
  rebalance_days: 30,
  grid_pct: 3,
  amount_per_grid: 500,
}

export default function FundBacktestPanel({ code }: Props) {
  const [strategies, setStrategies] = useState<FundStrategyInfo[]>([])
  const [strategy, setStrategy] = useState('dca')
  const [startDate, setStartDate] = useState('2024-01-01')
  const [endDate, setEndDate] = useState('')
  const [initialCapital, setInitialCapital] = useState(5000)
  const [params, setParams] = useState<StrategyParams>({})
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<FundBacktestResponse | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getFundBacktestStrategies().then(setStrategies).catch(() => {})
  }, [])

  const activeParams = STRATEGY_PARAMS[strategy] || []

  const handleRun = async () => {
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const reqParams: StrategyParams = {}
      for (const key of activeParams) {
        const v = params[key] ?? PARAM_DEFAULTS[key]
        if (v !== undefined) reqParams[key] = v as any
      }
      const res = await runFundBacktest({
        code,
        start_date: startDate,
        end_date: endDate || undefined,
        initial_capital: initialCapital,
        strategy,
        params: reqParams,
      })
      setResult(res)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e.message || '回测失败')
    } finally {
      setLoading(false)
    }
  }

  const chartOption = result ? buildChartOption(result) : null

  return (
    <div>
      {/* 策略选择 */}
      <div style={S.sectionTitle}>选择策略</div>
      <div style={S.strategyBar}>
        {strategies.map(s => (
          <button key={s.id} style={S.strategyBtn(strategy === s.id)}
            onClick={() => { setStrategy(s.id); setResult(null) }}
            title={s.description}
          >
            {s.name}
          </button>
        ))}
      </div>

      {/* 策略规则 */}
      {STRATEGY_RULES[strategy] && (
        <div style={{ background: colors.bgSecondary, borderRadius: 8, padding: '10px 14px', marginBottom: 16, fontSize: 11, fontFamily: fonts.mono, lineHeight: 1.8 }}>
          <div style={{ color: colors.rise, fontWeight: 600, marginBottom: 4 }}>买入规则</div>
          {STRATEGY_RULES[strategy].buy.map((r, i) => (
            <div key={i} style={{ color: colors.textSecondary, paddingLeft: 8 }}>{'• '}{r}</div>
          ))}
          <div style={{ color: colors.fall, fontWeight: 600, marginTop: 6, marginBottom: 4 }}>卖出规则</div>
          {STRATEGY_RULES[strategy].sell.map((r, i) => (
            <div key={i} style={{ color: colors.textSecondary, paddingLeft: 8 }}>{'• '}{r}</div>
          ))}
          {STRATEGY_RULES[strategy].note && (
            <div style={{ color: colors.textMuted, marginTop: 6, fontSize: 10, fontStyle: 'italic' }}>
              💡 {STRATEGY_RULES[strategy].note}
            </div>
          )}
        </div>
      )}

      {/* 参数配置 */}
      <div style={S.sectionTitle}>参数配置</div>
      <div style={S.configGrid}>
        <div style={S.fieldGroup}>
          <label style={S.label}>起始日期</label>
          <input style={S.input} type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
        </div>
        <div style={S.fieldGroup}>
          <label style={S.label}>结束日期</label>
          <input style={S.input} type="date" value={endDate} onChange={e => setEndDate(e.target.value)} placeholder="留空=至今" />
        </div>
        <div style={S.fieldGroup}>
          <label style={S.label}>初始资金</label>
          <input style={S.input} type="number" value={initialCapital} onChange={e => setInitialCapital(+e.target.value)} />
        </div>
        {activeParams.map(key => (
          <div key={key} style={S.fieldGroup}>
            <label style={S.label}>{PARAM_LABELS[key] || key}</label>
            <input style={S.input}
              type="number"
              step={key === 'drop_pct' ? 0.5 : 1}
              value={params[key] ?? PARAM_DEFAULTS[key] ?? ''}
              onChange={e => setParams({ ...params, [key]: +e.target.value })}
            />
          </div>
        ))}
      </div>
      <button style={S.runBtn(loading)} onClick={handleRun} disabled={loading}>
        {loading ? '回测中...' : '运行回测'}
      </button>

      {error && <div style={{ color: colors.fall, fontFamily: fonts.mono, fontSize: 13, marginBottom: 16 }}>{error}</div>}

      {/* 回测结果 */}
      {result && (
        <>
          {/* 统计卡片 */}
          <div style={S.sectionTitle}>回测结果</div>
          <div style={S.statsGrid}>
            {renderStatCard('总收益率', `${result.stats.total_return_pct.toFixed(2)}%`, result.stats.total_return_pct)}
            {renderStatCard('年化收益', `${result.stats.annualized_return_pct.toFixed(2)}%`, result.stats.annualized_return_pct)}
            {renderStatCard('总投入', result.stats.total_invested.toFixed(0))}
            {renderStatCard('最终资产', result.stats.final_value.toFixed(2))}
            {renderStatCard('最大回撤', `${result.stats.max_drawdown_pct.toFixed(2)}%`, -result.stats.max_drawdown_pct)}
            {renderStatCard('交易次数', `${result.stats.num_trades}笔（买${result.stats.num_buys}/卖${result.stats.num_sells}）`)}
            {renderStatCard('夏普比率', result.stats.sharpe_ratio?.toFixed(2) || '-')}
            {renderStatCard('平均买入', result.stats.avg_buy_amount.toFixed(0))}
          </div>

          {/* 资产曲线 */}
          <div style={S.sectionTitle}>资产曲线 vs 基金净值</div>
          <div style={S.chartWrap}>
            {chartOption && <ReactECharts option={chartOption} style={{ height: 320 }} notMerge />}
          </div>

          {/* 交易记录 */}
          <div style={S.sectionTitle}>交易记录</div>
          <div style={S.tableWrap}>
            <table style={S.table}>
              <thead>
                <tr>
                  <th style={S.th}>日期</th>
                  <th style={S.th}>类型</th>
                  <th style={{ ...S.th, ...S.tdRight }}>净值</th>
                  <th style={{ ...S.th, ...S.tdRight }}>份额</th>
                  <th style={{ ...S.th, ...S.tdRight }}>金额</th>
                  <th style={{ ...S.th, ...S.tdRight }}>手续费</th>
                  <th style={S.th}>原因</th>
                </tr>
              </thead>
              <tbody>
                {result.trades.map((t, i) => (
                  <tr key={i}>
                    <td style={S.td}>{t.date}</td>
                    <td style={S.td}>
                      <span style={t.type === 'buy' ? S.tagBuy : S.tagSell}>
                        {t.type === 'buy' ? '买入' : '卖出'}
                      </span>
                    </td>
                    <td style={{ ...S.td, ...S.tdRight }}>{t.nav.toFixed(4)}</td>
                    <td style={{ ...S.td, ...S.tdRight }}>{t.shares.toFixed(2)}</td>
                    <td style={{ ...S.td, ...S.tdRight }}>{t.amount.toFixed(2)}</td>
                    <td style={{ ...S.td, ...S.tdRight }}>{t.fee.toFixed(2)}</td>
                    <td style={{ ...S.td, fontSize: 10 }}>{t.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}

function renderStatCard(label: string, value: string, colorValue?: number) {
  return (
    <div style={S.statCard}>
      <div style={S.statLabel}>{label}</div>
      <div style={{
        ...S.statValue,
        color: colorValue != null ? changeColor(colorValue) : colors.textPrimary,
      }}>
        {value}
      </div>
    </div>
  )
}

function buildChartOption(result: FundBacktestResponse) {
  const ec = result.equity_curve
  const dates = ec.map(e => e.date)
  const totals = ec.map(e => e.total)
  const navs = ec.map(e => e.nav)

  // 计算 5 日 / 10 日均线
  const ma = (data: number[], n: number) =>
    data.map((_, i) => i < n - 1 ? null : data.slice(i - n + 1, i + 1).reduce((a, b) => a + b, 0) / n)
  const ma5 = ma(navs, 5)
  const ma10 = ma(navs, 10)

  // 构建买卖点标记 — 用 markPoint 在"组合资产"系列上标注
  const dateIndexMap = new Map(dates.map((d, i) => [d, i]))
  const buyMarks: any[] = []
  const sellMarks: any[] = []

  for (const t of result.trades) {
    const idx = dateIndexMap.get(t.date)
    if (idx == null) continue
    if (t.type === 'buy') {
      buyMarks.push({ coord: [idx, totals[idx]], value: t.amount })
    } else {
      sellMarks.push({ coord: [idx, totals[idx]], value: t.amount })
    }
  }

  // 构建 tooltip 中展示的交易信息索引
  const tradesByDate = new Map<string, typeof result.trades>()
  for (const t of result.trades) {
    const arr = tradesByDate.get(t.date) || []
    arr.push(t)
    tradesByDate.set(t.date, arr)
  }

  return {
    backgroundColor: colors.bgSecondary,
    animation: true,
    animationDuration: 600,
    tooltip: {
      trigger: 'axis' as const,
      backgroundColor: '#1a1a1a',
      borderColor: colors.border,
      textStyle: { color: colors.textPrimary, fontFamily: fonts.mono, fontSize: 11 },
      formatter: (params: any) => {
        const p0 = params[0]
        if (!p0) return ''
        const date = p0.axisValue
        const ep = ec[p0.dataIndex]

        let html = `<div style="font-family:${fonts}">`
        html += `<div style="color:${colors.textMuted};font-size:10px;margin-bottom:4px">${date}</div>`
        html += `<div>组合资产: <b>${ep.total.toFixed(0)}</b></div>`
        html += `<div style="color:${colors.textMuted}">现金 ${ep.cash.toFixed(0)} | 持仓 ${ep.position_value.toFixed(0)} | 份额 ${ep.shares.toFixed(2)}</div>`
        html += `<div style="color:${colors.textMuted};font-size:10px">净值 ${ep.nav.toFixed(4)}</div>`

        // 当日有交易时追加交易信息
        const dayTrades = tradesByDate.get(date)
        if (dayTrades) {
          for (const t of dayTrades) {
            const color = t.type === 'buy' ? colors.rise : colors.fall
            const label = t.type === 'buy' ? '买入' : '卖出'
            html += `<div style="margin-top:4px;padding-top:4px;border-top:1px solid ${colors.border}">`
            html += `<span style="color:${color};font-weight:600">${label}</span> `
            html += `金额 ${t.amount.toFixed(0)} | 份额 ${t.shares.toFixed(2)} | 手续费 ${t.fee.toFixed(2)}`
            html += `<div style="color:${colors.textMuted};font-size:10px">${t.reason}</div>`
            html += `</div>`
          }
        }
        html += '</div>'
        return html
      },
    },
    legend: { data: ['组合资产', '基金净值', 'MA5', 'MA10'], textStyle: { color: colors.textMuted, fontFamily: fonts.mono, fontSize: 10 }, top: 4 },
    grid: { left: 60, right: 60, top: 36, bottom: 30 },
    xAxis: { type: 'category' as const, data: dates, axisLine: { lineStyle: { color: colors.border } }, axisTick: { show: false }, axisLabel: { color: colors.textMuted, fontSize: 9, fontFamily: fonts.mono, formatter: (v: string) => v.slice(5) } },
    yAxis: [
      { type: 'value' as const, name: '资产', nameTextStyle: { color: colors.textMuted, fontFamily: fonts.mono, fontSize: 9 }, scale: true, axisLine: { show: false }, splitLine: { lineStyle: { color: colors.border, type: 'dashed' as const } }, axisLabel: { color: colors.textMuted, fontSize: 9, fontFamily: fonts.mono } },
      { type: 'value' as const, name: '净值', nameTextStyle: { color: colors.textMuted, fontFamily: fonts.mono, fontSize: 9 }, scale: true, axisLine: { show: false }, splitLine: { show: false }, axisLabel: { color: colors.textMuted, fontSize: 9, fontFamily: fonts.mono } },
    ],
    dataZoom: [{ type: 'inside' as const, start: 0, end: 100 }],
    series: [
      {
        name: '组合资产', type: 'line', data: totals, yAxisIndex: 0, smooth: true, showSymbol: false,
        lineStyle: { width: 1.5, color: '#e06666' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(224,102,102,0.2)' }, { offset: 1, color: 'rgba(0,0,0,0)' }]) },
        markPoint: {
          symbol: 'circle',
          symbolSize: 8,
          animation: false,
          data: [
            ...buyMarks.map(m => ({
              coord: m.coord,
              symbol: 'triangle' as const,
              symbolSize: 10,
              itemStyle: { color: colors.rise },
              label: { show: false },
            })),
            ...sellMarks.map(m => ({
              coord: m.coord,
              symbol: 'path://M0,-6L6,6L-6,6Z' as const,
              symbolSize: 10,
              symbolRotate: 180,
              itemStyle: { color: colors.fall },
              label: { show: false },
            })),
          ],
        },
      },
      {
        name: '基金净值', type: 'line', data: navs, yAxisIndex: 1, smooth: true, showSymbol: false,
        lineStyle: { width: 1, color: '#7aa4f5', type: 'dashed' as const },
      },
      {
        name: 'MA5', type: 'line', data: ma5, yAxisIndex: 1, smooth: true, showSymbol: false,
        lineStyle: { width: 1, color: '#f5a623' },
      },
      {
        name: 'MA10', type: 'line', data: ma10, yAxisIndex: 1, smooth: true, showSymbol: false,
        lineStyle: { width: 1, color: '#bd93f9' },
      },
    ],
  }
}
