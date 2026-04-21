"""FastAPI 应用入口"""
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.config import PROJECT_ROOT, CORS_ORIGINS, API_PREFIX
from server.routers import market, watchlist, screener, backtest, portfolio, system, fund


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时注入 sys.path，确保能导入现有模块"""
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    # 初始化数据库表（创建 watchlist/holdings/transactions）
    from server.db.models import init_tables
    init_tables()
    yield


app = FastAPI(
    title="A股量化分析平台",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS：允许 Vite 开发服务器跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(market.router, prefix=API_PREFIX)
app.include_router(watchlist.router, prefix=API_PREFIX)
app.include_router(screener.router, prefix=API_PREFIX)
app.include_router(backtest.router, prefix=API_PREFIX)
app.include_router(portfolio.router, prefix=API_PREFIX)
app.include_router(system.router, prefix=API_PREFIX)
app.include_router(fund.router, prefix=API_PREFIX)

# 生产环境：serve React 构建产物
# app.mount("/", StaticFiles(directory="web/dist", html=True), name="static")
