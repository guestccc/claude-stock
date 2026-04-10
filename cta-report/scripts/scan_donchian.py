#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTA 唐奇安扫描
扫描全市场所有股票的唐奇安突破情况，按综合分排序输出
"""

import sys
import math
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = "/Users/jschen/Desktop/person/claude-study/a_stock_db/a_stock.db"
DONCHIAN_PERIOD = 20


# ============================================================
# 数据库读取
# ============================================================

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_all_codes(conn, report_date):
    """获取某日有数据的股票"""
    cursor = conn.execute(
        "SELECT DISTINCT code FROM stock_daily WHERE 日期 LIKE ? ORDER BY code",
        (report_date + "%",)
    )
    return [r[0] for r in cursor.fetchall()]


def get_stock_name(conn, code):
    cursor = conn.execute(
        "SELECT 股票简称 FROM stock_basic WHERE code = ?", (code,)
    )
    row = cursor.fetchone()
    return row[0] if row else code


def get_history(conn, code, report_date, lookback=30):
    """获取近N日历史数据"""
    end = datetime.strptime(report_date, "%Y-%m-%d")
    start = end - timedelta(days=lookback * 1.5)
    cursor = conn.execute("""
        SELECT 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额
        FROM stock_daily
        WHERE code = ? AND 日期 >= ? AND 日期 <= ?
        ORDER BY 日期
    """, (code, start.strftime("%Y-%m-%d"), report_date + " 23:59:59"))
    rows = cursor.fetchall()
    data = []
    for r in rows:
        date_str = str(r[0])[:10] if r[0] else None
        data.append({
            "date": date_str,
            "open": r[1],
            "close": r[2],
            "high": r[3],
            "low": r[4],
            "volume": r[5],
            "turnover": r[6],
        })
    return data


# ============================================================
# 指标计算
# ============================================================

def calc_atr(rows, period=14):
    """计算 ATR"""
    if len(rows) < period + 1:
        return 0.0
    rows = rows[-(period + 1):]
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


def calc_donchian(rows, period=20, exclude_today=True):
    """计算唐奇安通道"""
    if exclude_today:
        rows = rows[:-1]
    if len(rows) < period:
        return 0.0, 0.0
    recent = rows[-period:]
    upper = max(r["high"] for r in recent)
    lower = min(r["low"] for r in recent)
    return upper, lower


def calc_breakout_days(rows, upper):
    """计算连续突破天数（从昨天往前数）"""
    breakout = 0
    # 从倒数第二天往前数
    for r in reversed(rows[:-1]):
        if r["close"] > upper:
            breakout += 1
        else:
            break
    return breakout


def calc_volume_ratio(rows):
    """计算量比（当日量 / 5日均量）"""
    if len(rows) < 6:
        return 1.0
    today_vol = rows[-1]["volume"] or 0
    avg_5 = sum((r["volume"] or 0) for r in rows[-6:-1]) / 5
    if avg_5 == 0:
        return 1.0
    return today_vol / avg_5


# ============================================================
# 评分
# ============================================================

def score_breakout_strength(pct):
    """突破强度评分（满分35）"""
    abs_pct = abs(pct)
    if 1.0 <= abs_pct <= 3.0:
        return 35
    elif abs_pct < 1.0:
        return int(abs_pct * 20)
    elif 3.0 < abs_pct <= 5.0:
        return 25
    elif 5.0 < abs_pct <= 8.0:
        return 15
    else:
        return 5


def score_breakout_days(days):
    """突破天数评分（满分25）"""
    if 1 <= days <= 3:
        return 25
    elif days == 4:
        return 20
    elif days == 5:
        return 15
    elif days > 5:
        return max(0, 15 - (days - 5) * 3)
    else:
        return 0


def score_safety_margin(pct):
    """距下轨安全垫评分（满分20）"""
    if pct >= 50:
        return 20
    elif pct >= 40:
        return 16
    elif pct >= 30:
        return 12
    elif pct >= 20:
        return 8
    elif pct >= 10:
        return 4
    else:
        return 0


def score_volume_ratio(vr):
    """量比评分（满分10）"""
    if vr >= 1.5:
        return 10
    elif vr >= 1.0:
        return 5
    else:
        return 0


def calc_total_score(bp, bd, sm, vr):
    """综合评分"""
    return score_breakout_strength(bp) + score_breakout_days(bd) + \
           score_safety_margin(sm) + score_volume_ratio(vr)


# ============================================================
# 主逻辑
# ============================================================

def scan_stocks(conn, report_date, lookback=30):
    """扫描全市场股票"""
    codes = get_all_codes(conn, report_date)
    results = []

    for i, code in enumerate(codes):
        if i % 500 == 0:
            print(f"  进度: {i}/{len(codes)}")

        rows = get_history(conn, code, report_date, lookback)
        if len(rows) < DONCHIAN_PERIOD + 5:
            continue

        name = get_stock_name(conn, code)
        today = rows[-1]
        prev_rows = rows[:-1]

        close = today["close"]
        upper, lower = calc_donchian(rows, DONCHIAN_PERIOD, exclude_today=True)

        if upper == 0:
            continue

        # 突破强度
        breakout_pct = (close - upper) / upper * 100
        breakout_amplitude = max(0, breakout_pct)
        breakout_days = calc_breakout_days(rows, upper)
        vol_ratio = calc_volume_ratio(rows)
        atr = calc_atr(rows)

        # 距下轨安全垫
        if lower > 0:
            safety_margin = (close - lower) / lower * 100
        else:
            safety_margin = 0

        # 量比
        vr = round(vol_ratio, 2)

        # 综合分
        total = calc_total_score(breakout_pct, breakout_days, safety_margin, vr)

        results.append({
            "code": code,
            "name": name,
            "close": round(close, 2),
            "upper": round(upper, 2),
            "lower": round(lower, 2),
            "breakout_pct": round(breakout_pct, 2),
            "breakout_days": breakout_days,
            "breakout_amplitude": round(breakout_amplitude, 2),
            "safety_margin": round(safety_margin, 2),
            "atr": round(atr, 3),
            "vol_ratio": vr,
            "total": total,
        })

    # 按综合分排序
    results.sort(key=lambda x: x["total"], reverse=True)
    return results


def save_to_db(conn, report_date, results):
    """保存到数据库"""
    date_str = report_date + " 00:00:00"

    # 先删除旧数据
    conn.execute(
        "DELETE FROM cta_donchian_scan WHERE scan_date LIKE ?",
        (report_date + "%",)
    )

    for r in results:
        conn.execute("""
            INSERT INTO cta_donchian_scan
            (code, 股票名称, scan_date, 收盘价, 上轨, 下轨, 突破强度,
             突破天数, 突破幅度, 距下轨_pct, atr, 量比, 综合分)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r["code"], r["name"], date_str, r["close"], r["upper"], r["lower"],
            r["breakout_pct"], r["breakout_days"], r["breakout_amplitude"],
            r["safety_margin"], r["atr"], r["vol_ratio"], r["total"]
        ))
    conn.commit()


