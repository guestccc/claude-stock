/** 回测结果展示组件 — 可被主页面和历史详情复用 */
import React, { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import KlineChart from '../charts/KlineChart'
import { colors, fonts, changeColor, changeSignRaw, BUY_SYMBOL, SELL_SYMBOL, PYRAMID_SYMBOL } from '../../theme/tokens'
import type { BacktestResponse, BacktestRequest, TradeResult, KlineBar } from '../../api/backtest'
import type { DailyBar } from '../../api/market'

// ---------- 工具 ----------
function fmt(v: number | null, d = 2): string {
  if (v == null) return '-'
  return v.toLocaleString('zh-CN', { minimumFractionDigits: d, maximumFractionDigits: d })
}

const UP_COLOR = colors.rise
const DOWN_COLOR = colors.fall

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

interface Props {
  result: BacktestResponse
}

export default function BacktestResultView({ result }: Props) {
  const { stats, trades, equity_curve, klines } = result
  const req = result.request

  // ---------- 绩效卡片 ----------
  const statCards = [
    { label: '总收益率', value: `${stats.total_return_pct >= 0 ? '+' : ''}${stats.total_return_pct.toFixed(1)}%`, color: changeColor(stats.total_return_pct), sub: `¥${fmt(stats.total_return)}` },
    { label: '最终资金', value: `¥${fmt(stats.final_capital, 0)}`, color: changeColor(stats.total_return), sub: `本金 ¥${fmt(stats.initial_capital, 0)}` },
    { label: '交易次数', value: String(stats.num_trades), color: colors.textPrimary, sub: `盈${stats.win_trades} 亏${stats.loss_trades}` },
    { label: '胜率', value: `${stats.win_rate.toFixed(0)}%`, color: changeColor(stats.win_rate - 50), sub: `盈¥${fmt(stats.avg_win)} / 亏¥${fmt(stats.avg_loss)}` },
    { label: '盈亏比', value: stats.rr_ratio < 0 ? '∞' : stats.rr_ratio.toFixed(2), color: colors.textPrimary, sub: `均持仓${stats.avg_holding_days.toFixed(0)}天` },
    { label: '最大回撤', value: `-${stats.max_drawdown_pct.toFixed(1)}%`, color: colors.fall, sub: `¥${fmt(stats.max_drawdown)}` },
    { label: '夏普比率', value: stats.sharpe_ratio.toFixed(2), color: stats.sharpe_ratio >= 1 ? colors.rise : stats.sharpe_ratio >= 0 ? colors.textMuted : colors.fall, sub: '年化' },
    { label: '日均收益', value: `${stats.daily_return_pct >= 0 ? '+' : ''}${stats.daily_return_pct.toFixed(4)}%`, color: changeColor(stats.daily_return_pct), sub: '总收益/交易日' },
  ]

  // ---------- K线数据转换 + 买卖标记 ----------
  const { klineData, buySellMarks } = useMemo(() => {
    if (!klines || klines.length === 0) return { klineData: [] as DailyBar[], buySellMarks: [] }

    // KlineBar → DailyBar（补 pct_change）
    const data: DailyBar[] = klines.map(k => ({
      date: k.date,
      open: k.open,
      close: k.close,
      high: k.high,
      low: k.low,
      volume: k.volume,
      turnover: k.turnover,
      pct_change: null,
    }))

    // 买卖点标记
    const dateIndexMap = new Map(data.map((d, i) => [d.date, i]))
    const marks: any[] = []
    for (const t of trades) {
      const isPyramid = t.reason === 'pyramid'
      const buyIdx = dateIndexMap.get(t.entry_date)
      if (buyIdx != null) {
        marks.push({
          coord: [buyIdx, t.entry_price],
          value: isPyramid ? '加' : '买',
          symbol: isPyramid ? PYRAMID_SYMBOL : BUY_SYMBOL,
          symbolSize: isPyramid ? 22 : 28,
          symbolOffset: [0, isPyramid ? -22 : -30],
          itemStyle: { opacity: isPyramid ? 0.7 : 0.5 },
        })
      }
      const sellIdx = dateIndexMap.get(t.exit_date)
      if (sellIdx != null) {
        marks.push({
          coord: [sellIdx, t.exit_price],
          value: '卖',
          symbol: SELL_SYMBOL,
          symbolSize: 28,
          symbolOffset: [0, 30],
          itemStyle: { opacity: 0.5 },
        })
      }
    }
    return { klineData: data, buySellMarks: marks }
  }, [klines, trades])

  // ---------- 资金曲线配置 ----------
  const equityOption = useMemo(() => {
    if (!equity_curve || equity_curve.length === 0) return null

    const dates = equity_curve.map(e => e.date)
    const values = equity_curve.map(e => e.total)
    const peaks = equity_curve.map(e => e.peak)

    return {
      animation: false,
      grid: { left: 55, right: 20, top: 15, bottom: 30 },
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category', data: dates,
        axisLabel: { fontSize: 10, color: colors.textMuted },
        axisLine: { lineStyle: { color: colors.border } },
        axisTick: { show: false },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value', scale: true,
        axisLabel: { fontSize: 10, color: colors.textMuted },
        axisLine: { show: false }, axisTick: { show: false },
        splitLine: { lineStyle: { color: colors.border } },
      },
      series: [
        {
          name: '资金曲线', type: 'line', data: values,
          smooth: true, symbol: 'none',
          lineStyle: { color: UP_COLOR, width: 2 },
          areaStyle: {
            color: {
              type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(224,102,102,0.2)' },
                { offset: 1, color: 'rgba(224,102,102,0.02)' },
              ],
            },
          },
        },
        {
          name: '峰值', type: 'line', data: peaks,
          symbol: 'none',
          lineStyle: { color: colors.textMuted, type: 'dashed', width: 1, opacity: 0.4 },
        },
        {
          type: 'line', silent: true, symbol: 'none',
          lineStyle: { color: colors.textMuted, type: 'dotted', width: 1 },
          markLine: {
            silent: true,
            data: [{ yAxis: stats.initial_capital }],
            label: { formatter: `本金 ¥${stats.initial_capital.toLocaleString()}`, color: colors.textMuted, fontSize: 10 },
          },
          data: [[0, stats.initial_capital], [0, stats.initial_capital]],
        },
      ],
    }
  }, [equity_curve, stats.initial_capital])

  return (
    <div>
      {/* 绩效统计 */}
      <div style={S.card}>
        <div style={S.sectionTitle}>绩效统计</div>
        <div style={S.statsGrid}>
          {statCards.map(c => (
            <div key={c.label} style={S.statItem}>
              <div style={S.statLabel}>{c.label}</div>
              <div style={{ ...S.statValue, color: c.color }}>{c.value}</div>
              <div style={S.statSub}>{c.sub}</div>
            </div>
          ))}
        </div>
      </div>

      {/* 资金曲线 */}
      {equityOption && (
        <div style={S.card}>
          <div style={S.sectionTitle}>资金曲线</div>
          <ReactECharts option={equityOption} style={{ height: 240 }} notMerge />
        </div>
      )}

      {/* K线图 */}
      {klineData.length > 0 && (
        <div style={S.card}>
          <div style={S.sectionTitle}>K线图（买卖点标注）</div>
          <KlineChart data={klineData} height={500} extraMarkPoints={buySellMarks} />
          <div style={{ display: 'flex', gap: 16, marginTop: 6, fontSize: 11, color: colors.textMuted, fontFamily: fonts.mono }}>
            <span><span style={{ color: UP_COLOR }}>▲ 买</span></span>
            <span><span style={{ color: '#2966C1' }}>⊕ 加仓</span></span>
            <span><span style={{ color: UP_COLOR }}>▼</span> 卖出（盈）</span>
            <span><span style={{ color: DOWN_COLOR }}>▼</span> 卖出（亏）</span>
            <span style={{ marginLeft: 'auto' }}>滚轮缩放</span>
          </div>
        </div>
      )}

      {/* 交易明细 */}
      <div style={S.card}>
        <div style={S.sectionTitle}>交易明细（{trades.length} 笔）</div>
        {trades.length === 0 ? (
          <div style={{ color: colors.textMuted, textAlign: 'center', padding: 24, fontFamily: fonts.mono }}>无交易记录</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={S.table}>
              <thead>
                <tr>
                  <th style={S.th}>买入日</th>
                  <th style={S.th}>卖出日</th>
                  <th style={{ ...S.th, ...S.thRight }}>持有天数</th>
                  <th style={{ ...S.th, ...S.thRight }}>买入价</th>
                  <th style={{ ...S.th, ...S.thRight }}>卖出价</th>
                  <th style={{ ...S.th, ...S.thRight }}>ATR</th>
                  <th style={{ ...S.th, ...S.thRight }}>止损</th>
                  <th style={{ ...S.th, ...S.thRight }}>止盈</th>
                  <th style={{ ...S.th, ...S.thRight }}>股数</th>
                  <th style={{ ...S.th, ...S.thRight }}>盈亏</th>
                  <th style={{ ...S.th, ...S.thRight }}>收益率</th>
                  <th style={{ ...S.th, ...S.thRight }}>R值</th>
                  <th style={S.th}>原因</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((t, i) => (
                  <TradeRow key={i} trade={t} strategy={req.exit_strategy} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 策略逻辑说明 */}
      <StrategyGuide strategy={req.exit_strategy} params={req} trades={trades} />
    </div>
  )
}


// ---------- 交易行组件（可展开详情） ----------
function TradeRow({ trade: t, strategy }: { trade: TradeResult; strategy: string }) {
  const [expanded, setExpanded] = React.useState(false)
  const isWin = t.pnl > 0
  const isTurtle = strategy === 'turtle'

  const reasonMap: Record<string, string> = {
    stop_loss: '止损',
    take_profit: '止盈',
    force_close: '强平',
    breakout: '突破',
    half_exit: '半仓止盈',
    half_exit_low3: '半仓+低3',
    half_exit_ma5: '半仓+MA5',
    pyramid: '加仓',
  }

  return (
    <>
      <tr
        style={S.tr}
        onClick={() => setExpanded(!expanded)}
        onMouseEnter={e => (e.currentTarget.style.background = colors.bgHover)}
        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
      >
        <td style={{ ...S.td, color: colors.accent }}>{t.entry_date}</td>
        <td style={{ ...S.td, color: colors.accent }}>{t.exit_date}</td>
        <td style={{ ...S.td, ...S.tdRight }}>{t.holding_days}</td>
        <td style={{ ...S.td, ...S.tdRight }}>{fmt(t.entry_price)}</td>
        <td style={{ ...S.td, ...S.tdRight }}>{fmt(t.exit_price)}</td>
        <td style={{ ...S.td, ...S.tdRight, color: colors.textMuted }}>{fmt(t.atr)}</td>
        <td style={{ ...S.td, ...S.tdRight, color: colors.fall }}>{fmt(t.stop_loss)}</td>
        <td style={{ ...S.td, ...S.tdRight, color: colors.rise }}>{fmt(t.take_profit)}</td>
        <td style={{ ...S.td, ...S.tdRight }}>{t.shares}</td>
        <td style={{ ...S.td, ...S.tdRight, color: changeColor(t.pnl), fontWeight: 600 }}>
          {changeSignRaw(t.pnl)}
        </td>
        <td style={{ ...S.td, ...S.tdRight, color: changeColor(t.pnl), fontWeight: 600 }}>
          {t.entry_price > 0 ? `${t.pnl >= 0 ? '+' : ''}${((t.exit_price - t.entry_price) / t.entry_price * 100).toFixed(2)}%` : '-'}
        </td>
        <td style={{ ...S.td, ...S.tdRight, color: changeColor(t.pnl_r) }}>
          {changeSignRaw(t.pnl_r)}R
        </td>
        <td style={S.td}>
          <span style={S.badge(isWin)}>{reasonMap[t.reason] || t.reason}</span>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={13} style={{ padding: '12px 16px', background: colors.bg, borderBottom: `1px solid ${colors.border}` }}>
            <div style={{ display: 'flex', gap: 16, fontSize: 12, fontFamily: fonts.mono, lineHeight: 1.8 }}>
              <div style={{ flex: 1 }}>
                <div style={{ color: colors.accent, fontWeight: 600, marginBottom: 4 }}>买入逻辑</div>
                <div style={{ color: colors.textSecondary }}>
                  唐奇安上轨 = {fmt(t.upper_band)}（20日最高）<br />
                  突破日收盘 = {fmt(t.breakout_close)}，高出上轨 {changeSignRaw(t.breakout_exceed_pct, 3)}%<br />
                  入场价（次日开盘）= {fmt(t.entry_price)}<br />
                  止损 = {fmt(t.stop_loss)}（入场 - ATR {t.atr.toFixed(3)} × {isTurtle ? '2.0' : '1.3'}）<br />
                  {isTurtle
                    ? <>仓位 = 本金 × 1% ÷ (2 × ATR) = {t.turtle_unit_size ?? t.shares} 股/仓<br /></>
                    : <>止盈 = {fmt(t.take_profit)}（入场 + ATR {t.atr.toFixed(3)} × 止盈倍数）<br /></>}
                  ATR = {t.atr.toFixed(3)}，共持仓 {t.shares} 股
                  {t.turtle_units && t.turtle_units.length > 1 && (
                    <><br /><span style={{ color: colors.accent }}>加仓明细（{t.turtle_units.length}仓）：</span><br />
                    {t.turtle_units.map((u, idx) => (
                      <span key={idx}>&nbsp;&nbsp;第{idx + 1}仓：{u.entry_date} @ {u.entry_price.toFixed(2)} × {u.shares}股<br /></span>
                    ))}</>
                  )}
                </div>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ color: colors.accent, fontWeight: 600, marginBottom: 4 }}>卖出逻辑</div>
                <div style={{ color: colors.textSecondary }}>
                  {t.exit_formula || `以 ${t.exit_price.toFixed(2)} 平仓`}<br />
                  盈亏 = ({t.exit_price.toFixed(2)} - {t.entry_price.toFixed(2)}) × {t.shares} = {changeSignRaw(t.pnl)} 元<br />
                  R值 = {changeSignRaw(t.pnl_r)}R
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}


// ---------- 策略逻辑说明 ----------
function StrategyGuide({ strategy, params, trades }: {
  strategy: string
  params: BacktestRequest
  trades: TradeResult[]
}) {
  const tp = params.tp_multiplier
  const trailingK = params.trailing_atr_k
  const halfPct = params.half_exit_pct

  const DONCHIAN_PERIOD = 20
  const BOLL_PERIOD = 20

  // 买入逻辑
  const isTurtle = strategy === 'turtle'
  const buySteps = [
    { label: '条件', desc: isTurtle ? `收盘价 > 唐奇安上轨（${DONCHIAN_PERIOD}日最高价）` : `收盘价 > 唐奇安上轨（${DONCHIAN_PERIOD}日最高价）且 收盘价 > BOLL上轨（${BOLL_PERIOD}日MA + 2倍标准差）` },
    { label: '买入', desc: '信号日次日，以开盘价买入' },
    { label: '止损', desc: isTurtle ? '买入价 - ATR(20) × 2.0（经典海龟止损）' : '买入价 - ATR(14) × 1.3' },
    { label: '止盈', desc: isTurtle ? '无固定止盈，靠10日低点出场' : `买入价 + ATR(14) × ${tp}` },
    { label: '仓位', desc: isTurtle ? '本金 × 1% ÷ (2 × ATR)，按100股取整' : '总资金 × 30%（按100股取整，最少100股）' },
  ]

  // 各策略的卖出逻辑
  const sellLogic: Record<string, { name: string; steps: { label: string; desc: string }[] }> = {
    fixed: {
      name: '固定止盈止损',
      steps: [
        { label: '止损', desc: '盘中最低价 ≤ 止损价 → 按止损价卖出（跳空低开按开盘价）' },
        { label: '止盈', desc: `盘中最高价 ≥ 止盈价（入场价 + ATR × ${tp}）→ 按止盈价卖出（跳空高开按开盘价）` },
        { label: '强平', desc: '回测区间结束仍持仓，按最后收盘价平仓' },
      ],
    },
    trailing: {
      name: '移动止盈',
      steps: [
        { label: '止损', desc: '同固定止损' },
        { label: '触及目标', desc: `盘中最高价 ≥ 止盈价 → 标记"目标已达成"，开始跟踪` },
        { label: '跟踪', desc: `用截至昨日的最高价计算跟踪止损价 = 目标后最高价 - ATR × ${trailingK}` },
        { label: '止盈', desc: '盘中最低价 ≤ 跟踪止损价 → 按跟踪止损价卖出（跳空低开按开盘价）。注意：每天收盘后才更新最高价，避免未来函数' },
      ],
    },
    boll_middle: {
      name: 'BOLL中轨止盈',
      steps: [
        { label: '止损', desc: '同固定止损' },
        { label: '止盈', desc: '收盘价 < BOLL中轨（20日均线）→ 按收盘价卖出' },
      ],
    },
    trailing_boll: {
      name: '移动止盈+BOLL中轨',
      steps: [
        { label: '止损', desc: '同固定止损' },
        { label: '触及目标', desc: `盘中最高价 ≥ 止盈价 → 开始跟踪` },
        { label: '条件A', desc: '收盘价 < BOLL中轨（20日均线）→ 按收盘价卖出' },
        { label: '条件B', desc: `盘中最低价 ≤ 跟踪止损价（截至昨日最高价 - ATR × ${trailingK}）→ 按跟踪止损价卖出` },
        { label: '优先级', desc: 'A、B 哪个先触发按哪个，两者独立判断' },
      ],
    },
    ma5_exit: {
      name: '跌破5日线止盈',
      steps: [
        { label: '止损', desc: '同固定止损' },
        { label: '计算', desc: 'MA5 = 近5日收盘均价（截至昨日，排除当天）' },
        { label: '信号', desc: '收盘价 < MA5 → 标记卖出信号' },
        { label: '执行', desc: '次日开盘价卖出（跳空会标注）' },
      ],
    },
    half_exit: {
      name: '半仓止盈+移动止损',
      steps: [
        { label: '止损', desc: '同固定止损（半仓前，作用于全部仓位）' },
        { label: '半仓', desc: `盘中最高价 ≥ 止盈价 → 卖出 ${halfPct}% 仓位，锁定部分利润` },
        { label: '跟踪', desc: `剩余仓位用移动止损：截至昨日最高价 - ATR × ${trailingK}` },
        { label: '清仓', desc: '剩余仓位盘中最低价 ≤ 跟踪止损价 → 全部卖出' },
      ],
    },
    half_exit_ma5: {
      name: '半仓止盈+5日线',
      steps: [
        { label: '止损', desc: '同固定止损（半仓前，作用于全部仓位）' },
        { label: '半仓', desc: `盘中最高价 ≥ 止盈价 → 卖出 ${halfPct}% 仓位` },
        { label: '跟踪', desc: '剩余仓位用 MA5 跟踪：MA5 = 近5日收盘均价（截至昨日）' },
        { label: '清仓', desc: '收盘价 < MA5 → 次日开盘价卖出全部剩余仓位' },
      ],
    },
    half_exit_low3: {
      name: '半仓止盈+前3日低点',
      steps: [
        { label: '止损', desc: '同固定止损（半仓前，作用于全部仓位）' },
        { label: '半仓', desc: `盘中最高价 ≥ 止盈价 → 卖出 ${halfPct}% 仓位` },
        { label: '跟踪', desc: '剩余仓位用前3日最低收盘价跟踪' },
        { label: '清仓', desc: '收盘价 < 前3日最低收盘价 → 按收盘价全部卖出' },
      ],
    },
    turtle: {
      name: '经典海龟交易',
      steps: [
        { label: '入场', desc: '收盘价突破 20 日最高价（无 BOLL 过滤），次日开盘买入' },
        { label: 'ATR', desc: '使用 ATR(20)（其他策略用 ATR(14)）' },
        { label: '仓位', desc: '1% 风险：股数 = 本金 × 1% / (2 × ATR)，按 100 股取整' },
        { label: '止损', desc: '买入价 - 2×ATR（固定，仅灾难性保护）' },
        { label: '加仓', desc: '每涨 0.5×ATR 加一仓（同股数），最多 4 仓。加仓后止损移到最新入场价 - 2×ATR' },
        { label: '出场', desc: '盘中最低价跌破 10 日最低价 → 止损单成交，卖出全部仓位' },
      ],
    },
  }

  const sell = sellLogic[strategy]
  if (!sell) return null

  // 举例：从交易明细中取第一笔盈利交易
  const example = trades.find(t => t.pnl > 0 && t.reason !== 'force_close')

  return (
    <div style={S.card}>
      <div style={S.sectionTitle}>策略逻辑说明 — {sell.name}</div>

      {/* 买入 */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: colors.accent, marginBottom: 8, fontFamily: fonts.mono }}>
          买入规则（所有策略共用）
        </div>
        <table style={{ ...S.table, fontSize: 11 }}>
          <tbody>
            {buySteps.map(s => (
              <tr key={s.label}>
                <td style={{ ...S.td, width: 60, color: colors.textLabel, fontWeight: 600 }}>{s.label}</td>
                <td style={S.td}>{s.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 卖出 */}
      <div style={{ marginBottom: example ? 16 : 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: colors.accent, marginBottom: 8, fontFamily: fonts.mono }}>
          卖出规则 — {sell.name}
        </div>
        <table style={{ ...S.table, fontSize: 11 }}>
          <tbody>
            {sell.steps.map((s, idx) => (
              <tr key={idx}>
                <td style={{ ...S.td, width: 80, color: colors.textLabel, fontWeight: 600 }}>{s.label}</td>
                <td style={S.td}>{s.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 举例 */}
      {example && (
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: colors.accent, marginBottom: 8, fontFamily: fonts.mono }}>
            举例（本次回测中的一笔交易）
          </div>
          <div style={{ background: colors.bg, borderRadius: 6, padding: 12, fontSize: 12, fontFamily: fonts.mono, lineHeight: 1.8, color: colors.textSecondary }}>
            <div>
              <span style={{ color: colors.textLabel }}>买入日：</span>{example.entry_date}，
              入场价 ¥{fmt(example.entry_price)}，ATR = {example.atr.toFixed(3)}
            </div>
            <div>
              <span style={{ color: colors.textLabel }}>止损 = </span>{fmt(example.entry_price)} - {example.atr.toFixed(3)} × 1.3 = <span style={{ color: colors.fall }}>{fmt(example.stop_loss)}</span>
            </div>
            <div>
              <span style={{ color: colors.textLabel }}>止盈 = </span>{fmt(example.entry_price)} + {example.atr.toFixed(3)} × {tp} = <span style={{ color: colors.rise }}>{fmt(example.take_profit)}</span>
            </div>
            <div>
              <span style={{ color: colors.textLabel }}>卖出日：</span>{example.exit_date}，
              卖出价 ¥{fmt(example.exit_price)}
            </div>
            <div>
              <span style={{ color: colors.textLabel }}>触发原因：</span>{example.exit_formula || example.reason}
            </div>
            <div>
              <span style={{ color: colors.textLabel }}>盈亏：</span>
              <span style={{ color: example.pnl > 0 ? colors.rise : colors.fall, fontWeight: 600 }}>
                {changeSignRaw(example.pnl)} 元（{changeSignRaw(example.pnl_r)}R）
              </span>
              ，持仓 {example.holding_days} 天
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
