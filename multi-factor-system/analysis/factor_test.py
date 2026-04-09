"""
单因子测试模块
对单个因子进行全面测试
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from loguru import logger

from .ic_analyzer import ICAnalyzer
from .neutralization import Neutralizer


class FactorTester:
    """单因子测试器"""

    def __init__(self, config):
        self.config = config
        self.ic_analyzer = ICAnalyzer(config)
        self.neutralizer = Neutralizer(config)

    def test_factor(
        self,
        factor: pd.Series,
        returns: pd.DataFrame,
        n_groups: int = 10,
        top_pct: float = 0.1
    ) -> Dict:
        """
        对单个因子进行全面测试

        Args:
            factor: 因子值，index=(date, code)
            returns: 收益率数据
            n_groups: 分组数量（用于分组回测）
            top_pct: 多空组合中多头比例

        Returns:
            测试结果字典
        """
        logger.info(f"开始测试因子: {factor.name}")

        # 确保收益率格式正确
        if isinstance(returns, pd.DataFrame) and 'daily_return' in returns.columns:
            returns = returns.set_index(['date', 'code'])['daily_return']

        results = {
            'factor_name': factor.name,
            'n_samples': len(factor.dropna()),
            'n_dates': factor.index.get_level_values(0).nunique() if factor.index.nlevels > 1 else 0
        }

        # 1. IC 分析
        try:
            ic_result = self.ic_analyzer.calculate_ic(
                factor.to_frame(),
                returns
            )
            results['ic_mean'] = ic_result['mean_ic']
            results['ic_std'] = ic_result['std_ic']
            results['ic_ir'] = ic_result['ir']
            results['ic_positive_ratio'] = (ic_result['ic_series'][factor.name] > 0).mean()
        except Exception as e:
            logger.warning(f"IC分析失败: {e}")

        # 2. 分组回测
        try:
            group_returns = self._calculate_group_returns(
                factor,
                returns,
                n_groups=n_groups
            )
            results['group_returns'] = group_returns

            # 计算多空组合收益
            long_short = group_returns.iloc[:, -1] - group_returns.iloc[:, 0]
            results['long_short_mean'] = long_short.mean()
            results['long_short_t'] = self._t_stat(long_short)
        except Exception as e:
            logger.warning(f"分组回测失败: {e}")

        # 3. 因子分布统计
        try:
            results['factor_stats'] = self._calculate_factor_stats(factor)
        except Exception as e:
            logger.warning(f"因子统计失败: {e}")

        # 4. 换手率分析
        try:
            results['turnover'] = self._calculate_turnover(factor, top_pct)
        except Exception as e:
            logger.warning(f"换手率分析失败: {e}")

        logger.info(f"因子测试完成: IC={results.get('ic_mean', 0):.4f}, "
                    f"IR={results.get('ic_ir', 0):.4f}")

        return results

    def _calculate_group_returns(
        self,
        factor: pd.Series,
        returns: pd.Series,
        n_groups: int = 10
    ) -> pd.DataFrame:
        """
        计算分组收益率

        Returns:
            DataFrame，index=date, columns=group_1, group_2, ..., group_n
        """
        # 合并数据
        combined = pd.DataFrame({
            'factor': factor,
            'return': returns
        }).dropna()

        if combined.empty:
            return pd.DataFrame()

        # 按日期分组
        if factor.index.nlevels > 1:
            dates = factor.index.get_level_values(0).unique()
        else:
            return pd.DataFrame()

        group_returns = []

        for date in dates:
            try:
                mask = combined.index.get_level_values(0) == date
                daily_data = combined.loc[mask]

                if len(daily_data) < n_groups:
                    continue

                # 分组
                daily_data = daily_data.copy()
                daily_data['group'] = pd.qcut(
                    daily_data['factor'],
                    q=n_groups,
                    labels=range(1, n_groups + 1),
                    duplicates='drop'
                )

                # 计算每组收益率
                group_ret = daily_data.groupby('group')['return'].mean()

                # 添加到结果
                group_returns.append(group_ret)

            except Exception:
                continue

        if not group_returns:
            return pd.DataFrame()

        result = pd.DataFrame(group_returns)
        result.columns = [f'group_{i}' for i in result.columns]

        return result

    def _calculate_factor_stats(self, factor: pd.Series) -> Dict:
        """计算因子分布统计"""
        f = factor.dropna()

        return {
            'mean': f.mean(),
            'std': f.std(),
            'min': f.min(),
            'max': f.max(),
            'skewness': f.skew(),
            'kurtosis': f.kurtosis(),
            'na_ratio': f.isna().mean()
        }

    def _calculate_turnover(
        self,
        factor: pd.Series,
        top_pct: float = 0.1
    ) -> Dict:
        """计算调仓换手率"""
        if factor.index.nlevels < 2:
            return {}

        dates = sorted(factor.index.get_level_values(0).unique())

        if len(dates) < 2:
            return {}

        turnovers = []

        for i in range(1, len(dates)):
            prev_date = dates[i - 1]
            curr_date = dates[i]

            try:
                prev_factor = factor.loc[prev_date]
                curr_factor = factor.loc[curr_date]

                # 获取前10%的股票
                prev_top = set(prev_factor.nlargest(int(len(prev_factor) * top_pct)).index)
                curr_top = set(curr_factor.nlargest(int(len(curr_factor) * top_pct)).index)

                # 计算换手率
                overlap = len(prev_top & curr_top)
                turnover = 1 - overlap / len(prev_top) if len(prev_top) > 0 else 0

                turnovers.append(turnover)

            except Exception:
                continue

        if not turnovers:
            return {}

        return {
            'mean_turnover': np.mean(turnovers),
            'median_turnover': np.median(turnovers),
            'max_turnover': np.max(turnovers)
        }

    def _t_stat(self, series: pd.Series) -> float:
        """计算 t 统计量"""
        if len(series) == 0 or series.std() == 0:
            return 0

        return series.mean() / (series.std() / np.sqrt(len(series)))

    def compare_factors(
        self,
        factors: pd.DataFrame,
        returns: pd.DataFrame
    ) -> pd.DataFrame:
        """
        比较多个因子

        Args:
            factors: 多因子数据
            returns: 收益率数据

        Returns:
            因子比较结果 DataFrame
        """
        results = []

        for factor_name in factors.columns:
            try:
                test_result = self.test_factor(
                    factors[factor_name],
                    returns
                )

                results.append({
                    'factor': factor_name,
                    'ic_mean': test_result.get('ic_mean', 0),
                    'ic_ir': test_result.get('ic_ir', 0),
                    'long_short': test_result.get('long_short_mean', 0),
                    'positive_ic_ratio': test_result.get('ic_positive_ratio', 0),
                    'turnover': test_result.get('turnover', {}).get('mean_turnover', 0)
                })

            except Exception as e:
                logger.warning(f"因子 {factor_name} 比较失败: {e}")

        return pd.DataFrame(results).sort_values('ic_ir', ascending=False)


class FactorCorrelationAnalyzer:
    """因子相关性分析器"""

    def __init__(self):
        pass

    def calculate_correlation_matrix(
        self,
        factors: pd.DataFrame,
        method: str = 'spearman'
    ) -> pd.DataFrame:
        """
        计算因子相关性矩阵

        Args:
            factors: 因子数据
            method: 'spearman' 或 'pearson'

        Returns:
            相关性矩阵
        """
        if method == 'spearman':
            return factors.corr(method='spearman')
        else:
            return factors.corr(method='pearson')

    def find_high_correlation_pairs(
        self,
        factors: pd.DataFrame,
        threshold: float = 0.8
    ) -> List[Tuple[str, str, float]]:
        """
        找出高相关因子对

        Args:
            factors: 因子数据
            threshold: 相关系数阈值

        Returns:
            高相关因子对列表
        """
        corr_matrix = self.calculate_correlation_matrix(factors)
        n = len(corr_matrix)

        high_corr = []

        for i in range(n):
            for j in range(i + 1, n):
                corr = corr_matrix.iloc[i, j]
                if abs(corr) >= threshold:
                    high_corr.append((
                        corr_matrix.index[i],
                        corr_matrix.columns[j],
                        corr
                    ))

        # 按相关系数绝对值排序
        high_corr.sort(key=lambda x: abs(x[2]), reverse=True)

        return high_corr

    def suggest_factor_removal(
        self,
        factors: pd.DataFrame,
        threshold: float = 0.8
    ) -> List[str]:
        """
        建议需要删除的因子（因冗余）

        Args:
            factors: 因子数据
            threshold: 相关系数阈值

        Returns:
            建议删除的因子列表
        """
        high_corr = self.find_high_correlation_pairs(factors, threshold)

        # 简单策略：保留IC高的，删除IC低的
        to_remove = set()

        for f1, f2, corr in high_corr:
            if f1 in to_remove or f2 in to_remove:
                continue

            # 两个都未标记，删除其中一个
            # 这里简化处理，删除第一个
            to_remove.add(f1)

        return list(to_remove)
