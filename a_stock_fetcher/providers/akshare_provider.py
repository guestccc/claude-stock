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
                if attempt < self.MAX_RETRIES - 1:
                    wait = 2 ** (attempt + 1)
                    print(f"  新浪重试 ({code}) 第{attempt+1}次，等待{wait}s: {e}")
                    time.sleep(wait)
                else:
                    print(f"  新浪错误 ({code}): {e}")
                    return []

        if df is None or df.empty:
            return []

        records = []
        prev_close = None
        for _, row in df.iterrows():
            close = float(row['close']) if pd.notna(row['close']) else None
            open_ = float(row['open']) if pd.notna(row['open']) else None
            high = float(row['high']) if pd.notna(row['high']) else None
            low = float(row['low']) if pd.notna(row['low']) else None

            # 涨跌幅/涨跌额需自行计算（新浪不提供）
            change = None
            pct_change = None
            if prev_close and prev_close > 0 and close is not None:
                change = round(close - prev_close, 4)
                pct_change = round(change / prev_close * 100, 4)

            # 振幅 = (最高-最低) / 昨收 * 100
            amplitude = None
            if prev_close and prev_close > 0 and high is not None and low is not None:
                amplitude = round((high - low) / prev_close * 100, 4)

            records.append({
                'date': str(row['date']),
                'open': open_,
                'close': close,
                'high': high,
                'low': low,
                'volume': float(row['volume']) if pd.notna(row.get('volume')) else None,
                'amount': float(row['amount']) if pd.notna(row.get('amount')) else None,
                'amplitude': amplitude,
                'pct_change': pct_change,
                'change': change,
                'turnover': float(row['turnover']) if pd.notna(row.get('turnover')) else None,
            })
            if close is not None:
                prev_close = close

        return records

    def name(self) -> str:
        return "akshare"
