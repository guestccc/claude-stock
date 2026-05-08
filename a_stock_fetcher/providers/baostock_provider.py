"""
BaoStock 日线数据源 Provider
从 daily.py 提取的 BaoStock 相关逻辑，只负责数据获取，返回标准化格式
"""
import threading
import pandas as pd
import baostock as bs
from typing import List
from .base import DailyDataProvider


# BaoStock 全局登录状态
_bs_logged_in = False
# BaoStock 并发锁（底层连接非线程安全）
_bs_lock = threading.Lock()


def _ensure_bs_login():
    """确保 BaoStock 已登录"""
    global _bs_logged_in
    if not _bs_logged_in:
        bs.login()
        _bs_logged_in = True


def _bs_query(query_func, *args, _retry=1, **kwargs):
    """
    BaoStock 查询的线程安全封装
    查询失败时自动重连重试
    """
    global _bs_logged_in
    for attempt in range(_retry + 1):
        with _bs_lock:
            _ensure_bs_login()
            result = query_func(*args, **kwargs)
        # 检查是否需要重连
        if hasattr(result, 'error_code') and result.error_code != '0':
            err_msg = getattr(result, 'error_msg', '')
            if '接收数据异常' in err_msg or 'Broken pipe' in err_msg or '网络' in err_msg:
                with _bs_lock:
                    bs.logout()
                    _bs_logged_in = False
                    bs.login()
                    _bs_logged_in = True
                continue
        break
    return result


def _get_bs_symbol(code: str) -> str:
    """获取 BaoStock 格式的股票代码"""
    if code.startswith('6'):
        return f'sh.{code}'
    elif code.startswith(('0', '3')):
        return f'sz.{code}'
    else:
        return f'sz.{code}'


class BaoStockProvider(DailyDataProvider):
    """BaoStock 日线数据源"""

    def fetch_daily(self, code: str, start_date: str, end_date: str) -> List[dict]:
        """
        获取单只股票日线数据
        :param code: 股票代码（如 "600519"）
        :param start_date: "YYYY-MM-DD"
        :param end_date: "YYYY-MM-DD"
        :return: 标准化记录列表 [{date, open, close, high, low, volume, amount}]
        """
        symbol = _get_bs_symbol(code)

        rs = _bs_query(
            bs.query_history_k_data_plus,
            symbol,
            'date,open,high,low,close,volume,amount',
            start_date=start_date,
            end_date=end_date,
            frequency='d',
            adjustflag='2'  # 前复权
        )

        if rs.error_code != '0':
            return []

        data_list = []
        while rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return []

        df = pd.DataFrame(data_list, columns=rs.fields)

        records = []
        for _, row in df.iterrows():
            records.append({
                'date': row['date'],
                'open': float(row['open']) if row.get('open') and row['open'] != '' else None,
                'close': float(row['close']) if row.get('close') and row['close'] != '' else None,
                'high': float(row['high']) if row.get('high') and row['high'] != '' else None,
                'low': float(row['low']) if row.get('low') and row['low'] != '' else None,
                'volume': float(row['volume']) if row.get('volume') and row['volume'] != '' else None,
                'amount': float(row['amount']) if row.get('amount') and row['amount'] != '' else None,
            })
        return records

    def name(self) -> str:
        return "baostock"
