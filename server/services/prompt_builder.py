"""Prompt 构建器 — 从 SQLite 读取股票数据，格式化为 AI 可理解的文本"""
from typing import Optional, List

from server.services import market_service
from a_stock_db.database import db
from a_stock_db import StockFinancial, StockDaily
from sqlalchemy import desc, func


# ---------- 技术指标实时计算 ----------

def _calc_ma(prices: List[float], period: int) -> Optional[float]:
    """计算简单移动平均"""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def _calc_rsi(prices: List[float], period: int = 6) -> Optional[float]:
    """计算 RSI（相对强弱指标）"""
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        change = prices[-i] - prices[-i - 1]
        if change >= 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _calc_macd(prices: List[float]) -> dict:
    """计算 MACD 指标 (DIF, DEA, MACD柱)"""
    if len(prices) < 26:
        return {"dif": None, "dea": None, "macd": None}

    def _ema(data: List[float], n: int) -> List[float]:
        k = 2 / (n + 1)
        ema = [data[0]]
        for p in data[1:]:
            ema.append(p * k + ema[-1] * (1 - k))
        return ema

    ema12 = _ema(prices, 12)
    ema26 = _ema(prices, 26)
    dif = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    dea = _ema(dif, 9)
    macd_hist = [2 * (d - de) for d, de in zip(dif, dea)]

    return {
        "dif": dif[-1] if dif else None,
        "dea": dea[-1] if dea else None,
        "macd": macd_hist[-1] if macd_hist else None,
    }


def _calc_boll(prices: List[float], period: int = 20) -> dict:
    """计算布林带 (上轨, 中轨, 下轨)"""
    if len(prices) < period:
        return {"upper": None, "mid": None, "lower": None}

    recent = prices[-period:]
    mid = sum(recent) / period
    variance = sum((p - mid) ** 2 for p in recent) / period
    std = variance ** 0.5

    return {
        "upper": mid + 2 * std,
        "mid": mid,
        "lower": mid - 2 * std,
    }


def _summarize_klines(klines: List[dict]) -> str:
    """摘要最近 K 线走势"""
    if not klines:
        return "无数据"

    closes = [k["close"] for k in klines if k["close"] is not None]
    if len(closes) < 2:
        return "数据不足"

    # 涨跌天数统计
    up_days = sum(1 for k in klines if (k.get("pct_change") or 0) > 0)
    down_days = len(klines) - up_days

    # 近5日走势描述
    recent5 = klines[-5:] if len(klines) >= 5 else klines
    trend_desc = []
    for k in recent5:
        if k.get("pct_change") is not None:
            sign = "↑" if k["pct_change"] > 0 else "↓" if k["pct_change"] < 0 else "→"
            trend_desc.append(f"{k['date']}{sign}{k['pct_change']:.2f}%")

    # 最高/最低价区间
    highs = [k["high"] for k in klines if k["high"] is not None]
    lows = [k["low"] for k in klines if k["low"] is not None]

    return (
        f"近{len(klines)}日: {up_days}阳{down_days}阴, "
        f"区间 {min(lows):.2f}~{max(highs):.2f}; "
        f"近5日: {' '.join(trend_desc)}"
    )


def _get_fundamentals(code: str) -> dict:
    """从数据库读取基本面数据（利润表最新一期）"""
    session = db.get_session()
    try:
        row = (
            session.query(StockFinancial)
            .filter(StockFinancial.code == code)
            .order_by(desc(StockFinancial.报告日期))
            .first()
        )
        if row:
            return {
                "report_date": row.报告日期.strftime("%Y-%m-%d") if row.报告日期 else "N/A",
                "revenue": row.营业总收入,
                "net_profit": row.净利润,
                "eps": row.基本每股收益,
            }
        return {}
    finally:
        session.close()


# ---------- 主构建函数 ----------

