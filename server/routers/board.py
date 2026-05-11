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
    """强制刷新板块行情"""
    return board_service.refresh_industry_boards()
