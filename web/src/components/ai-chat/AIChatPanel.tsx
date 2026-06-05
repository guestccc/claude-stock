/** AI 智能聊天面板 — 悬浮抽屉式 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { colors, fonts } from '../../theme/tokens'
import { useChatStream } from '../../hooks/useChatStream'
import type { ChatAction } from '../../types/chat'
import ChatMessageItem from './ChatMessage'
import SimpleMarkdown from './SimpleMarkdown'

interface Props {
  /** 当前股票代码 */
  code: string
  /** 用户持仓信息（可选，从 holdings 中读取） */
  position?: { cost: number; quantity: number }
  /** Action 执行后的回调（用于触发 K 线图画线等） */
  onActionExecuted?: (action: ChatAction, result: any) => void
  /** 显隐控制 */
  visible: boolean
  /** 关闭面板 */
  onClose: () => void
}

export default function AIChatPanel({ code, position, onActionExecuted, visible, onClose }: Props) {
  const [input, setInput] = useState('')
  const { messages, streamingText, isLoading, sendMessage, abort, clear } = useChatStream()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingText])

  // 面板打开时聚焦输入框
  useEffect(() => {
    if (visible) {
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [visible])

  // 发送消息
  const handleSend = useCallback(() => {
    const text = input.trim()
    if (!text || isLoading) return

    // 构建历史消息（最近的 20 条）
    const history = messages.slice(-20).map((m) => ({
      role: m.role,
      content: m.content,
    }))

    sendMessage({
      code,
      message: text,
      history,
      position: position || undefined,
    })
    setInput('')
  }, [input, isLoading, messages, code, position, sendMessage])

  // 回车发送（Shift+回车换行）
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Action 执行回调
  const handleActionExecuted = (action: ChatAction, result: any) => {
    onActionExecuted?.(action, result)
  }

  if (!visible) return null

  return (
    <div
      style={{
        position: 'fixed',
        right: 20,
        bottom: 20,
        width: 420,
        height: 560,
        background: colors.bgSecondary,
        border: `1px solid ${colors.border}`,
        borderRadius: 12,
        display: 'flex',
        flexDirection: 'column',
        zIndex: 1000,
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        fontFamily: fonts.mono,
      }}
    >
      {/* 头部 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '12px 16px',
          borderBottom: `1px solid ${colors.border}`,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: isLoading ? '#f5a623' : '#5cb85c',
            }}
          />
          <span style={{ fontSize: 13, fontWeight: 600, color: colors.textPrimary }}>
            AI 分析助手
          </span>
          <span style={{ fontSize: 11, color: colors.textMuted }}>{code}</span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={clear}
            title="清空对话"
            style={{
              background: 'none',
              border: 'none',
              color: colors.textMuted,
              cursor: 'pointer',
              fontSize: 12,
              padding: 4,
            }}
          >
            清空
          </button>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: colors.textMuted,
              cursor: 'pointer',
              fontSize: 16,
              padding: 4,
              lineHeight: 1,
            }}
          >
            x
          </button>
        </div>
      </div>

      {/* 消息区域 */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: 16,
        }}
      >
        {/* 欢迎消息 */}
        {messages.length === 0 && !isLoading && (
          <div style={{ textAlign: 'center', padding: '40px 20px' }}>
            <div style={{ fontSize: 28, marginBottom: 12 }}>📊</div>
            <div style={{ fontSize: 14, color: colors.textPrimary, fontWeight: 600, marginBottom: 8 }}>
              智能分析助手
            </div>
            <div style={{ fontSize: 12, color: colors.textMuted, lineHeight: 1.6 }}>
              可以分析当前股票的技术面、基本面、情绪面走势
              <br />
              也可以设置止盈止损策略
            </div>
            <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {[
                '分析一下这只股票的走势',
                '帮我制定止盈止损策略，成本100元买了100股',
                '从技术面分析当前是否适合买入',
              ].map((hint) => (
                <button
                  key={hint}
                  onClick={() => {
                    setInput(hint)
                    inputRef.current?.focus()
                  }}
                  style={{
                    padding: '8px 12px',
                    fontSize: 11,
                    color: colors.accent,
                    background: colors.accentBg,
                    border: `1px solid rgba(122,164,245,0.2)`,
                    borderRadius: 6,
                    cursor: 'pointer',
                    textAlign: 'left',
                    fontFamily: fonts.mono,
                  }}
                >
                  {hint}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 历史消息 */}
        {messages.map((msg, idx) => (
          <ChatMessageItem key={idx} message={msg} onActionExecuted={handleActionExecuted} />
        ))}

        {/* 流式输出（正在生成的内容） */}
        {isLoading && streamingText && (
          <div style={{ display: 'flex', flexDirection: 'row', gap: 8, marginBottom: 12 }}>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: '50%',
                background: '#4a4a4a',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 12,
                color: '#fff',
                fontWeight: 700,
                flexShrink: 0,
              }}
            >
              AI
            </div>
            <div
              style={{
                maxWidth: '85%',
                background: colors.bgHover,
                border: `1px solid ${colors.border}`,
                borderRadius: 8,
                padding: '10px 14px',
              }}
            >
              <SimpleMarkdown text={streamingText} />
              <span style={{ display: 'inline-block', width: 6, height: 14, background: colors.accent, animation: 'blink 1s infinite', verticalAlign: 'middle', marginLeft: 2 }} />
            </div>
          </div>
        )}

        {/* 加载中（还没有文本时） */}
        {isLoading && !streamingText && (
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: '50%',
                background: '#4a4a4a',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 12,
                color: '#fff',
                fontWeight: 700,
                flexShrink: 0,
              }}
            >
              AI
            </div>
            <div
              style={{
                background: colors.bgHover,
                border: `1px solid ${colors.border}`,
                borderRadius: 8,
                padding: '10px 14px',
              }}
            >
              <div style={{ color: colors.textMuted, fontSize: 12 }}>
                正在分析 {code} ...
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div
        style={{
          padding: 12,
          borderTop: `1px solid ${colors.border}`,
          display: 'flex',
          gap: 8,
        }}
      >
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入问题，如：分析一下走势..."
          rows={1}
          style={{
            flex: 1,
            background: colors.bgHover,
            border: `1px solid ${colors.border}`,
            borderRadius: 6,
            padding: '8px 12px',
            color: colors.textPrimary,
            fontSize: 13,
            fontFamily: fonts.mono,
            resize: 'none',
            outline: 'none',
          }}
        />
        <button
          onClick={isLoading ? abort : handleSend}
          style={{
            padding: '8px 16px',
            background: isLoading ? colors.rise : colors.accent,
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            cursor: 'pointer',
            fontSize: 12,
            fontWeight: 600,
            fontFamily: fonts.mono,
          }}
        >
          {isLoading ? '停止' : '发送'}
        </button>
      </div>

      {/* 光标闪烁动画 */}
      <style>{`@keyframes blink { 0%,100% { opacity:1 } 50% { opacity:0 } }`}</style>
    </div>
  )
}
