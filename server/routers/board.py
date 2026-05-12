"""板块行情路由"""
from fastapi import APIRouter, Query
from server.services import board_service

router = APIRouter(prefix="/board", tags=["板块行情"])


@router.get("/industry")
async def get_industry_boards(cache_minutes: int = Query(2, description="缓存分钟数")):
    """获取行业板块实时行情"""
    data = board_service.get_industry_boards(cache_minutes)
    return {"data": data, "total": len(data)}


@router.post("/industry/refresh")
async def refresh_industry_boards():
    """强制刷新行业板块行情"""
    return board_service.refresh_industry_boards()


@router.get("/concept")
async def get_concept_boards(cache_minutes: int = Query(2, description="缓存分钟数")):
    """获取概念板块实时行情"""
    data = board_service.get_concept_boards(cache_minutes)
    return {"data": data, "total": len(data)}


@router.post("/concept/refresh")
async def refresh_concept_boards():
    """强制刷新概念板块行情"""
    return board_service.refresh_concept_boards()


@router.get("/concept/{name}/kline")
async def get_concept_kline(
    name: str,
    period: str = Query('Y1', description="周期: Y1/Y3/Y5/ALL"),
    code: str = Query('', description="板块代码(platecode)，用于名称映射"),
):
    """获取概念板块指数 K 线"""
    return board_service.get_concept_kline(name, period, code)


@router.get("/watchlist")
async def get_board_watchlist():
    """获取关注的板块代码列表"""
    codes = board_service.get_watched_board_codes()
    return {"data": list(codes)}


@router.post("/watchlist/{code}")
async def add_board_watch(code: str, name: str = Query(..., description="板块名称")):
    """关注板块"""
    return board_service.add_board_watch(code, name)


@router.delete("/watchlist/{code}")
async def remove_board_watch(code: str):
    """取消关注板块"""
    return board_service.remove_board_watch(code)
