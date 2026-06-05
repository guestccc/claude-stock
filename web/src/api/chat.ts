/** AI 聊天相关 API */
import type { ChatRequestParams, ActionResult, StreamChunk } from '../types/chat'

/** SSE 流式对话
 *
 * 使用 fetch + ReadableStream 接收 SSE 流，通过 onChunk 回调处理每个数据块。
 */
export async function chatStream(
  params: ChatRequestParams,
  onChunk: (chunk: StreamChunk) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
    signal,
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  const reader = response.body?.getReader()
  const decoder = new TextDecoder()
  if (!reader) {
    throw new Error('无法读取响应流')
  }

  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // 解析 SSE: data: {...}\n\n
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      const trimmed = line.trim()
      if (trimmed.startsWith('data: ')) {
        try {
          const chunk: StreamChunk = JSON.parse(trimmed.slice(6))
          onChunk(chunk)
        } catch {
          // 忽略无法解析的行
        }
      }
    }
  }
}

/** 执行 Action */
export async function executeAction(
  type: string,
  data: Record<string, any>,
): Promise<ActionResult> {
  const response = await fetch('/api/chat/actions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type, data }),
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  return response.json()
}
