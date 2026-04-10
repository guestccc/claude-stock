#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTA Report Pipeline — 主调度脚本
数据来源: a_stock_db (通过 db_adapter 读取)
运行: 2_process.py → 3_render.py
用法: python run_pipeline.py [--date 2026-04-09]
"""

from __future__ import annotations
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_step(script_name: str, desc: str, date_str: str, extra_args: list = None) -> bool:
    """执行单个步骤"""
    script_path = Path(__file__).parent / script_name
    print(f"\n{'=' * 50}")
    print(f"  ▶  {desc}")
    print(f"{'=' * 50}")
    cmd = [sys.executable, str(script_path), "--date", date_str]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(cmd, cwd=script_path.parent.parent)
    if result.returncode != 0:
        print(f"\n❌ Step 失败: {desc}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="CTA 报告生成流水线")
    parser.add_argument(
        "--date", default=datetime.now().strftime("%Y-%m-%d"),
        help="报告日期 (YYYY-MM-DD)"
    )
    args = parser.parse_args()

    print("=" * 50)
    print("CTA 唐奇安突破信号报告")
    print(f"  数据源: a_stock_db")
    print(f"  报告日期: {args.date}")
    print(f"  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    steps = [
        ("2_process.py", "Step 1/2: 数据处理 (DB → 唐奇安/ATR/评分)"),
        ("3_render.py",  "Step 2/2: 报告渲染 (JSON → Markdown)"),
    ]

    for script, desc in steps:
        if not run_step(script, desc, args.date):
            sys.exit(1)

    print("\n" + "=" * 50)
    print("🎉 流水线执行完毕！")
    print(f"  报告: output/{args.date}_signal_report.md")
    print("=" * 50)


if __name__ == "__main__":
    main()
