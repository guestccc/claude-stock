"""
ETF 日线数据源 Provider — 东方财富（前复权）
通过 akshare.fund_etf_hist_em(adjust='qfq') 获取 ETF 日线数据

优点:
  - 前复权价格，自动处理份额拆分/合并，涨跌幅准确
  - 字段齐全：直接返回振幅、涨跌幅、涨跌额、换手率，无需手动计算
  - 东方财富官方数据，质量较高

缺点:
  - 东方财富接口限流较严，批量拉取需加大请求间隔（建议 ≥1s）
  - 前复权价格与真实交易价格不同（历史价格被调整），展示时需注意
  - 部分冷门 ETF 可能无数据
"""
import time
import akshare as ak
import pandas as pd
from typing import List
from .base import DailyDataProvider


class ETFEastMoneyProvider(DailyDataProvider):
    """ETF 日线数据源 — 东方财富前复权"""

    MAX_RETRIES = 3

    def fetch_daily(self, code: str, start_date: str, end_date: str) -> List[dict]:
        """
        获取单只 ETF 日线数据（前复权）
        :param code: ETF 代码（如 "510300"）
        :param start_date: "YYYY-MM-DD"
        :param end_date: "YYYY-MM-DD"
        :return: 标准化记录列表
        """
        ak_start = start_date.replace('-', '')
        ak_end = end_date.replace('-', '')

        _FATAL_ERRORS = ('No value to decode', '相互', '不存在', '没有数据')

        df = None
        for attempt in range(self.MAX_RETRIES):
            try:
                df = ak.fund_etf_hist_em(
                    symbol=code,
                    start_date=ak_start,
                    end_date=ak_end,
                    period="daily",
                    adjust="qfq",
                )
                break
            except Exception as e:
                err_msg = str(e)
                is_fatal = any(kw in err_msg for kw in _FATAL_ERRORS)
                if is_fatal:
                    print(f"  东财ETF跳过 ({code}): {err_msg}")
                    return []
                if attempt < self.MAX_RETRIES - 1:
                    wait = 2 ** (attempt + 1)
                    print(f"  东财ETF重试 ({code}) 第{attempt+1}次，等待{wait}s: {e}")
                    time.sleep(wait)
                else:
                    print(f"  东财ETF错误 ({code}): {e}")
                    return []

        if df is None or df.empty:
            return []

        # 东方财富字段映射
        _COL_MAP = {
            '日期': 'date', '开盘': 'open', '收盘': 'close',
            '最高': 'high', '最低': 'low', '成交量': 'volume',
            '成交额': 'amount', '振幅': 'amplitude', '涨跌幅': 'pct_change',
            '涨跌额': 'change', '换手率': 'turnover',
        }

        records = []
        for _, row in df.iterrows():
            record = {}
            for cn_name, en_name in _COL_MAP.items():
                if cn_name in row and pd.notna(row[cn_name]):
                    record[en_name] = float(row[cn_name])
                else:
                    record[en_name] = None
            if '日期' in row:
                record['date'] = str(row['日期'])
            records.append(record)

        return records

    def name(self) -> str:
        return "etf_eastmoney"

    def source_desc(self) -> str:
        return "东方财富ETF日线（前复权）"
