/** AI 聊天相关类型定义 */

/** 单条消息 */
export interface ChatMessageItem {
  role: 'user' | 'assistant' | 'system'
  content: string
}

/** Action 定义 */
export interface ChatAction {
  type: string
  data: Record<string, any>
}

/** 前端使用的消息对象（含解析出的 actions） */
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  actions?: ChatAction[]
}

/** 流式响应块 */
export interface StreamChunk {
  type: 'text' | 'done' | 'error'
  content: string
}

/** 聊天请求参数 */
export interface ChatRequestParams {
  code: string
  message: string
  history: ChatMessageItem[]
  position?: { cost: number; quantity: number }
}

/** Action 执行结果 */
export interface ActionResult {
  success: boolean
  message: string
  data?: any
}
