/** 持仓管理页 */
import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  getHoldings,
  getClosedPositions,
  buyStock,
  sellStock,
  getTransactions,
  removeHolding,
  type HoldingsResponse,
  type TransactionItem,
  type ClosedPositionItem,
} from '../api/portfolio'
import { searchStocks, type StockInfo } from '../api/market'
import { colors, fonts, changeColor, changeSign } from '../theme/tokens'

// 别名（向后兼容）
const rise = colors.rise
const fall = colors.fall

// ---------- 工具函数 ----------
function fmt(v: number | null, d = 2): string {
  if (v == null) return '-'
  return v.toLocaleString('zh-CN', { minimumFractionDigits: d, maximumFractionDigits: d })
}
function fmtYuan(v: number | null): string {
  return fmt(v, 2)
}

// ---------- 类型 ----------
type TradeTab = 'buy' | 'sell'
type ActiveSection = 'holdings' | 'transactions'
type SortKey = 'shares' | 'avg_cost' | 'current_price' | 'market_value' | 'profit_amount' | 'profit_pct' | 'first_buy_date'
type SortDir = 'asc' | 'desc'

// ---------- 样式 ----------
const S = {
  page: { maxWidth: 1200, margin: '0 auto' },
  // 汇总区
  summaryCard: {
    background: colors.bgSecondary,
    borderRadius: 8,
    padding: '16px 24px',
    display: 'flex',
    gap: 32,
    marginBottom: 16,
    alignItems: 'center',
    flexWrap: 'wrap' as const,
  },
  summaryItem: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 4,
  },
  summaryLabel: {
    fontSize: 11,
    color: colors.textLabel,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.05em',
    fontFamily: fonts.mono,
  },
  summaryValue: {
    fontSize: 18,
    fontFamily: fonts.mono,
    fontWeight: 600,
    color: colors.textPrimary,
  },
  // 标签切换
  tabs: {
    display: 'flex',
    gap: 4,
    marginBottom: 16,
  },
  tab: (active: boolean) => ({
    padding: '6px 16px',
    borderRadius: 6,
    border: 'none',
    cursor: 'pointer',
    fontSize: 13,
    fontFamily: fonts.mono,
    background: active ? colors.accentBg : 'transparent',
    color: active ? colors.accent : colors.textMuted,
    transition: 'all 0.15s',
  }),
  sectionTab: (active: boolean) => ({
    padding: '6px 16px',
    borderRadius: 6,
    border: 'none',
    cursor: 'pointer',
    fontSize: 13,
    fontFamily: fonts.mono,
    background: active ? colors.bgSecondary : 'transparent',
    color: active ? colors.textPrimary : colors.textMuted,
  }),
  // 持仓表格
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    marginBottom: 16,
    fontSize: 13,
    fontFamily: fonts.mono,
  },
  th: {
    padding: '8px 12px',
    textAlign: 'left' as const,
    color: colors.textLabel,
    fontSize: 11,
    borderBottom: `1px solid ${colors.border}`,
    whiteSpace: 'nowrap' as const,
  },
  thRight: { textAlign: 'right' as const },
  td: {
    padding: '10px 12px',
    borderBottom: `1px solid ${colors.border}`,
    color: colors.textPrimary,
  },
  tdRight: { textAlign: 'right' as const },
  tr: {
    transition: 'background 0.1s',
    cursor: 'pointer',
  },
  // 交易面板
  tradePanel: {
    background: colors.bgSecondary,
    borderRadius: 8,
    padding: 20,
    marginBottom: 16,
  },
  tradeGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 16,
    marginBottom: 16,
  },
  field: { display: 'flex', flexDirection: 'column' as const, gap: 6 },
  label: {
    fontSize: 11,
    color: colors.textLabel,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.05em',
    fontFamily: fonts.mono,
  },
  input: {
    background: colors.bg,
    border: `1px solid ${colors.border}`,
    borderRadius: 6,
    padding: '8px 12px',
    color: colors.textPrimary,
    fontSize: 13,
    fontFamily: fonts.mono,
    outline: 'none',
    width: '100%',
    boxSizing: 'border-box' as const,
  },
  select: {
    background: colors.bg,
    border: `1px solid ${colors.border}`,
    borderRadius: 6,
    padding: '8px 12px',
    color: colors.textPrimary,
    fontSize: 13,
    fontFamily: fonts.mono,
    outline: 'none',
    width: '100%',
    boxSizing: 'border-box' as const,
    cursor: 'pointer',
  },
  btn: (color: string) => ({
    padding: '10px 0',
    borderRadius: 6,
    border: 'none',
    cursor: 'pointer',
    fontSize: 14,
    fontFamily: fonts.mono,
    fontWeight: 600,
    background: color,
    color: '#fff',
    width: '100%',
    transition: 'opacity 0.15s',
  }),
  btnDanger: {
    padding: '4px 10px',
    borderRadius: 4,
    border: `1px solid ${colors.fall}`,
    background: 'transparent',
    color: colors.fall,
    cursor: 'pointer',
    fontSize: 12,
    fontFamily: fonts.mono,
  },
  btnExpand: {
    padding: '4px 10px',
    borderRadius: 4,
    border: `1px solid ${colors.accent}`,
    background: 'transparent',
    color: colors.accent,
    cursor: 'pointer',
    fontSize: 12,
    fontFamily: fonts.mono,
  },
  // 搜索下拉
  searchWrap: { position: 'relative' as const },
  searchDropdown: {
    position: 'absolute' as const,
    top: '100%',
    left: 0,
    right: 0,
    background: colors.bgCard,
    border: `1px solid ${colors.border}`,
    borderRadius: 6,
    zIndex: 100,
    maxHeight: 200,
    overflowY: 'auto' as const,
    marginTop: 4,
  },
  searchItem: {
    padding: '8px 12px',
    cursor: 'pointer',
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: 13,
    fontFamily: fonts.mono,
    color: colors.textPrimary,
  },
  // 消息
  msg: (type: 'success' | 'error') => ({
    padding: '8px 12px',
    borderRadius: 6,
    fontSize: 13,
    fontFamily: fonts.mono,
    marginBottom: 12,
    background: type === 'success' ? colors.riseBg : colors.fallBg,
    color: type === 'success' ? colors.rise : colors.fall,
    border: `1px solid ${type === 'success' ? colors.up : colors.down}`,
  }),
  // 空状态
  empty: {
    textAlign: 'center' as const,
    padding: 48,
    color: colors.textMuted,
    fontFamily: fonts.mono,
    fontSize: 13,
  },
  // 加载
  loading: {
    textAlign: 'center' as const,
    padding: 24,
    color: colors.textMuted,
    fontFamily: fonts.mono,
  },
}

