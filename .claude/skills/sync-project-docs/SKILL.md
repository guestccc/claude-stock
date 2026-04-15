---
name: sync-project-docs
description: 当用户要新增命令时，一定要用；当 a_stock_fetcher/cli.py 或 cta-report/cli.py 新增或更新命令时，同步更新对应 skill 和 README
---

# 同步项目文档

## 触发条件

当用户新增或更新了以下任一文件时，执行此 skill：

| 变更文件                 | 触发同步                       |
| ------------------------ | ------------------------------ |
| `a_stock_fetcher/cli.py` | 同步该子项目的 skill 和 README |
| `cta-report/cli.py`      | 同步该子项目的 skill 和 README |

## 同步目标

| 子项目             | Skill 文件                                | README                      |
| ------------------ | ----------------------------------------- | --------------------------- |
| `a_stock_fetcher/` | `.claude/skills/a-stock-fetcher/SKILL.md` | `a_stock_fetcher/README.md` |
| `cta-report/`      | `.claude/skills/cta-report.md`            | `cta-report/README.md`      |

## 执行流程

1. **识别变更文件**：确认用户修改了哪个子项目的 cli.py
2. **提取变更内容**：读取修改后的文件，提取新的命令列表
3. **更新 Skill**：将变更同步到对应的 skill 文件
4. **更新子项目 README**：将变更同步到对应的 README.md
5. **更新主 README**：同步更新根目录 README.md 的项目列表部分

## 同步规则

### a_stock_fetcher（cli.py 变更时）

从 cli.py 中提取：

- 命令列表（名称、参数、说明）
- 示例用法
- 新增/删除的命令

更新到：

- `.claude/skills/a-stock-fetcher/SKILL.md` — CLI 命令部分
- `a_stock_fetcher/README.md` — 命令列表和示例部分
- 主 `README.md` — a_stock_fetcher 的命令表格

### cta-report（cli.py 变更时）

从 cli.py 中提取：

- 命令列表（run / scan / backtest / test 等）
- 参数和选项
- 输出目录说明

更新到：

- `.claude/skills/cta-report.md` — 全部内容
- `cta-report/README.md` — 命令列表、评分体系、回测规则
- 主 `README.md` — cta_report 部分
