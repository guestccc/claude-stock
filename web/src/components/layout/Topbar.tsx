/** 顶部栏 — 标题 + 搜索 + 指数概览 */
import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { colors } from '../../theme/tokens'
import { searchStocks, type StockInfo } from '../../api/market'

const styles = {
  topbar: {
    height: 48,
    background: colors.bgSecondary,
    display: 'flex',
    alignItems: 'center',
    padding: '0 16px',
    gap: 16,
  },
  title: {
    color: colors.accent,
    fontSize: 13,
    fontWeight: 600,
    letterSpacing: 0.5,
    whiteSpace: 'nowrap' as const,
  },
  searchWrap: {
    flex: 1,
    maxWidth: 320,
    position: 'relative' as const,
  },
  searchInput: {
    width: '100%',
    background: colors.bgHover,
    border: 'none',
    borderRadius: 6,
    padding: '6px 12px',
    color: colors.textSecondary,
    fontSize: 12,
    outline: 'none',
    fontFamily: 'inherit',
  },
  dropdown: {
    position: 'absolute' as const,
    top: '100%',
    left: 0,
    right: 0,
    background: colors.bgSecondary,
    borderRadius: '0 0 6px 6px',
    zIndex: 100,
    maxHeight: 240,
    overflowY: 'auto' as const,
  },
  dropdownItem: {
    padding: '8px 12px',
    fontSize: 12,
    color: colors.textSecondary,
    cursor: 'pointer',
    display: 'flex',
    justifyContent: 'space-between' as const,
  },
  tag: {
    fontSize: 11,
    padding: '3px 8px',
    borderRadius: 4,
    color: colors.up,
    background: colors.upBg,
  },
  tagRed: {
    color: colors.down,
    background: colors.downBg,
  },
}

export default function Topbar() {
  const [keyword, setKeyword] = useState('')
  const [results, setResults] = useState<StockInfo[]>([])
  const [showDropdown, setShowDropdown] = useState(false)
  const navigate = useNavigate()
  const wrapRef = useRef<HTMLDivElement>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout>>()

  // 搜索防抖
  useEffect(() => {
    if (!keyword.trim()) {
      setResults([])
      setShowDropdown(false)
      return
    }
    clearTimeout(timerRef.current)
    timerRef.current = setTimeout(async () => {
      try {
        const data = await searchStocks(keyword)
        setResults(data)
        setShowDropdown(data.length > 0)
      } catch {
        setResults([])
      }
    }, 300)
    return () => clearTimeout(timerRef.current)
  }, [keyword])

  // 点击外部关闭下拉
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const handleSelect = (code: string) => {
    setShowDropdown(false)
    setKeyword('')
    navigate(`/market/${code}`)
  }

  return (
    <div style={styles.topbar}>
      <span style={styles.title}>📈 A股量化终端</span>
      <div ref={wrapRef} style={styles.searchWrap}>
        <input
          style={styles.searchInput}
          placeholder="输入股票代码或名称..."
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onFocus={() => results.length > 0 && setShowDropdown(true)}
        />
        {showDropdown && (
          <div style={styles.dropdown}>
            {results.map((item) => (
              <div
                key={item.code}
                style={styles.dropdownItem}
                onClick={() => handleSelect(item.code)}
                onMouseEnter={(e) =>
                  ((e.target as HTMLElement).style.background = colors.bgHover)
                }
                onMouseLeave={(e) =>
                  ((e.target as HTMLElement).style.background = 'transparent')
                }
              >
                <span>
                  <span style={{ color: colors.accent }}>{item.code}</span>
                  &nbsp;{item.name}
                </span>
                <span style={{ color: colors.textLabel, fontSize: 10 }}>{item.type}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      <div style={{ marginLeft: 'auto', display: 'flex', gap: 12 }}>
        <span style={{ ...styles.tag, fontSize: 10 }}>
          上证 3284.21 <span style={{ color: colors.up }}>+0.83%</span>
        </span>
        <span style={{ ...styles.tag, ...styles.tagRed, fontSize: 10 }}>
          深证 10578.43 <span style={{ color: colors.down }}>-0.21%</span>
        </span>
      </div>
    </div>
  )
}