// ---------- 组件 ----------
export default function PortfolioPage() {
  const [section, setSection] = useState<ActiveSection>('holdings')
  const [tradeTab, setTradeTab] = useState<TradeTab>('buy')
  const [holdings, setHoldings] = useState<HoldingsResponse | null>(null)
  const [closedPositions, setClosedPositions] = useState<ClosedPositionItem[]>([])
  const [transactions, setTransactions] = useState<TransactionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // 交易表单
  const [selectedStock, setSelectedStock] = useState<StockInfo | null>(null)
  const [tradeCode, setTradeCode] = useState('')
  const [tradeName, setTradeName] = useState('')
  const [tradeShares, setTradeShares] = useState('')
  const [tradePrice, setTradePrice] = useState('')
  const [tradeFee, setTradeFee] = useState('')
  const [tradeDate, setTradeDate] = useState('')
  const [tradeNote, setTradeNote] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // 排序
  const [sortKey, setSortKey] = useState<SortKey>('profit_pct')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const sortedHoldings = React.useMemo(() => {
    if (!holdings?.holdings) return []
    const list = [...holdings.holdings]
    list.sort((a, b) => {
      const va = a[sortKey] ?? 0
      const vb = b[sortKey] ?? 0
      if (typeof va === 'string' && typeof vb === 'string') {
        return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va)
      }
      return sortDir === 'asc' ? (va as number) - (vb as number) : (vb as number) - (va as number)
    })
    return list
  }, [holdings, sortKey, sortDir])

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const sortIndicator = (key: SortKey) => {
    if (sortKey !== key) return <span style={{ opacity: 0.3, marginLeft: 2 }}>↕</span>
    return sortDir === 'asc'
      ? <span style={{ marginLeft: 2 }}>↑</span>
      : <span style={{ marginLeft: 2 }}>↓</span>
  }

  const thSortable = (key: SortKey, label: string) => (
    <th style={{ ...S.th, ...S.thRight, cursor: 'pointer', userSelect: 'none' as const }} onClick={() => toggleSort(key)}>
      {label}{sortIndicator(key)}
    </th>
  )

  // 展开持仓的交易记录
  const [expandedCode, setExpandedCode] = useState<string | null>(null)
  const [stockTxs, setStockTxs] = useState<TransactionItem[]>([])
  const [txLoading, setTxLoading] = useState(false)

  // 股票搜索
  const [searchResults, setSearchResults] = useState<StockInfo[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const searchRef = useRef<HTMLDivElement>(null)

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [h, t, c] = await Promise.all([
        getHoldings(),
        getTransactions({ limit: 50 }),
        getClosedPositions(),
      ])
      setHoldings(h)
      setTransactions(t.transactions)
      setClosedPositions(c.items)
    } catch (e) {
      showMsg('error', '加载数据失败: ' + (e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  // 点击外部关闭搜索下拉
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setSearchResults([])
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // 股票搜索
  const handleCodeChange = (val: string) => {
    setTradeCode(val)
    setTradeName('')
    setSelectedStock(null)
    if (searchTimer.current) clearTimeout(searchTimer.current)
    if (!val.trim()) { setSearchResults([]); return }
    setSearchLoading(true)
    searchTimer.current = setTimeout(async () => {
      try {
        const results = await searchStocks(val)
        setSearchResults(results.slice(0, 8))
      } catch {
        setSearchResults([])
      } finally {
        setSearchLoading(false)
      }
    }, 300)
  }

  const selectStock = (s: StockInfo) => {
    setTradeCode(s.code)
    setTradeName(s.name)
    setSelectedStock(s)
    setSearchResults([])
    // 复用当前持仓的平均成本作为默认价格
    if (holdings) {
      const h = holdings.holdings.find(h => h.code === s.code)
      if (h) setTradePrice(h.avg_cost.toString())
    }
  }

  const showMsg = (type: 'success' | 'error', text: string) => {
    setMsg({ type, text })
    setTimeout(() => setMsg(null), 4000)
  }

  const resetForm = () => {
    setTradeCode('')
    setTradeName('')
    setTradeShares('')
    setTradePrice('')
    setTradeFee('')
    setTradeDate('')
    setTradeNote('')
    setSelectedStock(null)
    setSearchResults([])
  }

  const handleSubmit = async () => {
    if (!tradeCode || !tradeShares || !tradePrice) {
      showMsg('error', '请填写完整的交易信息')
      return
    }
    const shares = parseInt(tradeShares)
    const price = parseFloat(tradePrice)
    if (isNaN(shares) || shares <= 0) { showMsg('error', '数量必须是正整数'); return }
    if (isNaN(price) || price <= 0) { showMsg('error', '价格必须是正数'); return }

    setSubmitting(true)
    try {
      if (tradeTab === 'buy') {
        await buyStock({
          code: tradeCode,
          shares,
          price,
          fee: parseFloat(tradeFee) || 0,
          date: tradeDate || undefined,
          note: tradeNote,
        })
        showMsg('success', `买入成功：${tradeName || tradeCode} × ${shares}股 @ ${fmtYuan(price)}`)
      } else {
        await sellStock({
          code: tradeCode,
          shares,
          price,
          fee: parseFloat(tradeFee) || 0,
          date: tradeDate || undefined,
          note: tradeNote,
        })
        showMsg('success', `卖出成功：${tradeName || tradeCode} × ${shares}股 @ ${fmtYuan(price)}`)
      }
      resetForm()
      await loadData()
    } catch (e: any) {
      showMsg('error', (e as any)?.response?.data?.detail || (e as Error).message || '操作失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleRemoveHolding = async (code: string, name: string) => {
    if (!confirm(`确定清仓 ${name} (${code})？`)) return
    try {
      await removeHolding(code)
      showMsg('success', `已清仓 ${name}`)
      await loadData()
    } catch (e) {
      showMsg('error', (e as Error).message)
    }
  }

  const toggleExpand = async (code: string) => {
    if (expandedCode === code) {
      setExpandedCode(null)
      setStockTxs([])
      return
    }
    setExpandedCode(code)
    setTxLoading(true)
    try {
      const res = await getTransactions({ code, limit: 100 })
      setStockTxs(res.transactions)
    } catch {
      setStockTxs([])
    } finally {
      setTxLoading(false)
    }
  }

  const summary = holdings?.summary

  return (
    <div style={S.page}>
      {/* 汇总 */}
      <div style={S.summaryCard}>
        {[
          { label: '总成本', value: fmtYuan(summary?.total_cost ?? null) },
          { label: '总市值', value: fmtYuan(summary?.total_market_value ?? null) },
          {
            label: '总盈亏',
            value: changeSign(summary?.total_profit_pct ?? null),
            color: changeColor(summary?.total_profit_amount ?? null),
          },
          {
            label: '浮盈金额',
            value: ((summary?.total_profit_amount ?? 0) >= 0 ? '+' : '') + fmtYuan(summary?.total_profit_amount ?? null),
            color: changeColor(summary?.total_profit_amount ?? null),
          },
          { label: '持仓数', value: String(summary?.holding_count ?? 0) },
        ].map(item => (
          <div key={item.label} style={S.summaryItem}>
            <span style={S.summaryLabel}>{item.label}</span>
            <span style={{ ...S.summaryValue, color: item.color || S.summaryValue.color }}>
              {loading ? '-' : item.value}
            </span>
          </div>
        ))}
      </div>

      {/* 区块切换 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={S.tabs}>
          <button style={S.sectionTab(section === 'holdings')} onClick={() => setSection('holdings')}>持仓</button>
          <button style={S.sectionTab(section === 'transactions')} onClick={() => setSection('transactions')}>交易记录</button>
        </div>
      </div>

      {section === 'holdings' && (
        <>
          {/* 交易面板 */}
          <div style={S.tradePanel}>
            <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              <button
                style={S.tab(tradeTab === 'buy')}
                onClick={() => { setTradeTab('buy'); resetForm() }}
              >
                买入
              </button>
              <button
                style={S.tab(tradeTab === 'sell')}
                onClick={() => { setTradeTab('sell'); resetForm() }}
              >
                卖出
              </button>
            </div>

            {msg && <div style={S.msg(msg.type)}>{msg.text}</div>}

            <div style={S.tradeGrid}>
              {/* 股票搜索 */}
              <div style={S.field}>
                <span style={S.label}>股票代码/名称</span>
                <div ref={searchRef} style={S.searchWrap}>
                  <input
                    style={S.input}
                    placeholder="输入代码或名称搜索..."
                    value={tradeCode}
                    onChange={e => handleCodeChange(e.target.value)}
                    onFocus={() => tradeCode && handleCodeChange(tradeCode)}
                  />
                  {searchResults.length > 0 && (
                    <div style={S.searchDropdown}>
                      {searchResults.map(r => (
                        <div
                          key={r.code}
                          style={S.searchItem}
                          onMouseDown={() => selectStock(r)}
                        >
                          <span>{r.code}</span>
                          <span style={{ color: colors.textMuted }}>{r.name}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                {tradeName && <span style={{ fontSize: 11, color: colors.accent, fontFamily: fonts.mono }}>{tradeName}</span>}
              </div>

              <div style={S.field}>
                <span style={S.label}>数量（股）</span>
                <input
                  style={S.input}
                  type="number"
                  min="1"
                  placeholder="100"
                  value={tradeShares}
                  onChange={e => setTradeShares(e.target.value)}
                />
              </div>

              <div style={S.field}>
                <span style={S.label}>价格（元）</span>
                <input
                  style={S.input}
                  type="number"
                  min="0.01"
                  step="0.01"
                  placeholder="10.00"
                  value={tradePrice}
                  onChange={e => setTradePrice(e.target.value)}
                />
              </div>

              <div style={S.field}>
                <span style={S.label}>费用/税费（元）</span>
                <input
                  style={S.input}
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="0"
                  value={tradeFee}
                  onChange={e => setTradeFee(e.target.value)}
                />
              </div>

              <div style={S.field}>
                <span style={S.label}>日期（选填，默认今天）</span>
                <input
                  style={S.input}
                  type="date"
                  value={tradeDate}
                  onChange={e => setTradeDate(e.target.value)}
                />
              </div>

              <div style={{ gridColumn: '1 / -1', ...S.field }}>
                <span style={S.label}>备注（选填）</span>
                <input
                  style={S.input}
                  placeholder="备注..."
                  value={tradeNote}
                  onChange={e => setTradeNote(e.target.value)}
                />
              </div>
            </div>

            {tradeShares && tradePrice && (
              <div style={{ textAlign: 'right', fontSize: 12, color: colors.textMuted, fontFamily: fonts.mono, marginBottom: 12 }}>
                成交金额 ≈ {fmtYuan(parseFloat(tradeShares) * parseFloat(tradePrice))} 元
              </div>
            )}

            <button
              style={S.btn(tradeTab === 'buy' ? colors.rise : colors.fall)}
              onClick={handleSubmit}
              disabled={submitting}
            >
              {submitting ? '处理中...' : tradeTab === 'buy' ? `确认买入` : `确认卖出`}
            </button>
          </div>

          {/* 持仓列表 */}
          {loading ? (
            <div style={S.loading}>加载中...</div>
          ) : holdings?.holdings.length === 0 ? (
            <div style={S.empty}>暂无持仓，先买入股票吧</div>
          ) : (
            <table style={S.table}>
              <thead>
                <tr>
                  <th style={S.th}>代码</th>
                  <th style={S.th}>名称</th>
                  {thSortable('shares', '持仓(股)')}
                  {thSortable('avg_cost', '成本价')}
                  {thSortable('current_price', '现价')}
                  {thSortable('market_value', '市值')}
                  {thSortable('profit_amount', '盈亏额')}
                  {thSortable('profit_pct', '盈亏%')}
                  {thSortable('first_buy_date', '首买日期')}
                  <th style={{ ...S.th, textAlign: 'right' as const }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {sortedHoldings.map(h => (
                  <React.Fragment key={h.code}>
                  <tr
                    key={h.code}
                    style={S.tr}
                    onMouseEnter={e => (e.currentTarget.style.background = colors.bgHover)}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td style={{ ...S.td, color: colors.accent, cursor: 'pointer' }} onClick={() => toggleExpand(h.code)}>{h.code}</td>
                    <td style={{ ...S.td, color: colors.accent, cursor: 'pointer' }} onClick={() => toggleExpand(h.code)}>{h.name}</td>
                    <td style={{ ...S.td, ...S.tdRight }}>{h.shares.toLocaleString()}</td>
                    <td style={{ ...S.td, ...S.tdRight }}>{fmtYuan(h.avg_cost)}</td>
                    <td style={{ ...S.td, ...S.tdRight }}>{fmtYuan(h.current_price)}</td>
                    <td style={{ ...S.td, ...S.tdRight }}>{fmtYuan(h.market_value)}</td>
                    <td style={{ ...S.td, ...S.tdRight, color: changeColor(h.profit_amount) }}>
                      {h.profit_amount != null ? (h.profit_amount >= 0 ? '+' : '') + fmtYuan(h.profit_amount) : '-'}
                    </td>
                    <td style={{ ...S.td, ...S.tdRight, color: changeColor(h.profit_pct) }}>
                      {changeSign(h.profit_pct)}
                    </td>
                    <td style={{ ...S.td, ...S.tdRight, color: colors.textMuted }}>{h.first_buy_date}</td>
                    <td style={{ ...S.td, textAlign: 'right' as const }}>
                      <button style={S.btnExpand} onClick={() => toggleExpand(h.code)}>
                        {expandedCode === h.code ? '收起' : '交易'}
                      </button>
                      <button style={{ ...S.btnDanger, marginLeft: 8 }} onClick={() => handleRemoveHolding(h.code, h.name)}>
                        清仓
                      </button>
                    </td>
                  </tr>
                  {expandedCode === h.code && (
                    <tr key={`${h.code}-tx`}>
                      <td colSpan={10} style={{ padding: '12px 12px 16px', background: colors.bg }}>
                        {txLoading ? (
                          <div style={{ color: colors.textMuted, fontFamily: fonts.mono }}>加载中...</div>
                        ) : stockTxs.length === 0 ? (
                          <div style={{ color: colors.textMuted, fontFamily: fonts.mono }}>暂无交易记录</div>
                        ) : (
                          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, fontFamily: fonts.mono }}>
                            <thead>
                              <tr>
                                <th style={{ ...S.th, padding: '4px 8px' }}>日期</th>
                                <th style={{ ...S.th, padding: '4px 8px' }}>方向</th>
                                <th style={{ ...S.th, padding: '4px 8px', textAlign: 'right' }}>价格</th>
                                <th style={{ ...S.th, padding: '4px 8px', textAlign: 'right' }}>数量</th>
                                <th style={{ ...S.th, padding: '4px 8px', textAlign: 'right' }}>金额</th>
                                <th style={{ ...S.th, padding: '4px 8px', textAlign: 'right' }}>费用</th>
                                <th style={{ ...S.th, padding: '4px 8px' }}>备注</th>
                              </tr>
                            </thead>
                            <tbody>
                              {stockTxs.map(tx => (
                                <tr key={tx.id}>
                                  <td style={{ ...S.td, padding: '4px 8px' }}>{tx.date}</td>
                                  <td style={{ ...S.td, padding: '4px 8px', color: tx.type === 'buy' ? colors.rise : colors.fall, fontWeight: 600 }}>
                                    {tx.type === 'buy' ? '买入' : '卖出'}
                                  </td>
                                  <td style={{ ...S.td, padding: '4px 8px', textAlign: 'right' }}>{fmtYuan(tx.price)}</td>
                                  <td style={{ ...S.td, padding: '4px 8px', textAlign: 'right' }}>{tx.shares.toLocaleString()}</td>
                                  <td style={{ ...S.td, padding: '4px 8px', textAlign: 'right' }}>{fmtYuan(tx.amount)}</td>
                                  <td style={{ ...S.td, padding: '4px 8px', textAlign: 'right', color: colors.textMuted }}>{tx.fee > 0 ? fmtYuan(tx.fee) : '-'}</td>
                                  <td style={{ ...S.td, padding: '4px 8px', color: colors.textMuted }}>{tx.note || '-'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}
                      </td>
                    </tr>
                  )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          )}

          {/* 已清仓 */}
          {closedPositions.length > 0 && (
            <>
              <div style={{ marginTop: 32, marginBottom: 12, fontSize: 13, color: colors.textMuted, fontFamily: fonts.mono }}>已清仓（{closedPositions.length}只）</div>
              <table style={S.table}>
                <thead>
                  <tr>
                    <th style={S.th}>代码</th>
                    <th style={S.th}>名称</th>
                    <th style={{ ...S.th, ...S.thRight }}>累计买入</th>
                    <th style={{ ...S.th, ...S.thRight }}>累计卖出</th>
                    <th style={{ ...S.th, ...S.thRight }}>盈亏额</th>
                    <th style={{ ...S.th, ...S.thRight }}>盈亏%</th>
                    <th style={{ ...S.th, ...S.thRight }}>最后卖出</th>
                  </tr>
                </thead>
                <tbody>
                  {closedPositions.map(c => (
                    <tr key={c.code}
                      style={S.tr}
                      onMouseEnter={e => (e.currentTarget.style.background = colors.bgHover)}
                      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                    >
                      <td style={S.td}>{c.code}</td>
                      <td style={{ ...S.td, color: colors.accent }}>{c.name}</td>
                      <td style={{ ...S.td, ...S.tdRight }}>{fmtYuan(c.total_buy)}</td>
                      <td style={{ ...S.td, ...S.tdRight }}>{fmtYuan(c.total_sell)}</td>
                      <td style={{ ...S.td, ...S.tdRight, color: changeColor(c.profit) }}>
                        {(c.profit >= 0 ? '+' : '') + fmtYuan(c.profit)}
                      </td>
                      <td style={{ ...S.td, ...S.tdRight, color: changeColor(c.profit) }}>
                        {changeSign(c.profit_pct)}
                      </td>
                      <td style={{ ...S.td, ...S.tdRight, color: colors.textMuted }}>{c.last_sell_date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </>
      )}

      {section === 'transactions' && (
        <>
          {transactions.length === 0 ? (
            <div style={S.empty}>暂无交易记录</div>
          ) : (
            <table style={S.table}>
              <thead>
                <tr>
                  <th style={S.th}>日期</th>
                  <th style={S.th}>代码</th>
                  <th style={S.th}>名称</th>
                  <th style={{ ...S.th, ...S.thRight }}>方向</th>
                  <th style={{ ...S.th, ...S.thRight }}>数量</th>
                  <th style={{ ...S.th, ...S.thRight }}>价格</th>
                  <th style={{ ...S.th, ...S.thRight }}>金额</th>
                  <th style={{ ...S.th, ...S.thRight }}>费用</th>
                  <th style={S.th}>备注</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map(tx => (
                  <tr
                    key={tx.id}
                    style={S.tr}
                    onMouseEnter={e => (e.currentTarget.style.background = colors.bgHover)}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td style={S.td}>{tx.date}</td>
                    <td style={S.td}>{tx.code}</td>
                    <td style={{ ...S.td, color: colors.accent }}>{tx.name}</td>
                    <td style={{
                      ...S.td, ...S.tdRight,
                      color: tx.type === 'buy' ? colors.rise : colors.fall,
                      fontWeight: 600,
                    }}>
                      {tx.type === 'buy' ? '买入' : '卖出'}
                    </td>
                    <td style={{ ...S.td, ...S.tdRight }}>{tx.shares.toLocaleString()}</td>
                    <td style={{ ...S.td, ...S.tdRight }}>{fmtYuan(tx.price)}</td>
                    <td style={{ ...S.td, ...S.tdRight }}>{fmtYuan(tx.amount)}</td>
                    <td style={{ ...S.td, ...S.tdRight, color: colors.textMuted }}>{tx.fee > 0 ? fmtYuan(tx.fee) : '-'}</td>
                    <td style={{ ...S.td, color: colors.textMuted }}>{tx.note || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  )
}
