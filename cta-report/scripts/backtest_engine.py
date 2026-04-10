#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTA 海龟唐奇安突破回测引擎
"""

import sqlite3
import math
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = "/Users/jschen/Desktop/person/claude-study/a_stock_db/a_stock.db"
DONCHIAN_PERIOD = 20
ATR_PERIOD = 14
BOLL_PERIOD = 20
BOLL_STD = 2
INITIAL_CAPITAL = 100000  # 初始本金 10万


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_stock_data(conn, code, start_date, end_date, lookback=60):
    """获取股票历史数据（含回看期）"""
    start = datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=lookback)
    cursor = conn.execute("""
        SELECT 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额
        FROM stock_daily
        WHERE code = ? AND 日期 >= ? AND 日期 <= ?
        ORDER BY 日期
    """, (code, start.strftime("%Y-%m-%d"), end_date + " 23:59:59"))
    rows = []
    for r in cursor.fetchall():
        date_str = str(r[0])[:10] if r[0] else None
        # 数据库 high/low 列值有时颠倒，强制修正
        h, l = r[3], r[4]
        if (h or 0) < (l or 0):
            h, l = l, h
        rows.append({
            "date": date_str,
            "open": r[1],
            "close": r[2],
            "high": h,
            "low": l,
            "volume": r[5],
            "turnover": r[6],
        })
    return rows


def calc_atr(rows, period=ATR_PERIOD):
    """计算 ATR"""
    if len(rows) < period + 1:
        return 0.0
    rows = rows[-(period + 1):]
    trs = []
    for i in range(1, len(rows)):
        high = rows[i]["high"] or 0
        low = rows[i]["low"] or 0
        prev = rows[i - 1]["close"] or 0
        tr = max(high - low, abs(high - prev), abs(low - prev))
        trs.append(tr)
    if not trs:
        return 0.0
    atr = sum(trs) / len(trs)
    alpha = 1.0 / period
    for tr in trs[1:]:
        atr = atr * (1 - alpha) + tr * alpha
    return atr


def calc_donchian_upper(rows, period=DONCHIAN_PERIOD, exclude_today=True):
    """计算唐奇安上轨"""
    if exclude_today:
        rows = rows[:-1]
    if len(rows) < period:
        return 0.0
    recent = rows[-period:]
    return max((r["high"] or 0) for r in recent)


def calc_boll_upper(rows, period=BOLL_PERIOD, std_k=BOLL_STD, exclude_today=True):
    """计算 BOLL 上轨 = MA + K × STD（排除当天）"""
    if exclude_today:
        rows = rows[:-1]
    if len(rows) < period:
        return 0.0
    recent = rows[-period:]
    closes = [r["close"] or 0 for r in recent]
    if not closes:
        return 0.0
    # MA
    ma = sum(closes) / len(closes)
    # STD
    variance = sum((c - ma) ** 2 for c in closes) / len(closes)
    std = math.sqrt(variance)
    return ma + std_k * std


def calc_boll_middle(rows, period=BOLL_PERIOD, exclude_today=True):
    """计算 BOLL 中轨 = N日均线（排除当天）"""
    if exclude_today:
        rows = rows[:-1]
    if len(rows) < period:
        return 0.0
    recent = rows[-period:]
    closes = [r["close"] or 0 for r in recent]
    if not closes:
        return 0.0
    return sum(closes) / len(closes)


def calc_boll_middle_single(rows, period, idx):
    """计算某日 BOLL 中轨（排除当天）"""
    if idx < period:
        return 0.0
    recent = rows[max(0, idx - period):idx]
    if len(recent) < period:
        return 0.0
    closes = [r["close"] or 0 for r in recent]
    return sum(closes) / len(closes)


def _extract_trade_chart(rows, entry_idx, exit_idx, before=21, after=5):
    """提取交易图表数据：买入前 N 日 ~ 卖出后 N 日"""
    start = max(0, entry_idx - before)
    end = min(len(rows), exit_idx + after + 1)
    return [
        {
            "date": r["date"],
            "open": r["open"],
            "high": r["high"],
            "low": r["low"],
            "close": r["close"],
        }
        for r in rows[start:end]
    ]


class Trade:
    """单笔交易"""
    def __init__(self, entry_date, entry_price, stop_loss, take_profit, atr, reason=""):
        self.entry_date = entry_date          # 突破信号日（收盘突破）
        self.entry_price = entry_price        # 实际买入价（次日开盘）
        self.stop_loss = stop_loss            # 止损价
        self.take_profit = take_profit        # 止盈价
        self.atr = atr                        # 入场时 ATR
        self.exit_date = None                 # 实际卖出日
        self.exit_price = None                # 实际卖出价
        self.pnl = 0.0
        self.pnl_r = 0.0
        self.holding_days = 0
        self.shares = 0
        self.reason = reason                  # 触发原因: breakout/stop_loss/take_profit/force_close
        self.risk_per_share = 0.0             # 每股风险（入场价-止损价）
        self.max_dd = 0.0                     # 最大浮亏
        self.high_since_entry = 0.0            # 持仓期间最高价（用于跟踪止损）
        self.target_reached = False            # 是否已触及止盈目标（用于跟踪止损）
        self.high_since_target = 0.0           # 触及目标后的最高价（用于跟踪止损）
        # === 半仓止盈+移动止损 ===
        self.half_exited = False               # 是否已半仓止盈
        self.shares_at_half = 0                # 半仓止盈时的股数
        self.price_at_half = 0.0               # 半仓止盈时的价格
        self.high_since_half = 0.0             # 半仓止盈后的最高价
        self.pnl_half = 0.0                    # 半仓止盈时的盈利

        # === 买入细节 ===
        self.upper_band = 0.0                 # 突破的唐奇安上轨价格
        self.breakout_range_highs = []        # 构成上轨的那 N 天各自的最高价 [(date, high), ...]
        self.breakout_range_ohlc = []         # 构成上轨的那 N 天完整 OHLC
        self.breakout_upper_date = ""         # 上轨区间最后一天（突破确认日）
        self.breakout_close = 0.0             # 突破日收盘价
        self.breakout_exceed_pct = 0.0        # 收盘价比上轨高出多少 %
        self._entry_row_idx = 0               # 入场日在 rows 中的索引（内部用）
        self.trade_chart_ohlc = []            # 买入前21日 ~ 卖出后5日的完整 OHLC

        # === BOLL 细节 ===
        self.boll_upper = 0.0               # 入场时 BOLL 上轨
        self.boll_middle = 0.0              # 入场时 BOLL 中轨
        self.boll_breakout = False           # 是否 BOLL 上轨突破

        # === 卖出细节 ===
        self.exit_trigger_price = 0.0         # 触发卖出的那根 K 线的价（最高 or 最低）
        self.exit_trigger_date = ""           # 触发卖出那天的日期
        self.exit_formula = ""                # 文字说明：怎么算的


def backtest_stock(code, start_date, end_date, initial_capital=INITIAL_CAPITAL,
                   max_positions=3, lookback=60,
                   tp_multiplier=2.0,
                   exit_strategy="fixed",
                   trailing_atr_k=1.0,
                   half_exit_pct=50):
    """
    回测单只股票
    参数:
        tp_multiplier: 止盈倍数（默认2.0，即入场价+ATR×2.0）
        exit_strategy: 出场策略
            - "fixed": 固定止盈止损
            - "trailing": 先到目标位，再回撤 trailing_atr_k × ATR 止盈
            - "boll_middle": 跌破BOLL中轨止盈
            - "trailing_boll": 跟踪止损+BOLL中轨
            - "half_exit": 半仓止盈+移动止损
            - "half_exit_low3": 半仓止盈+跌破前3日最低收盘价清仓
        trailing_atr_k: 跟踪止损 ATR 系数（默认1.0）
        half_exit_pct: 半仓止盈卖出的比例%（默认50）
    返回: (trades, equity_curve, stats)
    """
    conn = get_conn()
    rows = get_stock_data(conn, code, start_date, end_date, lookback)
    conn.close()

    if len(rows) < DONCHIAN_PERIOD + 5:
        return [], [], {}

    trades = []
    equity_curve = []
    position = None
    capital = initial_capital
    peak_capital = capital
    # 持仓期间最大回撤
    position_max_dd = 0.0
    position_dd_entry_price = 0.0  # 回撤最大时的入场价

    for i in range(DONCHIAN_PERIOD, len(rows) - 1):
        today = rows[i]
        tomorrow = rows[i + 1]

        # 计算当日上轨（排除今天）
        upper = calc_donchian_upper(rows[:i + 1], DONCHIAN_PERIOD, exclude_today=True)
        if upper == 0:
            continue

        close_today = today["close"] or 0
        open_tomorrow = tomorrow["open"] or 0

        # 计算 BOLL 上轨和中轨（排除今天）
        boll_u = calc_boll_upper(rows[:i + 1], BOLL_PERIOD, BOLL_STD, exclude_today=True)
        boll_m = calc_boll_middle(rows[:i + 1], BOLL_PERIOD, exclude_today=True)

        # 检查是否在持仓中
        if position is None:
            # 入场条件：唐奇安上轨突破 且 BOLL 上轨突破
            if close_today > upper and close_today > boll_u and boll_u > 0:
                atr = calc_atr(rows[:i + 1], ATR_PERIOD)
                if atr <= 0:
                    continue
                stop = open_tomorrow - atr * 1.3
                target = open_tomorrow + atr * tp_multiplier
                position = Trade(
                    entry_date=tomorrow["date"],
                    entry_price=open_tomorrow,
                    stop_loss=stop,
                    take_profit=target,
                    atr=atr,
                    reason="breakout"
                )
                position.shares = math.floor(capital * 0.3 / open_tomorrow / 100) * 100
                position.shares = max(position.shares, 100)
                position.risk_per_share = open_tomorrow - stop
                position.high_since_entry = open_tomorrow
                position.target_reached = False
                position.high_since_target = open_tomorrow
                position.half_exited = False
                position.shares_at_half = 0
                position.price_at_half = 0.0
                position.high_since_half = open_tomorrow
                position.pnl_half = 0.0

                # 记录突破细节
                position.upper_band = round(upper, 3)
                position.breakout_close = round(close_today, 3)
                position.breakout_upper_date = today["date"]
                position.breakout_exceed_pct = round((close_today - upper) / upper * 100, 3)
                position._entry_row_idx = i
                # 记录 BOLL 细节
                position.boll_upper = round(boll_u, 3)
                position.boll_middle = round(boll_m, 3)
                position.boll_breakout = (close_today > boll_u)
                # 记录构成上轨的那 N 天的日期和最高价
                lookback_rows = rows[:i + 1]
                recent_n = lookback_rows[-(DONCHIAN_PERIOD):]
                position.breakout_range_highs = [
                    (r["date"], round(r["high"] or 0, 3))
                    for r in recent_n
                ]
                # 记录完整 OHLC（用于报告画 K 线）
                position.breakout_range_ohlc = [
                    {
                        "date": r["date"],
                        "open": r["open"],
                        "high": r["high"],
                        "low": r["low"],
                        "close": r["close"],
                    }
                    for r in recent_n
                ]

                # 记录买入日净值（次日）
                cost = position.shares * open_tomorrow
                equity = capital - cost
                equity_curve.append({
                    "date": tomorrow["date"],
                    "equity": equity,
                    "position_value": cost,
                    "total": capital,
                    "peak": peak_capital,
                    "dd": 0.0,
                    "dd_pct": 0.0,
                    "open_tomorrow": open_tomorrow,
                    "stop": stop,
                })
        else:
            # T+1 规则：买入当天不能卖出（_entry_row_idx 是信号日，买入日是信号日+1）
            if i <= position._entry_row_idx + 1:
                continue

            low_today = today["low"] or 0
            high_today = today["high"] or 0
            close_today_pos = today["close"] or 0

            exit_price = None
            exit_reason = None

            # 跟踪持仓期间最高价（用于跟踪止损）
            if not hasattr(position, 'high_since_entry') or high_today > position.high_since_entry:
                position.high_since_entry = high_today

            # 计算持仓期间最大回撤
            if low_today > 0 and position.shares > 0:
                pos_low_value = position.shares * low_today
                cost_basis = position.shares * position.entry_price
                floating_loss = cost_basis - pos_low_value
                if floating_loss > position_max_dd:
                    position_max_dd = floating_loss

            # === 出场策略 ===
            if exit_strategy in ("fixed", "trailing", "trailing_boll"):
                # 止损（固定）
                if low_today <= position.stop_loss:
                    exit_price = position.stop_loss
                    exit_reason = "stop_loss"
                    position.exit_trigger_price = round(low_today, 3)
                    position.exit_trigger_date = today["date"]
                    position.exit_formula = (
                        f"盘中最低 {low_today:.3f} ≤ 止损价 {position.stop_loss:.3f}，"
                        f"触发止损 | 止损 = 入场价 {position.entry_price:.3f} - ATR {position.atr:.3f} × 1.3"
                    )
                elif close_today_pos < position.stop_loss:
                    exit_price = position.stop_loss
                    exit_reason = "stop_loss"
                    position.exit_trigger_price = round(close_today_pos, 3)
                    position.exit_trigger_date = today["date"]
                    position.exit_formula = (
                        f"收盘价 {close_today_pos:.3f} < 止损价 {position.stop_loss:.3f}，"
                        f"触发止损 | 止损 = 入场价 {position.entry_price:.3f} - ATR {position.atr:.3f} × 1.3"
                    )
                # 止盈
                elif exit_strategy in ("trailing", "trailing_boll", "half_exit"):
                    # 跟踪止盈：先到目标位，再回撤 trailing_atr_k × ATR 才止盈
                    # 检查是否触及止盈目标
                    if not position.target_reached and high_today >= position.take_profit:
                        position.target_reached = True
                        position.high_since_target = high_today
                        position.exit_trigger_price = round(high_today, 3)
                        position.exit_trigger_date = today["date"]
                        position.exit_formula = (
                            f"盘中最高 {high_today:.3f} ≥ 目标价 {position.take_profit:.3f}，"
                            f"触及止盈目标！开始跟踪 | 止盈 = 入场价 {position.entry_price:.3f} + ATR {position.atr:.3f} × {tp_multiplier}"
                        )
                    elif position.target_reached:
                        # 目标已达到，跟踪最高价
                        if high_today > position.high_since_target:
                            position.high_since_target = high_today
                        trailing_trigger = position.high_since_target - trailing_atr_k * position.atr
                        if exit_strategy == "trailing":
                            # 纯跟踪止损
                            if low_today <= trailing_trigger:
                                exit_price = trailing_trigger
                                exit_reason = "take_profit"
                                position.exit_trigger_price = round(low_today, 3)
                                position.exit_trigger_date = today["date"]
                                position.exit_formula = (
                                    f"盘中最低 {low_today:.3f} ≤ 跟踪止损价 {trailing_trigger:.3f}，"
                                    f"触发止盈 | 跟踪止损 = 目标后最高 {position.high_since_target:.3f} - ATR {position.atr:.3f} × {trailing_atr_k}"
                                )
                        elif exit_strategy == "trailing_boll":
                            # 跟踪止损 + BOLL 中轨
                            boll_m = calc_boll_middle_single(rows[:i + 1], BOLL_PERIOD, i)
                            boll_m_val = round(boll_m, 3) if boll_m > 0 else 0
                            if close_today_pos < boll_m_val and boll_m_val > 0:
                                exit_price = close_today_pos
                                exit_reason = "take_profit"
                                position.exit_trigger_price = round(close_today_pos, 3)
                                position.exit_trigger_date = today["date"]
                                position.exit_formula = (
                                    f"收盘价 {close_today_pos:.3f} < BOLL中轨 {boll_m_val:.3f}，"
                                    f"触发止盈 | BOLL中轨 = {BOLL_PERIOD}日MA = {boll_m_val:.3f}"
                                )
                            elif low_today <= trailing_trigger:
                                exit_price = trailing_trigger
                                exit_reason = "take_profit"
                                position.exit_trigger_price = round(low_today, 3)
                                position.exit_trigger_date = today["date"]
                                position.exit_formula = (
                                    f"盘中最低 {low_today:.3f} ≤ 跟踪止损价 {trailing_trigger:.3f}，"
                                    f"触发止盈 | 跟踪止损 = 目标后最高 {position.high_since_target:.3f} - ATR {position.atr:.3f} × {trailing_atr_k}"
                                )
                elif exit_strategy == "fixed":
                    # 固定止盈
                    if high_today >= position.take_profit:
                        exit_price = position.take_profit
                        exit_reason = "take_profit"
                        position.exit_trigger_price = round(high_today, 3)
                        position.exit_trigger_date = today["date"]
                        position.exit_formula = (
                            f"盘中最高 {high_today:.3f} ≥ 止盈价 {position.take_profit:.3f}，"
                            f"触发止盈 | 止盈 = 入场价 {position.entry_price:.3f} + ATR {position.atr:.3f} × {tp_multiplier}"
                        )
            elif exit_strategy == "boll_middle":
                # 止损（固定）
                if low_today <= position.stop_loss:
                    exit_price = position.stop_loss
                    exit_reason = "stop_loss"
                    position.exit_trigger_price = round(low_today, 3)
                    position.exit_trigger_date = today["date"]
                    position.exit_formula = (
                        f"盘中最低 {low_today:.3f} ≤ 止损价 {position.stop_loss:.3f}，"
                        f"触发止损 | 止损 = 入场价 {position.entry_price:.3f} - ATR {position.atr:.3f} × 1.3"
                    )
                elif close_today_pos < position.stop_loss:
                    exit_price = position.stop_loss
                    exit_reason = "stop_loss"
                    position.exit_trigger_price = round(close_today_pos, 3)
                    position.exit_trigger_date = today["date"]
                    position.exit_formula = (
                        f"收盘价 {close_today_pos:.3f} < 止损价 {position.stop_loss:.3f}，"
                        f"触发止损 | 止损 = 入场价 {position.entry_price:.3f} - ATR {position.atr:.3f} × 1.3"
                    )
                else:
                    # BOLL 中轨止盈
                    boll_m = calc_boll_middle_single(rows[:i + 1], BOLL_PERIOD, i)
                    boll_m_val = round(boll_m, 3) if boll_m > 0 else 0
                    if close_today_pos < boll_m_val and boll_m_val > 0:
                        exit_price = close_today_pos
                        exit_reason = "take_profit"
                        position.exit_trigger_price = round(close_today_pos, 3)
                        position.exit_trigger_date = today["date"]
                        position.exit_formula = (
                            f"收盘价 {close_today_pos:.3f} < BOLL中轨 {boll_m_val:.3f}，"
                            f"触发止盈 | BOLL中轨 = {BOLL_PERIOD}日MA = {boll_m_val:.3f}"
                        )

            elif exit_strategy == "half_exit":
                # 半仓止盈 + 移动止损
                half_pct = half_exit_pct / 100.0
                shares_to_sell_first = math.floor(position.shares * half_pct / 100) * 100
                shares_to_sell_first = max(shares_to_sell_first, 100)

                if not position.half_exited:
                    # 止损（固定，作用于全部仓位）
                    if low_today <= position.stop_loss:
                        exit_price = position.stop_loss
                        exit_reason = "stop_loss"
                        position.exit_trigger_price = round(low_today, 3)
                        position.exit_trigger_date = today["date"]
                        position.exit_formula = (
                            f"盘中最低 {low_today:.3f} ≤ 止损价 {position.stop_loss:.3f}，"
                            f"触发止损 | 止损 = 入场价 {position.entry_price:.3f} - ATR {position.atr:.3f} × 1.3"
                        )
                    elif close_today_pos < position.stop_loss:
                        exit_price = position.stop_loss
                        exit_reason = "stop_loss"
                        position.exit_trigger_price = round(close_today_pos, 3)
                        position.exit_trigger_date = today["date"]
                        position.exit_formula = (
                            f"收盘价 {close_today_pos:.3f} < 止损价 {position.stop_loss:.3f}，"
                            f"触发止损 | 止损 = 入场价 {position.entry_price:.3f} - ATR {position.atr:.3f} × 1.3"
                        )
                    # 检查止盈目标——半仓止盈，拆成两笔交易
                    elif high_today >= position.take_profit:
                        half_pnl = (position.take_profit - position.entry_price) * shares_to_sell_first
                        capital += half_pnl
                        if capital > peak_capital:
                            peak_capital = capital

                        # === Trade 1：入场 → 半仓止盈 ===
                        t1 = Trade(
                            entry_date=position.entry_date,
                            entry_price=position.entry_price,
                            stop_loss=position.stop_loss,
                            take_profit=position.take_profit,
                            atr=position.atr,
                            reason="half_exit",
                        )
                        t1.shares = shares_to_sell_first
                        t1.risk_per_share = position.risk_per_share
                        t1.upper_band = position.upper_band
                        t1.breakout_close = position.breakout_close
                        t1.breakout_upper_date = position.breakout_upper_date
                        t1.breakout_exceed_pct = position.breakout_exceed_pct
                        t1.boll_upper = position.boll_upper
                        t1.boll_middle = position.boll_middle
                        t1.boll_breakout = position.boll_breakout
                        t1.breakout_range_highs = position.breakout_range_highs
                        t1.breakout_range_ohlc = position.breakout_range_ohlc
                        t1._entry_row_idx = position._entry_row_idx
                        t1.exit_date = today["date"]
                        t1.exit_price = position.take_profit
                        t1.exit_trigger_price = round(high_today, 3)
                        t1.exit_trigger_date = today["date"]
                        t1.exit_formula = (
                            f"盘中最高 {high_today:.3f} ≥ 止盈价 {position.take_profit:.3f}，"
                            f"半仓止盈！卖出 {shares_to_sell_first} 股 ¥{position.take_profit:.3f}，"
                            f"剩余 {position.shares - shares_to_sell_first} 股继续跟踪"
                        )
                        t1.pnl = half_pnl
                        t1.pnl_r = half_pnl / (position.risk_per_share * shares_to_sell_first) if position.risk_per_share > 0 else 0
                        t1.holding_days = (datetime.strptime(today["date"], "%Y-%m-%d") - datetime.strptime(position.entry_date, "%Y-%m-%d")).days
                        t1.trade_chart_ohlc = _extract_trade_chart(rows, position._entry_row_idx, i)
                        t1.high_since_entry = position.high_since_entry
                        t1.target_reached = False
                        t1.half_exited = False
                        t1.shares_at_half = 0
                        t1.price_at_half = 0.0
                        t1.high_since_half = 0.0
                        t1.pnl_half = 0.0
                        t1.max_dd = 0.0
                        trades.append(t1)

                        # === Trade 2：剩余仓位继续跟踪 ===
                        remaining_shares = position.shares - shares_to_sell_first
                        position.shares = remaining_shares
                        position.half_exited = True  # 标记已半仓止盈，防止重复触发
                        position.pnl_half = half_pnl  # 记录半仓盈利
                        position.shares_at_half = remaining_shares  # 记录剩余股数
                        position.price_at_half = position.take_profit  # 记录半仓价
                        position.high_since_half = max(high_today, position.take_profit)  # 初始化跟踪高点
                        position.high_since_entry = position.take_profit
                        position.high_since_target = position.take_profit
                        position.target_reached = True  # 视为已到目标，继续跟踪
                        position.exit_trigger_price = round(high_today, 3)
                        position.exit_trigger_date = today["date"]
                        position.exit_formula = (
                            f"盘中最高 {high_today:.3f} ≥ 止盈价 {position.take_profit:.3f}，"
                            f"半仓止盈卖出 {shares_to_sell_first} 股 ¥{position.take_profit:.3f}，"
                            f"剩余 {remaining_shares} 股继续跟踪"
                        )
                else:
                    # 半仓止盈后，剩余仓位跟踪
                    if high_today > position.high_since_half:
                        position.high_since_half = high_today
                    trailing_trigger = position.high_since_half - trailing_atr_k * position.atr
                    if low_today <= trailing_trigger:
                        exit_price = trailing_trigger
                        exit_reason = "take_profit"
                        position.exit_trigger_price = round(low_today, 3)
                        position.exit_trigger_date = today["date"]
                        position.exit_formula = (
                            f"盘中最低 {low_today:.3f} ≤ 移动止损价 {trailing_trigger:.3f}，"
                            f"触发止盈 | 移动止损 = 半仓后最高 {position.high_since_half:.3f} - ATR {position.atr:.3f} × {trailing_atr_k}"
                        )

            elif exit_strategy == "half_exit_low3":
                # 半仓止盈 + 跌破前3日最低收盘价清仓
                half_pct = half_exit_pct / 100.0
                shares_to_sell_first = math.floor(position.shares * half_pct / 100) * 100
                shares_to_sell_first = max(shares_to_sell_first, 100)

                if not position.half_exited:
                    # 止损（固定，作用于全部仓位）
                    if low_today <= position.stop_loss:
                        exit_price = position.stop_loss
                        exit_reason = "stop_loss"
                        position.exit_trigger_price = round(low_today, 3)
                        position.exit_trigger_date = today["date"]
                        position.exit_formula = (
                            f"盘中最低 {low_today:.3f} ≤ 止损价 {position.stop_loss:.3f}，"
                            f"触发止损 | 止损 = 入场价 {position.entry_price:.3f} - ATR {position.atr:.3f} × 1.3"
                        )
                    elif close_today_pos < position.stop_loss:
                        exit_price = position.stop_loss
                        exit_reason = "stop_loss"
                        position.exit_trigger_price = round(close_today_pos, 3)
                        position.exit_trigger_date = today["date"]
                        position.exit_formula = (
                            f"收盘价 {close_today_pos:.3f} < 止损价 {position.stop_loss:.3f}，"
                            f"触发止损 | 止损 = 入场价 {position.entry_price:.3f} - ATR {position.atr:.3f} × 1.3"
                        )
                    # 检查止盈目标——半仓止盈，拆成两笔交易
                    elif high_today >= position.take_profit:
                        half_pnl = (position.take_profit - position.entry_price) * shares_to_sell_first
                        capital += half_pnl
                        if capital > peak_capital:
                            peak_capital = capital

                        # === Trade 1：入场 → 半仓止盈 ===
                        t1 = Trade(
                            entry_date=position.entry_date,
                            entry_price=position.entry_price,
                            stop_loss=position.stop_loss,
                            take_profit=position.take_profit,
                            atr=position.atr,
                            reason="half_exit_low3",
                        )
                        t1.shares = shares_to_sell_first
                        t1.risk_per_share = position.risk_per_share
                        t1.upper_band = position.upper_band
                        t1.breakout_close = position.breakout_close
                        t1.breakout_upper_date = position.breakout_upper_date
                        t1.breakout_exceed_pct = position.breakout_exceed_pct
                        t1.boll_upper = position.boll_upper
                        t1.boll_middle = position.boll_middle
                        t1.boll_breakout = position.boll_breakout
                        t1.breakout_range_highs = position.breakout_range_highs
                        t1.breakout_range_ohlc = position.breakout_range_ohlc
                        t1._entry_row_idx = position._entry_row_idx
                        t1.exit_date = today["date"]
                        t1.exit_price = position.take_profit
                        t1.exit_trigger_price = round(high_today, 3)
                        t1.exit_trigger_date = today["date"]
                        t1.exit_formula = (
                            f"盘中最高 {high_today:.3f} ≥ 止盈价 {position.take_profit:.3f}，"
                            f"半仓止盈！卖出 {shares_to_sell_first} 股 ¥{position.take_profit:.3f}，"
                            f"剩余 {position.shares - shares_to_sell_first} 股改用前3日最低收盘价跟踪"
                        )
                        t1.pnl = half_pnl
                        t1.pnl_r = half_pnl / (position.risk_per_share * shares_to_sell_first) if position.risk_per_share > 0 else 0
                        t1.holding_days = (datetime.strptime(today["date"], "%Y-%m-%d") - datetime.strptime(position.entry_date, "%Y-%m-%d")).days
                        t1.trade_chart_ohlc = _extract_trade_chart(rows, position._entry_row_idx, i)
                        t1.high_since_entry = position.high_since_entry
                        t1.target_reached = False
                        t1.half_exited = False
                        t1.shares_at_half = 0
                        t1.price_at_half = 0.0
                        t1.high_since_half = 0.0
                        t1.pnl_half = 0.0
                        t1.max_dd = 0.0
                        trades.append(t1)

                        # === Trade 2：剩余仓位继续跟踪（前3日最低收盘价） ===
                        remaining_shares = position.shares - shares_to_sell_first
                        position.shares = remaining_shares
                        position.half_exited = True
                        position.pnl_half = half_pnl
                        position.shares_at_half = remaining_shares
                        position.price_at_half = position.take_profit
                        position.high_since_half = max(high_today, position.take_profit)
                        position.high_since_entry = position.take_profit
                        position.high_since_target = position.take_profit
                        position.target_reached = True
                        position.exit_trigger_price = round(high_today, 3)
                        position.exit_trigger_date = today["date"]
                        position.exit_formula = (
                            f"盘中最高 {high_today:.3f} ≥ 止盈价 {position.take_profit:.3f}，"
                            f"半仓止盈卖出 {shares_to_sell_first} 股 ¥{position.take_profit:.3f}，"
                            f"剩余 {remaining_shares} 股改用前3日最低收盘价跟踪"
                        )
                else:
                    # 半仓止盈后，剩余仓位：跌破前3日最低收盘价清仓
                    if i >= 3:
                        low3 = min(rows[i-1]["close"], rows[i-2]["close"], rows[i-3]["close"])
                        if close_today_pos < low3:
                            exit_price = close_today_pos
                            exit_reason = "take_profit"
                            position.exit_trigger_price = round(close_today_pos, 3)
                            position.exit_trigger_date = today["date"]
                            position.exit_formula = (
                                f"收盘价 {close_today_pos:.3f} < 前3日最低收盘价 {low3:.3f}，"
                                f"触发清仓 | 前3日收盘: {rows[i-1]['close']:.3f}, {rows[i-2]['close']:.3f}, {rows[i-3]['close']:.3f}"
                            )

            if exit_price and exit_price > 0:
                position.exit_date = today["date"]
                position.exit_price = exit_price
                position.reason = exit_reason
                # 半仓止盈后剩余仓位退出：PnL = 半仓盈利 + 剩余仓位盈利
                if position.half_exited:
                    pnl = position.pnl_half + (exit_price - position.entry_price) * position.shares_at_half
                else:
                    pnl = (exit_price - position.entry_price) * position.shares
                position.pnl = pnl
                position.pnl_r = pnl / (position.risk_per_share * position.shares) if position.risk_per_share > 0 else 0
                position.holding_days = (
                    datetime.strptime(today["date"], "%Y-%m-%d") -
                    datetime.strptime(position.entry_date, "%Y-%m-%d")
                ).days

                # 记录最大回撤到交易
                position.max_dd = position_max_dd
                position_max_dd = 0.0
                position_dd_entry_price = 0.0

                # 提取交易图表 K 线（买入前21日 ~ 卖出后5日）
                position.trade_chart_ohlc = _extract_trade_chart(
                    rows, position._entry_row_idx, i
                )

                trades.append(position)
                capital += pnl

                # 更新峰值
                if capital > peak_capital:
                    peak_capital = capital

                position = None

            # 记录当日净值（含最大回撤）
            pos_value = position.shares * close_today_pos if position else 0
            current_total = capital
            current_peak = peak_capital
            current_dd = current_peak - current_total
            current_dd_pct = current_dd / current_peak * 100 if current_peak > 0 else 0
            equity_curve.append({
                "date": today["date"],
                "equity": current_total - pos_value,
                "position_value": pos_value,
                "total": current_total,
                "peak": current_peak,
                "dd": current_dd,
                "dd_pct": current_dd_pct,
            })

    # 如果最后还有持仓，按最后收盘价平仓
    if position is not None and len(rows) > 0:
        last = rows[-1]
        position.exit_date = last["date"]
        position.exit_price = last["close"]
        position.reason = "force_close"
        position.exit_trigger_price = round(last["close"], 3)
        position.exit_trigger_date = last["date"]
        position.exit_formula = (
            f"回测区间结束，按最后收盘价 {last['close']:.3f} 强制平仓 | "
            f"仍持仓 {(datetime.strptime(last['date'], '%Y-%m-%d') - datetime.strptime(position.entry_date, '%Y-%m-%d')).days} 天，"
            f"止损价 {position.stop_loss:.3f}，止盈价 {position.take_profit:.3f}"
        )
        pnl = (position.exit_price - position.entry_price) * position.shares
        position.pnl = pnl
        position.pnl_r = pnl / (position.risk_per_share * position.shares) if position.risk_per_share > 0 else 0
        position.holding_days = (
            datetime.strptime(last["date"], "%Y-%m-%d") -
            datetime.strptime(position.entry_date, "%Y-%m-%d")
        ).days
        # 记录最大回撤到交易
        position.max_dd = position_max_dd

        # 提取交易图表 K 线
        last_idx = len(rows) - 1
        position.trade_chart_ohlc = _extract_trade_chart(
            rows, position._entry_row_idx, last_idx
        )

        trades.append(position)
        capital += pnl

    # 计算统计
    stats = calc_stats(trades, initial_capital, capital, peak_capital, start_date, end_date, equity_curve)
    # 只返回回测区间内的 K 线数据（用于绘图）
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    klines = [r for r in rows if r["date"] and datetime.strptime(r["date"], "%Y-%m-%d") >= start_dt]
    return trades, equity_curve, stats, klines


def merge_split_trades(trades):
    """合并半仓止盈拆分的两笔交易为一条记录（用于统计盈亏比等指标）"""
    merged = []
    i = 0
    while i < len(trades):
        t = trades[i]
        # 检查下一笔是否是同一笔拆出的另一半
        if (i + 1 < len(trades)
                and trades[i + 1].entry_date == t.entry_date
                and trades[i + 1].entry_price == t.entry_price
                and t.reason in ("half_exit", "half_exit_low3")):
            t2 = trades[i + 1]
            m = Trade(
                entry_date=t.entry_date,
                entry_price=t.entry_price,
                stop_loss=t.stop_loss,
                take_profit=t.take_profit,
                atr=t.atr,
                reason=t.reason,
            )
            m.shares = t.shares + t2.shares
            m.exit_date = t2.exit_date
            # 加权平均退出价
            total_shares = t.shares + t2.shares
            m.exit_price = (t.exit_price * t.shares + t2.exit_price * t2.shares) / total_shares
            m.pnl = t.pnl + t2.pnl
            m.risk_per_share = t.risk_per_share
            m.holding_days = max(t.holding_days, t2.holding_days)
            merged.append(m)
            i += 2
        else:
            merged.append(t)
            i += 1
    return merged


def _count_trading_days(merged_trades, equity_curve):
    """计算实际参与交易日数（首笔入场 ~ 末笔出场之间的交易日数）"""
    if not merged_trades or not equity_curve:
        return 0
    first_date = min(t.entry_date for t in merged_trades)
    last_date = max(t.exit_date for t in merged_trades)
    count = sum(1 for e in equity_curve if first_date <= e["date"][:10] <= last_date)
    return count


def calc_stats(trades, initial, final, peak, start_date, end_date, equity_curve=None):
    """计算绩效统计（自动合并半仓拆分交易）"""
    if not trades:
        return {
            "initial_capital": initial,
            "final_capital": final,
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
            "best_trade": None,
            "worst_trade": None,
            "avg_holding_days": 0.0,
            "start_date": start_date,
            "end_date": end_date,
        }

    # 用合并后的交易计算统计指标（盈亏比等）
    merged = merge_split_trades(trades)
    wins = [t for t in merged if t.pnl > 0]
    losses = [t for t in merged if t.pnl <= 0]

    # 最大回撤（从 equity_curve 找最大回撤点）
    max_dd = 0.0
    max_dd_date = None
    if equity_curve:
        for e in equity_curve:
            if e["dd"] > max_dd:
                max_dd = e["dd"]
                max_dd_date = e["date"]

    # 夏普比率（简化：月度收益）
    if len(merged) > 1:
        monthly_returns = []
        month_groups = {}
        for t in merged:
            ym = t.exit_date[:7]
            if ym not in month_groups:
                month_groups[ym] = []
            month_groups[ym].append(t.pnl)
        for ym in sorted(month_groups):
            total = sum(month_groups[ym])
            ret = total / initial
            monthly_returns.append(ret)

        if monthly_returns and len(monthly_returns) > 1:
            mean_ret = sum(monthly_returns) / len(monthly_returns)
            variance = sum((r - mean_ret) ** 2 for r in monthly_returns) / len(monthly_returns)
            std_ret = math.sqrt(variance) if variance > 0 else 0
            sharpe = (mean_ret / std_ret * math.sqrt(12)) if std_ret > 0 else 0
        else:
            sharpe = 0.0
    else:
        sharpe = 0.0

    avg_holding = sum(t.holding_days for t in merged) / len(merged) if merged else 0
    best = max(merged, key=lambda t: t.pnl) if merged else None
    worst = min(merged, key=lambda t: t.pnl) if merged else None

    return {
        "initial_capital": initial,
        "final_capital": round(final, 2),
        "total_return": round(final - initial, 2),
        "total_return_pct": round((final - initial) / initial * 100, 2),
        "num_trades": len(merged),
        "win_trades": len(wins),
        "loss_trades": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
        "avg_win": round(sum(t.pnl for t in wins) / len(wins), 2) if wins else 0,
        "avg_loss": round(sum(t.pnl for t in losses) / len(losses), 2) if losses else 0,
        "avg_pnl": round(sum(t.pnl for t in trades) / len(trades), 2) if trades else 0,
        "rr_ratio": round(
            abs(sum(t.pnl for t in wins) / len(wins)) / abs(sum(t.pnl for t in losses) / len(losses))
            if losses and wins else 0, 2
        ),
        "max_drawdown": round(max_dd, 2),
        "max_drawdown_pct": round(max_dd / initial * 100, 2),
        "max_dd_date": max_dd_date,
        "sharpe_ratio": round(sharpe, 2),
        "best_trade": best,
        "worst_trade": worst,
        "avg_holding_days": round(avg_holding, 1),
        "start_date": start_date,
        "end_date": end_date,
        "daily_return_pct": round(
            ((final - initial) / initial * 100) / trading_days, 4
        ) if (trading_days := _count_trading_days(merged, equity_curve)) > 0 else 0,
    }
