/** 自选股面板 — 右侧列表，点击切换股票 */
import { useState, useEffect, useCallback } from 'react'
import { PushpinOutlined, PushpinFilled } from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import { colors, changeColor, changeSign } from '../../theme/tokens'
import {
  getWatchlist,
  addWatchlist,
  removeWatchlist,
  updateWatchlist,
  type WatchlistItem,
} from '../../api/watchlist'
import { getQuotes, type QuoteItem } from '../../api/market'

const S = {
  panel: {
    width: 240,
    background: colors.bgCard,
    borderRadius: '0 0 8px 8px',
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden',
    alignSelf: 'flex-start',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 12px',
    borderBottom: `1px solid ${colors.bgHover}`,
  },
  title: {
    fontSize: 12,
    fontWeight: 600,
    color: colors.textSecondary,
    letterSpacing: 0.5,
  },
  count: {
    fontSize: 10,
    color: colors.textMuted,
  },
  list: {
    flex: 1,
    overflowY: 'auto' as const,
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 12px',
    cursor: 'pointer',
    transition: 'background 0.15s',
  },
  rowActive: {
    background: colors.accentBg,
  },
  codeText: {
    fontSize: 12,
    fontWeight: 600,
    color: colors.textSecondary,
    fontFamily: 'inherit',
  },
  nameText: {
    fontSize: 10,
    color: colors.textMuted,
    marginTop: 2,
  },
  priceText: {
    fontSize: 12,
    fontWeight: 600,
    fontFamily: 'inherit',
    textAlign: 'right' as const,
  },
  changeText: {
    fontSize: 10,
    textAlign: 'right' as const,
    marginTop: 2,
  },
  removeBtn: {
    background: 'none',
    border: 'none',
    color: colors.textMuted,
    cursor: 'pointer',
    fontSize: 12,
    padding: '0 2px',
    lineHeight: 1,
    opacity: 0.5,
  },
  addBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '8px 0',
    cursor: 'pointer',
    color: colors.accent,
    fontSize: 11,
    borderTop: `1px solid ${colors.bgHover}`,
    transition: 'background 0.15s',
  },
  empty: {
    padding: '24px 12px',
    textAlign: 'center' as const,
    color: colors.textMuted,
    fontSize: 11,
  },
}

interface WatchlistPanelProps {
  /** 外部传入 key 变化时刷新列表 */
  refreshKey?: number
}

export default function WatchlistPanel({ refreshKey }: WatchlistPanelProps) {
  const { code: currentCode } = useParams()
  const navigate = useNavigate()
  const [items, setItems] = useState<WatchlistItem[]>([])
  const [quotes, setQuotes] = useState<Record<string, QuoteItem>>({})
  const [inList, setInList] = useState(false)

  // 加载自选股列表
  const loadList = useCallback(async () => {
    try {
      const data = await getWatchlist()
      setItems(data)
      // 批量获取行情
      if (data.length > 0) {
        const codes = data.map((i) => i.code)
        const qs = await getQuotes(codes)
        const map: Record<string, QuoteItem> = {}
        qs.forEach((q) => { map[q.code] = q })
        setQuotes(map)
      }
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    loadList()
  }, [loadList, refreshKey])

  // 检查当前股票是否在自选股中
  useEffect(() => {
    setInList(items.some((i) => i.code === currentCode))
  }, [items, currentCode])

  // 添加自选
  const handleAdd = async () => {
    if (!currentCode || inList) return
    try {
      await addWatchlist(currentCode)
      await loadList()
    } catch {
      // 可能已存在
    }
  }

  // 删除自选
  const handleRemove = async (id: number) => {
    try {
      await removeWatchlist(id)
      await loadList()
    } catch {
      // ignore
    }
  }

  // 置顶/取消置顶
  const handlePin = async (item: WatchlistItem) => {
    try {
      if (item.sort_order < 0) {
        // 已置顶 → 取消：设为最大 sort_order + 1（排到最后）
        const maxSort = Math.max(...items.map((i) => i.sort_order))
        await updateWatchlist(item.id, { sort_order: maxSort + 1 })
      } else {
        // 未置顶 → 置顶：设为最小 sort_order - 1
        const minSort = Math.min(...items.map((i) => i.sort_order))
        await updateWatchlist(item.id, { sort_order: minSort - 1 })
      }
      await loadList()
    } catch {
      // ignore
    }
  }

  return (
    <div style={S.panel}>
      <div style={S.header}>
        <span style={S.title}>自选股</span>
        <span style={S.count}>{items.length}</span>
      </div>
      <div style={S.list}>
        {items.length === 0 ? (
          <div style={S.empty}>暂无自选股，点击下方添加当前股票</div>
        ) : (
          items.map((item) => {
            const q = quotes[item.code]
            const isActive = item.code === currentCode
            const chgPct = q?.change_pct
            const pinned = item.sort_order < 0
            return (
              <div
                key={item.id}
                style={{
                  ...S.row,
                  ...(isActive ? S.rowActive : {}),
                  ...(pinned ? { borderTop: `1px solid ${colors.accent}` } : {}),
                }}
                onMouseEnter={(e) => {
                  const el = e.currentTarget as HTMLElement
                  if (!isActive) el.style.background = colors.bgHover
                  // hover 时显示置顶按钮
                  const pinBtn = el.querySelector('.pin-btn') as HTMLElement
                  if (pinBtn && !pinned) pinBtn.style.opacity = '0.5'
                }}
                onMouseLeave={(e) => {
                  const el = e.currentTarget as HTMLElement
                  if (!isActive) el.style.background = 'transparent'
                  const pinBtn = el.querySelector('.pin-btn') as HTMLElement
                  if (pinBtn && !pinned) pinBtn.style.opacity = '0'
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }} onClick={() => navigate(`/market/${item.code}`)}>
                  <div style={S.codeText}>
                    {pinned && <PushpinFilled style={{ color: '#f5a742', fontSize: 10, marginRight: 4 }} />}
                    {item.code}
                  </div>
                  <div style={S.nameText}>{item.name}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  {q?.close != null && (
                    <>
                      <div style={{ ...S.priceText, color: changeColor(chgPct) }}>
                        {q.close.toFixed(2)}
                      </div>
                      <div style={{ ...S.changeText, color: changeColor(chgPct) }}>
                        {changeSign(chgPct)}
                      </div>
                    </>
                  )}
                </div>
                <button
                  className="pin-btn"
                  style={{
                    ...S.removeBtn,
                    opacity: pinned ? 0.9 : 0,
                    color: pinned ? '#f5a742' : colors.textMuted,
                  }}
                  onClick={(e) => { e.stopPropagation(); handlePin(item) }}
                  title={pinned ? '取消置顶' : '置顶'}
                >
                  {pinned ? '★' : '☆'}
                </button>
                <button style={S.removeBtn} onClick={(e) => { e.stopPropagation(); handleRemove(item.id) }} title="删除">
                  ×
                </button>
              </div>
            )
          })
        )}
      </div>
      {currentCode && !inList && (
        <div style={S.addBtn} onClick={handleAdd} onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.background = colors.bgHover} onMouseLeave={(e) => (e.currentTarget as HTMLElement).style.background = 'transparent'}>
          + 添加 {currentCode} 到自选
        </div>
      )}
      {inList && currentCode && (
        <div style={{ ...S.addBtn, color: colors.textMuted, cursor: 'default' }}>
          ✓ 已在自选股中
        </div>
      )}
    </div>
  )
}
