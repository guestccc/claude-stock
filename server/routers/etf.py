"""ETF 路由"""
from typing import Optional
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from server.services import etf_service, market_service
from server.models.etf import (
    ETFListResponse,
    ETFDetail,
    ETFRealtimeResponse,
    ETFRealtimeItem,
    ETFDailyResponse,
    ETFDailyBar,
)

router = APIRouter(prefix="/etf", tags=["ETF"])


@router.get("", response_model=ETFListResponse)
async def list_etfs(
    search: Optional[str] = Query(None, description="搜索关键词（代码或名称）"),
    etf_type: Optional[str] = Query(None, description="ETF 类型筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页条数"),
):
    """获取 ETF 列表"""
    result = etf_service.get_etf_list(
        search=search,
        etf_type=etf_type,
        page=page,
        page_size=page_size,
    )
    return ETFListResponse(**result)


@router.get("/search")
async def search_etfs(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100),
):
    """搜索 ETF"""
    results = etf_service.search_etfs(keyword, limit=limit)
    return {"results": results}


@router.get("/{code}", response_model=ETFDetail)
async def get_etf_detail(code: str):
    """获取 ETF 详情"""
    detail = etf_service.get_etf_detail(code)
    if not detail:
        raise HTTPException(status_code=404, detail=f"ETF {code} 不存在")
    return ETFDetail(**detail)


@router.get("/{code}/daily", response_model=ETFDailyResponse)
async def get_etf_daily(
    code: str,
    limit: int = Query(120, ge=1, le=1000, description="返回条数"),
):
    """获取 ETF 日 K 线"""
    # 获取名称
    name = market_service.get_stock_name(code) or code

    # 获取日 K
    data = market_service.get_daily(code, limit=limit)

    return ETFDailyResponse(
        code=code,
        name=name,
        data=[ETFDailyBar(**d) for d in data],
    )


@router.get("/realtime/all", response_model=ETFRealtimeResponse)
async def get_etf_realtime():
    """获取 ETF 实时行情（同花顺）"""
    from a_stock_fetcher.fetchers.etf import fetch_etf_realtime_ths

    df = fetch_etf_realtime_ths()
    if df is None or df.empty:
        return ETFRealtimeResponse(data=[], total=0)

    items = []
    for _, row in df.iterrows():
        items.append(
            ETFRealtimeItem(
                code=str(row.get("基金代码", "")),
                name=str(row.get("基金名称", "")),
                nav=_parse_float(row.get("当前-单位净值")),
                pct_change=_parse_float(row.get("增长率")),
                fund_type=str(row.get("基金类型", "")),
            )
        )

    return ETFRealtimeResponse(data=items, total=len(items))


def _parse_float(value) -> Optional[float]:
    """安全解析浮点数"""
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