def build_stock_prompt(
    code: str,
    user_message: str,
    position: Optional[dict] = None,
) -> str:
    """从数据库读取股票数据，构建 AI 分析 prompt

    Args:
        code: 股票代码
        user_message: 用户当前输入
        position: 用户持仓信息 {cost: float, quantity: int}

    Returns:
        完整的 system prompt 文本
    """
    # 1. 实时行情
    quote_list = market_service.get_quotes([code])
    quote = quote_list[0] if quote_list else {}
    name = quote.get("name") or code

    # 2. 近 60 天 K 线（计算指标用）
    klines = market_service.get_daily(code, limit=60)
    closes = [k["close"] for k in klines if k["close"] is not None]

    # 3. 基本面
    fundamentals = _get_fundamentals(code)

    # 4. 计算技术指标
    indicators = {
        "ma5": _calc_ma(closes, 5),
        "ma10": _calc_ma(closes, 10),
        "ma20": _calc_ma(closes, 20),
        "rsi": _calc_rsi(closes, 6) if len(closes) >= 7 else None,
    }
    indicators.update(_calc_macd(closes))
    indicators.update(_calc_boll(closes))

    # 5. 持仓信息
    holding_info = ""
    if position and position.get("cost") and position.get("quantity"):
        cost = float(position["cost"])
        qty = int(position["quantity"])
        current = quote.get("close") or cost
        pnl_pct = (current - cost) / cost * 100 if cost > 0 else 0
        market_value = current * qty
        holding_info = f"""
【用户持仓】
- 成本价: {cost:.2f} 元，持仓: {qty} 股
- 当前市值: {market_value:.2f} 元
- 浮动盈亏: {pnl_pct:+.2f}%"""

    # 6. 从 action_registry 自动提取 action 说明
    from server.services.action_registry import get_all_prompt_hints
    action_hints = get_all_prompt_hints()

    # 7. 组装系统提示词
    system_prompt = f"""你是一位资深 A 股投资分析师，正在分析股票 {name}({code})。

【当前行情】
- 最新价: {quote.get('close', 'N/A')} 元，涨跌幅: {quote.get('change_pct', 'N/A'):.2f}%
- 今日开盘: {quote.get('open', 'N/A')}，最高: {quote.get('high', 'N/A')}，最低: {quote.get('low', 'N/A')}
- 成交量: {quote.get('volume', 'N/A')} 手，成交额: {quote.get('turnover', 'N/A')} 万元

【技术面】
- MA5: {indicators.get('ma5', 'N/A'):.2f}, MA10: {indicators.get('ma10', 'N/A'):.2f}, MA20: {indicators.get('ma20', 'N/A'):.2f}
- RSI(6): {indicators.get('rsi', 'N/A'):.1f}
- MACD: DIF={indicators.get('dif', 'N/A'):.3f}, DEA={indicators.get('dea', 'N/A'):.3f}, MACD柱={indicators.get('macd', 'N/A'):.3f}
- 布林带: 上轨={indicators.get('upper', 'N/A'):.2f}, 中轨={indicators.get('mid', 'N/A'):.2f}, 下轨={indicators.get('lower', 'N/A'):.2f}

【基本面】（最新报告期: {fundamentals.get('report_date', 'N/A')}）
- 营业总收入: {fundamentals.get('revenue', 'N/A')} 亿元
- 净利润: {fundamentals.get('net_profit', 'N/A')} 亿元
- 每股收益(EPS): {fundamentals.get('eps', 'N/A')} 元

【近 10 日走势摘要】
{_summarize_klines(klines[-10:] if len(klines) >= 10 else klines)}
{holding_info}

你可以执行以下动作，在分析结论后输出对应的 XML 标签（必须放在回复最后）：

{action_hints}

要求：
- 价格字段必须为纯数字，不要带单位
- 如果用户未提供持仓成本，data 中 omit cost_price 和 quantity 字段
- 回复使用 Markdown 格式，关键数据加粗

现在开始回答用户的问题。"""

    return system_prompt
