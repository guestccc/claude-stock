#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTA 回测 CLI
用法:
    python backtest_cli.py --code 600584 --start 2024-01-01
    python backtest_cli.py --code 600584 --start 2024-01-01 --strategy half_exit
    python backtest_cli.py --code 600584 --start 2024-01-01 --strategy fixed --tp-multiplier 4.0
    # 不指定 strategy 时，默认跑全部方案并各自生成报告
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from backtest_engine import backtest_stock, get_conn
from backtest_report import generate_html_report
BASE_STRATEGIES = {
    "fixed": "固定止盈",
    "trailing": "跟踪止损",
    "boll_middle": "BOLL中轨止盈",
    "trailing_boll": "跟踪止损加BOLL中轨",
    "half_exit": "半仓止盈",
    "half_exit_low3": "半仓止盈+前3日低点",
}

# 半仓止盈的参数组合：3 × 3 = 9 种
HALF_EXIT_COMBOS = []
for tp in [2.0, 3.0, 4.0]:
    for atr_k in [0.5, 1.0, 1.5]:
        HALF_EXIT_COMBOS.append({
            "tp": tp,
            "atr_k": atr_k,
        })


def get_stock_name(code):
    conn = get_conn()
    cursor = conn.execute(
        "SELECT 股票简称 FROM stock_basic WHERE code = ?", (code,)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else code


def run_backtest(code, name, start_date, end_date, capital, lookback,
                 tp_multiplier, exit_strategy, trailing_atr_k, half_exit_pct=50):
    strategy_info = {
        "fixed": "固定止盈",
        "trailing": "跟踪止损",
        "boll_middle": "BOLL中轨止盈",
        "trailing_boll": "跟踪止损加BOLL中轨",
        "half_exit": "半仓止盈",
        "half_exit_low3": "半仓止盈+前3日低点",
    }.get(exit_strategy, exit_strategy)

    # 文件名用的key
    strategy_file_key = {
        "fixed": f"固定止盈×{tp_multiplier:.1f}",
        "trailing": f"跟踪止损×{tp_multiplier:.1f}",
        "boll_middle": f"BOLL中轨止盈×{tp_multiplier:.1f}",
        "trailing_boll": f"跟踪止损加BOLL中轨×{tp_multiplier:.1f}",
        "half_exit": f"半仓止盈×{tp_multiplier:.1f}回撤×{trailing_atr_k:.1f}ATR",
        "half_exit_low3": f"半仓止盈×{tp_multiplier:.1f}前3日低点",
    }.get(exit_strategy, exit_strategy)

    tp_suffix_map = {
        "fixed": f"×{tp_multiplier:.1f}",
        "trailing": f"×{tp_multiplier:.1f}+跟踪",
        "boll_middle": f"×{tp_multiplier:.1f}+BOLL中轨",
        "trailing_boll": f"×{tp_multiplier:.1f}+跟踪+BOLL",
        "half_exit": f"×{tp_multiplier:.1f}半仓+回撤×{trailing_atr_k:.1f}",
        "half_exit_low3": f"×{tp_multiplier:.1f}半仓+前3日低点",
    }
    tp_suffix = tp_suffix_map.get(exit_strategy, f"×{tp_multiplier:.1f}")

    print(f"\n{'='*50}")
    print(f"策略: {strategy_info} (止盈{tp_suffix})")

    trades, equity_curve, stats, klines = backtest_stock(
        code, start_date, end_date,
        initial_capital=capital,
        lookback=lookback,
        tp_multiplier=tp_multiplier,
        exit_strategy=exit_strategy,
        trailing_atr_k=trailing_atr_k,
        half_exit_pct=half_exit_pct,
    )

    if not trades:
        print(f"  ⚠️  无交易记录")
        return None

    # 报告文件名（中文）—— 收益率放末尾
    from backtest_report import BACKTEST_DIR
    today = datetime.now().strftime("%Y-%m-%d")
    safe_name = name.replace("/", "-")
    ret_sign = "+" if stats['total_return_pct'] >= 0 else ""
    filename = f"{today}_{code}_{safe_name}_{strategy_file_key}_{ret_sign}{stats['total_return_pct']:.1f}%.html"
    report_path = BACKTEST_DIR / filename

    stats["_strategy_name"] = strategy_info
    stats["_tp_suffix"] = tp_suffix

    from backtest_report import generate_html_report
    generate_html_report(code, name, trades, equity_curve, stats, klines,
                         report_filename=filename)

    print(f"  ✅ 完成: {stats['num_trades']} 笔交易")
    print(f"     收益率: {stats['total_return_pct']:+.1f}% | "
          f"胜率: {stats['win_rate']:.0f}% | "
          f"盈亏比: {stats['rr_ratio']:.2f} | "
          f"夏普: {stats['sharpe_ratio']:.2f} | "
          f"最大回撤: {stats['max_drawdown_pct']:.1f}%")
    print(f"  📄 报告: {report_path}")
    return stats


def main():
    parser = argparse.ArgumentParser(description="CTA 唐奇安回测")
    parser.add_argument("--code", help="单只股票代码，如 600584")
    parser.add_argument("--codes", help="多只股票，逗号分隔")
    parser.add_argument("--start", default="2024-01-01", help="回测开始日期")
    parser.add_argument("--end", help="回测结束日期（默认当天）")
    parser.add_argument("--capital", type=float, default=100000, help="初始本金")
    parser.add_argument("--lookback", type=int, default=60, help="回看天数")
    parser.add_argument("--strategy", choices=list(BASE_STRATEGIES.keys()),
                        help="指定出场策略，默认跑全部4种")
    parser.add_argument("--tp-multiplier", type=float, default=4.0,
                        help="止盈倍数（默认4.0）")
    parser.add_argument("--trailing-atr-k", type=float, default=1.0,
                        help="跟踪止损 ATR 系数（默认1.0）")
    args = parser.parse_args()

    end_date = args.end or datetime.now().strftime("%Y-%m-%d")

    codes = []
    if args.codes:
        codes = [c.strip() for c in args.codes.split(",")]
    elif args.code:
        codes = [args.code]
    else:
        print("❌ 请指定 --code 或 --codes")
        sys.exit(1)

    names = {c: get_stock_name(c) for c in codes}

    print("=" * 50)
    print("CTA 唐奇安突破回测")
    print(f"  股票: {', '.join(f'{c}({names[c]})' for c in codes)}")
    print(f"  区间: {args.start} ~ {end_date}")
    print(f"  本金: ¥{args.capital:,.0f}")
    print("=" * 50)

    # 基础策略（×2.0）
    BASE_RUNS = [
        ("fixed", 2.0, 1.0),
        ("trailing", 2.0, 1.0),
        ("boll_middle", 2.0, 1.0),
        ("trailing_boll", 2.0, 1.0),
    ]

    for code in codes:
        name = names[code]
        print(f"\n🔄 回测 {code} {name}...")

        all_results = []

        if args.strategy:
            # 只跑指定策略
            run_backtest(code, name, args.start, end_date, args.capital, args.lookback,
                         tp_multiplier=args.tp_multiplier,
                         exit_strategy=args.strategy,
                         trailing_atr_k=args.trailing_atr_k)
        else:
            # 跑所有关键策略，每个生成单独报告
            COMPARE_STRATEGIES = [
                ("fixed", 2.0, 1.0),
                ("trailing", 2.0, 1.0),
                ("half_exit", 2.0, 0.5),
                ("half_exit_low3", 2.0, 1.0),
            ]
            for exit_key, tp, atr_k in COMPARE_STRATEGIES:
                run_backtest(code, name, args.start, end_date, args.capital, args.lookback,
                             tp_multiplier=tp,
                             exit_strategy=exit_key,
                             trailing_atr_k=atr_k)

    print("\n✅ 全部完成")


if __name__ == "__main__":
    main()
