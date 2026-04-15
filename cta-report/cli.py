#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTA 唐奇安报告系统 CLI
用法:
    python cli.py run --date 2026-04-07
    python cli.py scan --date 2026-04-07 --top 50 --save
    python cli.py test
"""

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CTA_SCRIPTS = Path(__file__).parent / "scripts"


def cmd_run(args):
    """生成报告"""
    cmd = ["python3", str(CTA_SCRIPTS / "run_pipeline.py")]
    if args.date:
        cmd.extend(["--date", args.date])
    return subprocess.run(cmd, cwd=PROJECT_ROOT).returncode


def cmd_scan(args):
    """扫描唐奇安突破"""
    cmd = ["python3", str(CTA_SCRIPTS / "scan_donchian.py")]
    if args.date:
        cmd.extend(["--date", args.date])
    cmd.extend(["--top", str(args.top)])
    if args.save:
        cmd.append("--save")
    return subprocess.run(cmd, cwd=PROJECT_ROOT).returncode


def cmd_test(args):
    """运行测试"""
    cmd = ["python3", str(CTA_SCRIPTS / "run_tests.py")]
    return subprocess.run(cmd, cwd=PROJECT_ROOT).returncode


def cmd_rules(args):
    """输出现有回测规则"""
    # 策略定义（与 backtest_cli.py 保持同步）
    BASE_STRATEGIES = {
        "fixed": "固定止盈",
        "trailing": "跟踪止损",
        "boll_middle": "BOLL中轨止盈",
        "trailing_boll": "跟踪止损加BOLL中轨",
        "half_exit": "半仓止盈",
        "half_exit_low3": "半仓止盈+前3日低点",
    }

    BASE_RUNS = [
        ("fixed", 2.0, 1.0),
        ("trailing", 2.0, 1.0),
        ("boll_middle", 2.0, 1.0),
        ("trailing_boll", 2.0, 1.0),
    ]

    COMPARE_STRATEGIES = [
        ("fixed", 2.0, 1.0),
        ("trailing", 2.0, 1.0),
        ("half_exit", 2.0, 0.5),
        ("half_exit_low3", 2.0, 1.0),
    ]

    HALF_EXIT_COMBOS = [
        {"tp": tp, "atr_k": atr_k}
        for tp in [2.0, 3.0, 4.0]
        for atr_k in [0.5, 1.0, 1.5]
    ]

    print("=" * 60)
    print("CTA 唐奇安突破回测 — 现有规则一览")
    print("=" * 60)

    print("\n📋 出场策略列表:")
    print("-" * 40)
    for key, desc in BASE_STRATEGIES.items():
        print(f"  {key:20s}  {desc}")

    print(f"\n📊 默认基础策略（不指定 --strategy 时前4种 × 2.0 ATR）:")
    print("-" * 40)
    for exit_key, tp, atr_k in BASE_RUNS:
        label = BASE_STRATEGIES.get(exit_key, exit_key)
        print(f"  {exit_key:20s}  止盈倍数={tp:.1f}  ATR系数={atr_k:.1f}  ({label})")

    print(f"\n📊 多策略对比模式（不指定 --strategy 时的完整列表）:")
    print("-" * 40)
    for exit_key, tp, atr_k in COMPARE_STRATEGIES:
        label = BASE_STRATEGIES.get(exit_key, exit_key)
        print(f"  {exit_key:20s}  止盈倍数={tp:.1f}  ATR系数={atr_k:.1f}  ({label})")

    print(f"\n📊 半仓止盈参数组合（3×3 = {len(HALF_EXIT_COMBOS)} 种）:")
    print("-" * 40)
    for i, combo in enumerate(HALF_EXIT_COMBOS, 1):
        print(f"  #{i:<2d}  止盈倍数={combo['tp']:.1f}  ATR系数={combo['atr_k']:.1f}")

    print("\n" + "=" * 60)
    print("默认参数: lookback=60天  capital=100,000  tp_multiplier=4.0  trailing_atr_k=1.0")
    print("=" * 60)
    return 0


def cmd_backtest(args):
    """回测"""
    cmd = ["python3", str(CTA_SCRIPTS / "backtest_cli.py")]
    if args.code:
        cmd.extend(["--code", args.code])
    if args.codes:
        cmd.extend(["--codes", args.codes])
    if args.start:
        cmd.extend(["--start", args.start])
    if args.end:
        cmd.extend(["--end", args.end])
    cmd.extend(["--capital", str(args.capital)])
    return subprocess.run(cmd, cwd=PROJECT_ROOT).returncode


def main():
    parser = argparse.ArgumentParser(
        description="CTA 唐奇安报告系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python cli.py run                      # 生成当天报告
  python cli.py run --date 2026-04-07   # 生成指定日期报告
  python cli.py scan --top 50           # 扫描当天，Top 50
  python cli.py scan --date 2026-04-07 --save
  python cli.py backtest --code 000001 --start 2024-01-01  # 单股回测
  python cli.py backtest --codes 000001,002382 --capital 50000
  python cli.py rules                   # 查看现有回测规则
  python cli.py test                    # 运行测试
"""
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # run
    p_run = sub.add_parser("run", help="生成唐奇安突破信号报告")
    p_run.add_argument("--date", help="报告日期 (YYYY-MM-DD，默认当天)")

    # scan
    p_scan = sub.add_parser("scan", help="扫描全市场唐奇安突破情况")
    p_scan.add_argument("--date", help="扫描日期 (YYYY-MM-DD，默认当天)")
    p_scan.add_argument("--top", type=int, default=50, help="展示前N只 (默认50)")
    p_scan.add_argument("--save", action="store_true", help="保存到数据库")

    # backtest
    p_bt = sub.add_parser("backtest", help="回测指定股票的唐奇安突破策略")
    p_bt.add_argument("--code", help="单只股票代码，如 000001")
    p_bt.add_argument("--codes", help="多只股票，逗号分隔，如 000001,002382")
    p_bt.add_argument("--start", default="2024-01-01", help="回测开始日期")
    p_bt.add_argument("--end", help="回测结束日期（默认当天）")
    p_bt.add_argument("--capital", type=float, default=100000, help="初始本金（默认10万）")

    # rules
    sub.add_parser("rules", help="输出现有回测规则一览")

    # test
    sub.add_parser("test", help="运行测试套件")

    args = parser.parse_args()

    if args.cmd == "run":
        code = cmd_run(args)
    elif args.cmd == "scan":
        code = cmd_scan(args)
    elif args.cmd == "rules":
        code = cmd_rules(args)
    elif args.cmd == "backtest":
        code = cmd_backtest(args)
    elif args.cmd == "test":
        code = cmd_test(args)

    sys.exit(code if code else 0)


if __name__ == "__main__":
    main()
