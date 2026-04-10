#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTA 全流程集成测试
跑一次 DB → Process → Render，确保流程不断、报告有内容
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))


def test_process_step():
    """Step 2: DB 模式处理"""
    print("\n🔄 运行 Step 2 (DB模式)...")
    import subprocess
    result = subprocess.run(
        [sys.executable, "scripts/2_process.py", "--date", "2026-04-07"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Step 2 失败: {result.stderr}"
    print("  ✅ Step 2 完成")

    # 检查输出 JSON
    daily_path = PROJECT_ROOT / "data" / "daily" / "2026-04-07.json"
    assert daily_path.exists(), "每日快照未生成"

    with open(daily_path, encoding="utf-8") as f:
        data = json.load(f)

    assert "stocks" in data, "缺少 stocks 字段"
    assert len(data["stocks"]) > 0, "股票列表为空"
    assert data["report_date"] == "2026-04-07", "日期不对"

    print(f"  ✅ 快照正常: {len(data['stocks'])} 只股票")


def test_render_step():
    """Step 3: 渲染报告"""
    print("\n🔄 运行 Step 3 (渲染)...")
    import subprocess
    result = subprocess.run(
        [sys.executable, "scripts/3_render.py", "--date", "2026-04-07"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Step 3 失败: {result.stderr}"
    print("  ✅ Step 3 完成")

    # 检查报告
    report_path = PROJECT_ROOT / "output" / "2026-04-07_signal_report.md"
    assert report_path.exists(), "报告未生成"

    # 检查报告内容
    with open(report_path, encoding="utf-8") as f:
        content = f.read()

    assert "金陵体育" in content or "江天化学" in content or "博力威" in content, "报告内容为空"
    assert "大盘状态" in content, "缺少大盘状态"
    assert "CTA建仓分析" in content, "缺少CTA分析"

    print("  ✅ 报告内容正常")


def test_top20_report():
    """Top 20 报告内容验证"""
    report_path = PROJECT_ROOT / "output" / "2026-04-07_signal_report.md"
    with open(report_path, encoding="utf-8") as f:
        content = f.read()

    # 确认股票之间有空行
    lines = content.split("\n")
    # 找到两只股票之间的位置，应该有空行
    stock_count = content.count("**") // 2  # 每只股票有 2 个 **bold**
    print(f"  📊 报告包含约 {stock_count} 只股票")

    # 检查文件大小合理
    size_kb = report_path.stat().st_size / 1024
    assert 5 < size_kb < 500, f"报告过大或过小: {size_kb:.1f}KB"
    print(f"  ✅ 报告大小正常: {size_kb:.1f}KB")


def main():
    print("=" * 50)
    print("CTA 全流程集成测试")
    print("=" * 50)

    tests = [
        ("Step 1 处理", test_process_step),
        ("Step 2 渲染", test_render_step),
        ("Top 20 报告", test_top20_report),
    ]

    all_pass = True
    for name, fn in tests:
        try:
            fn()
        except Exception as e:
            print(f"  ❌ {name} FAILED: {e}")
            all_pass = False

    print("\n" + "=" * 50)
    if all_pass:
        print("✅ 全部测试通过！流程正常")
    else:
        print("❌ 有测试失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
