#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTA 回测 CLI
用法:
    python backtest_cli.py --code 000001 --start 2024-01-01 --end 2026-04-07
    python backtest_cli.py --codes 000001,002382 --capital 50000
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backtest_engine import backtest_stock, get_conn
from backtest_report import generate_html_report


def main():
    parser = argparse.ArgumentParser(description="CTA 唐奇安回测")
    parser.add_argument("--code", help="单只股票代码，如 000001")
    parser.add_argument("--codes", help="多只股票，逗号分隔，如 000001,002382")
    parser.add_argument("--start", default="2024-01-01", help="回测开始日期")
    parser.add_argument("--end", help="回测结束日期（默认当天）")
    parser.add_argument("--capital", type=float, default=100000, help="初始本金（默认10万）")
    parser.add_argument("--lookback", type=int, default=60, help="回看天数（默认60）")
    args = parser.parse_args()

    from datetime import datetime
    end_date = args.end or datetime.now().strftime("%Y-%m-%d")

    codes = []
    if args.codes:
        codes = [c.strip() for c in args.codes.split(",")]
    elif args.code:
        codes = [args.code]
    else:
        print("❌ 请指定 --code 或 --codes")
        sys.exit(1)

    # 获取股票名称
    conn = get_conn()
    names = {}
    for code in codes:
        cursor = conn.execute(
            "SELECT 股票简称 FROM stock_basic WHERE code = ?", (code,)
        )
        row = cursor.fetchone()
        names[code] = row[0] if row else code
    conn.close()

    print("=" * 50)
    print("CTA 唐奇安突破回测")
    print(f"  股票: {', '.join(f'{c}({names[c]})' for c in codes)}")
    print(f"  区间: {args.start} ~ {end_date}")
    print(f"  本金: ¥{args.capital:,.0f}")
    print("=" * 50)

    for code in codes:
        name = names[code]
        print(f"\n🔄 回测 {code} {name}...")

        trades, equity_curve, stats, klines = backtest_stock(
            code, args.start, end_date,
            initial_capital=args.capital,
            lookback=args.lookback
        )

        if not trades:
            print(f"  ⚠️  无交易记录")
            continue

        report_path = generate_html_report(code, name, trades, equity_curve, stats, klines)
        print(f"  ✅ 完成: {stats['num_trades']} 笔交易")
        print(f"     收益率: {stats['total_return_pct']:+.1f}% | "
              f"胜率: {stats['win_rate']:.0f}% | "
              f"夏普: {stats['sharpe_ratio']:.2f} | "
              f"最大回撤: {stats['max_drawdown_pct']:.1f}%")
        print(f"  📄 报告: {report_path}")

    print("\n✅ 全部完成")


if __name__ == "__main__":
    main()
