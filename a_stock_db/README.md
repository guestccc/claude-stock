# A股数据库层

## 项目路径
`/Users/jschen/Desktop/person/claude-study/a_stock_db`

## 架构

```
a_stock_fetcher (数据获取) → a_stock_db (数据存储) → cta_report (报告生成)
```

## 技术栈

- **数据库**: SQLite (WAL 模式)
- **ORM**: SQLAlchemy

## 数据库表

| 表名 | 说明 |
|------|------|
| `stock_basic` | 股票基本信息 |
| `stock_daily` | 日线行情（前复权） |
| `stock_minute` | 1分钟分时（5日保留） |
| `stock_financial` | 财务数据 |
| `stock_concept` | 概念/行业板块 |
| `stock_realtime` | 实时行情快照 |
| `cta_donchian_scan` | 唐奇安扫描结果 |

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

## 全局配置

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

- 被依赖: `a_stock_fetcher` (数据获取层)
- 被依赖: `cta_report` (报告生成层)
