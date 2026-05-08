/** 回测页面 — 配置 + 结果展示 + 历史入口 */
import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useParams } from 'react-router-dom'
import {
  Tabs,
  Button,
  AutoComplete,
  Select,
  DatePicker,
  InputNumber,
  Row,
  Col,
  Space,
  App,
} from 'antd'
import { PlayCircleOutlined, SaveOutlined, LeftOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import type { Dayjs } from 'dayjs'
import {
  getStrategies,
  getRecentStocks,
  runBacktest,
  saveBacktest,
  type ExitStrategyInfo,
  type BacktestResponse,
} from '../api/backtest'
import { searchStocks, type StockInfo } from '../api/market'
import { colors, fonts, changeColor, changeSignRaw } from '../theme/tokens'
import BacktestResultView from '../components/backtest/BacktestResultView'

// ---------- 主组件 ----------
export default function BacktestPage() {
  const { code: urlCode } = useParams<{ code?: string }>()
  const { message } = App.useApp()
  const [activeTab, setActiveTab] = useState('config')

  // 策略列表
  const [strategies, setStrategies] = useState<ExitStrategyInfo[]>([])

  // 配置表单
  const [tradeCode, setTradeCode] = useState(urlCode || '')
  const [tradeName, setTradeName] = useState('')
  const [startDate, setStartDate] = useState<Dayjs>(dayjs('2024-01-01'))
  const [endDate, setEndDate] = useState<Dayjs>(dayjs())
  const [capital, setCapital] = useState<number>(100000)
  const [strategy, setStrategy] = useState('half_exit')
  const [tpMultiplier, setTpMultiplier] = useState<number>(2.0)
  const [trailingAtrK, setTrailingAtrK] = useState<number>(0.5)
  const [halfExitPct, setHalfExitPct] = useState<number>(50)

  // 搜索
  const [stockOptions, setStockOptions] = useState<StockInfo[]>([])
  const [recentLoaded, setRecentLoaded] = useState(false)
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 状态
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<BacktestResponse | null>(null)
  const [saved, setSaved] = useState(false)

  // 加载策略列表
  useEffect(() => {
    getStrategies().then(r => setStrategies(r.strategies)).catch(() => {})
  }, [])

  // URL code 参数
  useEffect(() => {
    if (urlCode) setTradeCode(urlCode)
  }, [urlCode])

  // 股票搜索
  const handleSearch = (val: string) => {
    if (searchTimer.current) clearTimeout(searchTimer.current)
    if (!val.trim()) {
      // 输入框清空时，展示近期回测股票
      loadRecentStocks()
      return
    }
    searchTimer.current = setTimeout(async () => {
      try {
        const results = await searchStocks(val)
        setStockOptions(results.slice(0, 8))
      } catch { setStockOptions([]) }
    }, 300)
  }

  const loadRecentStocks = async () => {
    try {
      const { stocks } = await getRecentStocks(10)
      setStockOptions(stocks.map(s => ({ code: s.code, name: s.name })))
      setRecentLoaded(true)
    } catch { /* ignore */ }
  }

  const handleFocus = () => {
    // 聚焦时且输入框为空，加载近期回测股票
    if (!tradeCode.trim()) {
      loadRecentStocks()
    }
  }

  const handleSelectStock = (code: string) => {
    const found = stockOptions.find(r => r.code === code)
    if (found) {
      setTradeCode(found.code)
      setTradeName(found.name)
    }
    setStockOptions([])
  }

  // 运行回测
  const handleRun = async () => {
    if (!tradeCode) { message.error('请输入股票代码'); return }
    setRunning(true)
    setResult(null)
    setSaved(false)
    try {
      const resp = await runBacktest({
        code: tradeCode,
        start_date: startDate.format('YYYY-MM-DD'),
        end_date: endDate.format('YYYY-MM-DD'),
        initial_capital: capital,
        exit_strategy: strategy,
        tp_multiplier: tpMultiplier,
        trailing_atr_k: trailingAtrK,
        half_exit_pct: halfExitPct,
      })
      setResult(resp)
      message.success(`回测完成：${resp.name} ${resp.stats.total_return_pct > 0 ? '+' : ''}${resp.stats.total_return_pct}%，${resp.stats.num_trades} 笔交易`)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '回测失败')
    } finally {
      setRunning(false)
    }
  }

  // 保存结果
  const handleSave = async () => {
    if (!result) return
    try {
      const resp = await saveBacktest(result)
      setSaved(true)
      message.success(`已保存（ID: ${resp.id}）`)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }

  // 当前策略需要显示的参数
  const showTrailing = ['trailing', 'trailing_boll', 'half_exit'].includes(strategy)
  const showHalfExit = ['half_exit', 'half_exit_ma5', 'half_exit_low3'].includes(strategy)

  // 标签样式
  const labelStyle: React.CSSProperties = {
    marginBottom: 4,
    fontSize: 11,
    color: colors.textLabel,
    fontFamily: fonts.mono,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'config',
            label: '回测',
            children: (
              <>
                {/* 配置面板 */}
                <div style={{ background: colors.bgSecondary, borderRadius: 8, padding: 20, marginBottom: 16 }}>
                  <Row gutter={[16, 16]}>
                    {/* 股票搜索 */}
                    <Col xs={24} sm={12}>
                      <div style={labelStyle}>股票代码/名称</div>
                      <AutoComplete
                        value={tradeCode}
                        options={stockOptions.map(r => ({
                          value: r.code,
                          label: (
                            <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                              <span>{r.code}</span>
                              <span style={{ color: colors.textMuted }}>{r.name}</span>
                            </Space>
                          ),
                        }))}
                        onChange={(val: string) => { setTradeCode(val || ''); setTradeName('') }}
                        onSearch={handleSearch}
                        onSelect={handleSelectStock}
                        onFocus={handleFocus}
                        placeholder="输入代码或名称搜索..."
                        style={{ width: '100%' }}
                      />
                      {tradeName && (
                        <div style={{ fontSize: 11, color: colors.accent, fontFamily: fonts.mono, marginTop: 4 }}>
                          {tradeName}
                        </div>
                      )}
                    </Col>

                    {/* 出场策略 */}
                    <Col xs={24} sm={12}>
                      <div style={labelStyle}>出场策略</div>
                      <Select
                        value={strategy}
                        onChange={setStrategy}
                        options={strategies.map(s => ({ value: s.key, label: s.name }))}
                        style={{ width: '100%' }}
                      />
                    </Col>

                    {/* 日期 */}
                    <Col xs={24} sm={12}>
                      <div style={labelStyle}>开始日期</div>
                      <DatePicker value={startDate} onChange={(v: Dayjs | null) => v && setStartDate(v)} style={{ width: '100%' }} />
                    </Col>
                    <Col xs={24} sm={12}>
                      <div style={labelStyle}>结束日期（默认今天）</div>
                      <DatePicker value={endDate} onChange={(v: Dayjs | null) => v && setEndDate(v)} style={{ width: '100%' }} />
                    </Col>

                    {/* 本金 + 止盈倍数 */}
                    <Col xs={24} sm={12}>
                      <div style={labelStyle}>初始本金（元）</div>
                      <InputNumber value={capital} onChange={(v: number | null) => setCapital(v ?? 100000)} min={1000} step={10000} style={{ width: '100%' }} />
                    </Col>
                    <Col xs={24} sm={12}>
                      <div style={labelStyle}>止盈倍数（ATR×N）</div>
                      <InputNumber value={tpMultiplier} onChange={(v: number | null) => setTpMultiplier(v ?? 2.0)} min={0.5} step={0.5} style={{ width: '100%' }} />
                    </Col>

                    {/* 条件参数 */}
                    {showTrailing && (
                      <Col xs={24} sm={12}>
                        <div style={labelStyle}>跟踪止损ATR系数</div>
                        <InputNumber value={trailingAtrK} onChange={(v: number | null) => setTrailingAtrK(v ?? 0.5)} min={0.1} step={0.1} style={{ width: '100%' }} />
                      </Col>
                    )}
                    {showHalfExit && (
                      <Col xs={24} sm={12}>
                        <div style={labelStyle}>半仓止盈比例%</div>
                        <InputNumber value={halfExitPct} onChange={(v: number | null) => setHalfExitPct(v ?? 50)} min={10} max={100} step={10} style={{ width: '100%' }} />
                      </Col>
                    )}
                  </Row>

                  <Button
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    onClick={handleRun}
                    loading={running}
                    disabled={running}
                    block
                    style={{ marginTop: 16, fontFamily: fonts.mono, fontWeight: 600 }}
                  >
                    {running ? '回测中...' : '运行回测'}
                  </Button>
                </div>

                {/* 结果展示 */}
                {running && (
                  <div style={{ textAlign: 'center', padding: 24, color: colors.textMuted, fontFamily: fonts.mono }}>
                    回测计算中...
                  </div>
                )}
                {result && !running && (
                  <div>
                    <Space style={{ marginBottom: 12 }}>
                      <Button icon={<SaveOutlined />} onClick={handleSave} disabled={saved}>
                        {saved ? '已保存' : '保存结果'}
                      </Button>
                    </Space>
                    <BacktestResultView result={result} />
                  </div>
                )}
              </>
            ),
          },
          {
            key: 'history',
            label: '历史',
            children: <BacktestHistoryList />,
          },
        ]}
      />
    </div>
  )
}

