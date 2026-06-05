"""AI 聊天路由 — SSE 流式对话 + Action 执行"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from server.models.chat import ChatRequest, ActionPayload, ActionResult
from server.services import chat_service

router = APIRouter(prefix="/chat", tags=["AI聊天"])


class ChatActionRequest(BaseModel):
    """Action 执行请求"""
    type: str = Field(..., description="动作类型")
    data: dict = Field(default_factory=dict, description="动作数据")


@router.post("/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """SSE 流式对话

    前端通过 EventSource 或 fetch + ReadableStream 接收流式文本。
    每帧格式: data: {"type": "text", "content": "..."}\n\n
    """
    async def event_generator():
        async for chunk in chat_service.chat_stream(request):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/actions", response_model=ActionResult)
async def execute_action_endpoint(body: ActionPayload):
    """执行 AI 返回的 Action

    前端解析 AI 回复中的 <action/> 标签后，调用此接口执行。
    """
    result = await chat_service.execute_chat_action(body.type, body.data)
    return ActionResult(**result)
