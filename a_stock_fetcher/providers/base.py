"""
日线数据源抽象基类
所有数据源（BaoStock、妙想等）需实现此接口，返回标准化格式数据
标准化格式统一：volume 单位为股，amount 单位为元
"""
from abc import ABC, abstractmethod
from typing import List, Dict


class DailyDataProvider(ABC):
    """日线数据源抽象基类"""

    @abstractmethod
    def fetch_daily(self, code: str, start_date: str, end_date: str) -> List[dict]:
        """
        获取单只股票日线数据
        :param code: 股票代码（如 "600519"）
        :param start_date: 开始日期 "YYYY-MM-DD"
        :param end_date: 结束日期 "YYYY-MM-DD"
        :return: 标准化记录列表，每条 dict 含:
            date (str "YYYY-MM-DD"), open, close, high, low, volume, amount
            volume 单位: 股, amount 单位: 元
            字段值可能为 None（数据源未返回时）
        """

    def fetch_daily_batch(self, codes: List[str], start_date: str, end_date: str) -> Dict[str, List[dict]]:
        """
        批量获取多只股票日线数据
        默认实现：逐只调用 fetch_daily
        子类可覆写以优化 API 调用次数（如妙想支持一次查多只）
        :param codes: 股票代码列表
        :param start_date: 开始日期 "YYYY-MM-DD"
        :param end_date: 结束日期 "YYYY-MM-DD"
        :return: {code: [records]}
        """
        result = {}
        for code in codes:
            try:
                records = self.fetch_daily(code, start_date, end_date)
                if records:
                    result[code] = records
            except Exception:
                continue
        return result

    def supports_batch(self) -> bool:
        """是否支持真正的批量获取（子类覆写 fetch_daily_batch 时应返回 True）"""
        return False

    @abstractmethod
    def name(self) -> str:
        """数据源名称（如 "baostock", "mxdata"）"""

    def source_desc(self) -> str:
        """数据源描述（如 "新浪财经前复权"），子类可覆写"""
        return self.name()
