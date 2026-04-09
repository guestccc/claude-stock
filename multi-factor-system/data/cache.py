"""
数据缓存模块
本地存储和读取数据
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Union
from datetime import datetime
from loguru import logger


class DataCache:
    """数据缓存管理器"""

    def __init__(self, config):
        self.config = config
        self.cache_dir = Path(config.get("data_source.cache_dir", "./data/cache"))
        self.cache_type = config.get("data_source.cache_type", "parquet")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def save_data(
        self,
        df: pd.DataFrame,
        name: str,
        overwrite: bool = True
    ) -> bool:
        """
        保存数据到缓存

        Args:
            df: 要保存的数据
            name: 数据名称（文件名前缀）
            overwrite: 是否覆盖已存在的文件

        Returns:
            是否保存成功
        """
        if df.empty:
            logger.warning(f"数据为空，跳过保存: {name}")
            return False

        file_path = self._get_file_path(name)

        if file_path.exists() and not overwrite:
            logger.info(f"文件已存在，跳过: {file_path}")
            return False

        try:
            if self.cache_type == "parquet":
                df.to_parquet(file_path, index=True)
            elif self.cache_type == "hdf5":
                df.to_hdf(file_path, key=name, mode='w')
            elif self.cache_type == "csv":
                df.to_csv(file_path, index=True)
            else:
                logger.error(f"不支持的缓存格式: {self.cache_type}")
                return False

            file_size = file_path.stat().st_size / (1024 * 1024)  # MB
            logger.info(f"数据已保存: {file_path} ({file_size:.2f} MB)")
            return True

        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            return False

    def load_data(
        self,
        name: str,
        date_range: Optional[tuple] = None
    ) -> pd.DataFrame:
        """
        从缓存加载数据

        Args:
            name: 数据名称
            date_range: 可选的日期过滤 (start_date, end_date)

        Returns:
            加载的数据
        """
        file_path = self._get_file_path(name)

        if not file_path.exists():
            logger.warning(f"缓存文件不存在: {file_path}")
            return pd.DataFrame()

        try:
            if self.cache_type == "parquet":
                df = pd.read_parquet(file_path)
            elif self.cache_type == "hdf5":
                df = pd.read_hdf(file_path, key=name)
            elif self.cache_type == "csv":
                df = pd.read_csv(file_path, index_col=0)
                # 恢复日期列
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])

            # 按日期过滤
            if date_range and 'date' in df.columns:
                start_date, end_date = date_range
                if start_date:
                    df = df[df['date'] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df['date'] <= pd.to_datetime(end_date)]

            logger.info(f"从缓存加载数据: {name}, 共 {len(df)} 条记录")
            return df

        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            return pd.DataFrame()

    def _get_file_path(self, name: str) -> Path:
        """获取缓存文件路径"""
        extension = {
            "parquet": ".parquet",
            "hdf5": ".h5",
            "csv": ".csv"
        }.get(self.cache_type, ".parquet")

        return self.cache_dir / f"{name}{extension}"

    def exists(self, name: str) -> bool:
        """检查缓存是否存在"""
        return self._get_file_path(name).exists()

    def delete(self, name: str) -> bool:
        """删除缓存"""
        file_path = self._get_file_path(name)

        if file_path.exists():
            file_path.unlink()
            logger.info(f"已删除缓存: {file_path}")
            return True

        return False

    def clear_all(self) -> int:
        """清空所有缓存"""
        count = 0
        for file_path in self.cache_dir.glob(f"*.{self.cache_type}"):
            file_path.unlink()
            count += 1

        logger.info(f"已清空 {count} 个缓存文件")
        return count

    def get_cache_info(self) -> dict:
        """获取缓存信息"""
        files = list(self.cache_dir.glob(f"*.{self.cache_type}"))

        total_size = sum(f.stat().st_size for f in files)
        info = {
            "file_count": len(files),
            "total_size_mb": total_size / (1024 * 1024),
            "files": [
                {
                    "name": f.stem,
                    "size_mb": f.stat().st_size / (1024 * 1024),
                    "modified": datetime.fromtimestamp(f.stat().st_mtime)
                }
                for f in files
            ]
        }

        return info


class FactorCache(DataCache):
    """因子数据缓存"""

    def save_factors(
        self,
        factors: pd.DataFrame,
        date: str,
        name: str = "factors"
    ) -> bool:
        """
        保存因子数据

        Args:
            factors: 因子数据
            date: 数据日期
            name: 因子名称

        Returns:
            是否保存成功
        """
        # 按日期分别存储
        date_str = pd.to_datetime(date).strftime("%Y%m")
        full_name = f"{name}_{date_str}"
        return self.save_data(factors, full_name)

    def load_factors(
        self,
        start_date: str,
        end_date: str,
        name: str = "factors"
    ) -> pd.DataFrame:
        """
        加载日期范围内的因子数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            name: 因子名称

        Returns:
            合并后的因子数据
        """
        start_month = pd.to_datetime(start_date).strftime("%Y%m")
        end_month = pd.to_datetime(end_date).strftime("%Y%m")

        all_factors = []

        # 遍历月份
        current = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        while current <= end:
            month_str = current.strftime("%Y%m")
            full_name = f"{name}_{month_str}"

            df = self.load_data(full_name)
            if not df.empty:
                all_factors.append(df)

            current = current + pd.DateOffset(months=1)

        if not all_factors:
            return pd.DataFrame()

        return pd.concat(all_factors, ignore_index=True)