def print_results(results, top_n=50):
    """打印结果"""
    print(f"\n{'='*110}")
    print(f"{'代码':<8} {'名称':<10} {'收盘':>8} {'上轨':>8} {'下轨':>8} "
          f"{'突破强度':>8} {'天数':>4} {'幅度':>6} {'安全垫':>6} {'ATR':>6} {'量比':>5} {'综合分':>6}")
    print(f"{'='*110}")

    for r in results[:top_n]:
        flag = "▲" if r["breakout_pct"] > 0 else " "
        print(
            f"{r['code']:<8} {r['name']:<10} {r['close']:>8.2f} "
            f"{r['upper']:>8.2f} {r['lower']:>8.2f} "
            f"{flag}{r['breakout_pct']:>7.2f}% {r['breakout_days']:>4} "
            f"{r['breakout_amplitude']:>5.1f}% {r['safety_margin']:>6.1f}% "
            f"{r['atr']:>6.3f} {r['vol_ratio']:>5.2f} {r['total']:>6}"
        )

    print(f"{'='*110}")
    print(f"共 {len(results)} 只股票 | 展示 Top {top_n}")
    print(f"\n评分规则: 突破强度(35) + 突破天数(25) + 安全垫(20) + 量比(10) = 满分90")


# ============================================================
# 入口
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="CTA 唐奇安扫描")
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="扫描日期 (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--top",
        type=int, default=50,
        help="展示前N只 (默认50)"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="保存到数据库"
    )
    args = parser.parse_args()

    print("=" * 50)
    print("CTA 唐奇安扫描")
    print(f"  扫描日期: {args.date}")
    print(f"  数据源: a_stock_db")
    print("=" * 50)

    conn = get_conn()

    print(f"\n🔍 扫描中...")
    results = scan_stocks(conn, args.date)

    print_results(results, top_n=args.top)

    if args.save:
        print(f"\n💾 保存到数据库...")
        save_to_db(conn, args.date, results)
        print("✅ 已保存到 cta_donchian_scan 表")

    conn.close()
    print("\n✅ 扫描完成")


if __name__ == "__main__":
    main()
