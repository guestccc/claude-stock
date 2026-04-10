"""系统状态路由"""
import os
from fastapi import APIRouter
from server.config import DB_PATH

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
