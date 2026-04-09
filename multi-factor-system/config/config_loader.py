"""配置加载模块"""
import yaml
from pathlib import Path
from typing import Dict, Any


class Config:
    """配置类"""

    def __init__(self, config_dict: Dict[str, Any]):
        self._config = config_dict

    def get(self, key: str, default=None):
        """获取配置项，支持点号分隔的路径"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def __getitem__(self, key):
        return self._config[key]

    def __repr__(self):
        return f"Config({self._config})"


def load_config(config_path: str = None) -> Config:
    """
    加载配置文件

    Args:
        config_path: 配置文件路径，默认使用config/config.yaml

    Returns:
        Config对象
    """
    if config_path is None:
        # 默认从项目根目录加载
        config_path = Path(__file__).parent / "config.yaml"

    with open(config_path, 'r', encoding='utf-8') as f:
        config_dict = yaml.safe_load(f)

    return Config(config_dict)


def load_factor_config(factor_config_path: str = None) -> Dict[str, Any]:
    """
    加载因子配置文件

    Args:
        factor_config_path: 因子配置文件路径

    Returns:
        因子配置字典
    """
    if factor_config_path is None:
        factor_config_path = Path(__file__).parent / "factors.yaml"

    with open(factor_config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
