"""
akshare 东方财富日线数据源 Provider
通过 akshare.stock_zh_a_hist 获取A股日线数据（东方财富数据源）
字段比新浪更全：直接返回振幅、涨跌幅、涨跌额、换手率，无需手动计算
"""
import time
import akshare as ak
import pandas as pd
from typing import List
from .base import DailyDataProvider


class AkShareEastMoneyProvider(DailyDataProvider):
    """akshare 日线数据源 — 东方财富"""

    MAX_RETRIES = 3

    def fetch_daily(self, code: str, start_date: str, end_date: str) -> List[dict]:
        """
        获取单只股票日线数据
        :param code: 股票代码（如 "600519"）
        :param start_date: "YYYY-MM-DD"
        :param end_date: "YYYY-MM-DD"
        :return: 标准化记录列表
        """
        ak_start = start_date.replace('-', '')
        ak_end = end_date.replace('-', '')

        # 确定性错误（退市/停牌/代码无效），不重试直接返回空
        _FATAL_ERRORS = ('No value to decode', '相互', '不存在', '没有数据')

        df = None
        for attempt in range(self.MAX_RETRIES):
            try:
                df = ak.stock_zh_a_hist(
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
                    print(f"  东方财富跳过 ({code}): {err_msg}")
                    return []
                if attempt < self.MAX_RETRIES - 1:
                    wait = 2 ** (attempt + 1)
                    print(f"  东方财富重试 ({code}) 第{attempt+1}次，等待{wait}s: {e}")
                    time.sleep(wait)
                else:
                    print(f"  东方财富错误 ({code}): {e}")
                    return []

        if df is None or df.empty:
            return []

        # 东方财富字段映射：日期→date, 开盘→open, 收盘→close, 最高→high, 最低→low,
        # 成交量→volume, 成交额→amount, 振幅→amplitude, 涨跌幅→pct_change,
        # 涨跌额→change, 换手率→turnover
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
                    record[en_name] = float(row[cn_name]) if en_name != 'date' else str(row[cn_name])
                else:
                    record[en_name] = None
            # date 保持字符串
            if '日期' in row:
                record['date'] = str(row['日期'])
            records.append(record)

        return records

    def name(self) -> str:
        return "akshare_eastmoney"

    def source_desc(self) -> str:
        return "东方财富前复权"
