#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTA 测试套件 — 一键运行
用法: python scripts/run_tests.py
"""

import subprocess
import sys
from pathlib import Path

TESTS = [
    ("公式正确性", "test_formula.py"),
    ("全流程集成", "test_pipeline.py"),
]


def main():
    print("=" * 50)
    print("CTA 测试套件")
    print("=" * 50)

    script_dir = Path(__file__).parent
    all_pass = True

    for name, script in TESTS:
        script_path = script_dir / script
        if not script_path.exists():
            print(f"\n⚠️  找不到 {script}，跳过")
            continue

        print(f"\n{'─' * 40}")
        print(f"▶  {name}")
        print(f"{'─' * 40}")

        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=script_dir.parent
        )

        if result.returncode == 0:
            print(f"✅ {name} — PASS")
        else:
            print(f"❌ {name} — FAIL")
            all_pass = False

    print("\n" + "=" * 50)
    if all_pass:
        print("🎉 全部测试通过！")
    else:
        print("⚠️  有测试失败，请查看上方详情")
        sys.exit(1)


if __name__ == "__main__":
    main()
