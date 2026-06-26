"""
A股量化分析平台 — 统一交互式 CLI 入口

用法: python3 run.py

命令来源:
  前端:     自动读取 web/package.json 的 scripts
  后端:     本文件中声明式定义 (BACKEND_COMMANDS)
  数据获取: 从 a_stock_fetcher.cli.COMMAND_REGISTRY 导入
  系统:     本文件中声明式定义 (SYSTEM_COMMANDS)

维护规则:
  - 新增前端命令 → 编辑 web/package.json，run.py 自动读取
  - 新增数据命令 → 编辑 a_stock_fetcher/cli.py 的 COMMAND_REGISTRY + main()，run.py 自动读取
  - 新增后端/系统命令 → 编辑本文件中对应列表
"""
import json
import os
import signal
import subprocess
import sys

import questionary

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 1. 前端命令：自动从 package.json 读取
# ============================================================

def load_web_scripts() -> dict[str, str]:
    """自动读取 web/package.json 的 scripts"""
    pkg_path = os.path.join(PROJECT_ROOT, "web", "package.json")
    try:
        with open(pkg_path, "r", encoding="utf-8") as f:
            return json.load(f).get("scripts", {})
    except FileNotFoundError:
        return {}

# scripts 名称 → 友好描述
WEB_SCRIPT_DESC = {
    "dev": "启动开发服务器",
    "build": "生产构建",
    "lint": "代码检查",
    "preview": "预览生产构建",
}

# ============================================================
# 2. 后端命令：声明式定义
# ============================================================

BACKEND_COMMANDS = [
    {
        "label": "启动后端服务 (uvicorn --reload)",
        "cmd": ["python3", "-m", "uvicorn", "server.main:app", "--host", "::", "--port", "8000", "--reload"],
        "background": True,  # 后台运行，不阻塞
        "port": 8000,        # 启动前自动杀掉占用该端口的旧进程
        "url": "http://localhost:8000",
    },
    {
        "label": "启动定时调度器",
        "cmd": ["python3", "-m", "a_stock_fetcher.cli", "scheduler"],
        "background": True,
    },
    {
        "label": "查看调度器状态",
        "cmd": ["python3", "-m", "a_stock_fetcher.cli", "status"],
        "background": False,
    },
]

# ============================================================
# 3. 数据获取命令：从 cli.py 导入 COMMAND_REGISTRY
# ============================================================

def load_data_commands() -> list[tuple]:
    """从 a_stock_fetcher.cli 导入命令注册表"""
    try:
        from a_stock_fetcher.cli import COMMAND_REGISTRY
        return COMMAND_REGISTRY
    except ImportError:
        print("⚠ 无法导入 a_stock_fetcher.cli.COMMAND_REGISTRY")
        return []

# ============================================================
# 4. 系统命令：声明式定义
# ============================================================

SYSTEM_COMMANDS = [
    {
        "label": "初始化数据库",
        "cmd": ["python3", "-m", "a_stock_fetcher.cli", "init"],
    },
    {
        "label": "查看配置规则",
        "cmd": ["python3", "-m", "a_stock_fetcher.cli", "rules"],
    },
]

# ============================================================
# 执行器
# ============================================================

