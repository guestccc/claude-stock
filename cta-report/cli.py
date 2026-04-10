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

    # test
    sub.add_parser("test", help="运行测试套件")

    args = parser.parse_args()

    if args.cmd == "run":
        code = cmd_run(args)
    elif args.cmd == "scan":
        code = cmd_scan(args)
    elif args.cmd == "backtest":
        code = cmd_backtest(args)
    elif args.cmd == "test":
        code = cmd_test(args)

    sys.exit(code if code else 0)


if __name__ == "__main__":
    main()
