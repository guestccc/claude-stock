/** 流式聊天 Hook */
import { useState, useCallback, useRef } from 'react'
import type { ChatMessage, ChatMessageItem, ChatRequestParams, StreamChunk } from '../types/chat'
import { chatStream } from '../api/chat'

interface UseChatStreamReturn {
  /** 历史消息列表 */
  messages: ChatMessage[]
  /** 当前正在流式输出的完整文本（用于实时渲染） */
  streamingText: string
  /** 是否正在加载 */
  isLoading: boolean
  /** 发送消息 */
  sendMessage: (params: ChatRequestParams) => void
  /** 中断当前请求 */
  abort: () => void
  /** 清空对话 */
  clear: () => void
}

/** 从 AI 回复文本中解析 \u003caction/\u003e 标签 */
function parseActions(text: string): { text: string; actions: Array<{ type: string; data: Record<string, any> }> } {
  const actionRegex = /\u003caction\s+type="(\w+)"\s+data='(.+?)'\s*\/\u003e/g
  const actions: Array<{ type: string; data: Record<string, any> }> = []
  let cleanText = text
  let match: RegExpExecArray | null

  while ((match = actionRegex.exec(text)) !== null) {
    try {
      const data = JSON.parse(match[2])
      actions.push({ type: match[1], data })
      cleanText = cleanText.replace(match[0], '')
    } catch {
      // 解析失败则保留原文
    }
  }

  return { text: cleanText.trim(), actions }
}

export function useChatStream(): UseChatStreamReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streamingText, setStreamingText] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback((params: ChatRequestParams) => {
    // 添加用户消息
    const userMsg: ChatMessage = { role: 'user', content: params.message }
    setMessages((prev) => [...prev, userMsg])
    setIsLoading(true)
    setStreamingText('')

    const abortCtrl = new AbortController()
    abortRef.current = abortCtrl

    let fullText = ''

    chatStream(
      params,
      (chunk: StreamChunk) => {
        if (chunk.type === 'text') {
          fullText += chunk.content
          setStreamingText(fullText)
        } else if (chunk.type === 'done') {
          const { text, actions } = parseActions(fullText)
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: text, actions: actions.length > 0 ? actions : undefined },
          ])
          setStreamingText('')
          setIsLoading(false)
        } else if (chunk.type === 'error') {
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: `❌ ${chunk.content}` },
          ])
          setStreamingText('')
          setIsLoading(false)
        }
      },
      abortCtrl.signal,
    ).catch((err) => {
      if (err.name === 'AbortError') {
        // 用户主动中断，保留已生成的内容
        if (fullText) {
          const { text, actions } = parseActions(fullText)
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: text + '\n\n[已中断]', actions: actions.length > 0 ? actions : undefined },
          ])
        }
      } else {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: `❌ 请求失败: ${err.message}` },
        ])
      }
      setStreamingText('')
      setIsLoading(false)
    })
  }, [])

  const abort = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
  }, [])

  const clear = useCallback(() => {
    abort()
    setMessages([])
    setStreamingText('')
    setIsLoading(false)
  }, [abort])

  return { messages, streamingText, isLoading, sendMessage, abort, clear }
}
