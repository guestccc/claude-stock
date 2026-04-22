"""系统状态路由"""
import json
import os
from fastapi import APIRouter, Query
from server.config import DB_PATH, PROJECT_ROOT

router = APIRouter(prefix="/system", tags=["系统"])


@router.get("/status")
async def system_status():
    """获取系统状态"""
    db_size_mb = 0
    if os.path.exists(DB_PATH):
        db_size_mb = round(os.path.getsize(DB_PATH) / 1024 / 1024, 1)

    return {
        "db_size_mb": db_size_mb,
        "db_path": DB_PATH,
        "status": "running",
    }


@router.get("/scheduler")
async def scheduler_status():
    """获取调度器状态（从 scheduler_status.json 读取）"""
    status_path = os.path.join(PROJECT_ROOT, "scheduler_status.json")
    try:
        with open(status_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"running": False, "job_count": 0, "jobs": [], "updated_at": None}


@router.get("/tasks")
async def list_tasks():
    """获取所有任务状态"""
    from server.services.task_manager import get_all_tasks
    return {"tasks": get_all_tasks()}


# ---------- 任务触发端点 ----------


def _check_running(task_id: str):
    """检查任务是否正在运行"""
    from server.services.task_manager import get_task, TaskStatus
    existing = get_task(task_id)
    if existing and existing["status"] == TaskStatus.RUNNING.value:
        return {"error": "already_running", "message": "该任务正在运行中"}
    return None


@router.post("/tasks/daily-update")
async def trigger_daily_update(limit: int = Query(None, description="限制数量")):
    """触发增量更新日线数据"""
    guard = _check_running("daily_update")
    if guard:
        return guard

    from a_stock_fetcher import fetch_all_stocks_daily_incremental
    from server.services.task_manager import run_task
    return await run_task("daily_update", "增量更新日线", fetch_all_stocks_daily_incremental, limit=limit)


@router.post("/tasks/minute-update")
async def trigger_minute_update(limit: int = Query(None, description="限制数量")):
    """触发更新分时数据"""
    guard = _check_running("minute_update")
    if guard:
        return guard

    from a_stock_fetcher import fetch_all_stocks_minute
    from server.services.task_manager import run_task
    return await run_task("minute_update", "更新分时数据", fetch_all_stocks_minute, limit=limit)


@router.post("/tasks/financial-update")
async def trigger_financial_update(limit: int = Query(None, description="限制数量，默认100")):
    """触发更新财务数据"""
    guard = _check_running("financial_update")
    if guard:
        return guard

    from a_stock_fetcher import fetch_stock_financial
    from server.services.task_manager import run_task
    return await run_task("financial_update", "更新财务数据", fetch_stock_financial, limit=limit)


@router.post("/tasks/boards-update")
async def trigger_boards_update():
    """触发更新板块数据"""
    guard = _check_running("boards_update")
    if guard:
        return guard

    from a_stock_fetcher import fetch_all_boards
    from server.services.task_manager import run_task
    return await run_task("boards_update", "更新板块数据", fetch_all_boards)


@router.post("/tasks/fund-estimation")
async def trigger_fund_estimation():
    """触发更新自选基金估值"""
    guard = _check_running("fund_estimation")
    if guard:
        return guard

    from a_stock_fetcher import fetch_watchlist_estimations
    from server.services.task_manager import run_task
    return await run_task("fund_estimation", "更新基金估值", fetch_watchlist_estimations)


@router.post("/tasks/minute-cleanup")
async def trigger_minute_cleanup():
    """触发清理过期分时数据"""
    guard = _check_running("minute_cleanup")
    if guard:
        return guard

    from a_stock_fetcher import cleanup_old_minute_data
    from server.services.task_manager import run_task
    return await run_task("minute_cleanup", "清理分时数据", cleanup_old_minute_data)


@router.post("/tasks/daily-clean")
async def trigger_daily_clean(limit: int = Query(None, description="限制数量")):
    """触发清洗日线数据"""
    guard = _check_running("daily_clean")
    if guard:
        return guard

    from a_stock_fetcher import clean_daily_data
    from server.services.task_manager import run_task
    return await run_task("daily_clean", "清洗日线数据", clean_daily_data, limit=limit)