def run_command(cmd: list[str], cwd: str | None = None, background: bool = False, port: int | None = None) -> None:
    """执行命令"""
    if background:
        # 后台服务：先杀掉占用端口的旧进程
        if port:
            try:
                result = subprocess.run(
                    ["lsof", "-ti", f":{port}"],
                    capture_output=True, text=True,
                )
                pids = [p for p in result.stdout.strip().split('\n') if p.strip()]
                for pid in pids:
                    os.kill(int(pid.strip()), signal.SIGKILL)
                    print(f"  🔄 已终止旧进程 (PID: {pid.strip()})")
            except Exception:
                pass

        proc = subprocess.Popen(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        print(f"  ✅ 已启动 (PID: {proc.pid})")
    else:
        subprocess.run(cmd, cwd=cwd or PROJECT_ROOT)
        input("\n  按回车返回...")


def collect_param(param_mode: str | None, prompt: str | None) -> list[str]:
    """根据参数模式交互收集命令参数"""
    if param_mode is None:
        return []

    if param_mode == "limit":
        val = questionary.text(f"  {prompt or '数量N'}:", default="").ask()
        return [val] if val and val.strip() else []

    if param_mode == "code":
        val = questionary.text(f"  {prompt or '代码'}:").ask()
        return [val] if val else []

    if param_mode == "codes":
        val = questionary.text(f"  {prompt or '股票代码（逗号分隔）'}:").ask()
        return ["--codes", val] if val else []

    if param_mode == "days":
        val = questionary.text(f"  {prompt or '天数'}:").ask()
        return ["--days", val] if val else []

    if param_mode == "date_range":
        start = questionary.text("  开始日期 (如 2026-05-01):").ask()
        end = questionary.text("  结束日期 (如 2026-05-12):").ask()
        args = []
        if start:
            args += ["--start", start]
        if end:
            args += ["--end", end]
        return args

    return []

# ============================================================
# 菜单页面
# ============================================================

def page_frontend():
    """前端菜单 — 从 package.json 自动生成"""
    scripts = load_web_scripts()
    if not scripts:
        print("  ⚠ 未找到 web/package.json 或无 scripts")
        input("  按回车返回...")
        return

    choices = []
    for name, cmd in scripts.items():
        desc = WEB_SCRIPT_DESC.get(name, "")
        label = f"{name:12s} {desc}" if desc else f"{name:12s} {cmd}"
        choices.append(label)

    choices.append("↩ 返回主菜单")

    choice = questionary.select("  选择前端命令:", choices=choices).ask()
    if not choice or choice == "↩ 返回主菜单":
        return

    script_name = choice.split()[0]
    run_command(["npm", "run", script_name], cwd=os.path.join(PROJECT_ROOT, "web"))


def page_backend():
    """后端菜单"""
    choices = [cmd["label"] for cmd in BACKEND_COMMANDS]
    choices.append("↩ 返回主菜单")

    choice = questionary.select("  选择后端命令:", choices=choices).ask()
    if not choice or choice == "↩ 返回主菜单":
        return

    cmd_def = next((c for c in BACKEND_COMMANDS if c["label"] == choice), None)
    if cmd_def:
        run_command(
            cmd_def["cmd"],
            background=cmd_def.get("background", False),
            port=cmd_def.get("port"),
        )
        if cmd_def.get("url"):
            print(f"  🌐 {cmd_def['url']}")


def page_data():
    """数据获取菜单 — 从 COMMAND_REGISTRY 自动生成"""
    registry = load_data_commands()
    if not registry:
        print("  ⚠ 无可用数据命令")
        input("  按回车返回...")
        return

    # 第一步：选择数据类型分组
    groups = list(dict.fromkeys(item[0] for item in registry))
    group_choices = groups + ["↩ 返回主菜单"]

    group = questionary.select("  选择数据类型:", choices=group_choices).ask()
    if not group or group == "↩ 返回主菜单":
        return

    # 第二步：选择具体命令
    group_items = [item for item in registry if item[0] == group]
    cmd_choices = [f"{item[2]}" for item in group_items]
    cmd_choices.append("↩ 返回上层")

    cmd_choice = questionary.select(f"  [{group}] 选择命令:", choices=cmd_choices).ask()
    if not cmd_choice or cmd_choice == "↩ 返回上层":
        page_data()
        return

    # 找到选中的命令
    selected = next((item for item in group_items if item[2] == cmd_choice), None)
    if not selected:
        return

    _, cmd_name, _, param_mode, param_prompt = selected

    # 第三步：收集参数（如需要）
    extra_args = collect_param(param_mode, param_prompt)

    # 第四步：执行
    full_cmd = ["python3", "-m", "a_stock_fetcher.cli", cmd_name] + extra_args
    print(f"\n  执行: {' '.join(full_cmd)}\n")
    run_command(full_cmd)


def page_system():
    """系统菜单"""
    choices = [cmd["label"] for cmd in SYSTEM_COMMANDS]
    choices.append("↩ 返回主菜单")

    choice = questionary.select("  选择系统命令:", choices=choices).ask()
    if not choice or choice == "↩ 返回主菜单":
        return

    cmd_def = next((c for c in SYSTEM_COMMANDS if c["label"] == choice), None)
    if cmd_def:
        run_command(cmd_def["cmd"])

# ============================================================
# 主入口
# ============================================================

def main():
    while True:
        choice = questionary.select(
            "A股量化分析平台 — 命令中心",
            choices=[
                "1. 🖥 前端",
                "2. 🌐 后端",
                "3. 📊 数据获取",
                "4. 🔧 系统",
                "0. 退出",
            ],
        ).ask()

        if not choice or choice.startswith("0"):
            print("再见！")
            break
        elif choice.startswith("1"):
            page_frontend()
        elif choice.startswith("2"):
            page_backend()
        elif choice.startswith("3"):
            page_data()
        elif choice.startswith("4"):
            page_system()


if __name__ == "__main__":
    main()
