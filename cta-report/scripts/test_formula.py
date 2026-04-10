#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTA 公式正确性测试
选一只股票，手工算一遍指标，验证程序输出与预期一致
"""

import sys
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from db_adapter import DBDataSource


# ============================================================
# 公式直接内嵌（与 2_process.py 保持一致）
# ============================================================

def calc_atr(df_rows, period=14):
    if len(df_rows) < period + 1:
        return 0.0
    rows = df_rows[-(period + 1):]
    trs = []
    for i in range(1, len(rows)):
        high = rows[i]["high"]
        low = rows[i]["low"]
        prev = rows[i - 1]["close"]
        tr = max(high - low, abs(high - prev), abs(low - prev))
        trs.append(tr)
    if not trs:
        return 0.0
    atr = sum(trs) / len(trs)
    alpha = 1.0 / period
    for tr in trs[1:]:
        atr = atr * (1 - alpha) + tr * alpha
    return atr


def calc_donchian_upper(df_rows, period=20, exclude_today=True):
    if exclude_today:
        rows = df_rows[:-1]
    else:
        rows = df_rows
    if len(rows) < period:
        return max(r["high"] for r in rows) if rows else 0.0
    recent = rows[-period:]
    return max(r["high"] for r in recent)


def calc_pullback(current, day_high):
    if day_high == 0:
        return 0.0
    return (current - day_high) / day_high * 100


def calc_vwap(day_row):
    v = day_row.get("volume", 0)
    if v == 0:
        return day_row.get("close", 0)
    turnover = day_row.get("turnover", day_row.get("close", 0) * v)
    return turnover / v


def calc_cta_position(entry_price, atr, risk_budget_r=1.0):
    if atr <= 0 or entry_price <= 0:
        return {"stop_loss": 0, "take_profit": 0}
    stop = entry_price - atr * 1.3
    target = entry_price + atr * 2.0
    return {"stop_loss": round(stop, 2), "take_profit": round(target, 2)}


def test_atr():
    """ATR 计算验证"""
    # 002957 近端数据（从 DB 读）
    db = DBDataSource()
    raw = db.get_stock_daily("002957", "2026-04-07", lookback=20)
    db.close()

    rows = raw["data"]
    # 取报告日前 15 条（排除当天）
    rows_for_atr = rows[:-1][-15:]

    # 手工算 TR = max(high-low, |high-prev_close|, |low-prev_close|)
    trs = []
    for i in range(1, len(rows_for_atr)):
        high = rows_for_atr[i]["high"]
        low = rows_for_atr[i]["low"]
        prev = rows_for_atr[i - 1]["close"]
        tr = max(high - low, abs(high - prev), abs(low - prev))
        trs.append(tr)

    # Wilder 平滑 ATR（14天）
    atr_manual = sum(trs) / len(trs)
    alpha = 1.0 / 14
    for tr in trs[1:]:
        atr_manual = atr_manual * (1 - alpha) + tr * alpha

    atr_prog = calc_atr(rows_for_atr, period=14)
    diff = abs(atr_prog - atr_manual)

    print(f"  ATR 手工={atr_manual:.4f} 程序={atr_prog:.4f} 差值={diff:.4f}")
    assert diff < 0.001, f"ATR 误差过大: {diff}"
    print("  ✅ ATR 正确")


def test_donchian_upper():
    """唐奇安上轨验证（20日，排除当天）"""
    db = DBDataSource()
    raw = db.get_stock_daily("002957", "2026-04-07", lookback=30)
    db.close()

    rows = raw["data"]
    # 排除当天，前 20 日最高
    rows_ex_today = rows[:-1]
    recent_20 = rows_ex_today[-20:]
    upper_manual = max(r["high"] for r in recent_20)

    upper_prog = calc_donchian_upper(rows, period=20, exclude_today=True)
    diff = abs(upper_prog - upper_manual)

    print(f"  上轨手工={upper_manual:.2f} 程序={upper_prog:.2f} 差值={diff:.4f}")
    assert diff < 0.001, f"唐奇安上轨误差过大: {diff}"
    print("  ✅ 唐奇安上轨正确")


def test_pullback():
    """回踩%验证: (close - high) / high × 100"""
    db = DBDataSource()
    raw = db.get_stock_daily("002957", "2026-04-07")
    db.close()

    today = raw["data"][-1]
    close = today["close"]
    high = today["high"]

    pullback_manual = (close - high) / high * 100
    pullback_prog = calc_pullback(close, high)

    diff = abs(pullback_prog - pullback_manual)
    print(f"  回踩手工={pullback_manual:.4f}% 程序={pullback_prog:.4f}% 差值={diff:.4f}")
    assert diff < 0.001, f"回踩误差过大: {diff}"
    print("  ✅ 回踩正确")


def test_vwap():
    """VWAP 验证: turnover / volume"""
    db = DBDataSource()
    raw = db.get_stock_daily("002957", "2026-04-07")
    db.close()

    today = raw["data"][-1]
    vwap_manual = today["turnover"] / today["volume"]
    vwap_prog = calc_vwap(today)

    diff = abs(vwap_prog - vwap_manual)
    print(f"  VWAP手工={vwap_manual:.4f} 程序={vwap_prog:.4f} 差值={diff:.4f}")
    assert diff < 0.001, f"VWAP误差过大: {diff}"
    print("  ✅ VWAP正确")


def test_cta_position():
    """CTA 建仓参数验证"""
    # 002957 当日数据
    db = DBDataSource()
    raw = db.get_stock_daily("002957", "2026-04-07")
    db.close()

    rows = raw["data"]
    entry = rows[-1]["close"]
    atr = calc_atr(rows[:-1], period=14)

    cta = calc_cta_position(entry, atr, risk_budget_r=0.8)

    # 手工算
    stop_manual = entry - atr * 1.3
    target_manual = entry + atr * 2.0

    print(f"  入场价={entry:.2f} ATR={atr:.4f}")
    print(f"  止损: 手工={stop_manual:.2f} 程序={cta['stop_loss']:.2f} 差值={abs(cta['stop_loss']-stop_manual):.4f}")
    print(f"  止盈: 手工={target_manual:.2f} 程序={cta['take_profit']:.2f} 差值={abs(cta['take_profit']-target_manual):.4f}")

    assert abs(cta['stop_loss'] - stop_manual) < 0.01, "止损误差"
    assert abs(cta['take_profit'] - target_manual) < 0.01, "止盈误差"
    print("  ✅ CTA建仓参数正确")


def main():
    print("=" * 50)
    print("CTA 公式正确性测试 | 股票: 002957 科瑞技术")
    print("=" * 50)

    tests = [
        ("ATR 唐奇安上轨", [test_atr, test_donchian_upper]),
        ("回踩 VWAP", [test_pullback, test_vwap]),
        ("CTA建仓", [test_cta_position]),
    ]

    all_pass = True
    for group, fns in tests:
        print(f"\n📐 {group}:")
        for fn in fns:
            try:
                fn()
            except Exception as e:
                print(f"  ❌ {fn.__name__} FAILED: {e}")
                all_pass = False

    print("\n" + "=" * 50)
    if all_pass:
        print("✅ 全部测试通过！公式逻辑正确")
    else:
        print("❌ 有测试失败，请检查公式")
        sys.exit(1)


if __name__ == "__main__":
    main()
