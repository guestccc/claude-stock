"""选股路由"""
from fastapi import APIRouter, Query

router = APIRouter(prefix="/screener", tags=["选股"])


@router.get("/strategies")
async def list_strategies():
    """获取可用策略列表"""
    return {
        "strategies": [
            {
                "key": "donchian",
                "name": "Donchian 突破",
                "description": "20日Donchian通道突破扫描",
            }
        ]
    }


@router.get("/scan")
async def get_scan_results(
    strategy: str = Query("donchian"),
    date: str = Query(None),
    top: int = Query(50),
    min_score: int = Query(0),
):
    """获取扫描结果"""
    # TODO: Phase 3 实现
    return {"scan_date": date or "", "strategy": strategy, "total": 0, "results": []}


@router.post("/scan")
async def trigger_scan(body: dict):
    """触发新扫描"""
    # TODO: Phase 3 实现
    return {"task_id": "todo", "status": "pending"}
