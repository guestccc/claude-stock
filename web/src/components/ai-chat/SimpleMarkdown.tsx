/** Markdown 渲染器 — 基于 react-markdown */
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { colors, fonts } from '../../theme/tokens'

interface Props {
  text: string
}

export default function SimpleMarkdown({ text }: Props) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => (
          <div style={{ fontSize: 16, fontWeight: 700, color: colors.textPrimary, marginTop: 12, marginBottom: 6 }}>{children}</div>
        ),
        h2: ({ children }) => (
          <div style={{ fontSize: 14, fontWeight: 700, color: colors.textPrimary, marginTop: 10, marginBottom: 4 }}>{children}</div>
        ),
        h3: ({ children }) => (
          <div style={{ fontSize: 13, fontWeight: 700, color: colors.textPrimary, marginTop: 8, marginBottom: 4 }}>{children}</div>
        ),
        p: ({ children }) => (
          <p style={{ color: colors.textSecondary, fontSize: 13, margin: '6px 0', lineHeight: 1.7 }}>{children}</p>
        ),
        strong: ({ children }) => (
          <strong style={{ color: colors.textPrimary, fontWeight: 600 }}>{children}</strong>
        ),
        ul: ({ children }) => (
          <ul style={{ paddingLeft: 18, margin: '4px 0', color: colors.textSecondary, fontSize: 13 }}>{children}</ul>
        ),
        ol: ({ children }) => (
          <ol style={{ paddingLeft: 18, margin: '4px 0', color: colors.textSecondary, fontSize: 13 }}>{children}</ol>
        ),
        li: ({ children }) => (
          <li style={{ marginBottom: 3, lineHeight: 1.6 }}>{children}</li>
        ),
        code: ({ className, children, ...props }) => {
          const isBlock = className?.startsWith('language-')
          if (isBlock) {
            return (
              <pre style={{
                background: '#1a1a1a',
                border: `1px solid ${colors.border}`,
                borderRadius: 6,
                padding: '10px 14px',
                overflow: 'auto',
                fontFamily: fonts.mono,
                fontSize: 12,
                margin: '8px 0',
              }}>
                <code style={{ color: colors.textSecondary, whiteSpace: 'pre' }} {...props}>{children}</code>
              </pre>
            )
          }
          // 行内代码
          return (
            <code style={{
              background: '#1a1a1a',
              border: `1px solid ${colors.border}`,
              borderRadius: 3,
              padding: '1px 5px',
              fontSize: 12,
              fontFamily: fonts.mono,
              color: colors.accent,
            }} {...props}>{children}</code>
          )
        },
        pre: ({ children }) => <>{children}</>,
        blockquote: ({ children }) => (
          <blockquote style={{
            borderLeft: `3px solid ${colors.accent}`,
            margin: '8px 0',
            paddingLeft: 12,
            color: colors.textMuted,
            fontSize: 13,
          }}>{children}</blockquote>
        ),
        hr: () => (
          <hr style={{ border: 'none', borderTop: `1px solid ${colors.border}`, margin: '12px 0' }} />
        ),
        table: ({ children }) => (
          <table style={{
            borderCollapse: 'collapse',
            width: '100%',
            fontSize: 12,
            margin: '8px 0',
          }}>{children}</table>
        ),
        th: ({ children }) => (
          <th style={{
            border: `1px solid ${colors.border}`,
            padding: '6px 10px',
            background: colors.bgHover,
            color: colors.textPrimary,
            fontWeight: 600,
            textAlign: 'left',
          }}>{children}</th>
        ),
        td: ({ children }) => (
          <td style={{
            border: `1px solid ${colors.border}`,
            padding: '6px 10px',
            color: colors.textSecondary,
          }}>{children}</td>
        ),
      }}
    >
      {text}
    </ReactMarkdown>
  )
}
