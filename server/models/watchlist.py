"""自选股 Pydantic schemas"""
from typing import Optional, List
from pydantic import BaseModel


class WatchlistCreate(BaseModel):
    """添加自选股"""
    code: str


class WatchlistUpdate(BaseModel):
    """更新自选股"""
    note: Optional[str] = None
    sort_order: Optional[int] = None


class WatchlistItem(BaseModel):
    """自选股条目"""
    id: int
    code: str
    name: str
    added_at: str
    sort_order: int
    note: Optional[str] = None


class WatchlistResponse(BaseModel):
    """自选股列表响应"""
    items: List[WatchlistItem]
