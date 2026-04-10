---
name: a-stock-db
description: A股数据库层 - ORM模型、配置、查询工具
---

# A股数据库层 (a_stock_db)

## 项目概述

A股数据库底层模块，提供 ORM 模型、数据库管理、查询工具。

**技术栈**: SQLite + SQLAlchemy ORM

## 项目结构

```
a_stock_db/
├── __init__.py       # 包入口
├── config.py         # 配置文件
├── database.py       # ORM 模型 + 数据库管理
└── queries/          # 查询工具
    └── __init__.py
```

## 数据库表

| 表名 | 说明 |
|------|------|
| `stock_basic` | 股票基本信息 |
| `stock_daily` | 日线行情（前复权） |
| `stock_minute` | 1分钟分时（5日保留） |
| `stock_financial` | 财务数据 |
| `stock_concept` | 概念/行业板块 |
| `stock_realtime` | 实时行情快照 |

## 使用方式

```python
# 导入数据库层
from a_stock_db import db, StockBasic, StockDaily, StockQuery

# 初始化数据库
db.create_all()

# 查询股票
query = StockQuery()
stocks = query.search_stocks("茅台")
```

## 配置项 (config.py)

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `DB_PATH` | `a_stock.db` | 数据库文件路径 |
| `MINUTE_KEEP_DAYS` | `5` | 分时数据保留天数 |
| `REQUEST_DELAY` | `0.3` | API请求间隔(秒) |
| `ADJUST` | `qfq` | 复权类型 |

## 依赖关系

- 被依赖: `a_stock_fetcher` (数据获取层)
