/** 单条聊天消息渲染 */
import { colors, fonts } from '../../theme/tokens'
import type { ChatMessage } from '../../types/chat'
import SimpleMarkdown from './SimpleMarkdown'
import ActionCard from './ActionCard'

interface Props {
  message: ChatMessage
  onActionExecuted?: (action: any, result: any) => void
}

export default function ChatMessageItem({ message, onActionExecuted }: Props) {
  const isUser = message.role === 'user'

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: isUser ? 'row-reverse' : 'row',
        gap: 8,
        marginBottom: 12,
      }}
    >
      {/* 头像 */}
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: '50%',
          background: isUser ? colors.accent : '#4a4a4a',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 12,
          color: '#fff',
          fontWeight: 700,
          flexShrink: 0,
        }}
      >
        {isUser ? '我' : 'AI'}
      </div>

      {/* 内容 */}
      <div
        style={{
          maxWidth: '85%',
          background: isUser ? colors.accentBg : colors.bgHover,
          border: `1px solid ${isUser ? 'rgba(122,164,245,0.2)' : colors.border}`,
          borderRadius: 8,
          padding: '10px 14px',
          fontFamily: fonts.mono,
        }}
      >
        {message.content ? (
          <SimpleMarkdown text={message.content} />
        ) : (
          <div style={{ color: colors.textMuted, fontSize: 12 }}>思考中...</div>
        )}

        {/* Action 卡片 */}
        {message.actions?.map((action, idx) => (
          <ActionCard key={idx} action={action} onExecuted={onActionExecuted} />
        ))}
      </div>
    </div>
  )
}
