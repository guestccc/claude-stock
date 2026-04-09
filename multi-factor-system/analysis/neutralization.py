"""
因子中性化模块
行业中性化、市值中性化
"""
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from typing import Optional, Dict
from loguru import logger


class Neutralizer:
    """因子中性化处理器"""

    def __init__(self, config):
        self.config = config
        self.neutralize_industry = config.get("factors.neutralize_industry", True)
        self.neutralize_size = config.get("factors.neutralize_size", True)

    def neutralize(
        self,
        factors: pd.DataFrame,
        industry: Optional[pd.Series] = None,
        market_cap: Optional[pd.Series] = None
    ) -> pd.DataFrame:
        """
        对因子进行中性化处理

        Args:
            factors: 因子数据，index=(date, code), columns=因子名
            industry: 行业分类，index=(date, code)
            market_cap: 市值数据，index=(date, code)

        Returns:
            中性化后的因子
        """
        if factors.empty:
            return factors

        logger.info("开始因子中性化...")

        neutralized = factors.copy()

        # 对每个因子分别中性化
        for factor_name in factors.columns:
            try:
                neutralized[factor_name] = self._neutralize_single(
                    factors[factor_name],
                    industry,
                    market_cap
                )
            except Exception as e:
                logger.warning(f"因子 {factor_name} 中性化失败: {e}")
                neutralized[factor_name] = factors[factor_name]

        logger.info("中性化完成")
        return neutralized

    def _neutralize_single(
        self,
        factor: pd.Series,
        industry: Optional[pd.Series],
        market_cap: Optional[pd.Series]
    ) -> pd.Series:
        """
        对单个因子进行中性化

        回归因子对市值（和行业哑变量）的残差作为中性化后的因子
        """
        # 获取日期列表
        if factor.index.nlevels > 1:
            dates = factor.index.get_level_values(0).unique()
        else:
            return factor

        neutralized_values = []

        for date in dates:
            try:
                # 获取当日数据
                mask = factor.index.get_level_values(0) == date
                f = factor.loc[mask].values.reshape(-1, 1)
                codes = factor.loc[mask].index

                if len(f) < 20:
                    neutralized_values.extend(f.flatten())
                    continue

                # 准备回归变量
                X_list = []

                # 市值（对数市值）
                if market_cap is not None:
                    try:
                        mc = market_cap.loc[mask].values.reshape(-1, 1)
                        mc = np.log(mc + 1)  # 对数化
                        X_list.append(mc)
                    except Exception:
                        pass

                # 行业哑变量
                if industry is not None:
                    try:
                        ind = industry.loc[mask].values
                        ind_dummies = pd.get_dummies(ind, prefix='ind', drop_first=True)
                        X_list.append(ind_dummies.values)
                    except Exception:
                        pass

                if not X_list:
                    # 无控制变量，直接返回
                    neutralized_values.extend(f.flatten())
                    continue

                # 合并控制变量
                X = np.hstack(X_list)

                # 删除 NaN
                valid_mask = ~(np.isnan(f).flatten() | np.isnan(X).any(axis=1))
                if valid_mask.sum() < 20:
                    neutralized_values.extend(f.flatten())
                    continue

                # 回归
                f_valid = f[valid_mask]
                X_valid = X[valid_mask]

                try:
                    model = LinearRegression()
                    model.fit(X_valid, f_valid)

                    # 预测
                    f_pred = model.predict(X)

                    # 残差
                    residual = f - f_pred.flatten()

                    neutralized_values.extend(residual)

                except Exception:
                    neutralized_values.extend(f.flatten())

            except Exception as e:
                # 出错时返回原始值
                try:
                    neutralized_values.extend(factor.loc[mask].values)
                except Exception:
                    continue

        result = pd.Series(neutralized_values, index=factor.index)
        return result

    def neutralize_industry(
        self,
        factor: pd.Series,
        industry: pd.Series
    ) -> pd.Series:
        """
        仅进行行业中性化

        Args:
            factor: 因子值
            industry: 行业分类

        Returns:
            中性化后的因子
        """
        return self.neutralize(factor, industry=industry)

    def neutralize_market_cap(
        self,
        factor: pd.Series,
        market_cap: pd.Series
    ) -> pd.Series:
        """
        仅进行市值中性化

        Args:
            factor: 因子值
            market_cap: 市值

        Returns:
            中性化后的因子
        """
        return self.neutralize(factor, market_cap=market_cap)

    def neutralize_both(
        self,
        factor: pd.Series,
        industry: pd.Series,
        market_cap: pd.Series
    ) -> pd.Series:
        """
        同时进行行业和市值中性化

        Args:
            factor: 因子值
            industry: 行业分类
            market_cap: 市值

        Returns:
            中性化后的因子
        """
        return self.neutralize(factor, industry, market_cap)

    def get_industry_dummies(
        self,
        industry: pd.Series,
        drop_first: bool = True
    ) -> pd.DataFrame:
        """
        获取行业哑变量

        Args:
            industry: 行业分类
            drop_first: 是否删除第一个类别避免多重共线性

        Returns:
            行业哑变量 DataFrame
        """
        dummies = pd.get_dummies(industry, prefix='industry', drop_first=drop_first)
        return dummies


class SWIndustryClassifier:
    """申万行业分类器（简化版）"""

    # 简化版申万一级行业映射
    INDUSTRY_MAP = {
        'bank': '银行',
        'securities': '非银金融',
        'insurance': '保险',
        'real_estate': '房地产',
        'construction': '建筑装饰',
        'steel': '钢铁',
        'nonferrous': '有色金属',
        'chemical': '化工',
        'oil': '石油石化',
        'coal': '煤炭',
        'power': '电力设备',
        'machinery': '机械设备',
        'automobile': '汽车',
        'household': '家用电器',
        'food': '食品饮料',
        'textile': '纺织服装',
        'pharma': '医药生物',
        'electronics': '电子',
        'computer': '计算机',
        'media': '传媒',
        'communication': '通信',
        'transport': '交通运输',
        'retail': '商业贸易',
        'agriculture': '农林牧渔',
        'environmental': '环保',
        'defense': '国防军工',
        'other': '其他'
    }

    @classmethod
    def get_industry_code(cls, industry_name: str) -> str:
        """获取行业代码"""
        for code, name in cls.INDUSTRY_MAP.items():
            if name in industry_name or industry_name in name:
                return code
        return 'other'
