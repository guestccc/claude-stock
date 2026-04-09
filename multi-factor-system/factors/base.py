"""
因子基类
定义因子的通用接口和方法
"""
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from loguru import logger


class BaseFactor(ABC):
    """因子基类"""

    def __init__(
        self,
        name: str,
        display_name: str,
        category: str,
        direction: int = 1,
        params: Optional[Dict[str, Any]] = None
    ):
        """
        初始化因子

        Args:
            name: 因子名称（英文，用于代码标识）
            display_name: 因子显示名称
            category: 因子类别（size, value, quality, momentum, volatility, liquidity, growth）
            direction: 方向，1表示越大越好，-1表示越小越好，0表示中性
            params: 因子参数
        """
        self.name = name
        self.display_name = display_name
        self.category = category
        self.direction = direction
        self.params = params or {}

    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算因子值

        Args:
            data: 行情数据，包含 price, volume, market_cap 等

        Returns:
            因子值 Series，index 为 (date, code)
        """
        pass

    def validate(self, result: pd.Series) -> bool:
        """
        验证因子计算结果

        Args:
            result: 计算结果

        Returns:
            是否有效
        """
        if result.empty:
            logger.warning(f"因子 {self.name} 计算结果为空")
            return False

        if result.isna().all():
            logger.warning(f"因子 {self.name} 全部为 NaN")
            return False

        # 检查无穷值
        if np.isinf(result).any():
            logger.warning(f"因子 {self.name} 包含无穷值")
            result = result.replace([np.inf, -np.inf], np.nan)

        return True

    def __repr__(self):
        return f"Factor({self.name}, category={self.category}, direction={self.direction})"


class ReturnsFactor(BaseFactor):
    """收益率因子基类"""

    def __init__(self, name: str, display_name: str, period: int = 20, **kwargs):
        super().__init__(name, display_name, "momentum", **kwargs)
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算收益率"""
        if 'close' not in data.columns:
            raise ValueError("数据中缺少 close 列")

        # 按股票分组计算收益率
        result = data.groupby('code').apply(
            lambda x: x.set_index('date')['close'].pct_change(self.period)
        ).reset_index()

        result = result.set_index(['date', 'code'])[0]
        result.name = self.name

        return result


class ValuationFactor(BaseFactor):
    """估值因子基类"""

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算估值因子"""
        if 'pe' in data.columns:
            result = data.set_index(['date', 'code'])['pe']
            result.name = self.name
            return result

        raise NotImplementedError("数据中缺少估值指标")


class VolatilityFactor(BaseFactor):
    """波动率因子基类"""

    def __init__(self, name: str, display_name: str, period: int = 20, **kwargs):
        super().__init__(name, display_name, "volatility", **kwargs)
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算波动率"""
        if 'daily_return' not in data.columns:
            if 'close' in data.columns:
                data = data.copy()
                data['daily_return'] = data.groupby('code')['close'].pct_change()

        result = data.groupby('code')['daily_return'].apply(
            lambda x: x.rolling(window=self.period).std()
        ).reset_index()

        result = result.set_index(['date', 'code'])[0]
        result.name = self.name

        return result


class LiquidityFactor(BaseFactor):
    """流动性因子基类"""

    def __init__(self, name: str, display_name: str, period: int = 20, **kwargs):
        super().__init__(name, display_name, "liquidity", **kwargs)
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算换手率（需要成交额和市值数据）"""
        if 'turnover_rate' in data.columns:
            result = data.set_index(['date', 'code'])['turnover_rate']
            result.name = self.name
            return result

        # 如果没有换手率，从成交量计算
        if 'volume' in data.columns and 'amount' in data.columns:
            data = data.copy()
            data['implied_turnover'] = data['amount'] / data['close']  # 近似换手率

            result = data.groupby('code')['implied_turnover'].apply(
                lambda x: x.rolling(window=self.period).mean()
            ).reset_index()

            result = result.set_index(['date', 'code'])[0]
            result.name = self.name
            return result

        raise ValueError("数据中缺少成交量或成交额数据")


def standardize_factor(
    factor: pd.Series,
    method: str = 'zscore'
) -> pd.Series:
    """
    标准化因子

    Args:
        factor: 原始因子值
        method: 标准化方法，'zscore'（Z-score标准化）或 'rank'（排名标准化）

    Returns:
        标准化后的因子
    """
    if method == 'zscore':
        # Z-score 标准化
        mean = factor.mean()
        std = factor.std()

        if std == 0 or pd.isna(std):
            return factor * 0

        return (factor - mean) / std

    elif method == 'rank':
        # 排名标准化到 [0, 1]
        return factor.rank(pct=True)

    else:
        raise ValueError(f"不支持的标准化方法: {method}")


def winsorize_factor(
    factor: pd.Series,
    lower: float = 0.01,
    upper: float = 0.99
) -> pd.Series:
    """
    去极值处理

    Args:
        factor: 原始因子值
        lower: 下界百分位
        upper: 上界百分位

    Returns:
        去极值后的因子
    """
    lower_bound = factor.quantile(lower)
    upper_bound = factor.quantile(upper)

    return factor.clip(lower=lower_bound, upper=upper_bound)
