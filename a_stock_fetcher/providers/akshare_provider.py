"""
akshare 日线数据源 Provider
通过 akshare.stock_zh_a_hist 获取A股日线数据
无 API 调用限制，数据来源于东方财富
"""
import akshare as ak
import pandas as pd
from typing import List
from .base import DailyDataProvider


def _get_akshare_symbol(code: str) -> str:
    """
    获取 akshare 格式的股票代码
    akshare.stock_zh_a_hist 支持多种格式：600519, sh600519, SH600519
    """
    return code


class AkShareProvider(DailyDataProvider):
    """akshare 日线数据源 — 无限制、数据来源于东方财富"""

    def fetch_daily(self, code: str, start_date: str, end_date: str) -> List[dict]:
        """
        获取单只股票日线数据
        :param code: 股票代码（如 "600519"）
        :param start_date: "YYYY-MM-DD"
        :param end_date: "YYYY-MM-DD"
        :return: 标准化记录列表 [{date, open, close, high, low, volume, amount, amplitude, pct_change, change, turnover}]
        """
        # akshare 日期格式为 YYYYMMDD
        ak_start = start_date.replace('-', '')
        ak_end = end_date.replace('-', '')

        try:
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=ak_start,
                end_date=ak_end,
                adjust="qfq"
            )
        except Exception as e:
            print(f"  akshare 错误 ({code}): {e}")
            return []

        if df is None or df.empty:
            return []

        records = []
        for _, row in df.iterrows():
            # akshare 成交量单位为"手"，需转为"股"（×100）
            volume_shou = row.get('成交量')
            volume = float(volume_shou) * 100 if pd.notna(volume_shou) else None

            records.append({
                'date': str(row['日期']),
                'open': float(row['开盘']) if pd.notna(row.get('开盘')) else None,
                'close': float(row['收盘']) if pd.notna(row.get('收盘')) else None,
                'high': float(row['最高']) if pd.notna(row.get('最高')) else None,
                'low': float(row['最低']) if pd.notna(row.get('最低')) else None,
                'volume': volume,
                'amount': float(row['成交额']) if pd.notna(row.get('成交额')) else None,
                'amplitude': float(row['振幅']) if pd.notna(row.get('振幅')) else None,
                'pct_change': float(row['涨跌幅']) if pd.notna(row.get('涨跌幅')) else None,
                'change': float(row['涨跌额']) if pd.notna(row.get('涨跌额')) else None,
                'turnover': float(row['换手率']) if pd.notna(row.get('换手率')) else None,
            })

        return records

    def name(self) -> str:
        return "akshare"
