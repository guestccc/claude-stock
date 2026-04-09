"""
回测引擎
事件驱动回测框架
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from tqdm import tqdm
from loguru import logger

from .portfolio import PortfolioBuilder
from .rebalance import Rebalance


class BacktestEngine:
    """回测引擎"""

    def __init__(self, config, portfolio_builder: PortfolioBuilder = None):
        self.config = config

        # 回测参数
        self.start_date = config.get("backtest.start_date", "20180101")
        self.end_date = config.get("backtest.end_date", "20231231")
        self.commission_rate = config.get("backtest.commission_rate", 0.0003)
        self.stamp_tax = config.get("backtest.stamp_tax", 0.001)
        self.slippage = config.get("backtest.slippage", 0.001)

        # 调仓频率
        self.rebalance_freq = config.get("backtest.rebalance_freq", "monthly")

        # 组合构建器
        self.portfolio_builder = portfolio_builder or PortfolioBuilder(config)

        # 回测结果
        self.results = {}

    def run(
        self,
        factors: pd.DataFrame,
        price_data: pd.DataFrame,
        benchmark: Optional[pd.Series] = None
    ) -> Dict[str, Any]:
        """
        运行回测

        Args:
            factors: 因子数据，index=(date, code)
            price_data: 价格数据
            benchmark: 基准收益率序列

        Returns:
            回测结果字典
        """
        logger.info("=" * 60)
        logger.info("开始回测")
        logger.info(f"时间范围: {self.start_date} 至 {self.end_date}")
        logger.info(f"调仓频率: {self.rebalance_freq}")
        logger.info("=" * 60)

        # 预处理数据
        price_data = self._prepare_price_data(price_data)

        # 获取调仓日期
        rebalance_dates = self._get_rebalance_dates(factors)

        if len(rebalance_dates) == 0:
            logger.warning("没有调仓日期")
            return {}

        # 初始化变量
        current_positions = {}  # 当前持仓 {code: weight}
        portfolio_value = 1.0  # 初始组合价值
        history = []  # 交易历史

        # 记录每日净值
        daily_nav = []

        # 按调仓日期迭代
        for i, rebalance_date in enumerate(tqdm(rebalance_dates, desc="回测进度")):
            try:
                # 1. 获取目标持仓
                target_weights = self.portfolio_builder.build_portfolio(
                    factors.loc[:rebalance_date],
                    date=rebalance_date
                )

                if target_weights.empty:
                    continue

                # 2. 执行调仓
                trades, current_positions = self._execute_rebalance(
                    current_positions,
                    target_weights,
                    price_data,
                    rebalance_date
                )

                # 记录交易
                history.extend(trades)

                # 3. 持有期间计算收益
                next_date_idx = rebalance_dates.index(rebalance_date) + 1
                if next_date_idx < len(rebalance_dates):
                    next_rebalance = rebalance_dates[next_date_idx]
                else:
                    # 最后一次调仓后，持有到期末
                    next_rebalance = pd.to_datetime(self.end_date)

                # 计算持有期间收益
                period_returns = self._calculate_holding_returns(
                    current_positions,
                    price_data,
                    rebalance_date,
                    next_rebalance
                )

                # 更新组合价值
                period_return = sum(
                    w * r for w, r in zip(current_positions.values(), period_returns)
                )

                # 扣除交易成本
                trade_cost = self._calculate_trade_cost(trades, price_data, rebalance_date)
                portfolio_value *= (1 - trade_cost) * (1 + period_return)

                # 记录每日净值
                daily_nav.append({
                    'date': rebalance_date,
                    'nav': portfolio_value,
                    'positions': len(current_positions)
                })

            except Exception as e:
                logger.error(f"调仓日 {rebalance_date} 出错: {e}")
                continue

        # 汇总结果
        self.results = self._summarize_results(daily_nav, history, benchmark)

        logger.info("回测完成")
        logger.info(f"最终净值: {self.results.get('final_nav', 1):.4f}")
        logger.info(f"年化收益: {self.results.get('annual_return', 0):.2%}")
        logger.info(f"最大回撤: {self.results.get('max_drawdown', 0):.2%}")

        return self.results

    def _prepare_price_data(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """预处理价格数据"""
        if 'date' not in price_data.columns and price_data.index.names[0] == 'date':
            price_data = price_data.reset_index()

        # 确保日期格式
        if 'date' in price_data.columns:
            price_data['date'] = pd.to_datetime(price_data['date'])

        return price_data.sort_values(['date', 'code'])

    def _get_rebalance_dates(self, factors: pd.DataFrame) -> List[pd.Timestamp]:
        """获取调仓日期"""
        if factors.index.nlevels > 1:
            all_dates = sorted(factors.index.get_level_values(0).unique())
        else:
            return []

        # 按频率筛选
        dates = []

        for date in all_dates:
            if pd.to_datetime(date) < pd.to_datetime(self.start_date):
                continue
            if pd.to_datetime(date) > pd.to_datetime(self.end_date):
                break

            if self.rebalance_freq == 'monthly':
                # 每月第一个交易日
                if len(dates) == 0 or date.month != dates[-1].month:
                    dates.append(date)
            elif self.rebalance_freq == 'weekly':
                # 每周第一个交易日
                if len(dates) == 0 or date.week != dates[-1].week:
                    dates.append(date)
            elif self.rebalance_freq == 'daily':
                dates.append(date)

        return dates

    def _execute_rebalance(
        self,
        current_positions: Dict[str, float],
        target_weights: Dict[str, float],
        price_data: pd.DataFrame,
        date: pd.Timestamp
    ) -> Tuple[List[Dict], Dict[str, float]]:
        """
        执行调仓

        Returns:
            (交易列表, 新持仓)
        """
        trades = []

        # 计算权重差异
        weight_diff = {}
        for code, target_w in target_weights.items():
            current_w = current_positions.get(code, 0)
            diff = target_w - current_w
            weight_diff[code] = diff

        # 卖出
        for code, diff in weight_diff.items():
            if diff < -0.001:  # 卖出
                trades.append({
                    'date': date,
                    'code': code,
                    'action': 'sell',
                    'weight': abs(diff),
                    'price': self._get_price(price_data, code, date)
                })

        # 买入
        for code, diff in weight_diff.items():
            if diff > 0.001:  # 买入
                trades.append({
                    'date': date,
                    'code': code,
                    'action': 'buy',
                    'weight': diff,
                    'price': self._get_price(price_data, code, date)
                })

        return trades, target_weights

    def _get_price(
        self,
        price_data: pd.DataFrame,
        code: str,
        date: pd.Timestamp
    ) -> float:
        """获取价格"""
        try:
            if 'code' in price_data.columns:
                mask = (price_data['code'] == code) & (price_data['date'] == date)
                price = price_data.loc[mask, 'close'].values[0]
            else:
                price = price_data.loc[(date, code), 'close']

            # 加入滑点
            return price * (1 + self.slippage)
        except Exception:
            return np.nan

    def _calculate_holding_returns(
        self,
        positions: Dict[str, float],
        price_data: pd.DataFrame,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp
    ) -> List[float]:
        """计算持有期收益"""
        returns = []

        # 获取期间交易日
        if 'date' in price_data.columns:
            trading_days = price_data[
                (price_data['date'] > start_date) &
                (price_data['date'] <= end_date)
            ]['date'].unique()
        else:
            trading_days = price_data.loc[
                (price_data.index.get_level_values(0) > start_date) &
                (price_data.index.get_level_values(0) <= end_date)
            ].index.get_level_values(0).unique()

        trading_days = sorted(trading_days)

        # 累计收益
        cumulative_return = 0

        for code in positions.keys():
            try:
                start_price = self._get_price(price_data, code, start_date)
                end_price = self._get_price(price_data, code, end_date)

                if pd.notna(start_price) and pd.notna(end_price) and start_price > 0:
                    ret = (end_price - start_price) / start_price
                    returns.append(ret)
                else:
                    returns.append(0)

            except Exception:
                returns.append(0)

        return returns

    def _calculate_trade_cost(
        self,
        trades: List[Dict],
        price_data: pd.DataFrame,
        date: pd.Timestamp
    ) -> float:
        """计算交易成本"""
        total_cost = 0

        for trade in trades:
            weight = trade['weight']
            price = trade['price']

            # 佣金
            commission = weight * self.commission_rate
            total_cost += commission

            # 印花税（仅卖出）
            if trade['action'] == 'sell':
                total_cost += weight * self.stamp_tax

        return total_cost

    def _summarize_results(
        self,
        daily_nav: List[Dict],
        history: List[Dict],
        benchmark: Optional[pd.Series]
    ) -> Dict[str, Any]:
        """汇总回测结果"""
        if not daily_nav:
            return {}

        nav_df = pd.DataFrame(daily_nav)
        nav_df['date'] = pd.to_datetime(nav_df['date'])
        nav_df = nav_df.set_index('date')

        # 基本收益
        final_nav = nav_df['nav'].iloc[-1]
        total_return = final_nav - 1

        # 年化收益
        n_days = len(nav_df)
        n_years = n_days / 252
        annual_return = (final_nav ** (1 / n_years) - 1) if n_years > 0 else 0

        # 最大回撤
        cummax = nav_df['nav'].cummax()
        drawdown = (nav_df['nav'] - cummax) / cummax
        max_drawdown = drawdown.min()

        # 波动率
        daily_returns = nav_df['nav'].pct_change().dropna()
        volatility = daily_returns.std() * np.sqrt(252)

        # 夏普比率（假设无风险利率 3%）
        risk_free_rate = 0.03
        sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0

        results = {
            'nav_series': nav_df['nav'],
            'daily_returns': daily_returns,
            'final_nav': final_nav,
            'total_return': total_return,
            'annual_return': annual_return,
            'volatility': volatility,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'trades': pd.DataFrame(history),
            'n_trades': len(history),
            'avg_positions': nav_df['positions'].mean()
        }

        # 基准对比
        if benchmark is not None:
            benchmark_nav = (1 + benchmark).cumprod()
            results['benchmark_nav'] = benchmark_nav
            results['excess_return'] = annual_return - benchmark_nav.iloc[-1]

        return results


class EventDrivenBacktester(BacktestEngine):
    """事件驱动回测器（更灵活但更慢）"""

    def run(
        self,
        factors: pd.DataFrame,
        price_data: pd.DataFrame,
        benchmark: Optional[pd.Series] = None
    ) -> Dict[str, Any]:
        """
        运行事件驱动回测

        每个交易日都会：
        1. 检查是否需要调仓
        2. 更新持仓收益
        3. 执行交易
        """
        logger.info("使用事件驱动回测")

        # 预处理
        price_data = self._prepare_price_data(price_data)

        # 获取所有交易日
        if 'date' in price_data.columns:
            trading_days = sorted(price_data['date'].unique())
        else:
            trading_days = sorted(price_data.index.get_level_values(0).unique())

        # 过滤日期范围
        trading_days = [
            d for d in trading_days
            if pd.to_datetime(d) >= pd.to_datetime(self.start_date)
            and pd.to_datetime(d) <= pd.to_datetime(self.end_date)
        ]

        # 初始化
        current_positions = {}
        portfolio_value = 1.0
        history = []
        daily_nav = []

        # 获取调仓日期
        rebalance_dates = set(self._get_rebalance_dates(factors))

        for date in tqdm(trading_days, desc="事件驱动回测"):
            # 1. 检查是否调仓日
            if date in rebalance_dates:
                # 获取目标持仓
                target_weights = self.portfolio_builder.build_portfolio(
                    factors.loc[:date],
                    date=date
                )

                if not target_weights.empty:
                    # 执行调仓
                    trades, current_positions = self._execute_rebalance(
                        current_positions,
                        target_weights,
                        price_data,
                        date
                    )
                    history.extend(trades)

            # 2. 计算当日收益
            daily_return = 0
            for code, weight in current_positions.items():
                try:
                    price = self._get_price(price_data, code, date)
                    # 需要前一日价格
                    prev_date_idx = trading_days.index(date) - 1
                    if prev_date_idx >= 0:
                        prev_price = self._get_price(price_data, code, trading_days[prev_date_idx])
                        if pd.notna(price) and pd.notna(prev_price) and prev_price > 0:
                            ret = (price - prev_price) / prev_price
                            daily_return += weight * ret
                except Exception:
                    pass

            # 扣除交易成本（简化处理）
            portfolio_value *= (1 + daily_return)

            # 记录净值
            daily_nav.append({
                'date': date,
                'nav': portfolio_value,
                'positions': len(current_positions)
            })

        # 汇总
        return self._summarize_results(daily_nav, history, benchmark)
