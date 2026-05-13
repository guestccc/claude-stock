"""
akshare 日线数据源 Provider
通过 akshare.stock_zh_a_daily 获取A股日线数据（新浪财经数据源）
"""
import time
import akshare as ak
import pandas as pd
from typing import List
from .base import DailyDataProvider


def _sina_symbol(code: str) -> str:
    """转为新浪格式：sh600519 / sz000001"""
    if code.startswith(('6',)):
        return f'sh{code}'
    return f'sz{code}'


class AkShareProvider(DailyDataProvider):
    """akshare 日线数据源 — 新浪财经"""

    MAX_RETRIES = 3

    def fetch_daily(self, code: str, start_date: str, end_date: str) -> List[dict]:
        """
        获取单只股票日线数据
        :param code: 股票代码（如 "600519"）
        :param start_date: "YYYY-MM-DD"
        :param end_date: "YYYY-MM-DD"
        :return: 标准化记录列表
        """
        symbol = _sina_symbol(code)
        ak_start = start_date.replace('-', '')
        ak_end = end_date.replace('-', '')

        # 确定性错误（退市/停牌/代码无效），不重试直接返回空
        _FATAL_ERRORS = ('No value to decode', '相互', '不存在')

        df = None
        for attempt in range(self.MAX_RETRIES):
            try:
                df = ak.stock_zh_a_daily(
                    symbol=symbol,
                    start_date=ak_start,
                    end_date=ak_end,
                    adjust="qfq",
                )
                break
            except Exception as e:
                err_msg = str(e)
                is_fatal = any(kw in err_msg for kw in _FATAL_ERRORS)
                if is_fatal:
                    print(f"  新浪跳过 ({code}): {err_msg}")
                    return []
                if attempt < self.MAX_RETRIES - 1:
                    wait = 2 ** (attempt + 1)
                    print(f"  新浪重试 ({code}) 第{attempt+1}次，等待{wait}s: {e}")
                    time.sleep(wait)
                else:
                    print(f"  新浪错误 ({code}): {e}")
                    return []

        if df is None or df.empty:
            return []

        # 新浪源缺少振幅/涨跌幅/涨跌额，用 DataFrame 统一计算
        df = df.sort_values('date').reset_index(drop=True)
        prev_close = df['close'].shift(1)
        df['_change'] = (df['close'] - prev_close).round(4)
        df['_pct_change'] = (df['_change'] / prev_close * 100).round(4)
        df['_amplitude'] = ((df['high'] - df['low']) / prev_close * 100).round(4)

        records = []
        for _, row in df.iterrows():
            records.append({
                'date': str(row['date']),
                'open': float(row['open']) if pd.notna(row['open']) else None,
                'close': float(row['close']) if pd.notna(row['close']) else None,
                'high': float(row['high']) if pd.notna(row['high']) else None,
                'low': float(row['low']) if pd.notna(row['low']) else None,
                'volume': float(row['volume']) if pd.notna(row.get('volume')) else None,
                'amount': float(row['amount']) if pd.notna(row.get('amount')) else None,
                'amplitude': float(row['_amplitude']) if pd.notna(row['_amplitude']) else None,
                'pct_change': float(row['_pct_change']) if pd.notna(row['_pct_change']) else None,
                'change': float(row['_change']) if pd.notna(row['_change']) else None,
                'turnover': float(row['turnover']) if pd.notna(row.get('turnover')) else None,
            })

        return records

    def name(self) -> str:
        return "akshare"

    def source_desc(self) -> str:
        return "新浪财经前复权"
