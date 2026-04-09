"""
技术因子
包括动量因子、波动率因子、流动性因子、均线因子等
"""
import pandas as pd
import numpy as np
from typing import Optional
from .base import BaseFactor, standardize_factor


class MomentumFactor(BaseFactor):
    """动量因子"""

    def __init__(self, period: int = 20, name: str = None, display_name: str = None):
        self.period = period
        if name is None:
            name = f"momentum_{period}d"
        if display_name is None:
            display_name = f"{period}日动量"

        super().__init__(
            name=name,
            display_name=display_name,
            category="momentum",
            direction=1
        )

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算动量因子（收益率）"""
        if 'close' not in data.columns:
            raise ValueError("数据中缺少 close 列")

        result = data.groupby('code').apply(
            lambda x: x.set_index('date')['close'].pct_change(self.period)
        )

        # 重置索引
        if isinstance(result, pd.DataFrame):
            result = result.droplevel(0) if result.index.nlevels > 2 else result[0]
        elif isinstance(result, pd.Series) and result.name is None:
            result = result.droplevel(0)

        result.name = self.name
        return result


class Momentum12MFactor(BaseFactor):
    """12个月动量因子（排除最近1个月）"""

    def __init__(self):
        super().__init__(
            name="momentum_12m",
            display_name="12月动量",
            category="momentum",
            direction=1
        )

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算12个月动量（排除最近1个月）"""
        if 'close' not in data.columns:
            raise ValueError("数据中缺少 close 列")

        # 12个月前到1个月前的收益率
        result = data.groupby('code').apply(
            lambda x: (x.set_index('date')['close'].shift(20) /
                       x.set_index('date')['close'].shift(240) - 1)
        )

        if isinstance(result, pd.DataFrame):
            result = result.droplevel(0) if result.index.nlevels > 2 else result[0]

        result.name = self.name
        return result


class VolatilityFactor(BaseFactor):
    """波动率因子"""

    def __init__(self, period: int = 20, name: str = None, display_name: str = None):
        self.period = period
        if name is None:
            name = f"volatility_{period}d"
        if display_name is None:
            display_name = f"{period}日波动率"

        super().__init__(
            name=name,
            display_name=display_name,
            category="volatility",
            direction=-1  # 低波动效应
        )

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算历史波动率"""
        # 计算日收益率
        df = data.copy()
        if 'daily_return' not in df.columns:
            df['daily_return'] = df.groupby('code')['close'].pct_change()

        result = df.groupby('code')['daily_return'].apply(
            lambda x: x.rolling(window=self.period).std() * np.sqrt(252)
        )

        if isinstance(result, pd.DataFrame):
            result = result.droplevel(0) if result.index.nlevels > 2 else result[0]

        result.name = self.name
        return result


class BetaFactor(BaseFactor):
    """市场Beta因子"""

    def __init__(self, period: int = 60):
        super().__init__(
            name="beta",
            display_name="市场Beta",
            category="volatility",
            direction=0
        )
        self.period = period

    def calculate(self, data: pd.DataFrame, market_returns: pd.Series = None) -> pd.Series:
        """
        计算Beta

        Args:
            data: 行情数据
            market_returns: 市场收益率序列，如果为None则使用等权组合作为代理
        """
        df = data.copy()
        if 'daily_return' not in df.columns:
            df['daily_return'] = df.groupby('code')['close'].pct_change()

        # 计算每只股票与市场的协方差
        if market_returns is None:
            # 使用等权市场收益率
            market_returns = df.groupby('date')['daily_return'].mean()

        # 合并市场收益率
        df = df.merge(
            market_returns.reset_index().rename(columns={'daily_return': 'market_return'}),
            on='date',
            how='left'
        )

        # 计算Beta
        def calc_beta(group):
            valid = group.dropna()
            if len(valid) < 20:
                return pd.Series([np.nan] * len(group), index=group.index)

            cov = group['daily_return'].rolling(self.period).cov(group['market_return'])
            var = group['market_return'].rolling(self.period).var()

            # Beta = Cov(Ri, Rm) / Var(Rm)
            with np.errstate(divide='ignore', invalid='ignore'):
                beta = cov / var
                beta = beta.clip(-5, 5)  # 限制范围

            return beta

        result = df.groupby('code').apply(calc_beta)

        if isinstance(result, pd.DataFrame):
            result = result.droplevel(0) if result.index.nlevels > 2 else result[0]

        result.name = self.name
        return result


class TurnoverRateFactor(BaseFactor):
    """换手率因子"""

    def __init__(self, period: int = 20):
        super().__init__(
            name="turnover_rate",
            display_name="换手率",
            category="liquidity",
            direction=0
        )
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算平均换手率"""
        if 'turnover_rate' not in data.columns:
            raise ValueError("数据中缺少换手率数据")

        result = data.groupby('code')['turnover_rate'].apply(
            lambda x: x.rolling(window=self.period).mean()
        )

        if isinstance(result, pd.DataFrame):
            result = result.droplevel(0) if result.index.nlevels > 2 else result[0]

        result.name = self.name
        return result


