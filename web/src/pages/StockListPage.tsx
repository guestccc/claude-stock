/** 股票列表页 — 全市场股票筛选（左列表 + 右详情面板） */
import { useState, useEffect, useCallback } from 'react'
import { getStockList, type StockListItem } from '../api/market'
import { colors, fonts } from '../theme/tokens'
import StockDetailPanel from '../components/stock/StockDetailPanel'

// ---------- 常量 ----------
const PAGE_SIZE = 50

type SortField = 'pct_change' | 'close' | 'volume' | 'turnover'

const COLUMNS: {
  key: keyof StockListItem | 'index'
  label: string
  sortable: boolean
  sortKey?: SortField
  align: 'left' | 'right'
  width?: number
}[] = [
  { key: 'index', label: '#', sortable: false, align: 'left', width: 40 },
  { key: 'code', label: '代码', sortable: false, align: 'left', width: 80 },
  { key: 'name', label: '名称', sortable: false, align: 'left', width: 90 },
  { key: 'close', label: '最新价', sortable: true, sortKey: 'close', align: 'right', width: 80 },
  { key: 'pct_change', label: '涨跌幅', sortable: true, sortKey: 'pct_change', align: 'right', width: 80 },
  { key: 'volume', label: '成交量', sortable: true, sortKey: 'volume', align: 'right', width: 100 },
  { key: 'turnover', label: '成交额', sortable: true, sortKey: 'turnover', align: 'right' },
]

