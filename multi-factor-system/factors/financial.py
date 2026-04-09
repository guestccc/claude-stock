"""
财务因子
包括成长因子、财务健康因子、现金流因子等
"""
import pandas as pd
import numpy as np
from typing import Optional
from .base import BaseFactor


class RevenueGrowthFactor(BaseFactor):
    """营收增长率因子"""

    def __init__(self, period: int = 4):
        """
        Args:
            period: 计算周期数（季度），默认为4表示年度
        """
        super().__init__(
            name="revenue_growth",
            display_name="营收增长率",
            category="growth",
            direction=1
        )
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算营收增长率"""
        if 'revenue' not in data.columns:
            raise ValueError("数据中缺少营收数据")

        def calc_growth(group):
            # 同比增长率
            growth = group['revenue'].pct_change(self.period)
            return growth

        result = data.groupby('code').apply(calc_growth)

        if isinstance(result, pd.DataFrame):
            result = result.droplevel(0) if result.index.nlevels > 2 else result[0]

        # 限制异常值
        result = result.clip(lower=-0.99, upper=10)

        result.name = self.name
        return result


class ProfitGrowthFactor(BaseFactor):
    """净利润增长率因子"""

    def __init__(self, period: int = 4):
        super().__init__(
            name="profit_growth",
            display_name="净利润增长率",
            category="growth",
            direction=1
        )
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算净利润增长率"""
        if 'net_profit' not in data.columns:
            raise ValueError("数据中缺少净利润数据")

        def calc_growth(group):
            growth = group['net_profit'].pct_change(self.period)
            return growth

        result = data.groupby('code').apply(calc_growth)

        if isinstance(result, pd.DataFrame):
            result = result.droplevel(0) if result.index.nlevels > 2 else result[0]

        result = result.clip(lower=-0.99, upper=10)

        result.name = self.name
        return result


class BookValueGrowthFactor(BaseFactor):
    """净资产增长率因子"""

    def __init__(self, period: int = 4):
        super().__init__(
            name="book_value_growth",
            display_name="净资产增长率",
            category="growth",
            direction=1
        )
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算净资产增长率"""
        if 'book_value' not in data.columns:
            raise ValueError("数据中缺少净资产数据")

        def calc_growth(group):
            growth = group['book_value'].pct_change(self.period)
            return growth

        result = data.groupby('code').apply(calc_growth)

        if isinstance(result, pd.DataFrame):
            result = result.droplevel(0) if result.index.nlevels > 2 else result[0]

        result = result.clip(lower=-0.99, upper=10)

        result.name = self.name
        return result


class DebtRatioFactor(BaseFactor):
    """资产负债率因子"""

    def __init__(self):
        super().__init__(
            name="debt_ratio",
            display_name="资产负债率",
            category="health",
            direction=-1  # 低负债
        )

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算资产负债率"""
        if 'debt_ratio' in data.columns:
            result = data['debt_ratio'].copy()
        elif 'total_liability' in data.columns and 'total_assets' in data.columns:
            result = data['total_liability'] / (data['total_assets'] + 1)
        else:
            raise ValueError("数据中缺少资产负债率数据")

        result = result.clip(lower=0, upper=1)
        result.name = self.name
        return result


class CurrentRatioFactor(BaseFactor):
    """流动比率因子"""

    def __init__(self):
        super().__init__(
            name="current_ratio",
            display_name="流动比率",
            category="health",
            direction=1
        )

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算流动比率"""
        if 'current_ratio' in data.columns:
            result = data['current_ratio'].copy()
        elif 'current_liability' in data.columns and 'current_assets' in data.columns:
            result = data['current_assets'] / (data['current_liability'] + 1)
        else:
            raise ValueError("数据中缺少流动比率数据")

        result = result.clip(lower=0, upper=10)
        result.name = self.name
        return result


class CashFlowRatioFactor(BaseFactor):
    """经营现金流/净利润因子"""

    def __init__(self):
        super().__init__(
            name="cash_flow_ratio",
            display_name="经营现金流/净利润",
            category="cash_flow",
            direction=1
        )

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算经营现金流与净利润之比"""
        if 'cash_flow_ratio' in data.columns:
            result = data['cash_flow_ratio'].copy()
        elif 'operating_cf' in data.columns and 'net_profit' in data.columns:
            result = data['operating_cf'] / (data['net_profit'].abs() + 1)
        else:
            raise ValueError("数据中缺少现金流数据")

        # 限制范围
        result = result.clip(lower=-5, upper=5)
        result.name = self.name
        return result


class OperatingCashFlowFactor(BaseFactor):
    """经营现金流因子"""

    def __init__(self):
        super().__init__(
            name="operating_cf",
            display_name="经营现金流",
            category="cash_flow",
            direction=1
        )

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算经营现金流"""
        if 'operating_cf' not in data.columns:
            raise ValueError("数据中缺少经营现金流数据")

        result = data['operating_cf'].copy()

        # 对数化处理
        result = np.sign(result) * np.log(np.abs(result) + 1)

        result.name = self.name
        return result


class FinancialFactors:
    """财务因子集合"""

    @staticmethod
    def get_all_factors() -> list:
        """获取所有财务因子"""
        return [
            RevenueGrowthFactor(period=4),  # 年度营收增长
            ProfitGrowthFactor(period=4),   # 年度净利润增长
            BookValueGrowthFactor(period=4),
            DebtRatioFactor(),
            CurrentRatioFactor(),
            CashFlowRatioFactor(),
            OperatingCashFlowFactor(),
        ]

    @staticmethod
    def get_factor_by_name(name: str) -> Optional[BaseFactor]:
        """根据名称获取因子"""
        factory = {
            'revenue_growth': lambda: RevenueGrowthFactor(4),
            'profit_growth': lambda: ProfitGrowthFactor(4),
            'book_value_growth': lambda: BookValueGrowthFactor(4),
            'debt_ratio': DebtRatioFactor,
            'current_ratio': CurrentRatioFactor,
            'cash_flow_ratio': CashFlowRatioFactor,
            'operating_cf': OperatingCashFlowFactor,
        }

        factory_func = factory.get(name)
        return factory_func() if factory_func else None
