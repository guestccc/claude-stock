"""ETF 相关 Pydantic schemas"""
from typing import Optional, List
from pydantic import BaseModel


class ETFListItem(BaseModel):
    """ETF 列表单项"""
    code: str
    name: str
    etf_type: Optional[str] = None
    nav: Optional[float] = None
    market_price: Optional[float] = None
    discount_rate: Optional[float] = None


class ETFDetail(ETFListItem):
    """ETF 详情"""
    acc_nav: Optional[float] = None
    latest_date: Optional[str] = None
    open: Optional[float] = None
    close: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None
    turnover: Optional[float] = None
    pct_change: Optional[float] = None
    amplitude: Optional[float] = None
    turnover_rate: Optional[float] = None


class ETFListResponse(BaseModel):
    """ETF 列表响应"""
    data: List[ETFListItem]
    total: int
    page: int
    page_size: int


class ETFRealtimeItem(BaseModel):
    """ETF 实时行情单项"""
    code: str
    name: str
    nav: Optional[float] = None
    pct_change: Optional[float] = None
    fund_type: Optional[str] = None


class ETFRealtimeResponse(BaseModel):
    """ETF 实时行情响应"""
    data: List[ETFRealtimeItem]
    total: int


class ETFDailyBar(BaseModel):
    """ETF 日 K 线数据"""
    date: str
    open: Optional[float] = None
    close: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None
    turnover: Optional[float] = None
    pct_change: Optional[float] = None


class ETFDailyResponse(BaseModel):
    """ETF 日 K 线响应"""
    code: str
    name: str
    data: List[ETFDailyBar]
