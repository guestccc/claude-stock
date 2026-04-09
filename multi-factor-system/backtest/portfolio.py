"""
组合构建模块
基于因子的组合构建方法
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from loguru import logger


class PortfolioBuilder:
    """组合构建器"""

    def __init__(self, config):
        self.config = config
        self.top_n = config.get("portfolio.top_n", 50)
        self.weight_method = config.get("portfolio.weight_method", "equal")
        self.max_single_weight = config.get("portfolio.max_single_weight", 0.05)

    def build_portfolio(
        self,
        factors: pd.DataFrame,
        date: pd.Timestamp,
        weight_method: Optional[str] = None
    ) -> Dict[str, float]:
        """
        构建投资组合

        Args:
            factors: 因子数据
            date: 调仓日期
            weight_method: 加权方法

        Returns:
            持仓权重字典 {code: weight}
        """
        if factors.empty:
            return {}

        # 获取当日因子
        if factors.index.nlevels > 1:
            try:
                date_factors = factors.loc[:date].iloc[-1:].droplevel(0)
            except Exception:
                date_factors = factors.loc[date] if date in factors.index else pd.DataFrame()
        else:
            date_factors = factors

        if date_factors.empty:
            return {}

        # 选择因子
        if isinstance(date_factors, pd.Series):
            date_factors = date_factors.to_frame()

        # 合并多因子
        if len(date_factors.columns) > 1:
            composite = self._combine_factors(date_factors)
        else:
            composite = date_factors.iloc[:, 0]

        # 选择 Top N
        top_stocks = self._select_top_n(composite, self.top_n)

        # 计算权重
        method = weight_method or self.weight_method
        weights = self._calculate_weights(top_stocks, method)

        # 约束
        weights = self._apply_constraints(weights)

        return weights

    def _combine_factors(self, factors: pd.DataFrame) -> pd.Series:
        """合并多个因子为复合因子"""
        # 等权平均
        composite = factors.mean(axis=1)
        return composite

    def _select_top_n(
        self,
        factor: pd.Series,
        n: int
    ) -> pd.Series:
        """选择因子值最高/最低的N只股票"""
        # 排序并选择
        sorted_factor = factor.sort_values(ascending=False)
        top = sorted_factor.head(n)
        return top

    def _calculate_weights(
        self,
        stocks: pd.Series,
        method: str = "equal"
    ) -> Dict[str, float]:
        """
        计算持仓权重

        Args:
            stocks: 排序后的因子值
            method: 加权方法

        Returns:
            权重字典
        """
        if stocks.empty:
            return {}

        n = len(stocks)
        codes = stocks.index.tolist()

        if method == "equal":
            # 等权
            weight = 1.0 / n
            weights = {code: weight for code in codes}

        elif method == "factor_weighted":
            # 因子加权（按因子值比例）
            total = stocks.sum()
            if total == 0:
                weight = 1.0 / n
                weights = {code: weight for code in codes}
            else:
                weights = {code: v / total for code, v in stocks.items()}

        elif method == "ic_weighted":
            # IC加权（假设已知各因子IC）
            # 这里简化处理，使用因子值
            values = stocks.values
            values = np.maximum(values, 0)  # 确保非负
            total = values.sum()
            if total == 0:
                weight = 1.0 / n
                weights = {code: weight for code in codes}
            else:
                weights = {code: v / total for code, v in zip(codes, values)}

        elif method == "risk_parity":
            # 风险平价（简化：使用市值倒数作为风险代理）
            # 这里简化处理
            weight = 1.0 / n
            weights = {code: weight for code in codes}

        else:
            weight = 1.0 / n
            weights = {code: weight for code in codes}

        return weights

    def _apply_constraints(self, weights: Dict[str, float]) -> Dict[str, float]:
        """应用约束条件"""
        # 最大单只权重约束
        for code in weights:
            weights[code] = min(weights[code], self.max_single_weight)

        # 归一化
        total = sum(weights.values())
        if total > 0:
            weights = {code: w / total for code, w in weights.items()}

        return weights

    def build_long_short_portfolio(
        self,
        factors: pd.DataFrame,
        date: pd.Timestamp,
        long_pct: float = 0.1,
        short_pct: float = 0.1
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        构建多空组合

        Args:
            factors: 因子数据
            date: 调仓日期
            long_pct: 多头比例（总资产的百分比）
            short_pct: 空头比例

        Returns:
            (多头权重, 空头权重)
        """
        if factors.empty:
            return {}, {}

        # 获取当日因子
        if factors.index.nlevels > 1:
            try:
                date_factors = factors.loc[:date].iloc[-1:].droplevel(0)
            except Exception:
                date_factors = factors.loc[date] if date in factors.index else pd.DataFrame()
        else:
            date_factors = factors

        if isinstance(date_factors, pd.Series):
            date_factors = date_factors.to_frame()

        # 合并多因子
        if len(date_factors.columns) > 1:
            composite = date_factors.mean(axis=1)
        else:
            composite = date_factors.iloc[:, 0]

        # 排序
        sorted_factor = composite.sort_values(ascending=False)

        # 选择多头和空头
        n = len(sorted_factor)
        n_long = max(int(n * long_pct), 1)
        n_short = max(int(n * short_pct), 1)

        long_stocks = sorted_factor.head(n_long)
        short_stocks = sorted_factor.tail(n_short)

        # 等权
        long_weights = {code: 1.0 / n_long for code in long_stocks.index}
        short_weights = {code: 1.0 / n_short for code in short_stocks.index}

        # 归一化
        # 多头权重为正，空头权重为负
        total_long = sum(long_weights.values())
        total_short = sum(short_weights.values())

        # 杠杆率 1:1
        leverage = 1.0

        long_weights = {code: w / total_long * leverage for code, w in long_weights.items()}
        short_weights = {code: -w / total_short * leverage for code, w in short_weights.items()}

        return long_weights, short_weights


