"""聊天服务 — 业务编排层：组装 prompt → 调 AI → 返回 SSE 流"""
import json
from typing import AsyncGenerator

from server.models.chat import ChatRequest
from server.services import prompt_builder, action_handler
from server.services.ai_client import stream_chat


async def chat_stream(request: ChatRequest) -> AsyncGenerator[str, None]:
    """流式聊天：组装 prompt → 调 AI API → SSE 返回

    Args:
        request: 聊天请求（含股票代码、用户消息、历史记录、持仓信息）

    Yields:
        SSE 格式的 JSON 字符串：{"type": "text", "content": "..."}
    """
    try:
        # 1. 构建系统提示词（从 SQLite 读取股票数据）
        system_prompt = prompt_builder.build_stock_prompt(
            code=request.code,
            user_message=request.message,
            position=request.position,
        )

        # 2. 组装消息列表（历史 + 当前用户消息，不含 system）
        messages = []
        for msg in request.history:
            # Anthropic 不支持 system role，跳过
            if msg.role != "system":
                messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": request.message})

        # 3. 流式调用 AI API（system_prompt 单独传）
        full_text = ""
        async for chunk in stream_chat(system_prompt, messages):
            full_text += chunk
            yield json.dumps({"type": "text", "content": chunk})

        # 4. 结束标记
        yield json.dumps({"type": "done"})

    except Exception as e:
        yield json.dumps({"type": "error", "content": f"服务异常: {str(e)}"})


async def execute_chat_action(action_type: str, data: dict) -> dict:
    """执行聊天中的 Action

    Args:
        action_type: 动作类型
        data: 动作数据

    Returns:
        {"success": bool, "message": str, "data": dict}
    """
    return await action_handler.execute_action(action_type, data)