// ---------- 历史列表子组件 ----------
function BacktestHistoryList() {
  const [items, setItems] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [detailResult, setDetailResult] = useState<BacktestResponse | null>(null)

  const loadList = useCallback(async () => {
    setLoading(true)
    try {
      const resp = await (await import('../api/backtest')).getBacktestHistory({ page, page_size: 20 })
      setItems(resp.items)
      setTotal(resp.total)
    } catch { }
    finally { setLoading(false) }
  }, [page])

  useEffect(() => { loadList() }, [loadList])

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`确定删除 ${name} 的回测记录？`)) return
    try {
      await (await import('../api/backtest')).deleteBacktest(id)
      loadList()
    } catch { }
  }

  const handleView = async (id: number) => {
    try {
      const detail = await (await import('../api/backtest')).getBacktestDetail(id)
      setDetailResult({
        code: detail.code,
        name: detail.name,
        request: {
          code: detail.code,
          start_date: detail.start_date,
          end_date: detail.end_date,
          initial_capital: detail.initial_capital,
          exit_strategy: detail.exit_strategy,
          tp_multiplier: detail.tp_multiplier,
          trailing_atr_k: detail.trailing_atr_k,
          half_exit_pct: detail.half_exit_pct,
        },
        stats: detail.stats,
        trades: detail.trades,
        equity_curve: detail.equity_curve,
        klines: detail.klines,
      })
    } catch { }
  }

  if (detailResult) {
    return (
      <div>
        <Button icon={<LeftOutlined />} onClick={() => setDetailResult(null)} style={{ marginBottom: 16 }}>
          返回列表
        </Button>
        <BacktestResultView result={detailResult} />
      </div>
    )
  }

  if (loading) return <div style={{ textAlign: 'center', padding: 24, color: colors.textMuted, fontFamily: fonts.mono }}>加载中...</div>
  if (items.length === 0) return <div style={{ textAlign: 'center', padding: 48, color: colors.textMuted, fontFamily: fonts.mono, fontSize: 13 }}>暂无历史回测记录</div>

  const totalPages = Math.ceil(total / 20)

  return (
    <div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, fontFamily: fonts.mono }}>
        <thead>
          <tr>
            {['股票', '策略', '区间', '收益率', '交易数', '胜率', '最大回撤', '时间', '操作'].map(h => (
              <th key={h} style={{
                padding: '8px 12px',
                textAlign: h === '操作' ? 'right' as const : h === '收益率' || h === '胜率' || h === '最大回撤' ? 'right' as const : 'left' as const,
                color: colors.textLabel,
                fontSize: 11,
                borderBottom: `1px solid ${colors.border}`,
                whiteSpace: 'nowrap' as const,
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map(item => (
            <tr key={item.id}
              style={{ cursor: 'pointer', transition: 'background 0.1s' }}
              onMouseEnter={e => (e.currentTarget.style.background = colors.bgHover)}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <td style={{ padding: '10px 12px', borderBottom: `1px solid ${colors.border}`, color: colors.accent }}>
                {item.name}({item.code})
              </td>
              <td style={{ padding: '10px 12px', borderBottom: `1px solid ${colors.border}`, color: colors.textPrimary }}>
                {item.exit_strategy}
              </td>
              <td style={{ padding: '10px 12px', borderBottom: `1px solid ${colors.border}`, color: colors.textMuted }}>
                {item.start_date} ~ {item.end_date}
              </td>
              <td style={{ padding: '10px 12px', borderBottom: `1px solid ${colors.border}`, textAlign: 'right', color: changeColor(item.total_return_pct), fontWeight: 600 }}>
                {changeSignRaw(item.total_return_pct)}%
              </td>
              <td style={{ padding: '10px 12px', borderBottom: `1px solid ${colors.border}`, textAlign: 'right', color: colors.textPrimary }}>
                {item.num_trades}
              </td>
              <td style={{ padding: '10px 12px', borderBottom: `1px solid ${colors.border}`, textAlign: 'right', color: changeColor(item.win_rate - 50) }}>
                {item.win_rate}%
              </td>
              <td style={{ padding: '10px 12px', borderBottom: `1px solid ${colors.border}`, textAlign: 'right', color: colors.fall }}>
                -{item.max_drawdown_pct}%
              </td>
              <td style={{ padding: '10px 12px', borderBottom: `1px solid ${colors.border}`, color: colors.textMuted }}>
                {item.created_at}
              </td>
              <td style={{ padding: '10px 12px', borderBottom: `1px solid ${colors.border}`, textAlign: 'right' as const }}>
                <Button size="small" onClick={() => handleView(item.id)}>查看</Button>
                <Button size="small" danger onClick={() => handleDelete(item.id, item.name)} style={{ marginLeft: 6 }}>删除</Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {totalPages > 1 && (
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 16 }}>
          <Button size="small" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>上一页</Button>
          <span style={{ color: colors.textMuted, fontSize: 12, fontFamily: fonts.mono, lineHeight: '24px' }}>
            {page} / {totalPages}
          </span>
          <Button size="small" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>下一页</Button>
        </div>
      )}
    </div>
  )
}
