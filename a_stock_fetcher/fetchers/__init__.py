"""
数据获取模块初始化
依赖: a_stock_db (数据库层)
"""
from .basic import fetch_stock_basic, get_stock_type, is_enabled
from .daily import fetch_stock_daily, fetch_all_stocks_daily, fetch_stock_daily_incremental, fetch_all_stocks_daily_incremental, fetch_stock_daily_full_history
from .minute import fetch_stock_minute, fetch_all_stocks_minute, cleanup_old_minute_data
from .financial import fetch_stock_financial
from .concept import fetch_concept, fetch_industry, fetch_all_boards
from .clean import clean_daily_data
from .fund import fetch_fund_estimation, fetch_watchlist_estimations, add_watchlist, remove_watchlist, get_watchlist_codes

__all__ = [
    'fetch_stock_basic',
    'fetch_stock_daily',
    'fetch_all_stocks_daily',
    'fetch_stock_daily_incremental',
    'fetch_all_stocks_daily_incremental',
    'fetch_stock_daily_full_history',
    'fetch_stock_minute',
    'fetch_all_stocks_minute',
    'cleanup_old_minute_data',
    'fetch_stock_financial',
    'fetch_concept',
    'fetch_industry',
    'fetch_all_boards',
    # 数据清洗
    'clean_daily_data',
    # 股票分类
    'get_stock_type',
    'is_enabled',
    # 基金
    'fetch_fund_estimation',
    'fetch_watchlist_estimations',
    'add_watchlist',
    'remove_watchlist',
    'get_watchlist_codes',
]
