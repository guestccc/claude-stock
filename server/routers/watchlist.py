"""自选股路由"""
from fastapi import APIRouter

router = APIRouter(prefix="/watchlist", tags=["自选股"])


@router.get("")
async def list_watchlist():
    """获取自选股列表"""
    # TODO: Phase 2 实现
    return {"items": []}


@router.post("")
async def add_to_watchlist(body: dict):
    """添加自选股"""
    # TODO: Phase 2 实现
    return {"ok": True}


@router.delete("/{item_id}")
async def remove_from_watchlist(item_id: int):
    """删除自选股"""
    # TODO: Phase 2 实现
    return {"ok": True}


@router.put("/{item_id}")
async def update_watchlist(item_id: int, body: dict):
    """更新自选股"""
    # TODO: Phase 2 实现
    return {"ok": True}
