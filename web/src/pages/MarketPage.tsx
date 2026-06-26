/** 行情页 — 左侧 K 线详情 + 右侧自选股/持仓 + AI 聊天 */
import { useParams } from 'react-router-dom'
import { useState, useEffect, useCallback } from 'react'
import WatchlistPanel from '../components/stock/WatchlistPanel'
import HoldingsPanel from '../components/stock/HoldingsPanel'
import StockDetailPanel from '../components/stock/StockDetailPanel'
import AIChatPanel from '../components/ai-chat/AIChatPanel'
import { colors, fonts } from '../theme/tokens'
import type { ChatAction } from '../types/chat'
import { buildMarkLines } from '../components/ai-chat/actions/registry'

type RightTab = 'watchlist' | 'holdings'

const tabItems: { key: RightTab; label: string }[] = [
  { key: 'watchlist', label: '自选股' },
  { key: 'holdings', label: '持仓' },
]

const S = {
  tabBar: {
    display: 'flex',
    background: colors.bgCard,
    borderRadius: '8px 8px 0 0',
    borderBottom: `1px solid ${colors.bgHover}`,
  },
  tab: (active: boolean) => ({
    flex: 1,
    padding: '8px 0',
    textAlign: 'center' as const,
    fontSize: 11,
    fontFamily: fonts.mono,
    fontWeight: 600,
    color: active ? colors.accent : colors.textMuted,
    cursor: 'pointer',
    borderBottom: active ? `2px solid ${colors.accent}` : '2px solid transparent',
    transition: 'color 0.15s, border-color 0.15s',
  }),
  fab: {
    position: 'fixed' as const,
    right: 20,
    bottom: 20,
    width: 48,
    height: 48,
    borderRadius: '50%',
    background: colors.accent,
    border: 'none',
    color: '#fff',
    fontSize: 20,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 4px 16px rgba(122,164,245,0.4)',
    zIndex: 999,
    fontFamily: fonts.mono,
    transition: 'transform 0.15s, box-shadow 0.15s',
  },
}

export default function MarketPage() {
  const { code: urlCode } = useParams()
  const [code, setCode] = useState(urlCode || '600584')
  const [wlRefresh, setWlRefresh] = useState(0)
  const [activeTab, setActiveTab] = useState<RightTab>('watchlist')

  // AI 聊天面板状态
  const [chatVisible, setChatVisible] = useState(false)

  // K 线图额外标记线（止盈止损线）
  const [extraMarkLines, setExtraMarkLines] = useState<object[]>([])

  useEffect(() => {
    if (urlCode) setCode(urlCode)
  }, [urlCode])

  // 切换股票时清空标记线
  useEffect(() => {
    setExtraMarkLines([])
  }, [code])

  const handleWatchlistChange = useCallback(() => {
    setWlRefresh((k) => k + 1)
  }, [])

  // AI Action 执行后的回调 → 通过注册表生成 K 线图标记线
  const handleChatAction = useCallback((action: ChatAction, result: any) => {
    if (result.success) {
      const lines = buildMarkLines(action.type, action.data)
      if (lines.length > 0) {
        setExtraMarkLines((prev) => [...prev, ...lines])
      }
    }
  }, [])

  return (
    <div style={{ display: 'flex', gap: 16, height: '100%' }}>
      {/* 左侧：指标卡片 + K 线图 */}
      <StockDetailPanel
        code={code}
        onWatchlistChange={handleWatchlistChange}
        extraMarkLines={extraMarkLines}
      />

      {/* 右侧：自选股 / 持仓 Tab */}
      <div style={{ width: 240, alignSelf: 'flex-start', display: 'flex', flexDirection: 'column' }}>
        <div style={S.tabBar}>
          {tabItems.map((t) => (
            <div key={t.key} style={S.tab(activeTab === t.key)} onClick={() => setActiveTab(t.key)}>
              {t.label}
            </div>
          ))}
        </div>
        {activeTab === 'watchlist' ? (
          <WatchlistPanel refreshKey={wlRefresh} />
        ) : (
          <HoldingsPanel />
        )}
      </div>

      {/* AI 聊天浮动按钮（面板未打开时显示） */}
      {!chatVisible && (
        <button
          style={S.fab}
          onClick={() => setChatVisible(true)}
          title="AI 分析助手"
        >
          AI
        </button>
      )}

      {/* AI 聊天面板 */}
      <AIChatPanel
        code={code}
        visible={chatVisible}
        onClose={() => setChatVisible(false)}
        onActionExecuted={handleChatAction}
      />
    </div>
  )
}
