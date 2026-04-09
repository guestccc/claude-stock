"""
报告生成模块
生成可视化报告和绩效分析图表
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from loguru import logger

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class ReportGenerator:
    """报告生成器"""

    def __init__(self, config):
        self.config = config
        self.output_dir = Path(config.get('output_dir', './output'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        metrics: Dict,
        backtest_results: Dict,
        report_type: str = 'full'
    ) -> str:
        """
        生成完整报告

        Args:
            metrics: 绩效指标
            backtest_results: 回测结果
            report_type: 报告类型

        Returns:
            报告文件路径
        """
        logger.info("开始生成报告...")

        # 生成各类图表
        self.plot_nav_curve(backtest_results)
        self.plot_drawdown(backtest_results)
        self.plot_returns_distribution(backtest_results)
        self.plot_monthly_returns(backtest_results)

        if 'benchmark_nav' in backtest_results:
            self.plot_nav_vs_benchmark(backtest_results)

        # 生成绩效摘要
        summary_path = self._generate_summary(metrics, backtest_results)

        logger.info(f"报告已生成: {self.output_dir}")

        return str(self.output_dir)

    def plot_nav_curve(
        self,
        results: Dict,
        title: str = '组合净值曲线',
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """绘制净值曲线"""
        fig, ax = plt.subplots(figsize=(12, 6))

        nav = results.get('nav_series')
        if nav is None:
            logger.warning("无净值数据，跳过净值曲线图")
            return fig

        # 绘图
        ax.plot(nav.index, nav.values, linewidth=2, label='组合净值')

        # 基准对比
        if 'benchmark_nav' in results:
            benchmark = results['benchmark_nav']
            # 对齐索引
            common_idx = nav.index.intersection(benchmark.index)
            ax.plot(common_idx, benchmark.loc[common_idx].values,
                    linewidth=1.5, linestyle='--', alpha=0.7, label='基准')

        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('净值', fontsize=12)
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)

        # 日期格式化
        if isinstance(nav.index, pd.DatetimeIndex):
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            plt.xticks(rotation=45)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        else:
            plt.savefig(self.output_dir / 'nav_curve.png', dpi=150, bbox_inches='tight')

        plt.close()
        return fig

    def plot_nav_vs_benchmark(
        self,
        results: Dict,
        title: str = '组合 vs 基准',
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """绘制组合与基准对比图"""
        fig, ax = plt.subplots(figsize=(12, 6))

        nav = results['nav_series']
        benchmark = results['benchmark_nav']

        # 对齐
        common_idx = nav.index.intersection(benchmark.index)
        nav_aligned = nav.loc[common_idx]
        benchmark_aligned = benchmark.loc[common_idx]

        # 相对收益
        relative = nav_aligned / nav_aligned.iloc[0] - benchmark_aligned / benchmark_aligned.iloc[0]

        ax.fill_between(relative.index, 0, relative.values,
                        where=relative >= 0, color='green', alpha=0.3, label='超额')
        ax.fill_between(relative.index, 0, relative.values,
                        where=relative < 0, color='red', alpha=0.3, label='跑输')

        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax.plot(relative.index, relative.values, color='blue', linewidth=1.5)

        excess_return = relative.iloc[-1]
        ax.set_title(f'{title} - 超额收益: {excess_return:.2%}', fontsize=14, fontweight='bold')
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('相对收益', fontsize=12)
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)

        if isinstance(relative.index, pd.DatetimeIndex):
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            plt.xticks(rotation=45)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        else:
            plt.savefig(self.output_dir / 'nav_vs_benchmark.png', dpi=150, bbox_inches='tight')

        plt.close()
        return fig

    def plot_drawdown(
        self,
        results: Dict,
        title: str = '回撤分析',
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """绘制回撤图"""
        fig, axes = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[2, 1])

        nav = results.get('nav_series')
        if nav is None:
            return fig

        # 计算回撤
        cummax = nav.cummax()
        drawdown = (nav - cummax) / cummax

        # 上图：净值
        ax1 = axes[0]
        ax1.plot(nav.index, nav.values, linewidth=2, label='组合净值')
        ax1.plot(cummax.index, cummax.values, linewidth=1, linestyle='--',
                 alpha=0.5, label='净值高点')
        ax1.set_title(title, fontsize=14, fontweight='bold')
        ax1.set_ylabel('净值', fontsize=12)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)

        # 下图：回撤
        ax2 = axes[1]
        ax2.fill_between(drawdown.index, 0, drawdown.values,
                         color='red', alpha=0.5)
        ax2.set_ylabel('回撤', fontsize=12)
        ax2.set_xlabel('日期', fontsize=12)
        ax2.grid(True, alpha=0.3)

        # 标记最大回撤点
        max_dd_idx = drawdown.idxmin()
        ax2.annotate(f"最大回撤: {drawdown.min():.2%}",
                     xy=(max_dd_idx, drawdown.min()),
                     xytext=(max_dd_idx, drawdown.min() - 0.02),
                     fontsize=10,
                     arrowprops=dict(arrowstyle='->', color='black'))

        if isinstance(nav.index, pd.DatetimeIndex):
            for ax in axes:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            plt.xticks(rotation=45)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        else:
            plt.savefig(self.output_dir / 'drawdown.png', dpi=150, bbox_inches='tight')

        plt.close()
        return fig

    def plot_returns_distribution(
        self,
        results: Dict,
        title: str = '收益分布',
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """绘制收益分布图"""
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        daily_returns = results.get('daily_returns')
        if daily_returns is None or len(daily_returns) == 0:
            return fig

        # 左图：直方图
        ax1 = axes[0]
        ax1.hist(daily_returns.values, bins=50, edgecolor='black', alpha=0.7)
        ax1.axvline(x=daily_returns.mean(), color='red', linestyle='--',
                    linewidth=2, label=f'均值: {daily_returns.mean():.2%}')
        ax1.axvline(x=0, color='black', linestyle='-', linewidth=1)
        ax1.set_title(f'{title} - 日收益分布', fontsize=12, fontweight='bold')
        ax1.set_xlabel('日收益率', fontsize=10)
        ax1.set_ylabel('频数', fontsize=10)
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 右图：QQ图（正态性检验）
        ax2 = axes[1]
        from scipy import stats
        stats.probplot(daily_returns.values, dist="norm", plot=ax2)
        ax2.set_title('Q-Q图（正态性检验）', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        else:
            plt.savefig(self.output_dir / 'returns_distribution.png', dpi=150, bbox_inches='tight')

        plt.close()
        return fig

    def plot_monthly_returns(
        self,
        results: Dict,
        title: str = '月度收益',
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """绘制月度收益热力图"""
        nav = results.get('nav_series')
        if nav is None or not isinstance(nav.index, pd.DatetimeIndex):
            return plt.figure()

        # 计算月度收益
        monthly_nav = nav.resample('M').last()
        monthly_returns = monthly_nav.pct_change().dropna() * 100  # 转为百分比

        # 转为年月矩阵
        monthly_returns.index = monthly_returns.index.to_period('M')
        df = monthly_returns.to_frame('return')
        df['year'] = df.index.year
        df['month'] = df.index.month

        pivot = df.pivot(index='year', columns='month', values='return')

        # 绘图
        fig, ax = plt.subplots(figsize=(12, 8))

        sns.heatmap(pivot, annot=True, fmt='.1f', cmap='RdYlGn',
                    center=0, ax=ax, cbar_kws={'label': '收益率(%)'})

        ax.set_title(f'{title}（单位：%）', fontsize=14, fontweight='bold')
        ax.set_xlabel('月份', fontsize=12)
        ax.set_ylabel('年份', fontsize=12)

        # 设置月份标签
        month_names = ['1月', '2月', '3月', '4月', '5月', '6月',
                       '7月', '8月', '9月', '10月', '11月', '12月']
        ax.set_xticklabels(month_names[:len(pivot.columns)], rotation=45)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        else:
            plt.savefig(self.output_dir / 'monthly_returns.png', dpi=150, bbox_inches='tight')

        plt.close()
        return fig

    def plot_ic_analysis(
        self,
        ic_results: Dict,
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """绘制 IC 分析图"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        ic_series = ic_results.get('ic_series')
        if ic_series is None:
            return fig

        # 1. IC 时序图
        ax1 = axes[0, 0]
        ic_series.plot(ax=ax1, kind='line', marker='o', markersize=2)
        ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax1.set_title('IC 时序', fontsize=12, fontweight='bold')
        ax1.set_xlabel('日期')
        ax1.set_ylabel('IC')
        ax1.grid(True, alpha=0.3)

        # 2. IC 分布
        ax2 = axes[0, 1]
        ic_series.hist(bins=30, ax=ax2, edgecolor='black', alpha=0.7)
        ax2.axvline(x=ic_series.mean(), color='red', linestyle='--',
                    linewidth=2, label=f'均值: {ic_series.mean():.4f}')
        ax2.set_title('IC 分布', fontsize=12, fontweight='bold')
        ax2.set_xlabel('IC')
        ax2.set_ylabel('频数')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # 3. IC 累计
        ax3 = axes[1, 0]
        ic_cumsum = ic_series.cumsum()
        ax3.plot(ic_cumsum.index, ic_cumsum.values, linewidth=2)
        ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax3.fill_between(ic_cumsum.index, 0, ic_cumsum.values,
                         where=ic_cumsum >= 0, color='green', alpha=0.3)
        ax3.fill_between(ic_cumsum.index, 0, ic_cumsum.values,
                         where=ic_cumsum < 0, color='red', alpha=0.3)
        ax3.set_title('IC 累计', fontsize=12, fontweight='bold')
        ax3.set_xlabel('日期')
        ax3.set_ylabel('累计 IC')
        ax3.grid(True, alpha=0.3)

        # 4. IC 统计
        ax4 = axes[1, 1]
        ic_stats = ic_results.get('ic_stats')
        if ic_stats is not None:
            stats_df = pd.DataFrame({
                'IC均值': ic_stats['mean_ic'],
                'IC_IR': ic_stats['ir']
            }).sort_values('IC_IR', ascending=True)

            stats_df.plot(kind='barh', ax=ax4)
            ax4.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
            ax4.set_title('因子 IC 统计', fontsize=12, fontweight='bold')
            ax4.set_xlabel('值')
            ax4.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        else:
            plt.savefig(self.output_dir / 'ic_analysis.png', dpi=150, bbox_inches='tight')

        plt.close()
        return fig

    def _generate_summary(
        self,
        metrics: Dict,
        results: Dict,
        save_path: Optional[str] = None
    ) -> str:
        """生成文字摘要"""
        summary_text = f"""
{'='*60}
多因子选股策略 - 绩效报告
{'='*60}

一、收益表现
- 总收益率: {metrics.get('total_return', 0):.2%}
- 年化收益率: {metrics.get('annual_return', 0):.2%}
- 超额收益率: {metrics.get('excess_return', 0):.2%}

二、风险指标
- 年化波动率: {metrics.get('volatility', 0):.2%}
- 最大回撤: {metrics.get('max_drawdown', 0):.2%}
- 下行波动率: {metrics.get('downside_volatility', 0):.2%}
- VaR (95%): {metrics.get('var_95', 0):.2%}

三、风险调整收益
- 夏普比率: {metrics.get('sharpe_ratio', 0):.2f}
- 索提诺比率: {metrics.get('sortino_ratio', 0):.2f}
- Calmar比率: {metrics.get('calmar_ratio', 0):.2f}
- 信息比率: {metrics.get('information_ratio', 0):.2f}

四、交易统计
- 总交易次数: {metrics.get('total_trades', 0)}
- 平均持仓: {metrics.get('avg_positions', 0):.0f} 只

{'='*60}
"""

        # 保存文本报告
        report_path = save_path or str(self.output_dir / 'summary.txt')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(summary_text)

        return report_path


def create_factor_report(factor_data: pd.DataFrame, output_dir: str = './output') -> None:
    """
    创建因子分析报告

    Args:
        factor_data: 因子数据
        output_dir: 输出目录
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 因子相关性矩阵
    if len(factor_data.columns) > 1:
        corr_matrix = factor_data.corr(method='spearman')

        fig, ax = plt.subplots(figsize=(12, 10))
        sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm',
                    center=0, ax=ax, vmin=-1, vmax=1)
        ax.set_title('因子相关性矩阵', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(output_path / 'factor_correlation.png', dpi=150, bbox_inches='tight')
        plt.close()

    logger.info(f"因子报告已生成: {output_path}")