class AmihudIlliquidityFactor(BaseFactor):
    """Amihud非流动性因子"""

    def __init__(self, period: int = 20):
        super().__init__(
            name="amihud_illiquidity",
            display_name="Amihud非流动性",
            category="liquidity",
            direction=-1
        )
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算 Amihud 非流动性指标
        Amihud = (1/D) * Σ |Ri| / Volume_i
        """
        if 'daily_return' not in data.columns:
            data = data.copy()
            data['daily_return'] = data.groupby('code')['close'].pct_change()

        # 计算非流动性
        data = data.copy()
        data['abs_return'] = data['daily_return'].abs()

        # 成交量需要调整（这里假设 amount 是成交额，转换为手数）
        if 'volume' in data.columns:
            data['illiq'] = data['abs_return'] / (data['volume'] + 1)
        elif 'amount' in data.columns and 'close' in data.columns:
            # 成交额 / 价格 = 成交量
            data['volume_proxy'] = data['amount'] / data['close']
            data['illiq'] = data['abs_return'] / (data['volume_proxy'] + 1)
        else:
            raise ValueError("数据中缺少成交量/成交额数据")

        # 取绝对值再求均值（Amihud 流动性）
        result = data.groupby('code')['illiq'].apply(
            lambda x: x.rolling(window=self.period).mean()
        )

        if isinstance(result, pd.DataFrame):
            result = result.droplevel(0) if result.index.nlevels > 2 else result[0]

        # 取反，使其表示流动性
        result = -result  # 非流动性越低越好

        result.name = self.name
        return result


class MADeviationFactor(BaseFactor):
    """均线偏离度因子"""

    def __init__(self, period: int = 20):
        super().__init__(
            name=f"ma{period}_deviation",
            display_name=f"MA{period}偏离度",
            category="technical",
            direction=0
        )
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算价格与均线的偏离度"""
        if 'close' not in data.columns:
            raise ValueError("数据中缺少 close 列")

        result = data.groupby('code').apply(
            lambda x: (x.set_index('date')['close'] /
                       x.set_index('date')['close'].rolling(self.period).mean() - 1)
        )

        if isinstance(result, pd.DataFrame):
            result = result.droplevel(0) if result.index.nlevels > 2 else result[0]

        result.name = self.name
        return result


class TechnicalFactors:
    """技术因子集合"""

    @staticmethod
    def get_all_factors() -> list:
        """获取所有技术因子"""
        return [
            MomentumFactor(period=20, name="momentum_1m", display_name="1月动量"),
            MomentumFactor(period=60, name="momentum_3m", display_name="3月动量"),
            MomentumFactor(period=120, name="momentum_6m", display_name="6月动量"),
            MomentumFactor(period=240, name="momentum_12m", display_name="12月动量"),
            VolatilityFactor(period=20, name="volatility_20d", display_name="20日波动率"),
            VolatilityFactor(period=60, name="volatility_60d", display_name="60日波动率"),
            BetaFactor(period=60),
            TurnoverRateFactor(period=20),
            AmihudIlliquidityFactor(period=20),
            MADeviationFactor(period=20),
        ]

    @staticmethod
    def get_factor_by_name(name: str) -> Optional[BaseFactor]:
        """根据名称获取因子"""
        factory = {
            'momentum_1m': lambda: MomentumFactor(20, "momentum_1m", "1月动量"),
            'momentum_3m': lambda: MomentumFactor(60, "momentum_3m", "3月动量"),
            'momentum_6m': lambda: MomentumFactor(120, "momentum_6m", "6月动量"),
            'momentum_12m': lambda: MomentumFactor(240, "momentum_12m", "12月动量"),
            'volatility_20d': lambda: VolatilityFactor(20, "volatility_20d", "20日波动率"),
            'volatility_60d': lambda: VolatilityFactor(60, "volatility_60d", "60日波动率"),
            'beta': lambda: BetaFactor(60),
            'turnover_rate': lambda: TurnoverRateFactor(20),
            'amihud_illiquidity': lambda: AmihudIlliquidityFactor(20),
            'ma20_deviation': lambda: MADeviationFactor(20),
        }

        factory_func = factory.get(name)
        return factory_func() if factory_func else None
