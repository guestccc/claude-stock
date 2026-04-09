"""
因子计算引擎
统一管理所有因子的计算
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Union
from loguru import logger

from .base import BaseFactor, standardize_factor, winsorize_factor
from .fundamental import FundamentalFactors
from .technical import TechnicalFactors
from .financial import FinancialFactors


class FactorEngine:
    """因子计算引擎"""

    def __init__(self, config):
        self.config = config
        self.standardization = config.get("factors.standardization", "zscore")

        # 初始化因子集合
        self.fundamental_factors = FundamentalFactors()
        self.technical_factors = TechnicalFactors()
        self.financial_factors = FinancialFactors()

    def calculate_factor(
        self,
        factor_name: str,
        data: pd.DataFrame,
        standardize: bool = True
    ) -> pd.Series:
        """
        计算单个因子

        Args:
            factor_name: 因子名称
            data: 行情数据
            standardize: 是否标准化

        Returns:
            因子值序列
        """
        # 尝试从各因子集合获取
        factor = (
            self.fundamental_factors.get_factor_by_name(factor_name) or
            self.technical_factors.get_factor_by_name(factor_name) or
            self.financial_factors.get_factor_by_name(factor_name)
        )

        if factor is None:
            raise ValueError(f"未知因子: {factor_name}")

        # 计算因子
        result = factor.calculate(data)

        if standardize:
            result = self._process_factor(result)

        return result

    def calculate_all_factors(
        self,
        data: pd.DataFrame,
        factor_list: Optional[List[str]] = None,
        parallel: bool = False
    ) -> pd.DataFrame:
        """
        计算所有因子

        Args:
            data: 行情数据
            factor_list: 指定要计算的因子列表，None表示计算全部
            parallel: 是否并行计算

        Returns:
            因子 DataFrame，列为因子名，index 为 (date, code)
        """
        logger.info("开始计算因子...")

        # 获取因子列表
        if factor_list is None:
            all_factors = (
                self.fundamental_factors.get_all_factors() +
                self.technical_factors.get_all_factors() +
                self.financial_factors.get_all_factors()
            )
        else:
            all_factors = []
            for name in factor_list:
                factor = (
                    self.fundamental_factors.get_factor_by_name(name) or
                    self.technical_factors.get_factor_by_name(name) or
                    self.financial_factors.get_factor_by_name(name)
                )
                if factor:
                    all_factors.append(factor)
                else:
                    logger.warning(f"未找到因子: {name}")

        # 计算每个因子
        factor_results = {}

        for factor in all_factors:
            try:
                logger.debug(f"计算因子: {factor.name}")
                result = factor.calculate(data)

                if factor.validate(result):
                    factor_results[factor.name] = result
                    logger.debug(f"  -> 因子 {factor.name} 计算成功")
                else:
                    logger.warning(f"  -> 因子 {factor.name} 验证失败")

            except Exception as e:
                logger.error(f"  -> 因子 {factor.name} 计算失败: {e}")

        # 合并结果
        factors_df = pd.DataFrame(factor_results)

        # 标准化处理
        factors_df = self._standardize_all(factors_df)

        logger.info(f"因子计算完成，共 {len(factors_df.columns)} 个因子")

        return factors_df

    def _process_factor(self, factor: pd.Series) -> pd.Series:
        """处理单个因子：去极值 + 标准化"""
        # 去极值
        factor = winsorize_factor(factor)

        # 标准化
        if self.standardization == 'zscore':
            factor = standardize_factor(factor, method='zscore')
        elif self.standardization == 'rank':
            factor = standardize_factor(factor, method='rank')

        return factor

    def _standardize_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """对所有因子进行标准化"""
        if df.empty:
            return df

        # 按日期分组标准化
        result = df.groupby(level='date').apply(
            lambda x: pd.DataFrame(
                standardize_factor(x, method=self.standardization),
                index=x.index
            )
        )

        return result.droplevel(0) if result.index.nlevels > 2 else result

    def calculate_composite_factor(
        self,
        factors: pd.DataFrame,
        weights: Optional[Dict[str, float]] = None,
        method: str = 'equal'
    ) -> pd.Series:
        """
        计算复合因子

        Args:
            factors: 因子数据
            weights: 因子权重字典，{'factor_name': weight}
            method: 加权方式，'equal' 等权，'ic_weighted' IC加权，'custom' 自定义权重

        Returns:
            复合因子值
        """
        if factors.empty:
            return pd.Series(dtype=float)

        if method == 'equal':
            # 等权平均
            composite = factors.mean(axis=1)

        elif method == 'ic_weighted':
            # IC加权
            if weights is None:
                # 使用 IC 均值作为权重
                ic_values = self._calculate_factor_ic(factors)
                weights = ic_values.to_dict()

            weights = pd.Series(weights)
            # 标准化权重
            weights = weights / weights.sum()

            # 加权平均
            weighted_factors = factors.multiply(weights)
            composite = weighted_factors.sum(axis=1)

        elif method == 'custom':
            if weights is None:
                raise ValueError("自定义权重需要提供 weights 参数")
            weights = pd.Series(weights)
            weighted_factors = factors.multiply(weights)
            composite = weighted_factors.sum(axis=1)

        else:
            raise ValueError(f"未知的加权方式: {method}")

        composite.name = 'composite_factor'
        return composite

    def _calculate_factor_ic(self, factors: pd.DataFrame) -> pd.Series:
        """计算各因子的 IC 均值（用于 IC 加权）"""
        # 这里简化处理，返回等权
        # 实际应该与收益率数据结合计算 IC
        return pd.Series(1.0 / len(factors.columns), index=factors.columns)

    def get_factor_info(self) -> pd.DataFrame:
        """获取所有因子信息"""
        all_factors = (
            self.fundamental_factors.get_all_factors() +
            self.technical_factors.get_all_factors() +
            self.financial_factors.get_all_factors()
        )

        info = pd.DataFrame([
            {
                'name': f.name,
                'display_name': f.display_name,
                'category': f.category,
                'direction': f.direction,
                'direction_desc': '越大越好' if f.direction == 1 else '越小越好' if f.direction == -1 else '中性'
            }
            for f in all_factors
        ])

        return info

    def filter_factors_by_category(
        self,
        factors: List[str],
        category: str
    ) -> List[str]:
        """按类别筛选因子"""
        category_map = {
            'size': ['ln_market_cap', 'circulating_market_cap'],
            'value': ['pe_ratio', 'pb_ratio', 'ps_ratio'],
            'quality': ['roe', 'roa', 'gross_margin'],
            'momentum': [f for f in factors if 'momentum' in f],
            'volatility': [f for f in factors if 'volatility' in f or 'beta' in f],
            'liquidity': [f for f in factors if 'turnover' in f or 'amihud' in f],
            'growth': [f for f in factors if 'growth' in f],
            'health': [f for f in factors if 'ratio' in f and 'turnover' not in f],
        }

        return category_map.get(category, [])
