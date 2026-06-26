"""
数据源 Provider 工厂
根据配置创建对应的数据源实例（A 股 + ETF 分开管理）
"""
from a_stock_db.config import DAILY_DATA_SOURCE, ETF_DATA_SOURCE
from .base import DailyDataProvider


def get_provider(source: str = None) -> DailyDataProvider:
    """
    根据配置创建 A 股数据源 provider
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


def get_etf_provider(source: str = None) -> DailyDataProvider:
    """
    根据配置创建 ETF 数据源 provider
    :param source: 数据源名称，None 则从 config 读取
    :return: DailyDataProvider 实例
    """
    source = source or ETF_DATA_SOURCE

    if source == "etf_eastmoney":
        from .etf_eastmoney_provider import ETFEastMoneyProvider
        return ETFEastMoneyProvider()
    elif source == "etf_sina":
        from .etf_em import ETFEmProvider
        return ETFEmProvider()
    else:
        raise ValueError(f"未知 ETF 数据源: {source}，支持: etf_eastmoney, etf_sina")


__all__ = ['DailyDataProvider', 'get_provider', 'get_etf_provider']
