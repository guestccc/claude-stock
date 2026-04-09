"""
绩效指标模块
计算各种风险收益指标
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, Union
from loguru import logger


class PerformanceMetrics:
    """绩效指标计算器"""

    def __init__(self, backtest_results: Dict, config=None):
        self.results = backtest_results
        self.config = config

    def calculate(self) -> Dict[str, float]:
        """
        计算所有绩效指标

        Returns:
            绩效指标字典
        """
        metrics = {}

        # 收益率指标
        metrics.update(self._calculate_return_metrics())

        # 风险指标
        metrics.update(self._calculate_risk_metrics())

        # 风险调整收益指标
        metrics.update(self._calculate_risk_adjusted_metrics())

        # 交易指标
        metrics.update(self._calculate_trade_metrics())

        return metrics

    def _calculate_return_metrics(self) -> Dict[str, float]:
        """计算收益率指标"""
        metrics = {}

        nav = self.results.get('nav_series')
        if nav is None or len(nav) == 0:
            return metrics

        # 总收益率
        metrics['total_return'] = (nav.iloc[-1] / nav.iloc[0] - 1) if nav.iloc[0] != 0 else 0

        # 年化收益率
        n_days = len(nav)
        n_years = n_days / 252
        final_nav = nav.iloc[-1]
        metrics['annual_return'] = (final_nav ** (1 / n_years) - 1) if n_years > 0 else 0

        # 月度收益率
        if isinstance(nav.index, pd.DatetimeIndex):
            monthly_returns = nav.resample('M').last().pct_change().dropna()
            metrics['avg_monthly_return'] = monthly_returns.mean()
            metrics['best_month'] = monthly_returns.max()
            metrics['worst_month'] = monthly_returns.min()

        # 超额收益（如果有基准）
        if 'benchmark_nav' in self.results:
            benchmark_nav = self.results['benchmark_nav']
            metrics['excess_return'] = final_nav - benchmark_nav.iloc[-1]
            metrics['annual_excess_return'] = metrics['annual_return'] - (
                benchmark_nav.iloc[-1] ** (1 / n_years) - 1
            ) if n_years > 0 else 0

        return metrics

    def _calculate_risk_metrics(self) -> Dict[str, float]:
        """计算风险指标"""
        metrics = {}

        daily_returns = self.results.get('daily_returns')
        if daily_returns is None or len(daily_returns) == 0:
            return metrics

        # 波动率
        metrics['volatility'] = daily_returns.std() * np.sqrt(252)

        # 年化下行波动率
        negative_returns = daily_returns[daily_returns < 0]
        if len(negative_returns) > 0:
            metrics['downside_volatility'] = negative_returns.std() * np.sqrt(252)
        else:
            metrics['downside_volatility'] = 0

        # 最大回撤
        nav = self.results.get('nav_series')
        if nav is not None and len(nav) > 0:
            cummax = nav.cummax()
            drawdown = (nav - cummax) / cummax
            metrics['max_drawdown'] = drawdown.min()

            # 回撤期
            max_dd_idx = drawdown.idxmin()
            peak_idx = nav.loc[:max_dd_idx].idxmax()
            metrics['max_drawdown_duration'] = (
                max_dd_idx - peak_idx
            ).days if isinstance(max_dd_idx, pd.Timestamp) else 0

        # VaR (Value at Risk)
        metrics['var_95'] = daily_returns.quantile(0.05)
        metrics['var_99'] = daily_returns.quantile(0.01)

        # CVaR (Conditional VaR)
        metrics['cvar_95'] = daily_returns[daily_returns <= metrics['var_95']].mean()
        metrics['cvar_99'] = daily_returns[daily_returns <= metrics['var_99']].mean()

        # 偏度和峰度
        metrics['skewness'] = daily_returns.skew()
        metrics['kurtosis'] = daily_returns.kurtosis()

        return metrics

    def _calculate_risk_adjusted_metrics(self) -> Dict[str, float]:
        """计算风险调整收益指标"""
        metrics = {}

        daily_returns = self.results.get('daily_returns')
        if daily_returns is None or len(daily_returns) == 0:
            return metrics

        # 夏普比率
        risk_free_rate = self.config.get('risk_free_rate', 0.03) if self.config else 0.03
        annual_return = self.results.get('annual_return', 0)
        volatility = self.results.get('volatility', daily_returns.std() * np.sqrt(252))

        if volatility > 0:
            metrics['sharpe_ratio'] = (annual_return - risk_free_rate) / volatility
        else:
            metrics['sharpe_ratio'] = 0

        # 索提诺比率（只考虑下行风险）
        downside_vol = self.results.get('downside_volatility', 0)
        if downside_vol > 0:
            metrics['sortino_ratio'] = (annual_return - risk_free_rate) / downside_vol
        else:
            metrics['sortino_ratio'] = 0

        # Calmar 比率
        max_drawdown = abs(self.results.get('max_drawdown', 0))
        if max_drawdown > 0:
            metrics['calmar_ratio'] = annual_return / max_drawdown
        else:
            metrics['calmar_ratio'] = 0

        # 信息比率
        if 'benchmark_nav' in self.results:
            benchmark_nav = self.results['benchmark_nav']
            benchmark_returns = benchmark_nav.pct_change().dropna()

            # 对齐长度
            min_len = min(len(daily_returns), len(benchmark_returns))
            excess_returns = daily_returns.iloc[-min_len:] - benchmark_returns.iloc[-min_len:]

            tracking_error = excess_returns.std() * np.sqrt(252)
            if tracking_error > 0:
                metrics['information_ratio'] = (
                    self.results.get('annual_excess_return', 0) / tracking_error
                )
            else:
                metrics['information_ratio'] = 0

        # 特雷诺比率
        # 需要 Beta，这里简化处理

        return metrics

    def _calculate_trade_metrics(self) -> Dict[str, float]:
        """计算交易指标"""
        metrics = {}

        # 交易次数
        trades = self.results.get('trades')
        if trades is not None and not trades.empty:
            metrics['total_trades'] = len(trades)

            # 买卖次数
            metrics['buy_trades'] = len(trades[trades['action'] == 'buy'])
            metrics['sell_trades'] = len(trades[trades['action'] == 'sell'])

            # 平均持仓股票数
            metrics['avg_positions'] = self.results.get('avg_positions', 0)

        else:
            metrics['total_trades'] = 0
            metrics['buy_trades'] = 0
            metrics['sell_trades'] = 0
            metrics['avg_positions'] = 0

        return metrics

    def get_summary(self) -> pd.DataFrame:
        """获取绩效摘要表"""
        metrics = self.calculate()

        summary = pd.DataFrame([
            {
                '指标': '总收益率',
                '值': f"{metrics.get('total_return', 0):.2%}",
                '说明': '组合总收益率'
            },
            {
                '指标': '年化收益率',
                '值': f"{metrics.get('annual_return', 0):.2%}",
                '说明': '年化几何平均收益'
            },
            {
                '指标': '年化波动率',
                '值': f"{metrics.get('volatility', 0):.2%}",
                '说明': '收益率标准差'
            },
            {
                '指标': '最大回撤',
                '值': f"{metrics.get('max_drawdown', 0):.2%}",
                '说明': '历史最大回撤'
            },
            {
                '指标': '夏普比率',
                '值': f"{metrics.get('sharpe_ratio', 0):.2f}",
                '说明': '年化收益/波动率'
            },
            {
                '指标': '索提诺比率',
                '值': f"{metrics.get('sortino_ratio', 0):.2f}",
                '说明': '年化收益/下行波动'
            },
            {
                '指标': 'Calmar比率',
                '值': f"{metrics.get('calmar_ratio', 0):.2f}",
                '说明': '年化收益/最大回撤'
            },
        ])

        if 'excess_return' in metrics:
            summary = pd.concat([summary, pd.DataFrame([{
                '指标': '超额收益',
                '值': f"{metrics.get('excess_return', 0):.2%}",
                '说明': '相对基准超额收益'
            }])], ignore_index=True)

        return summary


def calculate_win_rate(returns: pd.Series, threshold: float = 0) -> float:
    """计算胜率"""
    if len(returns) == 0:
        return 0
    return (returns > threshold).mean()


def calculate_profit_loss_ratio(returns: pd.Series) -> float:
    """计算盈亏比"""
    wins = returns[returns > 0]
    losses = returns[returns < 0]

    if len(wins) == 0 or len(losses) == 0:
        return 0

    avg_win = wins.mean()
    avg_loss = abs(losses.mean())

    return avg_win / avg_loss if avg_loss > 0 else 0


def calculate_recovery_factor(total_return: float, max_drawdown: float) -> float:
    """计算恢复因子"""
    if max_drawdown == 0:
        return 0
    return total_return / abs(max_drawdown)
