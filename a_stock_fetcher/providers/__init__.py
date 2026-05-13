"""
数据源 Provider 工厂
根据配置创建对应的数据源实例
"""
from a_stock_db.config import DAILY_DATA_SOURCE
from .base import DailyDataProvider


def get_provider(source: str = None) -> DailyDataProvider:
    """
    根据配置创建数据源 provider
    :param source: 数据源名称，None 则从 config 读取
    :return: DailyDataProvider 实例
    """
    source = source or DAILY_DATA_SOURCE

    if source == "baostock":
        from .baostock_provider import BaoStockProvider
        return BaoStockProvider()
    elif source == "mxdata":
        from .mxdata_provider import MxDataProvider
        return MxDataProvider()
    elif source == "akshare":
        from .akshare_provider import AkShareProvider
        return AkShareProvider()
    elif source == "akshare_eastmoney":
        from .akshare_eastmoney_provider import AkShareEastMoneyProvider
        return AkShareEastMoneyProvider()
    else:
        raise ValueError(f"未知数据源: {source}，支持: baostock, mxdata, akshare, akshare_eastmoney")


__all__ = ['DailyDataProvider', 'get_provider']
