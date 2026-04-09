"""
IC分析模块
计算因子 IC/IR 值，分析因子有效性
"""
import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Optional, Union
from loguru import logger


class ICAnalyzer:
    """IC分析器"""

    def __init__(self, config):
        self.config = config
        self.ic_window = config.get("analysis.ic_window", 20)

    def calculate_ic(
        self,
        factors: pd.DataFrame,
        returns: pd.DataFrame,
        method: str = 'rank'
    ) -> Dict[str, pd.DataFrame]:
        """
        计算因子 IC 值

        Args:
            factors: 因子数据，index=(date, code), columns=因子名
            returns: 收益率数据，需要包含 daily_return 列
            method: IC计算方法，'rank'（Spearman相关）或 'pearson'（Pearson相关）

        Returns:
            IC结果字典，包含:
            - ic_series: 每日IC序列
            - ic_stats: IC统计信息
            - ir: IC_IR比率
        """
        logger.info(f"开始计算IC，使用{method}相关法...")

        # 确保收益率数据格式正确
        if isinstance(returns, pd.DataFrame) and 'daily_return' in returns.columns:
            returns = returns.set_index(['date', 'code'])['daily_return']

        # 合并因子和收益率
        combined = factors.copy()
        combined['return'] = returns

        # 删除缺失值
        combined = combined.dropna()

        if combined.empty:
            logger.warning("合并后数据为空")
            return {}

        # 计算每个因子的 IC
        ic_results = {}

        for factor_name in factors.columns:
            ic_series = self._calculate_single_ic(
                combined[factor_name],
                combined['return'],
                method=method
            )
            ic_results[factor_name] = ic_series

        # 汇总结果
        ic_df = pd.DataFrame(ic_results)

        # 计算统计量
        ic_stats = self._calculate_ic_stats(ic_df)

        # 计算 ICIR
        ir = ic_stats['mean_ic'] / ic_stats['std_ic']

        return {
            'ic_series': ic_df,
            'ic_stats': ic_stats,
            'ir': ir,
            'mean_ic': ic_stats['mean_ic'],
            'std_ic': ic_stats['std_ic'],
            'ir_ratio': ir
        }

    def _calculate_single_ic(
        self,
        factor: pd.Series,
        returns: pd.Series,
        method: str = 'rank'
    ) -> pd.Series:
        """
        计算单个因子的 IC 序列

        Args:
            factor: 因子值
            returns: 收益率
            method: 'rank' 或 'pearson'

        Returns:
            IC 序列
        """
        # 按日期分组计算 IC
        def calc_daily_ic(group):
            f = group.dropna()
            r = returns.loc[f.index]

            if len(f) < 10:  # 样本太少跳过
                return np.nan

            if method == 'rank':
                # Spearman 相关系数（Rank IC）
                corr, _ = stats.spearmanr(f, r)
            else:
                # Pearson 相关系数
                corr, _ = stats.pearsonr(f, r)

            return corr

        # 按日期分组
        if factor.index.nlevels > 1:
            dates = factor.index.get_level_values(0).unique()
        else:
            return pd.Series()

        ic_series = []
        for date in dates:
            try:
                mask = factor.index.get_level_values(0) == date
                f = factor.loc[mask]
                r = returns.loc[f.index]

                daily_ic = calc_daily_ic(f, r)
                ic_series.append((date, daily_ic))
            except Exception:
                continue

        return pd.Series(
            [x[1] for x in ic_series],
            index=[x[0] for x in ic_series]
        )

    def _calculate_ic_stats(self, ic_df: pd.DataFrame) -> pd.DataFrame:
        """计算 IC 统计量"""
        stats_list = []

        for factor_name in ic_df.columns:
            ic_series = ic_df[factor_name].dropna()

            if len(ic_series) == 0:
                continue

            # 基本统计量
            mean_ic = ic_series.mean()
            std_ic = ic_series.std()
            ir = mean_ic / std_ic if std_ic > 0 else 0

            # T 统计量
            t_stat = mean_ic / (std_ic / np.sqrt(len(ic_series))) if std_ic > 0 else 0

            # 正 IC 比例
            positive_ratio = (ic_series > 0).mean()

            # IC > 0.02 的比例（显著正相关）
            significant_pos = (ic_series > 0.02).mean()

            # IC < -0.02 的比例（显著负相关）
            significant_neg = (ic_series < -0.02).mean()

            stats_list.append({
                'factor': factor_name,
                'mean_ic': mean_ic,
                'std_ic': std_ic,
                'ir': ir,
                't_stat': t_stat,
                'positive_ratio': positive_ratio,
                'significant_pos': significant_pos,
                'significant_neg': significant_neg,
                'ic_count': len(ic_series)
            })

        return pd.DataFrame(stats_list).set_index('factor')

    def calculate_rolling_ic(
        self,
        factors: pd.DataFrame,
        returns: pd.DataFrame,
        window: int = 12
    ) -> pd.DataFrame:
        """
        计算滚动 IC

        Args:
            factors: 因子数据
            returns: 收益率数据
            window: 滚动窗口（月数）

        Returns:
            滚动 IC DataFrame
        """
        # 计算月度 IC
        ic_result = self.calculate_ic(factors, returns)
        ic_series = ic_result['ic_series']

        # 滚动平均
        rolling_ic = ic_series.rolling(window=window).mean()

        return rolling_ic

    def analyze_ic_decay(
        self,
        factors: pd.DataFrame,
        returns: pd.DataFrame,
        max_lags: int = 12
    ) -> pd.DataFrame:
        """
        分析因子 IC 衰减

        Args:
            factors: 因子数据
            returns: 收益率数据
            max_lags: 最大滞后月数

        Returns:
            IC 衰减数据
        """
        logger.info(f"分析因子 IC 衰减，滞后 {max_lags} 期...")

        # 获取因子名
        if isinstance(factors, pd.DataFrame):
            factor_names = factors.columns[:5].tolist()  # 限制数量
        else:
            factor_names = [factors.name]

        decay_results = []

        for factor_name in factor_names:
            ic_0 = self.calculate_ic(factors[[factor_name]], returns)['ic_series'][factor_name].mean()

            for lag in range(max_lags + 1):
                if lag == 0:
                    ic = ic_0
                else:
                    # 滞后收益率
                    lagged_returns = returns.shift(-lag)
                    ic_series = self._calculate_single_ic(
                        factors[factor_name],
                        lagged_returns,
                        method='rank'
                    )
                    ic = ic_series.mean()

                decay_results.append({
                    'factor': factor_name,
                    'lag': lag,
                    'ic': ic,
                    'ic_ratio': ic / ic_0 if ic_0 != 0 else 0
                })

        return pd.DataFrame(decay_results)

    def get_top_factors(
        self,
        ic_stats: pd.DataFrame,
        top_n: int = 10,
        min_ir: float = 0.3,
        min_ic: float = 0.02
    ) -> list:
        """
        获取优质因子

        Args:
            ic_stats: IC统计结果
            top_n: 返回前N个
            min_ir: 最小 IR 要求
            min_ic: 最小 IC 要求

        Returns:
            优质因子列表
        """
        # 筛选条件
        filtered = ic_stats[
            (ic_stats['ir'].abs() >= min_ir) &
            (ic_stats['mean_ic'].abs() >= min_ic) &
            (ic_stats['positive_ratio'] >= 0.5)
        ]

        # 按 IR 排序
        filtered = filtered.sort_values('ir', ascending=False)

        # 取前N个
        top_factors = filtered.head(top_n).index.tolist()

        logger.info(f"筛选出 {len(top_factors)} 个优质因子（IR>{min_ir}, IC>{min_ic}）")

        return top_factors
