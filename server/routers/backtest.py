"""回测路由"""
from fastapi import APIRouter

from server.models.backtest import BacktestRequest, BacktestResponse, ExitStrategyListResponse

router = APIRouter(prefix="/backtest", tags=["回测"])


@router.get("/strategies", response_model=ExitStrategyListResponse)
async def list_strategies():
    """获取出场策略列表"""
    return {
        "strategies": [
            {"key": "fixed", "name": "固定止盈止损"},
            {"key": "trailing", "name": "移动止盈"},
            {"key": "boll_middle", "name": "BOLL中轨止盈"},
            {"key": "trailing_boll", "name": "移动止盈+BOLL中轨"},
            {"key": "half_exit", "name": "半仓止盈"},
        ]
    }


@router.post("/run")
async def run_backtest(req: BacktestRequest):
    """运行回测"""
    # TODO: Phase 4 实现 - 调用 backtest_engine.backtest_stock()
    return {"message": "TODO: Phase 4"}