class FactorWeightedBuilder(PortfolioBuilder):
    """因子加权组合构建器"""

    def __init__(self, config, ic_weights: Dict[str, float] = None):
        super().__init__(config)
        self.ic_weights = ic_weights or {}

    def _combine_factors(self, factors: pd.DataFrame) -> pd.Series:
        """使用IC权重合并因子"""
        if not self.ic_weights:
            return factors.mean(axis=1)

        weights = []
        for col in factors.columns:
            w = self.ic_weights.get(col, 1.0)
            weights.append(w)

        weights = np.array(weights)
        weights = weights / weights.sum()

        composite = (factors * weights).sum(axis=1)
        return composite


class RiskParityBuilder(PortfolioBuilder):
    """风险平价组合构建器"""

    def _calculate_weights(
        self,
        stocks: pd.Series,
        method: str = "risk_parity"
    ) -> Dict[str, float]:
        """风险平价加权"""
        # 使用因子暴露的倒数作为风险代理
        # 这里简化处理
        n = len(stocks)
        return {code: 1.0 / n for code in stocks.index}


class OptimizationBuilder(PortfolioBuilder):
    """优化器组合构建器"""

    def __init__(self, config, constraints: Dict = None):
        super().__init__(config)
        self.constraints = constraints or {}

    def optimize_portfolio(
        self,
        factors: pd.DataFrame,
        date: pd.Timestamp,
        factor_cov: Optional[pd.DataFrame] = None
    ) -> Dict[str, float]:
        """
        使用优化方法构建组合

        Args:
            factors: 因子暴露
            date: 日期
            factor_cov: 因子协方差矩阵

        Returns:
            最优权重
        """
        # 获取目标持仓
        target = self.build_portfolio(factors, date, weight_method="equal")

        if not target:
            return {}

        # 简单优化：最大化因子暴露同时控制风险
        # 这里使用简化方法
        n = len(target)
        weight = 1.0 / n

        return {code: weight for code in target.keys()}
