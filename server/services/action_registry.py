"""Action 注册表 — 所有 action 的唯一真相源

新增 action 只需:
  1. 在 handlers/ 下新建 xxx.py，实现 async handle(data) -> dict
  2. 在此文件 REGISTRY 中加一项（导入 handler + 声明配置）
  3. 如需数据库表，在 server/db/models.py 中添加
  4. 前端新建卡片组件 + 注册

无需改动: prompt_builder.py / action_handler.py / ActionCard.tsx / MarketPage.tsx
"""
from server.services.handlers.set_tp_sl import handle as handle_set_tp_sl
from server.services.handlers.add_watchlist import handle as handle_add_watchlist
from server.services.handlers.set_support_resistance import handle as handle_support_resistance


# action 注册表
# chart_lines 中的 color 对应前端 theme/tokens.ts 中的 colors key
REGISTRY = {
    "set_tp_sl": {
        "label": "设置止盈止损",
        "prompt_hint": (
            '1. 设置止盈止损\n'
            '<action type="set_tp_sl" data=\'{"stock_code":"600519","tp_price":16.80,"sl_price":13.50,'
            '"cost_price":14.30,"quantity":1000,"strategy":"突破回踩","reason":"..."}\' />\n'
            "要求: tp_price/sl_price 为纯数字，必须说明盈亏比例"
        ),
        "handler": handle_set_tp_sl,
        "chart_lines": [
            {"field": "tp_price",   "label": "止盈", "color": "rise",   "style": "dashed"},
            {"field": "sl_price",   "label": "止损", "color": "fall",   "style": "dashed"},
            {"field": "cost_price", "label": "成本", "color": "accent", "style": "solid"},
        ],
    },
    "set_support_resistance": {
        "label": "设置压力支撑位",
        "prompt_hint": (
            '2. 设置压力支撑位\n'
            '<action type="set_support_resistance" data=\'{"stock_code":"600519",'
            '"pressure_price":16.80,"support_price":13.50,"reason":"前期高点/密集成交区"}\' />\n'
            "要求: pressure_price/support_price 为纯数字"
        ),
        "handler": handle_support_resistance,
        "chart_lines": [
            {"field": "pressure_price", "label": "压力位", "color": "rise",   "style": "dotted"},
            {"field": "support_price",  "label": "支撑位", "color": "fall",   "style": "dotted"},
        ],
    },
    "add_watchlist": {
        "label": "加入自选股",
        "prompt_hint": (
            '3. 加入自选股\n'
            '<action type="add_watchlist" data=\'{"stock_code":"600519"}\' />\n'
        ),
        "handler": handle_add_watchlist,
        "chart_lines": [],
    },
}


def get_all_prompt_hints() -> str:
    """自动提取所有 action 的 prompt 说明，供 prompt_builder 调用"""
    return "\n".join(item["prompt_hint"] for item in REGISTRY.values())


def get_chart_lines(action_type: str) -> list:
    """获取某个 action 的画线规则"""
    return REGISTRY.get(action_type, {}).get("chart_lines", [])


def list_action_types() -> list[str]:
    """返回所有已注册的 action 类型"""
    return list(REGISTRY.keys())
