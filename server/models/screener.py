"""选股信号 Pydantic schemas"""
from typing import Optional, List
from pydantic import BaseModel


class ScanResultItem(BaseModel):
    """单条扫描结果"""
    code: str
    name: str
    close: float
    upper_band: float
    lower_band: float
    breakout_pct: float
    breakout_days: int
    breakout_amplitude: float
    safety_margin: float
    atr: float
    volume_ratio: float
    score: int


class ScanResponse(BaseModel):
    """扫描结果响应"""
    scan_date: str
    strategy: str
    total: int
    results: List[ScanResultItem]


class StrategyInfo(BaseModel):
    """策略信息"""
    key: str
    name: str
    description: str


class StrategyListResponse(BaseModel):
    """策略列表响应"""
    strategies: List[StrategyInfo]
