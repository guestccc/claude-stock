"""Action 通用执行器 — 从 registry 查找 handler 并执行"""
from server.services.action_registry import REGISTRY, get_chart_lines


async def execute_action(action_type: str, data: dict) -> dict:
    """执行指定 action

    Args:
        action_type: 动作类型（在 action_registry.py 中注册）
        data: 动作数据

    Returns:
        {"success": bool, "message": str, "data": ..., "chart_lines": [...]}
    """
    entry = REGISTRY.get(action_type)
    if not entry:
        return {"success": False, "message": f"未识别的动作类型: {action_type}"}

    try:
        result = await entry["handler"](data)
        # 附加注册表中的 chart_lines 规则，前端可据此画 K 线标记线
        result["chart_lines"] = get_chart_lines(action_type)
        return result
    except Exception as e:
        return {"success": False, "message": f"执行失败: {str(e)}"}
