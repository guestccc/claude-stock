---
name: a-stock-fetcher
description: A股数据获取器 - 更新日线/分时/财务/板块数据
---

# A股数据获取器 (a_stock_fetcher)

## 项目概述

A股数据获取层，负责从 BaoStock 获取日线数据并写入数据库。

**数据来源**: BaoStock
**依赖**: `a_stock_db` (数据库层)

## 项目结构

```
a_stock_fetcher/
├── __init__.py       # 包入口
├── cli.py            # CLI 入口
├── scheduler.py      # 定时任务调度
└── fetchers/         # 数据获取模块
    ├── basic.py      # 股票基本信息
    ├── daily.py      # 日线数据
    ├── minute.py     # 分时数据
    ├── financial.py  # 财务数据
    └── concept.py    # 板块数据
```

## CLI 命令

```bash
cd /Users/jschen/Desktop/person/claude-study
python3 -m a_stock_fetcher.cli [命令] [参数]
```

### 命令列表

| 命令 | 说明 |
|------|------|
| `init` | 初始化数据库（创建表 + 股票基本信息 + 板块） |
| `daily [N]` | 全量获取日线数据，可指定 N 限制数量 |
| `daily-update [N]` | 增量更新日线数据 |
| `daily-update --codes 600519,000001` | 增量更新指定股票 |
| `daily-full <CODE>` | 获取指定股票所有历史日线数据 |
| `minute [N]` | 更新 1 分钟分时数据，可指定 N 限制数量 |
| `financial [N]` | 更新财务数据，默认 100 条 |
| `boards` | 更新概念/行业板块 |
| `cleanup` | 清理过期分时数据 |
| `scheduler` | 启动定时任务调度器 |
| `status` | 查看调度器状态 |

### 示例

```bash
cd /Users/jschen/Desktop/person/claude-study
python3 -m a_stock_fetcher.cli init                              # 初始化
python3 -m a_stock_fetcher.cli daily-update                     # 增量更新日线（全部）
python3 -m a_stock_fetcher.cli daily-update 100                  # 增量更新前100只
python3 -m a_stock_fetcher.cli daily-update --codes 600519,000001 # 增量更新指定股票
python3 -m a_stock_fetcher.cli daily-full 600519                  # 获取贵州茅台所有历史数据
python3 -m a_stock_fetcher.cli scheduler                          # 启动定时任务
python3 -m a_stock_fetcher.cli status                             # 查看调度器状态
```

## Python 模块调用

```python
from a_stock_fetcher import (
    fetch_stock_basic,
    fetch_all_stocks_daily,
    fetch_all_stocks_daily_incremental,
    fetch_stock_daily_full_history,
    fetch_all_stocks_minute,
    cleanup_old_minute_data,
    fetch_stock_financial,
    fetch_all_boards,
    run_scheduler,
)

# 初始化
fetch_stock_basic()

# 增量更新
fetch_all_stocks_daily_incremental()

# 获取单只股票所有历史数据
fetch_stock_daily_full_history('600519')

# 定时任务
run_scheduler()
```

## 定时任务

启动 `scheduler` 命令后自动执行：

| 任务 | 时间 |
|------|------|
| 日线增量更新 | 每个交易日 16:00 |
| 分时数据更新 | 交易时段每 5 分钟 |
| 过期数据清理 | 每个交易日 17:00 |

## 全局配置

在 `a_stock_db/config.py` 中配置：

```python
# 可交易的市场配置
ENABLED_EXCHANGES = {
    'SH': True,   # 沪市主板
    'SZ': True,   # 深市主板
    'BJ': False,  # 北交所
    'CY': False,  # 创业板
    'KC': False,  # 科创板
}
```

## 依赖关系

- 依赖: `a_stock_db` (数据库层)
