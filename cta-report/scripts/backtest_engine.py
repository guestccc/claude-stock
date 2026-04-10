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
        rows.append({
            "date": date_str,
            "open": r[1],
            "close": r[2],
            "high": r[3],
            "low": r[4],
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


class Trade:
    """单笔交易"""
    def __init__(self, entry_date, entry_price, stop_loss, take_profit, atr, reason=""):
        self.entry_date = entry_date
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.atr = atr
        self.exit_date = None
        self.exit_price = None
        self.pnl = 0.0
        self.pnl_r = 0.0
        self.holding_days = 0
        self.shares = 0
        self.reason = reason  # 触发原因: stop/target/force
        self.risk_per_share = 0.0
        self.max_dd = 0.0  # 最大浮亏


def backtest_stock(code, start_date, end_date, initial_capital=INITIAL_CAPITAL,
                   max_positions=3, lookback=60):
    """
    回测单只股票
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

        # 检查是否在持仓中
        if position is None:
            # 检查是否突破
            if close_today > upper:
                atr = calc_atr(rows[:i + 1], ATR_PERIOD)
                if atr <= 0:
                    continue
                stop = open_tomorrow - atr * 1.3
                target = open_tomorrow + atr * 2.0
                position = Trade(
                    entry_date=today["date"],
                    entry_price=open_tomorrow,
                    stop_loss=stop,
                    take_profit=target,
                    atr=atr,
                    reason="breakout"
                )
                position.shares = math.floor(capital * 0.3 / open_tomorrow / 100) * 100
                position.shares = max(position.shares, 100)
                position.risk_per_share = open_tomorrow - stop

                # 记录买入日净值
                cost = position.shares * open_tomorrow
                equity = capital - cost
                equity_curve.append({
                    "date": today["date"],
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
            # 持仓中，检查是否触发止损/止盈
            low_today = today["low"] or 0
            high_today = today["high"] or 0
            close_today_pos = today["close"] or 0

            exit_price = None
            exit_reason = None

            # 计算持仓期间最大回撤（用当日最低价模拟）
            if low_today > 0 and position.shares > 0:
                # 以最低价计算持仓价值
                pos_low_value = position.shares * low_today
                # 成本 = shares * entry_price
                cost_basis = position.shares * position.entry_price
                # 浮亏
                floating_loss = cost_basis - pos_low_value
                if floating_loss > position_max_dd:
                    position_max_dd = floating_loss
                    position_dd_entry_price = position.entry_price

            # 优先检查止盈（盘中最高价触及）
            if high_today >= position.take_profit:
                exit_price = position.take_profit
                exit_reason = "take_profit"
            # 检查止损（盘中最低价触及）
            elif low_today <= position.stop_loss:
                exit_price = position.stop_loss
                exit_reason = "stop_loss"
            # 收盘前检查：是否跌破止损
            elif close_today_pos < position.stop_loss:
                exit_price = position.stop_loss
                exit_reason = "stop_loss"

            if exit_price and exit_price > 0:
                position.exit_date = today["date"]
                position.exit_price = exit_price
                position.reason = exit_reason
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
        pnl = (position.exit_price - position.entry_price) * position.shares
        position.pnl = pnl
        position.pnl_r = pnl / (position.risk_per_share * position.shares) if position.risk_per_share > 0 else 0
        position.holding_days = (
            datetime.strptime(last["date"], "%Y-%m-%d") -
            datetime.strptime(position.entry_date, "%Y-%m-%d")
        ).days
        # 记录最大回撤到交易
        position.max_dd = position_max_dd

        trades.append(position)
        capital += pnl

    # 计算统计
    stats = calc_stats(trades, initial_capital, capital, peak_capital, start_date, end_date, equity_curve)
    # 只返回回测区间内的 K 线数据（用于绘图）
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    klines = [r for r in rows if r["date"] and datetime.strptime(r["date"], "%Y-%m-%d") >= start_dt]
    return trades, equity_curve, stats, klines


def calc_stats(trades, initial, final, peak, start_date, end_date, equity_curve=None):
    """计算绩效统计"""
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

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]

    # 最大回撤（从 equity_curve 找最大回撤点）
    max_dd = 0.0
    max_dd_date = None
    if equity_curve:
        for e in equity_curve:
            if e["dd"] > max_dd:
                max_dd = e["dd"]
                max_dd_date = e["date"]

    # 夏普比率（简化：月度收益）
    if len(trades) > 1:
        monthly_returns = []
        month_groups = {}
        for t in trades:
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

    avg_holding = sum(t.holding_days for t in trades) / len(trades) if trades else 0
    best = max(trades, key=lambda t: t.pnl) if trades else None
    worst = min(trades, key=lambda t: t.pnl) if trades else None

    return {
        "initial_capital": initial,
        "final_capital": round(final, 2),
        "total_return": round(final - initial, 2),
        "total_return_pct": round((final - initial) / initial * 100, 2),
        "num_trades": len(trades),
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
    }
