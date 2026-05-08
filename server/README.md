# 服务端 (FastAPI)

基于 FastAPI + SQLAlchemy 构建的 REST API 服务端，为前端 Web 应用提供数据接口，同时管理持仓、回测、自选股等业务数据。

## 目录结构

```
server/
├── main.py           # FastAPI 应用入口，注册路由和 CORS
├── config.py         # 服务端配置（HOST/PORT/CORS/数据库路径）
├── run.py            # 本地启动脚本（uvicorn）
├── requirements.txt  # Python 依赖
├── routers/          # API 路由
│   ├── market.py     # 行情数据（日K/分钟/实时报价/板块）
│   ├── watchlist.py  # 自选股管理
│   ├── portfolio.py  # 持仓管理（买入/卖出/交易记录/清仓/批量导入）
│   ├── backtest.py   # 回测管理（创建/运行/保存/列表）
│   ├── fund.py       # 基金数据
│   ├── screener.py   # 股票筛选器
│   └── system.py     # 系统任务（数据更新/调度器）
├── services/         # 业务逻辑层
│   ├── portfolio_service.py   # 持仓买入/卖出/批量导入
│   ├── market_service.py      # 行情查询
│   ├── backtest_service.py    # 回测执行
│   └── ...
├── models/           # Pydantic Schemas
│   └── portfolio.py  # 持仓/交易/回测等请求/响应模型
└── db/
    └── models.py     # SQLAlchemy ORM 模型（Transaction/Holding 等）
```

## 安装依赖

```bash
cd /Users/jschen/Desktop/person/claude-study
pip3 install -r server/requirements.txt
```

## 启动方式

### 方式一：推荐（uvicorn 自动重载）

**⚠️ 必须在项目根目录执行**，否则 Python 找不到 `server` 模块：

```bash
cd /Users/jschen/Desktop/person/claude-study
python3 -m uvicorn server.main:app --host :: --port 8000 --reload
```

### 方式二：使用 run.py 脚本

```bash
cd /Users/jschen/Desktop/person/claude-study
python3 server/run.py
```

### 方式三：后台常驻

```bash
cd /Users/jschen/Desktop/person/claude-study
nohup python3 -m uvicorn server.main:app --host :: --port 8000 > server.log 2>&1 &
```

## 配置

配置文件位于 `server/config.py`，主要项：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| HOST | `::` | 监听地址，IPv4+IPv6 |
| PORT | `8000` | 监听端口 |
| API_PREFIX | `/api` | 所有路由前缀 |
| CORS_ORIGINS | `localhost:5173` | 允许的跨域来源 |
| DB_PATH | `a_stock_db/a_stock.db` | SQLite 数据库路径 |

## API 文档

启动后自动 Swagger 文档：`http://localhost:8000/docs`

主要路由前缀：`http://localhost:8000/api`

| 模块 | 路由 | 说明 |
|------|------|------|
| 行情 | `GET /api/market/...` | 日K/分时/实时/板块 |
| 自选股 | `GET/POST/DELETE /api/watchlist` | 自选股增删改查 |
| 持仓 | `GET/POST /api/portfolio/...` | 持仓/买入/卖出/交易记录/批量导入 |
| 回测 | `GET/POST /api/backtest/...` | 创建/运行/保存回测 |
| 基金 | `GET /api/fund/...` | 基金数据 |
| 系统 | `GET/POST /api/system/...` | 数据更新/定时任务/状态 |
