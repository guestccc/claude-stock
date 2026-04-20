# A股数据获取器

## 项目路径
`/Users/jschen/Desktop/person/claude-study/a_stock_fetcher`

## 架构

```
BaoStock API → a_stock_fetcher → a_stock_db (数据库)
```

## 命令（统一入口 cli.py）

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
| `daily-full-all` | 获取所有股票所有历史日线数据 |
| `minute [N]` | 更新 1 分钟分时数据，可指定 N 限制数量 |
| `financial [N]` | 更新财务数据，默认 100 条 |
| `boards` | 更新概念/行业板块 |
| `cleanup` | 清理过期分时数据 |
| `clean-daily [N]` | 清洗日线数据：补全涨跌幅/涨跌额/振幅 |
| `rules/rules2/rules3` | 查看配置规则 |
| `scheduler` | 启动定时任务调度器 |
| `status` | 查看调度器状态 |

### 示例

```bash
# 初始化
python3 -m a_stock_fetcher.cli init

# 增量更新日线（全部）
python3 -m a_stock_fetcher.cli daily-update

# 增量更新前100只
python3 -m a_stock_fetcher.cli daily-update 100

# 增量更新指定股票
python3 -m a_stock_fetcher.cli daily-update --codes 600519,000001

# 获取贵州茅台所有历史数据
python3 -m a_stock_fetcher.cli daily-full 600519

# 获取所有股票所有历史数据
python3 -m a_stock_fetcher.cli daily-full-all

# 启动定时任务
python3 -m a_stock_fetcher.cli scheduler

# 查看调度器状态
python3 -m a_stock_fetcher.cli status

# 清洗日线数据（补全涨跌幅/涨跌额/振幅）
python3 -m a_stock_fetcher.cli clean-daily

# 清洗日线数据（限制处理前 100 只）
python3 -m a_stock_fetcher.cli clean-daily 100
```

## 数据源

- **BaoStock** - 免费、稳定的 A股数据源

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
