/** ETF 列表页 — 左列表 + 右详情面板 */
import { useState, useEffect, useCallback } from 'react'
import { getETFList, type ETFListItem } from '../api/etf'
import { colors, fonts, changeColor } from '../theme/tokens'
import StockDetailPanel from '../components/stock/StockDetailPanel'

const PAGE_SIZE = 50

const ETF_TYPES = [
  { label: '全部', value: '' },
  { label: '股票', value: '股票' },
  { label: '固收', value: '固收' },
  { label: '海外', value: '海外' },
]

export default function ETFListPage() {
  const [selectedCode, setSelectedCode] = useState('')
  const [search, setSearch] = useState('')
  const [etfType, setEtfType] = useState('')
  const [page, setPage] = useState(1)
  const [etfs, setEtfs] = useState<ETFListItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getETFList({
        search: search || undefined,
        etf_type: etfType || undefined,
        page,
        page_size: PAGE_SIZE,
      })
      setEtfs(res.data)
      setTotal(res.total)
      if (res.data.length > 0) {
        setSelectedCode((prev) => prev || res.data[0].code)
      }
    } catch {
      setEtfs([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [search, etfType, page])

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

  const totalPages = Math.ceil(total / PAGE_SIZE)
  const startIndex = (page - 1) * PAGE_SIZE

  return (
    <div style={{ height: '100%', display: 'flex', gap: 0 }}>
      {/* 左侧：ETF 列表 */}
      <div style={{
        width: selectedCode ? '38%' : '100%',
        minWidth: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        padding: '0 4px',
        transition: 'width 0.3s ease',
        borderRight: selectedCode ? `1px solid ${colors.border}` : 'none',
      }}>
        {/* 筛选栏 */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0, flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder="搜索代码 / 名称"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            style={styles.input}
          />
          <div style={{ display: 'flex', gap: 4 }}>
            {ETF_TYPES.map((t) => (
              <button
                key={t.value}
                onClick={() => { setEtfType(t.value); setPage(1) }}
                style={{
                  ...styles.typeBtn,
                  background: etfType === t.value ? colors.accent : colors.bgSecondary,
                  color: etfType === t.value ? '#fff' : colors.textSecondary,
                }}
              >
                {t.label}
              </button>
            ))}
          </div>
          <span style={{ color: colors.textMuted, fontSize: 11 }}>
            共 {total} 只
          </span>
        </div>

        {/* 表格 */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={{ ...styles.th, width: 36 }}>#</th>
                <th style={{ ...styles.th, width: 72 }}>代码</th>
                <th style={{ ...styles.th }}>名称</th>
                <th style={{ ...styles.th, width: 56 }}>类型</th>
                <th style={{ ...styles.th, width: 72, textAlign: 'right' }}>净值</th>
                <th style={{ ...styles.th, width: 72, textAlign: 'right' }}>市价</th>
                <th style={{ ...styles.th, width: 60, textAlign: 'right' }}>折价率</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} style={styles.empty}>加载中...</td>
                </tr>
              ) : etfs.length === 0 ? (
                <tr>
                  <td colSpan={7} style={styles.empty}>暂无数据</td>
                </tr>
              ) : (
                etfs.map((etf, idx) => (
                  <tr
                    key={etf.code}
                    style={{
                      ...styles.row,
                      background: selectedCode === etf.code ? colors.accentBg : undefined,
                    }}
                    onClick={() => setSelectedCode(etf.code)}
                  >
                    <td style={{ ...styles.td, width: 36, color: colors.textMuted }}>
                      {startIndex + idx + 1}
                    </td>
                    <td style={{ ...styles.td, width: 72, fontFamily: fonts.mono, color: colors.accent }}>
                      {etf.code}
                    </td>
                    <td style={styles.td}>
                      <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 140 }}>
                        {etf.name}
                      </div>
                    </td>
                    <td style={{ ...styles.td, width: 56 }}>
                      <span style={typeTagStyle(etf.etf_type)}>{shortType(etf.etf_type)}</span>
                    </td>
                    <td style={{ ...styles.td, width: 72, textAlign: 'right' }}>
                      {fmtNav(etf.nav)}
                    </td>
                    <td style={{ ...styles.td, width: 72, textAlign: 'right' }}>
                      {fmtNav(etf.market_price)}
                    </td>
                    <td style={{
                      ...styles.td,
                      width: 60,
                      textAlign: 'right',
                      color: discountColor(etf.discount_rate),
                    }}>
                      {fmtDiscount(etf.discount_rate)}
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
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} style={styles.pageBtn}>
              上一页
            </button>
            <span style={{ color: colors.textSecondary, fontSize: 12 }}>
              {page} / {totalPages}
            </span>
            <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)} style={styles.pageBtn}>
              下一页
            </button>
          </div>
        )}
      </div>

      {/* 右侧：K 线详情面板（复用 StockDetailPanel，因为 getDaily 已支持 ETF fallback） */}
      {selectedCode && (
        <div style={{ flex: 1, minWidth: 0, padding: '0 12px', overflow: 'auto' }}>
          <StockDetailPanel code={selectedCode} />
        </div>
      )}
    </div>
  )
}

// ---------- 工具函数 ----------
function fmtNav(v: number | null): string {
  if (v == null) return '-'
  return v >= 100 ? v.toFixed(2) : v.toFixed(4)
}

function fmtDiscount(v: number | null): string {
  if (v == null) return '-'
  return (v > 0 ? '+' : '') + v.toFixed(2) + '%'
}

function discountColor(v: number | null): string {
  if (v == null) return colors.textMuted
  if (v > 0) return colors.rise   // 溢价（红）
  if (v < 0) return colors.fall   // 折价（绿）
  return colors.textSecondary
}

function shortType(t: string | null): string {
  if (!t) return '-'
  if (t.includes('固收')) return '固收'
  if (t.includes('海外')) return '海外'
  if (t.includes('股票')) return '股票'
  if (t.includes('商品')) return '商品'
  return t.slice(0, 2)
}

function typeTagStyle(t: string | null): React.CSSProperties {
  const colorMap: Record<string, string> = {
    '股票': '#e06666',
    '固收': '#5cb85c',
    '海外': '#9b59b6',
    '商品': '#f0ad4e',
  }
  const key = t ? (t.includes('固收') ? '固收' : t.includes('海外') ? '海外' : t.includes('商品') ? '商品' : '股票') : '股票'
  const c = colorMap[key] || colors.accent
  return {
    display: 'inline-block',
    fontSize: 10,
    fontFamily: fonts.mono,
    color: c,
    background: c + '22',
    borderRadius: 3,
    padding: '1px 4px',
  }
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
    width: 200,
  },
  typeBtn: {
    padding: '4px 10px',
    borderRadius: 4,
    border: 'none',
    cursor: 'pointer',
    fontSize: 11,
    fontFamily: fonts.mono,
    fontWeight: 600,
    transition: 'all 0.15s',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 12,
  },
  th: {
    padding: '8px 8px',
    color: colors.textLabel,
    fontSize: 10,
    textTransform: 'uppercase' as const,
    letterSpacing: 0.5,
    borderBottom: `1px solid ${colors.border}`,
    position: 'sticky' as const,
    top: 0,
    background: colors.bg,
    fontWeight: 500,
    textAlign: 'left' as const,
  },
  td: {
    padding: '7px 8px',
    color: colors.textSecondary,
    borderBottom: `1px solid ${colors.border}`,
    whiteSpace: 'nowrap' as const,
    fontSize: 12,
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
    fontFamily: fonts.mono,
  },
}
