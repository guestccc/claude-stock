"""
数据处理模块
数据清洗、缺失值处理、停牌处理等
"""
import pandas as pd
import numpy as np
from typing import Optional, Tuple
from loguru import logger


class DataProcessor:
    """数据处理器"""

    def __init__(self, config):
        self.config = config
        self.exclude_st = config.get("market.exclude_st", True)
        self.exclude_new_stock = config.get("market.exclude_new_stock", True)
        self.min_market_cap = config.get("market.min_market_cap", 0)

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理原始数据

        Args:
            df: 原始行情数据

        Returns:
            处理后的数据
        """
        if df.empty:
            logger.warning("输入数据为空")
            return df

        logger.info(f"开始处理 {len(df)} 条数据...")

        # 1. 基本清洗
        df = self._basic_cleaning(df)

        # 2. 处理停牌
        df = self._handle_suspensions(df)

        # 3. 计算收益率
        df = self._calculate_returns(df)

        # 4. 处理ST股票
        if self.exclude_st:
            df = self._exclude_st_stocks(df)

        # 5. 处理新股
        if self.exclude_new_stock:
            df = self._exclude_new_stocks(df)

        logger.info(f"数据处理完成，剩余 {df['code'].nunique()} 只股票，{len(df)} 条记录")

        return df

    def _basic_cleaning(self, df: pd.DataFrame) -> pd.DataFrame:
        """基本清洗"""
        # 删除重复记录
        before = len(df)
        df = df.drop_duplicates(subset=['code', 'date'], keep='last')
        after = len(df)

        if before > after:
            logger.info(f"删除 {before - after} 条重复记录")

        # 删除缺失值
        essential_cols = ['code', 'date', 'close']
        df = df.dropna(subset=essential_cols)

        # 确保日期格式
        if not pd.api.types.is_datetime64_any_dtype(df['date']):
            df['date'] = pd.to_datetime(df['date'])

        # 按日期和股票排序
        df = df.sort_values(['date', 'code']).reset_index(drop=True)

        return df

    def _handle_suspensions(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理停牌股票"""
        # 计算成交量为0的记录（可能是停牌）
        # 注意：停牌时前复权价格可能保持不变

        # 标记停牌
        df['suspended'] = (df['volume'] == 0).astype(int)

        # 对于停牌日，填充价格（前一天收盘价）
        df = df.sort_values(['code', 'date'])

        for code in df['code'].unique():
            mask = df['code'] == code
            price_cols = ['open', 'high', 'low', 'close']

            for col in price_cols:
                # 前向填充
                df.loc[mask, col] = df.loc[mask, col].ffill()

                # 如果还有NaN（停牌前的数据），用后向填充
                df.loc[mask, col] = df.loc[mask, col].bfill()

        return df

    def _calculate_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算收益率"""
        df = df.sort_values(['code', 'date'])

        # 日收益率（已在原始数据中包含 pct_change）
        if 'pct_change' not in df.columns or df['pct_change'].isna().all():
            df['daily_return'] = df.groupby('code')['close'].pct_change()
        else:
            df['daily_return'] = df['pct_change'] / 100  # 转换为小数

        # 计算累计收益率
        df['cumulative_return'] = df.groupby('code')['daily_return'].apply(
            lambda x: (1 + x).cumprod() - 1
        ).reset_index(level=0, drop=True)

        return df

    def _exclude_st_stocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """排除ST股票"""
        # 注意：这里需要股票名称数据
        # 如果没有名称数据，暂时跳过
        if 'name' not in df.columns:
            logger.debug("缺少股票名称，跳过ST过滤")
            return df

        before = df['code'].nunique()
        df = df[~df['name'].str.contains('ST|退', na=False, case=False)]
        after = df['code'].nunique()

        logger.info(f"排除ST股票，剩余 {after} 只（排除 {before - after} 只）")

        return df

    def _exclude_new_stocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """排除新股（上市不满一年）"""
        # 计算每只股票的最早日期
        listing_dates = df.groupby('code')['date'].min()

        # 假设数据起始日期为一年前
        min_date = df['date'].min()
        cutoff_date = min_date + pd.DateOffset(months=12)

        # 过滤上市不满一年的股票
        old_stocks = listing_dates[listing_dates <= cutoff_date].index.tolist()

        before = df['code'].nunique()
        df = df[df['code'].isin(old_stocks)]
        after = df['code'].nunique()

        logger.info(f"排除次新股，剩余 {after} 只（排除 {before - after} 只）")

        return df

    def fill_missing_values(
        self,
        df: pd.DataFrame,
        method: str = 'ffill'
    ) -> pd.DataFrame:
        """
        填充缺失值

        Args:
            df: 输入数据
            method: 填充方法，'ffill'前向填充，'bfill'后向填充，'interpolate'插值

        Returns:
            填充后的数据
        """
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        if method == 'ffill':
            df[numeric_cols] = df.groupby('code')[numeric_cols].ffill()
        elif method == 'bfill':
            df[numeric_cols] = df.groupby('code')[numeric_cols].bfill()
        elif method == 'interpolate':
            df[numeric_cols] = df.groupby('code')[numeric_cols].transform(
                lambda x: x.interpolate(method='linear')
            )

        return df

    def align_data_frequency(
        self,
        df: pd.DataFrame,
        freq: str = 'D'
    ) -> pd.DataFrame:
        """
        对齐数据频率

        Args:
            df: 输入数据
            freq: 目标频率，'D'=日，'W'=周，'M'=月

        Returns:
            对齐后的数据
        """
        if freq == 'D':
            return df

        # 按频率重采样
        if freq == 'W':
            df['date'] = df['date'] - pd.to_timedelta(df['date'].dt.dayofweek, unit='d')
        elif freq == 'M':
            df['date'] = df['date'].dt.to_period('M').dt.to_timestamp()

        # 取每期最后一条记录
        agg_dict = {
            'open': 'last',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'amount': 'sum'
        }

        df = df.groupby(['code', 'date']).agg(agg_dict).reset_index()

        return df

    def get_trading_dates(
        self,
        df: pd.DataFrame,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DatetimeIndex:
        """
        获取交易日列表

        Args:
            df: 行情数据
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            交易日索引
        """
        dates = df['date'].unique()

        if start_date:
            dates = dates[dates >= pd.to_datetime(start_date)]
        if end_date:
            dates = dates[dates <= pd.to_datetime(end_date)]

        return pd.DatetimeIndex(sorted(dates))

    def calculate_trade_stats(self, df: pd.DataFrame) -> dict:
        """
        计算交易统计

        Args:
            df: 行情数据

        Returns:
            统计字典
        """
        stats = {
            'total_records': len(df),
            'total_stocks': df['code'].nunique(),
            'date_range': (df['date'].min(), df['date'].max()),
            'trading_days': df['date'].nunique(),
            'avg_daily_return': df['daily_return'].mean(),
            'return_std': df['daily_return'].std(),
            'suspension_ratio': df['suspended'].mean() if 'suspended' in df.columns else 0
        }

        return stats
