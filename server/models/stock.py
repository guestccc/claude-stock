"""股票相关 Pydantic schemas"""
from typing import Optional, List
from pydantic import BaseModel


class StockInfo(BaseModel):
    """股票基本信息"""
    code: str
    name: str
    type: Optional[str] = None


class StockSearchResponse(BaseModel):
    """搜索结果"""
    results: List[StockInfo]


class DailyBar(BaseModel):
    """日 K 线数据"""
    date: str
    open: Optional[float] = None
    close: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None
    turnover: Optional[float] = None
    pct_change: Optional[float] = None


class DailyResponse(BaseModel):
    """日 K 线响应"""
    code: str
    name: str
    data: List[DailyBar]


class QuoteItem(BaseModel):
    """单只股票行情摘要"""
    code: str
    name: str
    close: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    prev_close: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[float] = None
    turnover: Optional[float] = None
    pe: Optional[float] = None
    pb: Optional[float] = None
    market_cap: Optional[float] = None


class QuotesResponse(BaseModel):
    """批量行情响应"""
    data: List[QuoteItem]


class MinuteBar(BaseModel):
    """分钟 K 线数据"""
    time: str
    open: Optional[float] = None
    close: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None
    turnover: Optional[float] = None


class MinuteResponse(BaseModel):
    """分钟数据响应"""
    code: str
    data: List[MinuteBar]


class IndexSummary(BaseModel):
    """指数概览"""
    close: Optional[float] = None
    change_pct: Optional[float] = None


class MarketIndexResponse(BaseModel):
    """市场指数响应"""
    sh: IndexSummary
    sz: IndexSummary


class StockListItem(BaseModel):
    """股票列表单项"""
    code: str
    name: str
    date: str
    open: Optional[float] = None
    close: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None
    turnover: Optional[float] = None
    pct_change: Optional[float] = None


class StockListResponse(BaseModel):
    """股票列表响应"""
    data: List[StockListItem]
    total: int
    page: int
    page_size: int
