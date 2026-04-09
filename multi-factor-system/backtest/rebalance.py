"""
调仓逻辑模块
管理调仓时机和执行
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
from loguru import logger


class Rebalance:
    """调仓管理器"""

    def __init__(self, config):
        self.config = config
        self.rebalance_freq = config.get("backtest.rebalance_freq", "monthly")
        self.top_n = config.get("portfolio.top_n", 50)

        # 调仓触发条件
        self.rebalance_triggers = []

    def should_rebalance(
        self,
        date: pd.Timestamp,
        last_rebalance_date: Optional[pd.Timestamp],
        conditions: Optional[Dict] = None
    ) -> bool:
        """
        判断是否需要调仓

        Args:
            date: 当前日期
            last_rebalance_date: 上次调仓日期
            conditions: 额外的调仓条件

        Returns:
            是否需要调仓
        """
        # 基础条件：时间频率
        if last_rebalance_date is None:
            return True

        freq_condition = self._check_frequency(date, last_rebalance_date)
        if not freq_condition:
            return False

        # 检查额外条件
        if conditions:
            for check_func in self.rebalance_triggers:
                if not check_func(date, conditions):
                    return False

        return True

    def _check_frequency(
        self,
        date: pd.Timestamp,
        last_date: pd.Timestamp
    ) -> bool:
        """检查调仓频率条件"""
        if self.rebalance_freq == 'daily':
            return True

        elif self.rebalance_freq == 'weekly':
            # 每周一
            return date.dayofweek == 0

        elif self.rebalance_freq == 'monthly':
            # 每月第一个交易日
            return date.day <= 5

        elif self.rebalance_freq == 'quarterly':
            # 每季度末月
            return date.month in [3, 6, 9, 12] and date.day <= 5

        return False

    def add_trigger(self, trigger_func: Callable):
        """添加调仓触发条件"""
        self.rebalance_triggers.append(trigger_func)


class ThresholdRebalance(Rebalance):
    """阈值触发调仓"""

    def __init__(self, config, turnover_threshold: float = 0.3):
        super().__init__(config)
        self.turnover_threshold = turnover_threshold

    def should_rebalance(
        self,
        date: pd.Timestamp,
        last_rebalance_date: Optional[pd.Timestamp],
        current_positions: Dict[str, float],
        target_positions: Dict[str, float]
    ) -> bool:
        """
        根据换手率阈值判断是否调仓

        Args:
            current_positions: 当前持仓
            target_positions: 目标持仓

        Returns:
            是否需要调仓
        """
        # 首先检查频率
        if not super().should_rebalance(date, last_rebalance_date):
            return False

        # 计算预期换手率
        turnover = self._calculate_turnover(current_positions, target_positions)

        # 超过阈值才调仓
        return turnover >= self.turnover_threshold

    def _calculate_turnover(
        self,
        current: Dict[str, float],
        target: Dict[str, float]
    ) -> float:
        """计算换手率"""
        all_codes = set(current.keys()) | set(target.keys())

        turnover = 0
        for code in all_codes:
            curr_w = current.get(code, 0)
            targ_w = target.get(code, 0)
            turnover += abs(targ_w - curr_w)

        return turnover / 2  # 单边换手率


class SignalRebalance(Rebalance):
    """信号触发调仓"""

    def __init__(self, config, signals: pd.DataFrame = None):
        super().__init__(config)
        self.signals = signals

    def should_rebalance(
        self,
        date: pd.Timestamp,
        last_rebalance_date: Optional[pd.Timestamp],
        signal: Optional[float] = None
    ) -> bool:
        """
        根据信号判断是否调仓

        Args:
            date: 当前日期
            last_rebalance_date: 上次调仓日期
            signal: 当日信号值（如动量方向）

        Returns:
            是否需要调仓
        """
        # 基础频率检查
        if not super().should_rebalance(date, last_rebalance_date):
            return False

        # 信号检查（信号由外部传入）
        if signal is not None:
            # 信号阈值
            return abs(signal) > 0.5

        return True


class ScheduledRebalance(Rebalance):
    """固定日期调仓"""

    def __init__(self, config, rebalance_dates: List[str]):
        super().__init__(config)
        self.rebalance_dates = [
            pd.to_datetime(d) for d in rebalance_dates
        ]

    def should_rebalance(
        self,
        date: pd.Timestamp,
        last_rebalance_date: Optional[pd.Timestamp] = None,
        **kwargs
    ) -> bool:
        """检查是否是预定的调仓日期"""
        return date in self.rebalance_dates


class AdaptiveRebalance(Rebalance):
    """自适应调仓"""

    def __init__(
        self,
        config,
        base_freq: str = 'monthly',
        volatility_threshold: float = 0.02
    ):
        super().__init__(config)
        self.base_freq = base_freq
        self.volatility_threshold = volatility_threshold

    def should_rebalance(
        self,
        date: pd.Timestamp,
        last_rebalance_date: Optional[pd.Timestamp],
        recent_returns: pd.Series
    ) -> bool:
        """
        根据市场波动率自适应调仓

        Args:
            recent_returns: 近期收益率序列

        Returns:
            是否需要调仓
        """
        # 基础频率检查
        if not super().should_rebalance(date, last_rebalance_date):
            return False

        # 检查波动率
        if len(recent_returns) > 0:
            vol = recent_returns.std() * np.sqrt(252)

            # 高波动时更频繁调仓
            if vol > self.volatility_threshold:
                return True

        return False


def create_rebalancer(config, rebalancer_type: str = "default", **kwargs) -> Rebalance:
    """
    工厂函数：创建调仓器

    Args:
        config: 配置对象
        rebalancer_type: 调仓器类型
            - "default": 基础调仓
            - "threshold": 阈值触发
            - "signal": 信号触发
            - "scheduled": 固定日期
            - "adaptive": 自适应

    Returns:
        调仓器实例
    """
    if rebalancer_type == "default":
        return Rebalance(config)

    elif rebalancer_type == "threshold":
        threshold = kwargs.get("turnover_threshold", 0.3)
        return ThresholdRebalance(config, threshold)

    elif rebalancer_type == "signal":
        signals = kwargs.get("signals")
        return SignalRebalance(config, signals)

    elif rebalancer_type == "scheduled":
        dates = kwargs.get("rebalance_dates", [])
        return ScheduledRebalance(config, dates)

    elif rebalancer_type == "adaptive":
        base_freq = kwargs.get("base_freq", "monthly")
        vol_threshold = kwargs.get("volatility_threshold", 0.02)
        return AdaptiveRebalance(config, base_freq, vol_threshold)

    else:
        logger.warning(f"未知的调仓器类型: {rebalancer_type}，使用默认调仓器")
        return Rebalance(config)
