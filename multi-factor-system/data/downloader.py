"""
数据下载模块
使用 Akshare 获取 A 股市场数据
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from tqdm import tqdm
from loguru import logger

try:
    import akshare as ak
except ImportError:
    logger.warning("akshare 未安装，请运行: pip install akshare")
    ak = None


class DataDownloader:
    """数据下载器"""

    def __init__(self, config):
        self.config = config
        self.cache_dir = config.get("data_source.cache_dir", "./data/cache")
        self.provider = config.get("data_source.provider", "akshare")

    def get_stock_list(self) -> pd.DataFrame:
        """
        获取A股股票列表

        Returns:
            股票列表 DataFrame，包含 code, name, industry 等字段
        """
        logger.info("获取A股股票列表...")

        try:
            # 获取A股所有股票
            stock_info = ak.stock_info_a_code_name()

            # 重命名列
            stock_info.columns = ['code', 'name']

            # 获取股票详细信息（行业、市值等）
            stock_individual = ak.stock_info_sh_name_code(symbol="主板A股")
            stock_individual.columns = ['code', 'name', 'listing_date']

            # 合并数据
            stock_list = pd.concat([stock_individual], ignore_index=True)
            stock_list['code'] = stock_list['code'].astype(str).str.zfill(6)

            # 标记交易所
            stock_list['exchange'] = stock_list['code'].apply(
                lambda x: 'SH' if x.startswith(('6', '9')) else 'SZ'
            )

            logger.info(f"获取到 {len(stock_list)} 只股票")
            return stock_list

        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return pd.DataFrame()

    def get_index_components(self, index_code: str = "000300.SH") -> List[str]:
        """
        获取指数成分股

        Args:
            index_code: 指数代码，000300.SH=沪深300, 000905.SH=中证500

        Returns:
            成分股代码列表
        """
        logger.info(f"获取指数 {index_code} 成分股...")

        try:
            if index_code == "000300.SH":
                # 沪深300
                df = ak.index_stock_cons_sina(symbol="sh000300")
            elif index_code == "000905.SH":
                # 中证500
                df = ak.index_stock_cons_sina(symbol="sh000905")
            else:
                logger.warning(f"不支持的指数代码: {index_code}")
                return []

            components = df['品种代码'].tolist()
            logger.info(f"获取到 {len(components)} 只成分股")
            return components

        except Exception as e:
            logger.error(f"获取指数成分失败: {e}")
            return []

    def get_daily_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        获取单只股票的日线数据

        Args:
            symbol: 股票代码，如 '000001.SZ'
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD

        Returns:
            日线数据 DataFrame
        """
        try:
            # 转换代码格式
            if '.' not in symbol:
                code = symbol.zfill(6)
                symbol = f"{code}.SH" if code.startswith(('6', '9')) else f"{code}.SZ"

            # 获取历史数据
            df = ak.stock_zh_a_hist(
                symbol=symbol.split('.')[0],
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )

            if df.empty:
                return df

            # 重命名列
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '涨跌幅': 'pct_change',
                '换手率': 'turnover_rate'
            })

            # 添加股票代码
            df['code'] = symbol

            # 转换日期格式
            df['date'] = pd.to_datetime(df['date'])

            return df

        except Exception as e:
            logger.debug(f"获取 {symbol} 数据失败: {e}")
            return pd.DataFrame()

    def get_bulk_daily_data(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        批量获取多只股票的日线数据

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            use_cache: 是否使用缓存

        Returns:
            合并后的日线数据
        """
        all_data = []

        logger.info(f"开始下载 {len(symbols)} 只股票的数据...")
        logger.info(f"时间范围: {start_date} 至 {end_date}")

        for symbol in tqdm(symbols, desc="下载数据"):
            df = self.get_daily_data(symbol, start_date, end_date)
            if not df.empty:
                all_data.append(df)

        if not all_data:
            logger.warning("未获取到任何数据")
            return pd.DataFrame()

        # 合并数据
        combined = pd.concat(all_data, ignore_index=True)
        combined = combined.sort_values(['code', 'date'])

        logger.info(f"数据下载完成，共 {len(combined)} 条记录")
        return combined

    def get_stock_data(self) -> pd.DataFrame:
        """
        获取完整的股票数据（主入口方法）

        Returns:
            包含行情数据的 DataFrame
        """
        # 从配置获取参数
        stock_pool = self.config.get("market.stock_pool", "hs300")
        start_date = self.config.get("backtest.start_date", "20180101")
        end_date = self.config.get("backtest.end_date", "20231231")

        # 获取股票列表
        if stock_pool == "hs300":
            symbols = self.get_index_components("000300.SH")
        elif stock_pool == "zz500":
            symbols = self.get_index_components("000905.SH")
        else:
            # 全A股，取部分代表性股票用于演示
            stock_list = self.get_stock_list()
            # 取沪深300成分或前500只
            if len(stock_list) > 300:
                symbols = stock_list.head(300)['code'].tolist()
            else:
                symbols = stock_list['code'].tolist()

        if not symbols:
            logger.warning("未获取到股票列表，使用默认样本")
            # 使用一些常见股票作为示例
            symbols = [f"{str(i).zfill(6)}" for i in [1, 600000, 600016, 600019, 600028,
                                                        600030, 600031, 600036, 600050, 600104]]

        # 限制数量以加快演示
        symbols = symbols[:100] if len(symbols) > 100 else symbols

        return self.get_bulk_daily_data(symbols, start_date, end_date)

    def get_financial_data(
        self,
        symbol: str,
        start_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取财务报表数据

        Args:
            symbol: 股票代码
            start_date: 开始日期

        Returns:
            财务数据 DataFrame
        """
        try:
            code = symbol.split('.')[0] if '.' in symbol else symbol.zfill(6)

            # 获取财务指标
            df = ak.stock_financial_analysis_indicator(
                symbol=code,
                start_year=start_date[:4] if start_date else None
            )

            if df is not None and not df.empty:
                return df

            return pd.DataFrame()

        except Exception as e:
            logger.debug(f"获取 {symbol} 财务数据失败: {e}")
            return pd.DataFrame()

    def get_market_capitalization(self, symbol: str) -> Optional[float]:
        """
        获取最新市值

        Args:
            symbol: 股票代码

        Returns:
            总市值（元）
        """
        try:
            code = symbol.split('.')[0] if '.' in symbol else symbol.zfill(6)
            df = ak.stock_a_lg_indicator(symbol=code)

            if df is not None and not df.empty:
                return df.iloc[0].get('总市值')

            return None

        except Exception as e:
            logger.debug(f"获取 {symbol} 市值失败: {e}")
            return None
