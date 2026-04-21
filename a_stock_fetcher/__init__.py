"""
A股数据获取器
依赖: a_stock_db (数据库层)
"""
from .fetchers import (
    fetch_stock_basic,
    fetch_stock_daily,
    fetch_all_stocks_daily,
    fetch_stock_daily_incremental,
    fetch_all_stocks_daily_incremental,
    fetch_stock_daily_full_history,
    fetch_stock_minute,
    fetch_all_stocks_minute,
    cleanup_old_minute_data,
    fetch_stock_financial,
    fetch_concept,
    fetch_industry,
    fetch_all_boards,
    clean_daily_data,
    is_enabled,
    get_stock_type,
    fetch_fund_estimation,
    fetch_watchlist_estimations,
    add_watchlist,
    remove_watchlist,
    get_watchlist_codes,
)
from .scheduler import start_scheduler, run_scheduler, get_scheduler

__all__ = [
    # 基础数据
    'fetch_stock_basic',
    # 日线数据
    'fetch_stock_daily',
    'fetch_all_stocks_daily',
    'fetch_stock_daily_incremental',
    'fetch_all_stocks_daily_incremental',
    'fetch_stock_daily_full_history',
    # 分时数据
    'fetch_stock_minute',
    'fetch_all_stocks_minute',
    'cleanup_old_minute_data',
    # 财务数据
    'fetch_stock_financial',
    # 板块数据
    'fetch_concept',
    'fetch_industry',
    'fetch_all_boards',
    # 数据清洗
    'clean_daily_data',
    # 调度器
    'start_scheduler',
    'run_scheduler',
    'get_scheduler',
    # 过滤
    'is_enabled',
    'get_stock_type',
    # 基金
    'fetch_fund_estimation',
    'fetch_watchlist_estimations',
    'add_watchlist',
    'remove_watchlist',
    'get_watchlist_codes',
]
