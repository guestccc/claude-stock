"""行情路由"""
from typing import Optional, List
from fastapi import APIRouter, Query

from server.services import market_service
from server.models.stock import (
    StockSearchResponse,
    DailyResponse,
    QuotesResponse,
    MinuteResponse,
    MarketIndexResponse,
    StockListResponse,
)

router = APIRouter(prefix="/market", tags=["行情"])


@router.get("/search", response_model=StockSearchResponse)
async def search_stocks(q: str = Query(..., min_length=1, description="搜索关键词")):
    """搜索股票（代码或名称）"""
    results = market_service.search_stocks(q)
    return {"results": results}


@router.get("/daily/{code}", response_model=DailyResponse)
async def get_daily(
    code: str,
    start: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(120, ge=1, le=1000, description="返回条数"),
):
    """获取日 K 线数据"""
    data = market_service.get_daily(code, start_date=start, end_date=end, limit=limit)
    name = market_service.get_stock_name(code) or code
    return {"code": code, "name": name, "data": data}


@router.get("/quotes", response_model=QuotesResponse)
async def get_quotes(
    codes: str = Query(..., description="股票代码，逗号分隔，如 600519,000001"),
):
    """批量获取股票行情"""
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    data = market_service.get_quotes(code_list)
    return {"data": data}


@router.get("/minute/{code}", response_model=MinuteResponse)
async def get_minute(
    code: str,
    date: Optional[str] = Query(None, description="日期 YYYY-MM-DD"),
):
    """获取分钟 K 线数据"""
    data = market_service.get_minute(code, date)
    return {"code": code, "data": data}


@router.get("/index", response_model=MarketIndexResponse)
async def get_market_index():
    """获取市场指数概览"""
    # 上证指数代码 000001，深证成指 399001
    from server.services.market_service import get_quotes

    indices = get_quotes(["000001", "399001"])
    sh = next((i for i in indices if i["code"] == "000001"), {})
    sz = next((i for i in indices if i["code"] == "399001"), {})
    return {
        "sh": {"close": sh.get("close"), "change_pct": sh.get("change_pct")},
        "sz": {"close": sz.get("close"), "change_pct": sz.get("change_pct")},
    }


@router.get("/stocks", response_model=StockListResponse)
async def get_stock_list(
    date: Optional[str] = Query(None, description="日期 YYYY-MM-DD，默认最新交易日"),
    search: Optional[str] = Query(None, description="搜索关键词（代码或名称）"),
    sort_by: str = Query("pct_change", description="排序字段: pct_change/close/volume/turnover"),
    sort_order: str = Query("desc", description="排序方向: asc/desc"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页条数"),
):
    """获取股票列表"""
    return market_service.get_stock_list(
        date=date,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
