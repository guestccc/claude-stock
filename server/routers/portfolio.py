"""持仓路由"""
from fastapi import APIRouter

router = APIRouter(prefix="/portfolio", tags=["持仓"])


@router.get("/holdings")
async def list_holdings():
    """获取当前持仓"""
    # TODO: Phase 5 实现
    return {"holdings": [], "summary": {"total_cost": 0, "holding_count": 0}}


@router.post("/buy")
async def buy_stock(body: dict):
    """买入"""
    # TODO: Phase 5 实现
    return {"message": "TODO"}


@router.post("/sell")
async def sell_stock(body: dict):
    """卖出"""
    # TODO: Phase 5 实现
    return {"message": "TODO"}


@router.get("/transactions")
async def list_transactions(code: str = None, limit: int = 50):
    """获取交易记录"""
    # TODO: Phase 5 实现
    return {"transactions": []}
