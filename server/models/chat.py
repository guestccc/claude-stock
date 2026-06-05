"""聊天相关 Pydantic schemas"""
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class ChatMessageItem(BaseModel):
    """单条消息"""
    role: str = Field(..., description="user/assistant/system")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """聊天请求"""
    code: str = Field(..., description="股票代码")
    message: str = Field(..., description="用户输入")
    history: List[ChatMessageItem] = Field(default_factory=list, description="历史消息")
    position: Optional[dict] = Field(None, description="用户持仓 {cost, quantity}")


class ChatStreamChunk(BaseModel):
    """SSE 流式响应块"""
    type: str = Field(..., description="text/done/error")
    content: str = Field(default="", description="内容")


class ActionPayload(BaseModel):
    """Action 执行请求"""
    type: str = Field(..., description="动作类型: set_tp_sl/add_watchlist/...")
    data: dict = Field(default_factory=dict, description="动作数据")


class ActionResult(BaseModel):
    """Action 执行结果"""
    success: bool
    message: str
    data: Optional[Any] = None


class TPSLListItem(BaseModel):
    """止盈止损列表项"""
    id: int
    code: str
    cost_price: Optional[float]
    quantity: Optional[int]
    tp_price: float
    sl_price: float
    strategy: Optional[str]
    reason: Optional[str]
    status: str
    created_at: str
