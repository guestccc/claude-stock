"""基金路由"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional

from server.services import fund_service

router = APIRouter(prefix="/fund", tags=["基金"])


class FundHistoryItem(BaseModel):
    date: str
    nav: Optional[float] = None
    est_pct: Optional[float] = None


class FundItem(BaseModel):
    code: str
    name: str
    fund_type: str = ''
    company: str = ''
    manager: str = ''
    remark: str = ''
    added_at: str = ''
    nav: Optional[float] = None
    nav_date: str = ''
    est_nav: Optional[float] = None
    est_pct: Optional[float] = None
    update_time: str = ''
    history: List[FundHistoryItem] = []
    nav_change_pct: Optional[float] = None


class FundWatchlistResponse(BaseModel):
    data: List[FundItem]


class FundSearchItem(BaseModel):
    code: str
    name: str
    fund_type: str = ''
    company: str = ''


@router.get("/watchlist", response_model=FundWatchlistResponse)
async def get_watchlist():
    """获取自选基金列表（含实时估值）"""
    data = fund_service.get_watchlist()
    return {"data": data}


@router.post("/watchlist/{code}")
async def add_watchlist(code: str, remark: str = Query("", description="备注")):
    """添加自选基金"""
    result = fund_service.add_watchlist(code, remark)
    return result


@router.delete("/watchlist/{code}")
async def remove_watchlist(code: str):
    """移除自选基金"""
    result = fund_service.remove_watchlist(code)
    return result


@router.get("/search", response_model=List[FundSearchItem])
async def search_fund(q: str = Query(..., min_length=1, description="搜索关键词")):
    """搜索基金（代码或名称）"""
    return fund_service.search_fund(q)
