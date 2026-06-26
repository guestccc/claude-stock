#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
组合回测引擎 — 多股票共享资金池

核心特性:
  - 提供候选股票池，多只股票同时运行突破策略
  - 最多同时持有 max_positions 只股票
  - 同一天多个信号时，按评分引擎排序选最强的
  - 账户资金共享，有钱有仓位才能买入

出场策略支持: fixed / trailing / trailing_boll / boll_middle / ma5_exit
（half_exit* 和 turtle 是单股专用策略，组合模式不支持，会返回 400）

设计说明:
  - 不复用 backtest_stock() 的主循环（它是单股线性处理）
  - 而是提取独立的入场检查 + 出场检查函数，按日驱动多只股票
  - 持仓用轻量的 PortfolioPosition 类，避免 Trade 的复杂字段
"""

import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from server.services.backtest_service import (
    get_stock_data,
    get_stock_name,
    calc_atr,
    calc_donchian_upper,
    calc_boll_upper,
    calc_boll_middle_single,
    calc_stats,
)
from server.services.score_engine import score_signal

DONCHIAN_PERIOD = 20
ATR_PERIOD = 14
BOLL_PERIOD = 20
BOLL_STD = 2
LOOKBACK = 60  # 数据回看期，保证有足够历史计算指标

# 组合模式支持的出场策略
SUPPORTED_STRATEGIES = {"fixed", "trailing", "trailing_boll", "boll_middle", "ma5_exit", "half_exit"}


# ============================================================
# 持仓对象
# ============================================================

class PortfolioPosition:
    """组合回测的轻量持仓对象"""

    def __init__(self, code: str, entry_date: str, entry_price: float,
                 shares: int, cost: float, stop_loss: float, take_profit: float,
                 atr: float, upper_band: float, breakout_close: float,
                 breakout_exceed_pct: float, entry_signal_idx: int):
        self.code = code
        self.entry_date = entry_date
        self.entry_price = entry_price
        self.shares = shares
        self.cost = cost                    # 买入总成本（股数×买入价）
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.atr = atr
        self.upper_band = upper_band        # 突破的唐奇安上轨价
        self.breakout_close = breakout_close
        self.breakout_exceed_pct = breakout_exceed_pct
        self.entry_signal_idx = entry_signal_idx  # 信号日在 rows 中的索引

        # 跟踪止损状态
        self.high_since_entry = entry_price
        self.target_reached = False
        self.high_since_target = entry_price

        # ma5_exit 的 pending 状态
        self.ma5_pending = False
        self.ma5_pending_price = 0.0
        self.ma5_pending_trigger = 0.0
        self.ma5_pending_date = ""
        self.ma5_pending_formula = ""

        # 半仓止盈状态
        self.half_exited = False
        self.shares_at_half = 0
        self.shares_sold_at_half = 0
        self.price_at_half = 0.0
        self.pnl_half = 0.0
        self.high_since_half = 0.0

        # 出场信息
        self.exit_date: Optional[str] = None
        self.exit_price: Optional[float] = None
        self.reason: str = ""
        self.exit_formula: str = ""
        self.exit_trigger_price: float = 0.0
        self.exit_trigger_date: str = ""

    def to_trade_dict(self) -> Dict[str, Any]:
        """序列化为与单股回测兼容的交易 dict 格式"""
        if self.half_exited and self.exit_price:
            # 半仓止盈后剩余仓位平仓：合并统计
            total_shares = self.shares_sold_at_half + self.shares_at_half
            pnl = self.pnl_half + (self.exit_price - self.entry_price) * self.shares_at_half
        else:
            total_shares = self.shares
            pnl = (self.exit_price - self.entry_price) * self.shares if self.exit_price else 0

        risk_per_share = self.entry_price - self.stop_loss
        pnl_r = pnl / (risk_per_share * total_shares) if risk_per_share > 0 and total_shares > 0 else 0
        holding_days = (
            (datetime.strptime(self.exit_date, "%Y-%m-%d") - datetime.strptime(self.entry_date, "%Y-%m-%d")).days
            if self.exit_date else 0
        )
        return {
            "entry_date": self.entry_date,
            "exit_date": self.exit_date or "",
            "entry_price": round(self.entry_price, 3),
            "exit_price": round(self.exit_price, 3) if self.exit_price else 0,
            "stop_loss": round(self.stop_loss, 3),
            "take_profit": round(self.take_profit, 3),
            "shares": total_shares,
            "pnl": round(pnl, 2),
            "pnl_r": round(pnl_r, 2),
            "holding_days": holding_days,
            "reason": self.reason,
            "atr": round(self.atr, 3),
            "upper_band": round(self.upper_band, 3),
            "breakout_close": round(self.breakout_close, 3),
            "breakout_exceed_pct": round(self.breakout_exceed_pct, 3),
            "exit_formula": self.exit_formula,
            "group_date": self.entry_date,
        }


# ============================================================
# 入场信号检查
# ============================================================

def has_entry_signal(rows, idx: int, exit_strategy: str) -> bool:
    """检查某只股票在某日是否有入场信号（唐奇安上轨突破 + BOLL 上轨突破）"""
    if idx < DONCHIAN_PERIOD:
        return False
    upper = calc_donchian_upper(rows[:idx + 1], DONCHIAN_PERIOD, exclude_today=True)
    if upper <= 0:
        return False
    close_today = rows[idx]["close"] or 0
    if close_today <= 0:
        return False
    boll_u = calc_boll_upper(rows[:idx + 1], BOLL_PERIOD, BOLL_STD, exclude_today=True)
    # 唐奇安上轨突破 且 BOLL 上轨突破
    return close_today > upper and close_today > boll_u and boll_u > 0


# ============================================================
# 出场检查（核心）
# ============================================================

def check_exit(pos: PortfolioPosition, rows, idx: int, exit_strategy: str,
               tp_multiplier: float, trailing_atr_k: float,
               half_exit_pct: float = 50) -> Optional[Tuple[str, float, str]]:
    """
    检查持仓是否触发出场条件

    参数:
        pos: 持仓对象（会被修改 high_since_entry/target_reached 等状态）
        rows: K 线数据
        idx: 当日索引
        exit_strategy: 出场策略
        tp_multiplier: 止盈倍数
        trailing_atr_k: 跟踪止损 ATR 系数
        half_exit_pct: 半仓止盈比例%

    返回: (action, exit_price, exit_reason) 或 None（未触发出场）
          action: "full" 完整平仓 | "half" 半仓止盈
          注意：ma5_exit 的次日开盘卖出用 ma5_pending 状态机实现
    """
    today = rows[idx]
    low_today = today["low"] or 0
    high_today = today["high"] or 0
    close_today = today["close"] or 0
    open_today = today["open"] or 0

    # 更新持仓最高价
    if high_today > pos.high_since_entry:
        pos.high_since_entry = high_today

    # === ma5_exit: 次日开盘卖出 pending ===
    if exit_strategy == "ma5_exit" and pos.ma5_pending:
        exit_price = pos.ma5_pending_price
        pos.exit_trigger_price = pos.ma5_pending_trigger
        pos.exit_trigger_date = pos.ma5_pending_date
        pos.exit_formula = pos.ma5_pending_formula
        pos.ma5_pending = False
        return ("full", exit_price, "take_profit")

    # === 固定止损（所有策略通用）===
    if low_today <= pos.stop_loss:
        gap_note = "，跳空低开按开盘价成交" if open_today > 0 and open_today < pos.stop_loss else ""
        exit_price = min(pos.stop_loss, open_today) if open_today > 0 else pos.stop_loss
        pos.exit_trigger_price = round(low_today, 3)
        pos.exit_trigger_date = today["date"]
        pos.exit_formula = (
            f"盘中最低 {low_today:.3f} ≤ 止损价 {pos.stop_loss:.3f}{gap_note}，"
            f"触发止损 | 止损 = 入场价 {pos.entry_price:.3f} - ATR {pos.atr:.3f} × 1.3"
        )
        return ("full", exit_price, "stop_loss")

    if close_today < pos.stop_loss:
        pos.exit_trigger_price = round(close_today, 3)
        pos.exit_trigger_date = today["date"]
        pos.exit_formula = (
            f"收盘价 {close_today:.3f} < 止损价 {pos.stop_loss:.3f}，"
            f"触发止损 | 止损 = 入场价 {pos.entry_price:.3f} - ATR {pos.atr:.3f} × 1.3"
        )
        return ("full", pos.stop_loss, "stop_loss")

    # === 各策略止盈逻辑 ===
    if exit_strategy == "fixed":
        if high_today >= pos.take_profit:
            gap_note = "，跳空高开按开盘价成交" if open_today > 0 and open_today > pos.take_profit else ""
            exit_price = max(pos.take_profit, open_today) if open_today > 0 else pos.take_profit
            pos.exit_trigger_price = round(high_today, 3)
            pos.exit_trigger_date = today["date"]
            pos.exit_formula = (
                f"盘中最高 {high_today:.3f} ≥ 止盈价 {pos.take_profit:.3f}{gap_note}，"
                f"触发止盈 | 止盈 = 入场价 {pos.entry_price:.3f} + ATR {pos.atr:.3f} × {tp_multiplier}"
            )
            return ("full", exit_price, "take_profit")

    elif exit_strategy in ("trailing", "trailing_boll"):
        # 先检查是否触及目标价
        if not pos.target_reached and high_today >= pos.take_profit:
            pos.target_reached = True
            pos.high_since_target = high_today
            pos.exit_trigger_price = round(high_today, 3)
            pos.exit_trigger_date = today["date"]
            pos.exit_formula = (
                f"盘中最高 {high_today:.3f} ≥ 目标价 {pos.take_profit:.3f}，"
                f"触及止盈目标！开始跟踪 | 止盈 = 入场价 {pos.entry_price:.3f} + ATR {pos.atr:.3f} × {tp_multiplier}"
            )
            # 触及目标当日不出场，继续跟踪
            return None
        if pos.target_reached:
            trailing_trigger = pos.high_since_target - trailing_atr_k * pos.atr
            if exit_strategy == "trailing":
                if low_today <= trailing_trigger:
                    gap_note = "，跳空低开按开盘价成交" if open_today > 0 and open_today < trailing_trigger else ""
                    exit_price = min(trailing_trigger, open_today) if open_today > 0 else trailing_trigger
                    pos.exit_trigger_price = round(low_today, 3)
                    pos.exit_trigger_date = today["date"]
                    pos.exit_formula = (
                        f"盘中最低 {low_today:.3f} ≤ 跟踪止损价 {trailing_trigger:.3f}{gap_note}，"
                        f"触发止盈 | 跟踪止损 = 截至昨日最高 {pos.high_since_target:.3f} - ATR {pos.atr:.3f} × {trailing_atr_k}"
                    )
                    return ("full", exit_price, "take_profit")
                if high_today > pos.high_since_target:
                    pos.high_since_target = high_today
            else:  # trailing_boll
                boll_m = calc_boll_middle_single(rows[:idx + 1], BOLL_PERIOD, idx)
                boll_m_val = round(boll_m, 3) if boll_m > 0 else 0
                trailing_trigger = round(trailing_trigger, 3)
                if close_today < boll_m_val and boll_m_val > 0:
                    pos.exit_trigger_price = round(close_today, 3)
                    pos.exit_trigger_date = today["date"]
                    pos.exit_formula = (
                        f"收盘价 {close_today:.3f} < BOLL中轨 {boll_m_val:.3f}，"
                        f"触发BOLL中轨止盈 | BOLL中轨 = {BOLL_PERIOD}日MA = {boll_m_val:.3f}"
                        f" | 跟踪止损价 = {trailing_trigger:.3f}（截至昨日最高 {pos.high_since_target:.3f} - ATR {pos.atr:.3f} × {trailing_atr_k}）"
                        f" | 盘中最低 {low_today:.3f}"
                    )
                    return ("full", close_today, "take_profit")
                if low_today <= trailing_trigger:
                    gap_note = "，跳空低开按开盘价成交" if open_today > 0 and open_today < trailing_trigger else ""
                    exit_price = min(trailing_trigger, open_today) if open_today > 0 else trailing_trigger
                    pos.exit_trigger_price = round(low_today, 3)
                    pos.exit_trigger_date = today["date"]
                    pos.exit_formula = (
                        f"盘中最低 {low_today:.3f} ≤ 跟踪止损价 {trailing_trigger:.3f}{gap_note}，"
                        f"触发跟踪止盈 | 跟踪止损 = 截至昨日最高 {pos.high_since_target:.3f} - ATR {pos.atr:.3f} × {trailing_atr_k} = {trailing_trigger:.3f}"
                        f" | BOLL中轨 = {boll_m_val:.3f}（收盘价 {close_today:.3f} 未破中轨）"
                    )
                    return ("full", exit_price, "take_profit")
                if high_today > pos.high_since_target:
                    pos.high_since_target = high_today

    elif exit_strategy == "boll_middle":
        boll_m = calc_boll_middle_single(rows[:idx + 1], BOLL_PERIOD, idx)
        boll_m_val = round(boll_m, 3) if boll_m > 0 else 0
        if close_today < boll_m_val and boll_m_val > 0:
            pos.exit_trigger_price = round(close_today, 3)
            pos.exit_trigger_date = today["date"]
            pos.exit_formula = (
                f"收盘价 {close_today:.3f} < BOLL中轨 {boll_m_val:.3f}，"
                f"触发止盈 | BOLL中轨 = {BOLL_PERIOD}日MA = {boll_m_val:.3f}"
            )
            return ("full", close_today, "take_profit")

    elif exit_strategy == "ma5_exit":
        # 收盘跌破5日线 → 标记次日开盘卖出
        if idx >= 5:
            ma5_closes = [rows[j]["close"] or 0 for j in range(idx - 5, idx)]
            ma5_val = sum(ma5_closes) / 5
            if ma5_val > 0 and close_today < ma5_val:
                tomorrow_idx = idx + 1
                if tomorrow_idx < len(rows):
                    sell_price = rows[tomorrow_idx]["open"] or close_today
                else:
                    sell_price = close_today
                gap_note = ""
                if sell_price > close_today:
                    gap_note = "，次日跳空高开"
                elif sell_price < close_today:
                    gap_note = "，次日跳空低开"
                pos.ma5_pending = True
                pos.ma5_pending_price = sell_price
                pos.ma5_pending_trigger = round(close_today, 3)
                pos.ma5_pending_date = today["date"]
                pos.ma5_pending_formula = (
                    f"收盘价 {close_today:.3f} < 5日均线 {ma5_val:.3f}{gap_note}，"
                    f"次日开盘价 {sell_price:.3f} 卖出 | MA5 = 近5日收盘均值"
                )

    elif exit_strategy == "half_exit":
        # 半仓止盈 + 移动止损
        half_pct = half_exit_pct / 100.0
        shares_to_sell_first = math.floor(pos.shares * half_pct / 100) * 100
        shares_to_sell_first = max(shares_to_sell_first, 100)

        if not pos.half_exited:
            # Phase 1: 未半仓止盈前，检查止盈目标（止损已在通用部分检查）
            if high_today >= pos.take_profit:
                open_today = today["open"] or 0
                actual_tp = max(pos.take_profit, open_today) if open_today > 0 else pos.take_profit
                gap_note = "（跳空高开按开盘价成交）" if open_today > 0 and open_today > pos.take_profit else ""
                pos.exit_trigger_price = round(high_today, 3)
                pos.exit_trigger_date = today["date"]
                pos.exit_formula = (
                    f"盘中最高 {high_today:.3f} ≥ 止盈价 {pos.take_profit:.3f}{gap_note}，"
                    f"半仓止盈！卖出 {shares_to_sell_first} 股 ¥{actual_tp:.3f}，"
                    f"剩余 {pos.shares - shares_to_sell_first} 股继续跟踪"
                )
                return ("half", actual_tp, "half_exit")
        else:
            # Phase 2: 半仓止盈后，剩余仓位跟踪止损
            trailing_trigger = pos.high_since_half - trailing_atr_k * pos.atr
            if low_today <= trailing_trigger:
                open_today = today["open"] or 0
                exit_price = min(trailing_trigger, open_today) if open_today > 0 else trailing_trigger
                pos.exit_trigger_price = round(low_today, 3)
                pos.exit_trigger_date = today["date"]
                gap_note = "，跳空低开按开盘价成交" if open_today > 0 and open_today < trailing_trigger else ""
                pos.exit_formula = (
                    f"盘中最低 {low_today:.3f} ≤ 移动止损价 {trailing_trigger:.3f}{gap_note}，"
                    f"触发止盈 | 移动止损 = 截至昨日最高 {pos.high_since_half:.3f} - ATR {pos.atr:.3f} × {trailing_atr_k}"
                )
                return ("full", exit_price, "take_profit")
            else:
                if high_today > pos.high_since_half:
                    pos.high_since_half = high_today

    return None


# ============================================================
# 组合回测主流程
# ============================================================

def portfolio_backtest(codes: List[str], start_date: str, end_date: str,
                       initial_capital: float = 100000, max_positions: int = 3,
                       exit_strategy: str = "fixed", tp_multiplier: float = 2.0,
                       trailing_atr_k: float = 1.0, half_exit_pct: float = 50,
                       score_config: Optional[Dict] = None) -> Dict[str, Any]:
    """
    组合回测主入口

    参数:
        codes: 候选股票池代码列表
        start_date / end_date: 回测区间
        initial_capital: 初始本金
        max_positions: 最多同时持仓数
        exit_strategy: 出场策略
        tp_multiplier: 止盈倍数
        trailing_atr_k: 跟踪止损 ATR 系数
        half_exit_pct: 半仓止盈比例（组合模式不使用，保留参数兼容）
        score_config: 评分配置覆盖

    返回: {
        "portfolio_stats": BacktestStats,
        "overall_equity": List[EquityPoint],
        "stock_results": List[{code, name, trades, equity_curve, stats}],
    }
    """
    # 1. 加载所有股票数据
    stock_data: Dict[str, List[Dict]] = {}
    stock_name_map: Dict[str, str] = {}
    for code in codes:
        try:
            rows = get_stock_data(code, start_date, end_date, lookback=LOOKBACK)
        except Exception:
            rows = []
        if len(rows) < DONCHIAN_PERIOD + 5:
            stock_data[code] = []
            stock_name_map[code] = get_stock_name(code)
            continue
        stock_data[code] = rows
        stock_name_map[code] = get_stock_name(code)

    # 2. 构建 {date: {code: row_idx}} 索引 + 统一日历
    stock_lookup: Dict[str, Dict[str, int]] = {}
    for code, rows in stock_data.items():
        for i, r in enumerate(rows):
            d = r["date"]
            if not d:
                continue
            if d not in stock_lookup:
                stock_lookup[d] = {}
            stock_lookup[d][code] = i

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    all_dates = sorted(
        d for d in stock_lookup.keys()
        if d and start_dt <= datetime.strptime(d, "%Y-%m-%d") <= end_dt
    )

    # 3. 状态初始化
    capital = float(initial_capital)
    peak_capital = capital
    positions: Dict[str, PortfolioPosition] = {}   # code -> 活跃持仓
    per_stock_trades: Dict[str, List[PortfolioPosition]] = {code: [] for code in codes}
    overall_equity: List[Dict[str, Any]] = []

    # 4. 逐日遍历
    for date in all_dates:
        day_stocks = stock_lookup.get(date, {})

        # 4.1 出场检查（先出场释放资金和仓位）
        for code in list(positions.keys()):
            if code not in day_stocks:
                continue
            idx = day_stocks[code]
            rows = stock_data[code]
            pos = positions[code]
            # T+1：买入次日（信号日+2 对应数据索引）才能卖
            if idx <= pos.entry_signal_idx + 1:
                continue
            result = check_exit(pos, rows, idx, exit_strategy, tp_multiplier, trailing_atr_k, half_exit_pct)
            if result is not None:
                action, exit_price, exit_reason = result
                if action == "half":
                    # 半仓止盈：卖出部分仓位，剩余继续跟踪
                    half_pct = half_exit_pct / 100.0
                    shares_to_sell = math.floor(pos.shares * half_pct / 100) * 100
                    shares_to_sell = max(shares_to_sell, 100)
                    remaining = pos.shares - shares_to_sell
                    if remaining <= 0:
                        # 实际全部卖出，按完整平仓处理
                        _close_position(pos, date, exit_price, exit_reason)
                        capital += pos.shares * exit_price
                        per_stock_trades[code].append(pos)
                        del positions[code]
                    else:
                        capital += shares_to_sell * exit_price
                        pos.half_exited = True
                        pos.shares_sold_at_half = shares_to_sell
                        pos.shares_at_half = remaining
                        pos.price_at_half = exit_price
                        pos.pnl_half = (exit_price - pos.entry_price) * shares_to_sell
                        pos.high_since_half = exit_price
                        pos.shares = remaining
                        # 半仓止盈不出场，继续跟踪剩余仓位
                else:  # "full"
                    _close_position(pos, date, exit_price, exit_reason)
                    capital += pos.shares * exit_price
                    per_stock_trades[code].append(pos)
                    del positions[code]

        # 4.2 入场检查（有空位 + 有钱）
        slots = max_positions - len(positions)
        if slots > 0 and capital > 0:
            signals = []
            for code in codes:
                if code in positions:
                    continue
                if code not in day_stocks:
                    continue
                rows = stock_data[code]
                if not rows:
                    continue
                idx = day_stocks[code]
                if has_entry_signal(rows, idx, exit_strategy):
                    score, detail = score_signal(rows, idx, score_config)
                    signals.append({"code": code, "idx": idx, "score": score})

            # 按评分降序，取前 N 个
            signals.sort(key=lambda x: x["score"], reverse=True)
            for sig in signals[:slots]:
                code = sig["code"]
                rows = stock_data[code]
                idx = sig["idx"]
                tomorrow_idx = idx + 1
                if tomorrow_idx >= len(rows):
                    continue
                open_price = rows[tomorrow_idx]["open"] or 0
                if open_price <= 0:
                    continue
                # 仓位：可用资金的 30%（与单股回测一致），取整到百股
                shares = math.floor(capital * 0.3 / open_price / 100) * 100
                shares = max(shares, 100)
                cost = shares * open_price
                if cost > capital:
                    # 钱不够，尝试降低仓位
                    shares = math.floor(capital / open_price / 100) * 100
                    if shares < 100:
                        continue
                    cost = shares * open_price
                    if cost > capital:
                        continue

                atr = calc_atr(rows[:idx + 1], ATR_PERIOD)
                if atr <= 0:
                    continue
                stop = open_price - atr * 1.3
                target = open_price + atr * tp_multiplier
                upper = calc_donchian_upper(rows[:idx + 1], DONCHIAN_PERIOD, exclude_today=True)
                breakout_close = rows[idx]["close"] or 0
                breakout_exceed_pct = (
                    round((breakout_close - upper) / upper * 100, 3) if upper > 0 else 0
                )
                pos = PortfolioPosition(
                    code=code,
                    entry_date=rows[tomorrow_idx]["date"],
                    entry_price=open_price,
                    shares=shares,
                    cost=cost,
                    stop_loss=stop,
                    take_profit=target,
                    atr=atr,
                    upper_band=round(upper, 3),
                    breakout_close=round(breakout_close, 3),
                    breakout_exceed_pct=breakout_exceed_pct,
                    entry_signal_idx=idx,
                )
                positions[code] = pos
                capital -= cost  # 扣除买入成本

        # 4.3 记录当日净值
        pos_value = 0.0
        for code, pos in positions.items():
            if code in day_stocks:
                idx = day_stocks[code]
                close = stock_data[code][idx]["close"] or 0
                pos_value += pos.shares * close
        total = capital + pos_value
        if total > peak_capital:
            peak_capital = total
        dd = peak_capital - total
        overall_equity.append({
            "date": date,
            "equity": capital,
            "position_value": pos_value,
            "total": total,
            "peak": peak_capital,
            "dd": dd,
            "dd_pct": dd / peak_capital * 100 if peak_capital > 0 else 0,
            "num_positions": len(positions),
        })

    # 5. 强制平仓剩余持仓
    last_date = all_dates[-1] if all_dates else end_date
    for code, pos in list(positions.items()):
        rows = stock_data.get(code, [])
        last_close = rows[-1]["close"] if rows else pos.entry_price
        pos.exit_date = last_date
        pos.exit_price = last_close
        pos.reason = "force_close"
        pos.exit_trigger_price = round(last_close, 3)
        pos.exit_trigger_date = last_date
        holding_days = (
            datetime.strptime(last_date, "%Y-%m-%d") - datetime.strptime(pos.entry_date, "%Y-%m-%d")
        ).days
        pos.exit_formula = (
            f"回测区间结束，按最后收盘价 {last_close:.3f} 强制平仓 | "
            f"仍持仓 {holding_days} 天，止损价 {pos.stop_loss:.3f}，止盈价 {pos.take_profit:.3f}"
        )
        capital += pos.shares * last_close
        per_stock_trades[code].append(pos)
    positions.clear()

    # 6. 计算统计
    # 组合总统计：所有交易合并
    all_trades = [t for code in codes for t in per_stock_trades[code]]
    # 转换为简易 Trade-like 对象供 calc_stats 使用
    all_trade_dicts = [_pos_to_simple_trade(t) for t in all_trades]
    portfolio_stats = _calc_portfolio_stats(
        all_trade_dicts, initial_capital, capital, peak_capital,
        start_date, end_date, overall_equity,
    )

    # 各股票统计
    stock_results = []
    for code in codes:
        trades = per_stock_trades[code]
        trade_dicts = [t.to_trade_dict() for t in trades]
        if trades:
            # 虚拟本金 = 该股票最大单笔仓位成本（代表该股分到的资金）
            stock_initial = max(t.cost for t in trades)
            stock_total_pnl = sum(
                (t.exit_price - t.entry_price) * t.shares for t in trades if t.exit_price
            )
            stock_final = stock_initial + stock_total_pnl
            stock_peak = stock_initial
            # 用虚拟本金构建等比净值曲线
            stock_equity = _build_stock_equity(trades, stock_data[code], start_date, end_date, stock_initial)
            for e in stock_equity:
                if e["total"] > stock_peak:
                    stock_peak = e["total"]
            stock_stats = _calc_portfolio_stats(
                [_pos_to_simple_trade(t) for t in trades],
                stock_initial, stock_final, stock_peak,
                start_date, end_date, stock_equity,
            )
        else:
            stock_equity = []
            stock_stats = _empty_stats(initial_capital)
        stock_results.append({
            "code": code,
            "name": stock_name_map.get(code, code),
            "trades": trade_dicts,
            "equity_curve": stock_equity,
            "stats": stock_stats,
        })

    return {
        "portfolio_stats": portfolio_stats,
        "overall_equity": overall_equity,
        "stock_results": stock_results,
    }


# ============================================================
# 辅助函数
# ============================================================

def _close_position(pos: PortfolioPosition, exit_date: str, exit_price: float, reason: str):
    """记录持仓平仓信息"""
    pos.exit_date = exit_date
    pos.exit_price = exit_price
    pos.reason = reason


class _SimpleTrade:
    """简易交易对象，供 calc_stats 使用（只含统计需要的字段）"""
    def __init__(self, d: Dict):
        self.entry_date = d.get("entry_date", "")
        self.exit_date = d.get("exit_date", "")
        self.entry_price = d.get("entry_price", 0)
        self.exit_price = d.get("exit_price", 0)
        self.shares = d.get("shares", 0)
        self.pnl = d.get("pnl", 0)
        self.pnl_r = d.get("pnl_r", 0)
        self.holding_days = d.get("holding_days", 0)
        self.reason = d.get("reason", "")
        self.risk_per_share = d.get("risk_per_share", 1)


def _pos_to_simple_trade(pos: PortfolioPosition) -> _SimpleTrade:
    """PortfolioPosition → _SimpleTrade（供 calc_stats）"""
    d = pos.to_trade_dict()
    risk = pos.entry_price - pos.stop_loss
    d["risk_per_share"] = risk if risk > 0 else 1
    return _SimpleTrade(d)


def _calc_portfolio_stats(trades, initial, final, peak,
                          start_date, end_date, equity_curve) -> Dict[str, Any]:
    """计算组合/单股统计（复用 backtest_service.calc_stats）"""
    if not trades:
        return _empty_stats(initial)
    stats = calc_stats(trades, initial, final, peak, start_date, end_date, equity_curve)
    # calc_stats 返回的 best_trade/worst_trade 已经是 dict，直接返回
    return stats


def _empty_stats(initial: float) -> Dict[str, Any]:
    """空统计（无交易时）"""
    return {
        "initial_capital": initial,
        "final_capital": initial,
        "total_return": 0.0,
        "total_return_pct": 0.0,
        "num_trades": 0,
        "win_trades": 0,
        "loss_trades": 0,
        "win_rate": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
        "avg_pnl": 0.0,
        "rr_ratio": 0.0,
        "max_drawdown": 0.0,
        "max_drawdown_pct": 0.0,
        "max_dd_date": None,
        "sharpe_ratio": 0.0,
        "avg_holding_days": 0.0,
        "daily_return_pct": 0.0,
        "best_trade": None,
        "worst_trade": None,
    }


def _build_stock_equity(trades, rows, start_date, end_date,
                        initial_capital) -> List[Dict[str, Any]]:
    """构建单只股票在组合中的贡献净值曲线（基于该股票持仓期间的资金占用变化）"""
    if not rows or not trades:
        return []
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    # 构建日期→close 映射
    close_map = {r["date"]: (r["close"] or 0) for r in rows if r["date"]}

    # 构建交易时间轴
    sorted_trades = sorted(trades, key=lambda t: t.entry_date)
    result = []
    peak = initial_capital
    for r in rows:
        d = r["date"]
        if not d or not (start_dt <= datetime.strptime(d, "%Y-%m-%d") <= end_dt):
            continue
        # 计算当日该股票的累计盈亏
        cum_pnl = 0.0
        for t in sorted_trades:
            entry_dt = datetime.strptime(t.entry_date, "%Y-%m-%d")
            exit_dt = datetime.strptime(t.exit_date, "%Y-%m-%d") if t.exit_date else end_dt
            current_dt = datetime.strptime(d, "%Y-%m-%d")
            if entry_dt <= current_dt:
                if current_dt <= exit_dt:
                    # 持仓中：按当日收盘价计算浮盈
                    close = close_map.get(d, 0)
                    cum_pnl += (close - t.entry_price) * t.shares
                else:
                    # 已平仓：加上实现盈亏
                    cum_pnl += (t.exit_price - t.entry_price) * t.shares
        total = initial_capital + cum_pnl
        if total > peak:
            peak = total
        dd = peak - total
        result.append({
            "date": d,
            "equity": total,
            "position_value": cum_pnl,
            "total": total,
            "peak": peak,
            "dd": dd,
            "dd_pct": dd / peak * 100 if peak > 0 else 0,
        })
    return result
