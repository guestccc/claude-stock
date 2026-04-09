"""
基础因子
包括规模因子、估值因子、质量因子
"""
import pandas as pd
import numpy as np
from typing import Optional
from .base import BaseFactor


class LnMarketCapFactor(BaseFactor):
    """对数市值因子"""

    def __init__(self):
        super().__init__(
            name="ln_market_cap",
            display_name="对数市值",
            category="size",
            direction=-1  # 小市值溢价
        )

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算对数市值

        Args:
            data: 需要包含 close（收盘价）和 股本数据，或直接有 market_cap

        Returns:
            对数市值序列
        """
        if 'market_cap' in data.columns:
            # 直接使用市值
            result = np.log(data['market_cap'] + 1)
        elif 'total_share' in data.columns and 'close' in data.columns:
            # 计算市值
            market_cap = data['total_share'] * data['close'] * 1e8  # 亿股 -> 股
            result = np.log(market_cap + 1)
        else:
            raise ValueError("数据中缺少市值信息")

        result.name = self.name
        return result


class CirculatingMarketCapFactor(BaseFactor):
    """流通市值因子"""

    def __init__(self):
        super().__init__(
            name="circulating_market_cap",
            display_name="流通市值",
            category="size",
            direction=-1
        )

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算流通市值"""
        if 'float_share' in data.columns and 'close' in data.columns:
            market_cap = data['float_share'] * data['close'] * 1e8
            result = np.log(market_cap + 1)
        else:
            # 使用总市值作为代理
            if 'market_cap' in data.columns:
                result = np.log(data['market_cap'] + 1) * 0.7  # 流通比例约70%
            else:
                raise ValueError("数据中缺少流通市值信息")

        result.name = self.name
        return result


class PEratioFactor(BaseFactor):
    """市盈率因子"""

    def __init__(self):
        super().__init__(
            name="pe_ratio",
            display_name="市盈率",
            category="value",
            direction=-1  # 低估值
        )

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算 PE """
        if 'pe' in data.columns:
            result = data['pe'].copy()
        else:
            # 从利润和市值计算
            if 'net_profit' in data.columns and 'market_cap' in data.columns:
                # PE = 市值 / 净利润
                result = data['market_cap'] / (data['net_profit'] + 1)
            else:
                raise ValueError("数据中缺少PE信息")

        # 处理异常PE值
        result = result.clip(lower=0, upper=200)  # 限制合理范围

        result.name = self.name
        return result


class PBratioFactor(BaseFactor):
    """市净率因子"""

    def __init__(self):
        super().__init__(
            name="pb_ratio",
            display_name="市净率",
            category="value",
            direction=-1
        )

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算 PB """
        if 'pb' in data.columns:
            result = data['pb'].copy()
        else:
            if 'book_value' in data.columns and 'market_cap' in data.columns:
                result = data['market_cap'] / (data['book_value'] + 1)
            else:
                raise ValueError("数据中缺少PB信息")

        result = result.clip(lower=0, upper=20)
        result.name = self.name
        return result


class PSratioFactor(BaseFactor):
    """市销率因子"""

    def __init__(self):
        super().__init__(
            name="ps_ratio",
            display_name="市销率",
            category="value",
            direction=-1
        )

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算 PS """
        if 'ps' in data.columns:
            result = data['ps'].copy()
        else:
            if 'revenue' in data.columns and 'market_cap' in data.columns:
                result = data['market_cap'] / (data['revenue'] + 1)
            else:
                raise ValueError("数据中缺少PS信息")

        result = result.clip(lower=0, upper=50)
        result.name = self.name
        return result


class ROEFactor(BaseFactor):
    """净资产收益率因子"""

    def __init__(self):
        super().__init__(
            name="roe",
            display_name="净资产收益率",
            category="quality",
            direction=1  # 高ROE
        )

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算 ROE """
        if 'roe' in data.columns:
            result = data['roe'].copy()
        else:
            raise ValueError("数据中缺少ROE信息")

        # 限制范围
        result = result.clip(lower=-1, upper=1)
        result.name = self.name
        return result


class ROAFactor(BaseFactor):
    """资产收益率因子"""

    def __init__(self):
        super().__init__(
            name="roa",
            display_name="资产收益率",
            category="quality",
            direction=1
        )

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算 ROA """
        if 'roa' in data.columns:
            result = data['roa'].copy()
        else:
            raise ValueError("数据中缺少ROA信息")

        result = result.clip(lower=-0.5, upper=0.5)
        result.name = self.name
        return result


class GrossMarginFactor(BaseFactor):
    """毛利率因子"""

    def __init__(self):
        super().__init__(
            name="gross_margin",
            display_name="毛利率",
            category="quality",
            direction=1
        )

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算毛利率"""
        if 'gross_margin' in data.columns:
            result = data['gross_margin'].copy()
        else:
            raise ValueError("数据中缺少毛利率信息")

        result = result.clip(lower=0, upper=1)
        result.name = self.name
        return result


class FundamentalFactors:
    """基础因子集合"""

    @staticmethod
    def get_all_factors() -> list:
        """获取所有基础因子"""
        return [
            LnMarketCapFactor(),
            CirculatingMarketCapFactor(),
            PEratioFactor(),
            PBratioFactor(),
            PSratioFactor(),
            ROEFactor(),
            ROAFactor(),
            GrossMarginFactor(),
        ]

    @staticmethod
    def get_factor_by_name(name: str) -> Optional[BaseFactor]:
        """根据名称获取因子"""
        factors = {
            'ln_market_cap': LnMarketCapFactor,
            'circulating_market_cap': CirculatingMarketCapFactor,
            'pe_ratio': PEratioFactor,
            'pb_ratio': PBratioFactor,
            'ps_ratio': PSratioFactor,
            'roe': ROEFactor,
            'roa': ROAFactor,
            'gross_margin': GrossMarginFactor,
        }

        factor_class = factors.get(name)
        return factor_class() if factor_class else None
