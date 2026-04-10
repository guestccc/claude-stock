#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTA Report Pipeline — Step 2/2
报告渲染: 读取每日快照 → Jinja2 模版 → Markdown 报告
输出: output/{date}_signal_report.md
"""

from __future__ import annotations
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    from jinja2 import Template
except ImportError:
    print("❌ 需要安装 jinja2: pip install jinja2")
    sys.exit(1)


# ============================================================
# 路径配置
# ============================================================

PROJECT_ROOT  = Path(__file__).parent.parent
DATA_DAILY_DIR = PROJECT_ROOT / "data" / "daily"
TEMPLATE_DIR  = PROJECT_ROOT / "templates"
OUTPUT_DIR    = PROJECT_ROOT / "output"

from datetime import datetime as _dt
REPORT_DATE = _dt.now().strftime("%Y-%m-%d")
REPORT_TIME   = "14:12"  # 可动态获取当前时间


# ============================================================
# 报告渲染
# ============================================================

def load_snapshot(date_str: str) -> dict:
    """加载每日快照"""
    path = DATA_DAILY_DIR / f"{date_str}.json"
    if not path.exists():
        print(f"❌ 快照不存在: {path}")
        print(f"   请先运行: python scripts/2_process.py")
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_template() -> str:
    """加载 Jinja2 模版"""
    template_path = TEMPLATE_DIR / "signal_report.md.j2"
    with open(template_path, encoding="utf-8") as f:
        return f.read()


def render_report(snapshot: dict, date_str: str, time_str: str) -> str:
    """渲染报告"""
    tmpl = Template(load_template(), keep_trailing_newline=True)

    # 过滤 ≥30 分股票，按评分降序
    all_stocks = [
        s for s in snapshot.get("stocks", [])
        if s.get("total_score", 0) >= 30
    ]
    all_stocks.sort(key=lambda x: x.get("total_score", 0), reverse=True)

    # Top 20 用于报告预览
    stocks = all_stocks[:20]
    total_count = len(all_stocks)

    return tmpl.render(
        report_date=date_str,
        report_time=time_str,
        market=snapshot.get("market", {}),
        stocks=stocks,
        total_count=total_count,
    )


def save_report(content: str, date_str: str) -> Path:
    """保存报告"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{date_str}_signal_report.md"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)

    return out_path


# ============================================================
# 主函数
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="CTA Step 3: 报告渲染")
    parser.add_argument("--date", default=REPORT_DATE, help="报告日期 (YYYY-MM-DD)")
    args = parser.parse_args()

    report_date = args.date

    print("=" * 50)
    print("CTA Step 2/2: 报告渲染")
    print(f"  日期: {report_date}")
    print("=" * 50)

    # 加载快照
    snapshot = load_snapshot(report_date)

    # 渲染
    report_time = datetime.now().strftime("%H:%M")
    content = render_report(snapshot, report_date, report_time)

    # 保存
    out_path = save_report(content, report_date)

    print(f"\n📄 报告已生成: {out_path}")
    print("\n" + "=" * 50)
    print("📋 报告预览:")
    print("=" * 50)
    print(content)
    print("=" * 50)
    print(f"\n✅ Step 3 完成！")


if __name__ == "__main__":
    main()
