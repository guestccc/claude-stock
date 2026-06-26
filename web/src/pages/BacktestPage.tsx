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
  Collapse,
  Switch,
  Slider,
  Tag,
} from 'antd'
import { PlayCircleOutlined, SaveOutlined, LeftOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import type { Dayjs } from 'dayjs'
import {
  getStrategies,
  getRecentStocks,
  runBacktest,
  saveBacktest,
  runPortfolioBacktest,
  getScoreConfig,
  updateScoreConfig,
  getPortfolioPools,
  createPortfolioPool,
  updatePortfolioPool,
  deletePortfolioPool,
  type ExitStrategyInfo,
  type BacktestResponse,
  type PortfolioBacktestResponse,
  type ScoreDimension,
  type PortfolioPool,
} from '../api/backtest'
import { searchStocks, type StockInfo } from '../api/market'
import { colors, fonts, changeColor, changeSignRaw } from '../theme/tokens'
import BacktestResultView from '../components/backtest/BacktestResultView'
import PortfolioResultView from '../components/backtest/PortfolioResultView'

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
            key: 'portfolio',
            label: '组合回测',
            children: <PortfolioBacktestPanel strategies={strategies} />,
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

// ---------- 组合回测子组件 ----------
// 组合模式支持的出场策略（与后端 PORTFOLIO_STRATEGIES 对应）
const PORTFOLIO_STRATEGY_KEYS = ['fixed', 'trailing', 'trailing_boll', 'boll_middle', 'ma5_exit', 'half_exit']

// 评分预设：ETF 波动小、量能放大不明显，参数需要调低
const SCORE_PRESETS: Record<string, { label: string; params: Record<string, Record<string, any>> }> = {
  stock: {
    label: '个股（默认）',
    params: {},  // 空对象 = 用后端默认参数
  },
  etf: {
    label: 'ETF',
    params: {
      breakout_strength: { optimal_min: 0.3, optimal_max: 1.5 },
      volume_ratio: { optimal_min: 1.2 },
      breakout_days: { optimal_min: 1, optimal_max: 2 },
    },
  },
}

function PortfolioBacktestPanel({ strategies }: { strategies: ExitStrategyInfo[] }) {
  const { message } = App.useApp()

  // 候选股票池
  const [poolCodes, setPoolCodes] = useState<string[]>([])
  const [poolOptions, setPoolOptions] = useState<StockInfo[]>([])
  const [codeNameMap, setCodeNameMap] = useState<Record<string, string>>({})
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 持久化候选池
  const [pools, setPools] = useState<PortfolioPool[]>([])
  const [selectedPoolId, setSelectedPoolId] = useState<number | null>(null)
  const [poolName, setPoolName] = useState('')
  const [savingPool, setSavingPool] = useState(false)

  // 参数
  const [maxPositions, setMaxPositions] = useState(3)
  const [startDate, setStartDate] = useState<Dayjs>(dayjs('2024-01-01'))
  const [endDate, setEndDate] = useState<Dayjs>(dayjs())
  const [capital, setCapital] = useState(100000)
  const [strategy, setStrategy] = useState('fixed')
  const [tpMultiplier, setTpMultiplier] = useState(2.0)
  const [trailingAtrK, setTrailingAtrK] = useState(1.0)
  const [halfExitPct, setHalfExitPct] = useState(50)

  // 评分配置
  const [scoreDims, setScoreDims] = useState<ScoreDimension[]>([])
  const [scoreLoaded, setScoreLoaded] = useState(false)
  const [scorePreset, setScorePreset] = useState<string>('stock')

  // 状态
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<PortfolioBacktestResponse | null>(null)

  // 组合模式只显示支持的策略
  const portfolioStrategies = strategies.filter(s => PORTFOLIO_STRATEGY_KEYS.includes(s.key))

  // 加载评分配置
  useEffect(() => {
    getScoreConfig().then(r => {
      setScoreDims(r.dimensions)
      setScoreLoaded(true)
    }).catch(() => {})
  }, [])

  // 加载持久化候选池
  const loadPools = async () => {
    try {
      const r = await getPortfolioPools()
      setPools(r.items)
    } catch { /* ignore */ }
  }
  useEffect(() => { loadPools() }, [])

  // 选择候选池
  const handleSelectPool = (id: number | null) => {
    if (id == null) {
      setSelectedPoolId(null)
      setPoolName('')
      return
    }
    const pool = pools.find(p => p.id === id)
    if (pool) {
      setSelectedPoolId(id)
      setPoolCodes(pool.codes)
      setPoolName(pool.name)
      // 用后端返回的 code_names 填充 tag 名称映射
      if (pool.code_names && Object.keys(pool.code_names).length > 0) {
        setCodeNameMap(prev => ({ ...prev, ...pool.code_names }))
      }
    }
  }

  // 保存候选池
  const handleSavePool = async () => {
    if (poolCodes.length === 0) { message.error('候选池为空'); return }
    const name = poolName.trim()
    if (!name) { message.error('请输入候选池名称'); return }
    setSavingPool(true)
    try {
      if (selectedPoolId) {
        // 更新已有
        await updatePortfolioPool(selectedPoolId, { name, codes: poolCodes })
        message.success('候选池已更新')
      } else {
        // 新建
        const pool = await createPortfolioPool({ name, codes: poolCodes })
        setSelectedPoolId(pool.id)
        message.success('候选池已保存')
      }
      await loadPools()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    } finally {
      setSavingPool(false)
    }
  }

  // 删除候选池
  const handleDeletePool = async (id: number) => {
    if (!confirm('确定删除该候选池？')) return
    try {
      await deletePortfolioPool(id)
      if (selectedPoolId === id) {
        setSelectedPoolId(null)
        setPoolName('')
        setPoolCodes([])
      }
      await loadPools()
      message.success('已删除')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '删除失败')
    }
  }

  // 股票搜索（用于候选池下拉）
  const handlePoolSearch = (val: string) => {
    if (searchTimer.current) clearTimeout(searchTimer.current)
    if (!val.trim()) { setPoolOptions([]); return }
    searchTimer.current = setTimeout(async () => {
      try {
        const results = await searchStocks(val)
        setPoolOptions(results.slice(0, 12))
        setCodeNameMap(prev => {
          const next = { ...prev }
          results.forEach(r => { next[r.code] = r.name })
          return next
        })
      } catch { setPoolOptions([]) }
    }, 300)
  }

  // 修改评分维度
  const handleDimChange = (key: string, field: 'weight' | 'enabled', value: number | boolean) => {
    setScoreDims(dims => dims.map(d =>
      d.key === key ? { ...d, [field]: value } : d
    ))
  }

  // 保存评分配置
  const handleSaveScore = async () => {
    try {
      const resp = await updateScoreConfig(scoreDims)
      setScoreDims(resp.dimensions)
      message.success('评分配置已保存')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }

  // 运行组合回测
  const handleRun = async () => {
    if (poolCodes.length === 0) { message.error('请选择候选股票'); return }
    if (maxPositions < 1) { message.error('最大持仓数至少为 1'); return }
    setRunning(true)
    setResult(null)
    try {
      // 构建评分覆盖配置（权重 + 预设 params）
      const presetParams = SCORE_PRESETS[scorePreset]?.params || {}
      const scoreConfig: Record<string, any> = {}
      scoreDims.forEach(d => {
        scoreConfig[d.key] = {
          weight: d.weight,
          enabled: d.enabled,
          ...(presetParams[d.key] || {}),  // 合并预设参数（如 optimal_min/optimal_max）
        }
      })

      const resp = await runPortfolioBacktest({
        codes: poolCodes,
        start_date: startDate.format('YYYY-MM-DD'),
        end_date: endDate.format('YYYY-MM-DD'),
        initial_capital: capital,
        max_positions: maxPositions,
        exit_strategy: strategy,
        tp_multiplier: tpMultiplier,
        trailing_atr_k: trailingAtrK,
        half_exit_pct: halfExitPct,
        score_config: scoreConfig,
      })
      setResult(resp)
      const ps = resp.portfolio_stats
      message.success(`组合回测完成：${ps.num_trades} 笔交易，总收益 ${ps.total_return_pct > 0 ? '+' : ''}${ps.total_return_pct}%`)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '组合回测失败')
    } finally {
      setRunning(false)
    }
  }

  const labelStyle: React.CSSProperties = {
    marginBottom: 4,
    fontSize: 11,
    color: colors.textLabel,
    fontFamily: fonts.mono,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  }

  return (
    <>
      {/* 配置面板 */}
      <div style={{ background: colors.bgSecondary, borderRadius: 8, padding: 20, marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          {/* 候选池选择 + 保存 */}
          <Col xs={24}>
            <div style={labelStyle}>候选股票池</div>
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <Select
                value={selectedPoolId}
                onChange={(v: number | null) => handleSelectPool(v)}
                placeholder="选择已保存的候选池..."
                style={{ flex: 1 }}
                allowClear
                options={pools.map(p => ({ value: p.id, label: p.name }))}
              />
              {selectedPoolId && (
                <Button danger size="small" onClick={() => handleDeletePool(selectedPoolId)}>
                  删除
                </Button>
              )}
            </div>
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <input
                value={poolName}
                onChange={e => setPoolName(e.target.value)}
                placeholder="候选池名称（保存时用）"
                style={{
                  flex: 1,
                  padding: '4px 11px',
                  background: colors.bg,
                  color: colors.textPrimary,
                  border: `1px solid ${colors.border}`,
                  borderRadius: 4,
                  fontSize: 13,
                  fontFamily: fonts.mono,
                  outline: 'none',
                }}
              />
              <Button size="small" loading={savingPool} onClick={handleSavePool}>
                {selectedPoolId ? '更新候选池' : '保存为新候选池'}
              </Button>
            </div>
            <Select
              mode="multiple"
              value={poolCodes}
              onChange={(vals: string[]) => {
                setPoolCodes(vals)
                if (selectedPoolId) setSelectedPoolId(null)
              }}
              onSearch={handlePoolSearch}
              filterOption={false}
              placeholder="输入代码或名称搜索并添加..."
              style={{ width: '100%' }}
              optionLabelProp="label"
              options={poolOptions.map(r => ({
                value: r.code,
                label: `${r.code} ${r.name}`,
              }))}
              tagRender={(props) => {
                const name = codeNameMap[props.value as string]
                const label = name ? `${props.value} ${name}` : props.value
                return (
                  <Tag color="blue" closable onClose={props.onClose} style={{ marginRight: 3 }}>
                    {label}
                  </Tag>
                )
              }}
            />
            {poolCodes.length > 0 && (
              <div style={{ fontSize: 11, color: colors.accent, fontFamily: fonts.mono, marginTop: 4 }}>
                已选 {poolCodes.length} 只股票
              </div>
            )}
          </Col>

          {/* 最大持仓数 + 策略 */}
          <Col xs={24} sm={12}>
            <div style={labelStyle}>最大同时持仓数</div>
            <InputNumber value={maxPositions} onChange={(v: number | null) => setMaxPositions(v ?? 3)} min={1} max={10} style={{ width: '100%' }} />
          </Col>
          <Col xs={24} sm={12}>
            <div style={labelStyle}>出场策略</div>
            <Select
              value={strategy}
              onChange={setStrategy}
              options={portfolioStrategies.map(s => ({ value: s.key, label: s.name }))}
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

          {/* 跟踪止损 ATR 系数（trailing/trailing_boll/half_exit 时显示）*/}
          {(strategy === 'trailing' || strategy === 'trailing_boll' || strategy === 'half_exit') && (
            <Col xs={24} sm={12}>
              <div style={labelStyle}>跟踪止损ATR系数</div>
              <InputNumber value={trailingAtrK} onChange={(v: number | null) => setTrailingAtrK(v ?? 1.0)} min={0.1} step={0.1} style={{ width: '100%' }} />
            </Col>
          )}
          {/* 半仓止盈比例（half_exit 时显示）*/}
          {strategy === 'half_exit' && (
            <Col xs={24} sm={12}>
              <div style={labelStyle}>半仓止盈比例%</div>
              <InputNumber value={halfExitPct} onChange={(v: number | null) => setHalfExitPct(v ?? 50)} min={10} max={100} step={10} style={{ width: '100%' }} />
            </Col>
          )}
        </Row>

        {/* 评分配置 */}
        <Collapse
          ghost
          style={{ marginTop: 12 }}
          items={[{
            key: 'score',
            label: <span style={{ fontSize: 13, fontFamily: fonts.mono, color: colors.accent }}>评分配置（可选，调整信号排序权重）</span>,
            children: scoreLoaded && (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                  <span style={{ fontSize: 11, color: colors.textLabel, fontFamily: fonts.mono }}>信号预设</span>
                  <Select
                    value={scorePreset}
                    onChange={setScorePreset}
                    size="small"
                    style={{ width: 140 }}
                    options={Object.entries(SCORE_PRESETS).map(([k, v]) => ({ value: k, label: v.label }))}
                  />
                  <span style={{ fontSize: 11, color: colors.textMuted, fontFamily: fonts.mono }}>
                    {scorePreset === 'etf' ? 'ETF 波动小，突破参数已调低' : '使用默认个股参数'}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: colors.textMuted, fontFamily: fonts.mono, marginBottom: 12 }}>
                  启用的维度权重会归一化为百分比。关闭的维度不参与评分。
                </div>
                {scoreDims.map(d => (
                  <div key={d.key} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8, padding: '4px 0' }}>
                    <Switch size="small" checked={d.enabled} onChange={(v) => handleDimChange(d.key, 'enabled', v)} />
                    <div style={{ width: 110, fontSize: 12, fontFamily: fonts.mono, color: d.enabled ? colors.textPrimary : colors.textMuted }}>
                      {d.name}
                    </div>
                    <Slider
                      min={0}
                      max={50}
                      step={5}
                      value={d.weight}
                      onChange={(v) => handleDimChange(d.key, 'weight', v)}
                      style={{ flex: 1, margin: '0 8px' }}
                      disabled={!d.enabled}
                    />
                    <div style={{ width: 40, textAlign: 'right', fontSize: 12, fontFamily: fonts.mono, color: colors.accent }}>
                      {d.weight}
                    </div>
                  </div>
                ))}
                <Button size="small" onClick={handleSaveScore} style={{ marginTop: 8 }}>保存评分配置</Button>
              </div>
            ),
          }]}
        />

        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          onClick={handleRun}
          loading={running}
          disabled={running}
          block
          style={{ marginTop: 16, fontFamily: fonts.mono, fontWeight: 600 }}
        >
          {running ? '组合回测中...' : '运行组合回测'}
        </Button>
      </div>

      {/* 结果展示 */}
      {running && (
        <div style={{ textAlign: 'center', padding: 24, color: colors.textMuted, fontFamily: fonts.mono }}>
          组合回测计算中...
        </div>
      )}
      {result && !running && (
        <PortfolioResultView result={result} />
      )}
    </>
  )
}
