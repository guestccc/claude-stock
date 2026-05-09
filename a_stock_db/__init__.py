"""
A股数据库层
提供 ORM 模型、数据库管理、查询工具
"""
from .database import (
    db,
    to_json,
    Base,
    StockBasic,
    StockDaily,
    StockMinute,
    StockFinancial,
    StockConcept,
    StockRealtime,
    StockIndexComponents,
    FundBasic,
    FundWatchlist,
    FundEstimation,
    FundNavHistory,
    DatabaseManager,
)
from .config import (
    DB_PATH,
    MINUTE_KEEP_DAYS,
    REQUEST_DELAY,
    MINUTE_STOCK_LIMIT,
    TRADING_HOURS,
    ADJUST,
    DAILY_HISTORY_DAYS,
)

__all__ = [
    # 数据库管理
    'db',
    'Base',
    'DatabaseManager',
    'to_json',
    # 模型
    'StockBasic',
    'StockDaily',
    'StockMinute',
    'StockFinancial',
    'StockConcept',
    'StockRealtime',
    'StockIndexComponents',
    # 基金模型
    'FundBasic',
    'FundWatchlist',
    'FundEstimation',
    'FundNavHistory',
    # 配置
    'DB_PATH',
    'MINUTE_KEEP_DAYS',
    'REQUEST_DELAY',
    'MINUTE_STOCK_LIMIT',
    'TRADING_HOURS',
    'ADJUST',
    'DAILY_HISTORY_DAYS',
]
