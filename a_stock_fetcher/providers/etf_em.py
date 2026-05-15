"""
ETF 日线数据源 Provider — 新浪财经
通过 akshare.fund_etf_hist_sina 获取 ETF 日线数据
东方财富易限流，新浪更稳定；缺振幅/涨跌幅/换手率，通过前后日计算补全
"""
import akshare as ak
import pandas as pd
from typing import List
from .base import DailyDataProvider


def _get_sina_symbol(code: str) -> str:
    """ETF 代码 → 新浪 symbol（加交易所前缀）"""
    # 沪市: 51/56/58 开头
    if code.startswith(('51', '56', '58')):
        return f'sh{code}'
    # 深市: 15/16/17/18 开头
    return f'sz{code}'


class ETFEmProvider(DailyDataProvider):
    """ETF 日线数据源 — 新浪财经（东方财富限流时的替代）"""

    def fetch_daily(self, code: str, start_date: str, end_date: str) -> List[dict]:
        """
        获取单只 ETF 日线数据
        :param code: ETF 代码（如 "510300"）
        :param start_date: "YYYY-MM-DD"
        :param end_date: "YYYY-MM-DD"
        :return: 标准化记录列表
        """
        sina_symbol = _get_sina_symbol(code)

        try:
            df = ak.fund_etf_hist_sina(symbol=sina_symbol)
        except Exception as e:
            print(f"  ETF 新浪错误 ({code}): {str(e)[:60]}")
            return []

        if df is None or df.empty:
            return []

        # 新浪字段: date, open, high, low, close, volume, amount
        # 缺 amplitude/pct_change/change/turnover，通过前后日计算
        records = []
        prev_close = None

        for _, row in df.iterrows():
            date_str = str(row['date'])
            open_p = float(row['open']) if pd.notna(row['open']) else None
            high_p = float(row['high']) if pd.notna(row['high']) else None
            low_p = float(row['low']) if pd.notna(row['low']) else None
            close_p = float(row['close']) if pd.notna(row['close']) else None
            volume = float(row['volume']) if pd.notna(row['volume']) else None
            amount = float(row['amount']) if pd.notna(row['amount']) else None

            # 计算涨跌幅/涨跌额/振幅（需要 prev_close）
            pct_change = None
            change = None
            amplitude = None
            if prev_close and prev_close > 0 and close_p is not None:
                pct_change = (close_p - prev_close) / prev_close * 100
                change = close_p - prev_close
                if high_p is not None and low_p is not None:
                    amplitude = (high_p - low_p) / prev_close * 100

            if close_p is not None:
                prev_close = close_p

            # 日期范围过滤
            if date_str < start_date or date_str > end_date:
                continue

            records.append({
                'date': date_str,
                'open': open_p,
                'close': close_p,
                'high': high_p,
                'low': low_p,
                'volume': volume,
                'amount': amount,
                'pct_change': pct_change,
                'change': change,
                'amplitude': amplitude,
                'turnover': None,  # 新浪无换手率
            })

        return records

    def name(self) -> str:
        return "etf_sina"

    def source_desc(self) -> str:
        return "新浪财经ETF日线"
