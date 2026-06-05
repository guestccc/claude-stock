"""Action 中间调度层 — 解析并执行 AI 返回的动作指令"""
import json
import re
from typing import Callable, Awaitable, Any

from server.db.models import PositionTPSL
from a_stock_db.database import db


# ---------- Action 解析 ----------

def parse_actions(text: str) -> tuple[str, list[dict]]:
    """从 AI 回复文本中解析 <action> 标签

    Args:
        text: AI 回复的完整文本

    Returns:
        (清理后的文本, action 列表)
    """
    action_pattern = re.compile(
        r'<action\s+type="(\w+)"\s+data=\'(.+?)\'\s*/>',
        re.DOTALL,
    )
    actions = []
    clean_text = text

    for match in action_pattern.finditer(text):
        action_type = match.group(1)
        try:
            data = json.loads(match.group(2))
            actions.append({"type": action_type, "data": data})
            clean_text = clean_text.replace(match.group(0), "")
        except json.JSONDecodeError:
            # 解析失败，保留原文
            continue

    return clean_text.strip(), actions


# ---------- Action 处理器注册 ----------

ActionHandler = Callable[[dict], Awaitable[dict]]

_ACTION_HANDLERS: dict[str, ActionHandler] = {}


def register_action(action_type: str):
    """注册 Action 处理器的装饰器"""
    def decorator(func: ActionHandler) -> ActionHandler:
        _ACTION_HANDLERS[action_type] = func
        return func
    return decorator


# ---------- 具体 Action 实现 ----------

@register_action("set_tp_sl")
async def handle_set_tp_sl(data: dict) -> dict:
    """设置止盈止损：保存到数据库

    Args:
        data: {"stock_code": "600519", "tp_price": 120.0, "sl_price": 90.0,
               "cost_price": 100.0, "quantity": 100, "strategy": "...", "reason": "..."}

    Returns:
        {"success": bool, "message": str, "data": dict}
    """
    code = data.get("stock_code")
    tp = data.get("tp_price")
    sl = data.get("sl_price")

    if not code or tp is None or sl is None:
        return {"success": False, "message": "参数错误: 缺少 stock_code/tp_price/sl_price"}

    try:
        session = db.get_session()
        try:
            tp_sl = PositionTPSL(
                code=code,
                tp_price=float(tp),
                sl_price=float(sl),
                cost_price=data.get("cost_price"),
                quantity=data.get("quantity"),
                strategy=data.get("strategy", ""),
                reason=data.get("reason", ""),
                status="active",
            )
            session.add(tp_sl)
            session.commit()
            session.refresh(tp_sl)

            return {
                "success": True,
                "message": f"✅ 已保存止盈止损：止盈 {tp} / 止损 {sl}",
                "data": {
                    "id": tp_sl.id,
                    "code": code,
                    "tp_price": tp,
                    "sl_price": sl,
                    "cost_price": data.get("cost_price"),
                    "quantity": data.get("quantity"),
                },
            }
        finally:
            session.close()
    except Exception as e:
        return {"success": False, "message": f"保存失败: {str(e)}"}


@register_action("add_watchlist")
async def handle_add_watchlist(data: dict) -> dict:
    """加入自选股"""
    code = data.get("stock_code")
    if not code:
        return {"success": False, "message": "参数错误: 缺少 stock_code"}

    try:
        from server.db.models import WatchlistItem
        from server.services.market_service import get_stock_name

        session = db.get_session()
        try:
            # 检查是否已存在
            exists = session.query(WatchlistItem).filter(WatchlistItem.code == code).first()
            if exists:
                return {"success": True, "message": f"✅ {code} 已在自选股中"}

            name = get_stock_name(code) or code
            item = WatchlistItem(code=code, name=name, sort_order=0, note="")
            session.add(item)
            session.commit()
            return {"success": True, "message": f"✅ {name}({code}) 已加入自选股"}
        finally:
            session.close()
    except Exception as e:
        return {"success": False, "message": f"加入自选失败: {str(e)}"}


# ---------- 统一执行入口 ----------

async def execute_action(action_type: str, data: dict) -> dict:
    """执行指定类型的 Action

    Args:
        action_type: 动作类型
        data: 动作数据

    Returns:
        {"success": bool, "message": str, "data": ...}
    """
    handler = _ACTION_HANDLERS.get(action_type)
    if not handler:
        return {"success": False, "message": f"未识别的动作类型: {action_type}"}

    try:
        return await handler(data)
    except Exception as e:
        return {"success": False, "message": f"执行失败: {str(e)}"}


def list_action_types() -> list[str]:
    """返回所有已注册的 Action 类型"""
    return list(_ACTION_HANDLERS.keys())
