---
name: sync-project-docs
description: 项目文档自动同步执行器。当用户说"新增命令"、"增加命令"、"同步文档"、"更新 skill"、"同步 skill"、或修改了 cli.py 时，自动执行以下流程同步文档：扫描 cli.py 变更 -> 更新对应 skill -> 更新子项目 README -> 更新主 README
---

# 项目文档同步执行器

## 触发条件（关键词命中）

当用户说以下任意一种话时，加载并执行本 skill：
- "新增命令"、"增加命令"、"添加命令"
- "同步文档"、"更新文档"、"更新 skill"
- "修改了 cli.py"、"cli.py 变了"
- "同步 skill 和 README"

## 执行命令（按以下顺序执行）

### 第一步：识别变更源

读取用户最近修改的 `cli.py` 文件，确认属于哪个子项目：

```python
# 读取文件确认变更
read("a_stock_fetcher/cli.py")
read("cta-report/cli.py")
```

### 第二步：提取 cli.py 中的最新命令列表

从 cli.py 中提取所有命令及其说明，生成结构化的命令表格。

### 第三步：同步更新对应文件（必须执行）

根据变更的 cli.py，更新以下 3 个目标文件：

| 变更源 | 需要更新的文件 |
|--------|--------------|
| `a_stock_fetcher/cli.py` | 1. `.claude/skills/a-stock-fetcher/SKILL.md` — CLI 命令列表 + 示例 |
| | 2. `a_stock_fetcher/README.md` — 命令列表 + 示例 |
| | 3. `README.md` — 主 README 中 a_stock_fetcher 的命令表格 |
| `cta-report/cli.py` | 1. `.claude/skills/cta-report.md` — CLI 命令列表 + 示例 |
| | 2. `cta-report/README.md` — 命令列表 + 示例 |
| | 3. `README.md` — 主 README 中 cta_report 的命令表格 |

### 第四步：验证同步结果

执行以下命令验证文件一致性：

```bash
# 检查 a_stock_fetcher 的命令是否在 skill 和 README 中都有
python3 -c "
import re

# 从 cli.py 提取命令
with open('a_stock_fetcher/cli.py') as f:
    cli = f.read()

cmds = re.findall(r'elif cmd == \"(\w+)\"', cli)
print('cli.py 命令:', cmds)

# 从 skill 提取命令
with open('.claude/skills/a-stock-fetcher/SKILL.md') as f:
    skill = f.read()

for cmd in cmds:
    if cmd in skill:
        print(f'  {cmd}: skill ✓')
    else:
        print(f'  {cmd}: skill ✗ MISSING!')
"
```

## 同步规则（更新时必须遵守）

### 命令列表格式

统一使用 Markdown 表格：

```markdown
| 命令 | 说明 |
|------|------|
| `init` | 初始化数据库 |
| `daily [N]` | 全量获取日线数据 |
```

### 示例代码格式

在 README 和 SKILL 的示例部分，必须包含所有命令的用法示例。

### Python 模块导出格式

如果 cli.py 新增了导入的函数，检查并更新：
- `a_stock_fetcher/__init__.py` 的 `__all__` 列表
- `a_stock_fetcher/fetchers/__init__.py` 的导出列表

## 防遗漏检查清单

同步完成后，确认以下事项：

- [ ] cli.py 中所有命令都在 skill 的表格中
- [ ] cli.py 中所有命令都在 README 的表格中
- [ ] 新增命令有对应的示例用法
- [ ] 主 README 中的命令表格已更新
- [ ] Python 模块的 `__init__.py` 导出新函数（如有新增）
- [ ] 文件编码为 UTF-8（中文正常显示）

## 常见遗漏修复

如果某个命令在 cli.py 中有但 skill/README 中没有：

1. 立即在 skill 表格中添加该行
2. 立即在 README 表格中添加该行
3. 在示例代码中添加该命令的用法
4. 在主 README 中添加该命令

不要只更新一个地方，必须三处同时更新。
