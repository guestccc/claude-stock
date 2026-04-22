"""内存任务状态管理器

所有 fetcher 函数均为同步阻塞，通过 run_in_executor 在线程池中执行，
避免阻塞 FastAPI 事件循环。
"""
import asyncio
import time
from enum import Enum
from typing import Optional, Callable, Any
from dataclasses import dataclass, asdict


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskRecord:
    task_id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    message: str = ""
    error: Optional[str] = None


# 全局内存存储（server 重启后清空，管理面板可接受）
_tasks: dict[str, TaskRecord] = {}


def get_all_tasks() -> list[dict]:
    """返回所有任务记录（字典列表，JSON 可序列化）"""
    return [asdict(t) for t in _tasks.values()]


def get_task(task_id: str) -> Optional[dict]:
    """获取单个任务状态"""
    if task_id not in _tasks:
        return None
    return asdict(_tasks[task_id])


async def run_task(task_id: str, name: str, fn: Callable, *args: Any, **kwargs: Any) -> dict:
    """
    注册并执行任务。fn 在线程池中运行，状态自动追踪。

    :param task_id: 固定任务标识（同类任务互斥）
    :param name: 显示名称（中文）
    :param fn: 同步阻塞的执行函数
    :return: 最终任务记录（字典）
    """
    record = TaskRecord(task_id=task_id, name=name)
    _tasks[task_id] = record

    record.status = TaskStatus.RUNNING
    record.started_at = time.time()

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, lambda: fn(*args, **kwargs))
        record.status = TaskStatus.COMPLETED
        record.message = str(result) if result is not None else "done"
    except Exception as e:
        record.status = TaskStatus.FAILED
        record.error = f"{type(e).__name__}: {str(e)}"
    finally:
        record.finished_at = time.time()

    return asdict(record)