// ---------- 工具函数 ----------
function fmtNum(v: number | null, decimals = 2): string {
  return v != null ? v.toLocaleString('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) : '-'
}

function fmtVol(v: number | null): string {
  if (v == null) return '-'
  if (v >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toFixed(0)
}

function pctColor(v: number | null): string {
  if (v == null) return colors.textMuted
  return v > 0 ? colors.down : v < 0 ? colors.up : colors.textMuted
}

// ---------- 组件 ----------
export default function StockListPage() {
  // 选中的股票代码（右侧详情面板）
  const [selectedCode, setSelectedCode] = useState('')

  // 筛选状态
  const [search, setSearch] = useState('')
  const [date, setDate] = useState('')
  const [sortBy, setSortBy] = useState<SortField>('pct_change')
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc')
  const [page, setPage] = useState(1)

  // 数据状态
  const [stocks, setStocks] = useState<StockListItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)

  // 请求数据
  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getStockList({
        date: date || undefined,
        search: search || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        page,
        page_size: PAGE_SIZE,
      })
      setStocks(res.data)
      setTotal(res.total)
      // 默认选中第一只
      if (res.data.length > 0) {
        setSelectedCode((prev) => prev || res.data[0].code)
      }
    } catch {
      setStocks([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [date, search, sortBy, sortOrder, page])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // 搜索防抖
  const [inputVal, setInputVal] = useState(search)
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(inputVal)
      setPage(1)
    }, 400)
    return () => clearTimeout(timer)
  }, [inputVal])

  // 排序切换
  const handleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortOrder((o) => (o === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortBy(field)
      setSortOrder('desc')
    }
    setPage(1)
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)
  const startIndex = (page - 1) * PAGE_SIZE

  return (
    <div style={{ height: '100%', display: 'flex', gap: 0 }}>
      {/* ===== 左侧：股票列表 ===== */}
      <div style={{
        width: selectedCode ? '35%' : '100%',
        minWidth: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        padding: '0 4px',
        transition: 'width 0.3s ease',
        borderRight: selectedCode ? `1px solid ${colors.border}` : 'none',
      }}>
        {/* 筛选栏 */}
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexShrink: 0 }}>
          <input
            type="date"
            value={date}
            onChange={(e) => { setDate(e.target.value); setPage(1) }}
            style={styles.input}
          />
          <input
            type="text"
            placeholder="搜索代码 / 名称"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            style={{ ...styles.input, flex: 1, maxWidth: 240 }}
          />
          <span style={{ color: colors.textMuted, fontSize: 11 }}>
            共 {total} 只
          </span>
        </div>

        {/* 表格 */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          <table style={styles.table}>
            <thead>
              <tr>
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    style={{
                      ...styles.th,
                      textAlign: col.align,
                      width: col.width,
                      cursor: col.sortable ? 'pointer' : 'default',
                      userSelect: 'none',
                    }}
                    onClick={() => col.sortable && col.sortKey && handleSort(col.sortKey)}
                  >
                    {col.label}
                    {col.sortable && sortBy === col.sortKey && (
                      <span style={{ marginLeft: 4, fontSize: 9 }}>
                        {sortOrder === 'desc' ? '▼' : '▲'}
                      </span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={COLUMNS.length} style={styles.empty}>加载中...</td>
                </tr>
              ) : stocks.length === 0 ? (
                <tr>
                  <td colSpan={COLUMNS.length} style={styles.empty}>暂无数据</td>
                </tr>
              ) : (
                stocks.map((s, idx) => (
                  <tr
                    key={s.code}
                    style={{
                      ...styles.row,
                      background: selectedCode === s.code ? colors.accentBg : undefined,
                    }}
                    onClick={() => setSelectedCode(s.code)}
                  >
                    <td style={{ ...styles.td, textAlign: 'left', width: 40, color: colors.textMuted }}>
                      {startIndex + idx + 1}
                    </td>
                    <td style={{ ...styles.td, textAlign: 'left', width: 80, fontFamily: fonts.mono, color: colors.accent }}>
                      {s.code}
                    </td>
                    <td style={{ ...styles.td, textAlign: 'left', width: 90 }}>
                      {s.name}
                    </td>
                    <td style={{ ...styles.td, textAlign: 'right', width: 80 }}>
                      {fmtNum(s.close)}
                    </td>
                    <td style={{ ...styles.td, textAlign: 'right', width: 80, color: pctColor(s.pct_change), fontWeight: 600 }}>
                      {s.pct_change != null ? `${s.pct_change > 0 ? '+' : ''}${s.pct_change.toFixed(2)}%` : '-'}
                    </td>
                    <td style={{ ...styles.td, textAlign: 'right', width: 100 }}>
                      {fmtVol(s.volume)}
                    </td>
                    <td style={{ ...styles.td, textAlign: 'right' }}>
                      {fmtVol(s.turnover)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* 分页 */}
        {totalPages > 1 && (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, padding: '8px 0', flexShrink: 0 }}>
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              style={styles.pageBtn}
            >
              上一页
            </button>
            <span style={{ color: colors.textSecondary, fontSize: 12 }}>
              {page} / {totalPages}
            </span>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              style={styles.pageBtn}
            >
              下一页
            </button>
          </div>
        )}
      </div>

      {/* ===== 右侧：股票详情面板 ===== */}
      {selectedCode && (
        <div style={{
          flex: 1,
          minWidth: 0,
          padding: '0 12px',
          overflow: 'auto',
        }}>
          <StockDetailPanel code={selectedCode} />
        </div>
      )}
    </div>
  )
}

// ---------- 样式 ----------
const styles: Record<string, React.CSSProperties> = {
  input: {
    background: colors.bgSecondary,
    border: `1px solid ${colors.border}`,
    borderRadius: 6,
    color: colors.textPrimary,
    fontSize: 12,
    padding: '6px 10px',
    outline: 'none',
    fontFamily: fonts.mono,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 12,
  },
  th: {
    padding: '8px 10px',
    color: colors.textLabel,
    fontSize: 10,
    textTransform: 'uppercase' as const,
    letterSpacing: 0.5,
    borderBottom: `1px solid ${colors.border}`,
    position: 'sticky' as const,
    top: 0,
    background: colors.bg,
    fontWeight: 500,
  },
  td: {
    padding: '7px 10px',
    color: colors.textSecondary,
    borderBottom: `1px solid ${colors.border}`,
    whiteSpace: 'nowrap' as const,
  },
  row: {
    cursor: 'pointer',
    transition: 'background 0.15s',
  },
  empty: {
    padding: '40px 0',
    textAlign: 'center',
    color: colors.textMuted,
    fontSize: 13,
  },
  pageBtn: {
    background: colors.bgSecondary,
    border: `1px solid ${colors.border}`,
    borderRadius: 6,
    color: colors.textSecondary,
    fontSize: 12,
    padding: '4px 14px',
    cursor: 'pointer',
  },
}
