"""基金路由"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional

from server.services import fund_service
from server.services import fund_backtest_service
from server.models.fund_backtest import FundBacktestRequest, FundBacktestResponse

router = APIRouter(prefix="/fund", tags=["基金"])


class FundHistoryItem(BaseModel):
    date: Optional[str] = ''
    nav: Optional[float] = None
    pct_change: Optional[float] = None


class FundItem(BaseModel):
    code: str
    name: str
    fund_type: Optional[str] = ''
    company: Optional[str] = ''
    manager: Optional[str] = ''
    remark: Optional[str] = ''
    tags: List[str] = []
    added_at: Optional[str] = ''
    nav: Optional[float] = None
    nav_date: Optional[str] = ''
    est_nav: Optional[float] = None
    est_pct: Optional[float] = None
    update_time: Optional[str] = ''
    history: List[FundHistoryItem] = []
    nav_change_pct: Optional[float] = None


class FundWatchlistResponse(BaseModel):
    data: List[FundItem]


class FundSearchItem(BaseModel):
    code: str
    name: str
    fund_type: str = ''
    company: str = ''


class FundDetailResponse(BaseModel):
    code: str
    name: str
    full_name: Optional[str] = ''
    fund_type: Optional[str] = ''
    company: Optional[str] = ''
    manager: Optional[str] = ''
    setup_date: Optional[str] = ''
    scale: Optional[str] = ''
    benchmark: Optional[str] = ''
    strategy: Optional[str] = ''
    nav: Optional[float] = None
    nav_date: Optional[str] = ''
    est_nav: Optional[float] = None
    est_pct: Optional[float] = None
    update_time: Optional[str] = ''


class FundNavPoint(BaseModel):
    date: str
    nav: float
    pct_change: Optional[float] = None


class FundNavHistoryResponse(BaseModel):
    code: str
    period: str
    data: List[FundNavPoint]


@router.get("/watchlist", response_model=FundWatchlistResponse)
async def get_watchlist(cache_minutes: int = Query(2, description="估值缓存分钟数")):
    """获取自选基金列表（含估值，优先使用缓存）"""
    data = fund_service.get_watchlist(cache_minutes)
    return {"data": data}


@router.post("/watchlist/refresh")
async def refresh_estimations():
    """强制刷新所有自选基金估值"""
    return fund_service.refresh_estimations()


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


@router.put("/watchlist/{code}/tags")
async def update_tags(code: str, tags: str = Query(..., description="标签，逗号分隔")):
    """更新基金标签"""
    return fund_service.update_tags(code, tags)


@router.get("/search", response_model=List[FundSearchItem])
async def search_fund(q: str = Query(..., min_length=1, description="搜索关键词")):
    """搜索基金（代码或名称）"""
    return fund_service.search_fund(q)


@router.get("/detail/{code}", response_model=FundDetailResponse)
async def get_fund_detail(code: str):
    """获取基金详情（基本信息 + 最新估值）"""
    detail = fund_service.get_fund_detail(code)
    if not detail:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"基金 {code} 不存在")
    return detail


@router.get("/nav-history/{code}", response_model=FundNavHistoryResponse)
async def get_fund_nav_history(
    code: str,
    period: str = Query('1年', description="时间周期: 1月/3月/6月/1年/3年/5年/今年来/成立来"),
):
    """获取基金历史净值数据"""
    data = fund_service.get_fund_nav_history(code, period)
    return {'code': code, 'period': period, 'data': data}


@router.get("/backtest/strategies")
async def get_backtest_strategies():
    """获取基金回测策略列表"""
    return fund_backtest_service.STRATEGIES


@router.post("/backtest/run", response_model=FundBacktestResponse)
async def run_fund_backtest(req: FundBacktestRequest):
    """运行基金回测"""
    try:
        return fund_backtest_service.run_fund_backtest(req)
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
