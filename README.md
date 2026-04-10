# A股量化投资工具集

本目录包含三个相互协作的项目，用于A股市场的数据获取、存储和量化分析。

---

## 项目列表

### 1. a_stock_db - A股数据库层

**作用**: 数据持久化层，统一管理所有股票数据的存储

**核心功能**:
- ORM模型定义（StockBasic、StockDaily、StockMinute、StockFinancial等）
- SQLite数据库配置（WAL模式，提升并发性能）
- 全局参数配置（市场开关、请求间隔、数据保留天数等）

**数据表**:
| 表名 | 说明 |
|------|------|
| stock_basic | 股票基本信息 |
| stock_daily | 日线行情数据 |
| stock_minute | 1分钟分时数据 |
| stock_financial | 财务数据 |
| concept | 概念板块 |
| industry | 行业板块 |

---

### 2. a_stock_fetcher - A股数据获取器

**作用**: 从BaoStock API获取数据并写入数据库

**核心功能**:
- 日线数据获取（支持全量/增量/历史）
- 分时数据获取（1分钟K线）
- 财务数据获取
- 概念/行业板块更新
- 定时任务调度

**数据源**: BaoStock（免费、稳定）

**使用方式**:
```bash
cd /Users/jschen/Desktop/person/claude-study
python3 -m a_stock_fetcher.cli [命令]
```

**主要命令**:
| 命令 | 说明 |
|------|------|
| `init` | 初始化数据库 |
| `daily-update` | 增量更新日线数据 |
| `daily-full <CODE>` | 获取单只股票所有历史数据 |
| `minute` | 更新分时数据 |
| `scheduler` | 启动定时任务 |

---

### 3. cta_report - CTA策略报告生成器

**作用**: 读取回测结果，生成格式化分析报告

**核心功能**:
- 读取cta_report目录下的回测数据
- 生成Markdown格式的分析报告
- 支持模板渲染
- 输出到output目录

**使用方式**:
```bash
cd /Users/jschen/Desktop/person/claude-study/cta_report
python3 cli.py [命令]
```

---

## 依赖关系

```
cta_report (报告生成)
    ↓ 读取
a_stock_db (数据存储)
    ↑
a_stock_fetcher (数据获取)
    ↓ 请求
BaoStock API
```

---

## 快速开始

1. **初始化数据库**
```bash
python3 -m a_stock_fetcher.cli init
```

2. **获取历史数据（可选）**
```bash
python3 -m a_stock_fetcher.cli daily-full 600519  # 贵州茅台
```

3. **启动定时任务**
```bash
python3 -m a_stock_fetcher.cli scheduler
```

4. **查看状态**
```bash
python3 -m a_stock_fetcher.cli status
```
