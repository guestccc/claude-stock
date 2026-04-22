"""持仓管理 Pydantic schemas"""
from typing import Optional, List
from pydantic import BaseModel, Field


class HoldingItem(BaseModel):
    """持仓条目"""
    id: int
    code: str
    name: str
    shares: int
    avg_cost: float
    total_cost: float
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    profit_amount: Optional[float] = None
    profit_pct: Optional[float] = None
    first_buy_date: Optional[str] = None
    note: Optional[str] = None
    created_at: str
    updated_at: str


class HoldingSummary(BaseModel):
    """持仓汇总"""
    total_cost: float
    total_market_value: float
    total_profit_amount: float
    total_profit_pct: float
    holding_count: int


class HoldingsResponse(BaseModel):
    """持仓列表响应"""
    holdings: List[HoldingItem]
    summary: HoldingSummary


class TransactionItem(BaseModel):
    """交易记录条目"""
    id: int
    code: str
    name: str
    type: str  # buy / sell
    shares: int
    price: float
    amount: float
    fee: float = 0
    date: str
    note: Optional[str] = None
    created_at: str


class TransactionsResponse(BaseModel):
    """交易记录列表响应"""
    transactions: List[TransactionItem]


class BuyRequest(BaseModel):
    """买入请求"""
    code: str = Field(..., description="股票代码，如 600519")
    shares: int = Field(..., gt=0, description="买入数量（股）")
    price: float = Field(..., gt=0, description="买入价格（元）")
    fee: float = Field(0, ge=0, description="费用/税费（元）")
    date: Optional[str] = Field(None, description="交易日期 YYYY-MM-DD，默认当前时间")
    note: Optional[str] = Field("", description="备注")


class SellRequest(BaseModel):
    """卖出请求"""
    code: str = Field(..., description="股票代码，如 600519")
    shares: int = Field(..., gt=0, description="卖出数量（股）")
    price: float = Field(..., gt=0, description="卖出价格（元）")
    fee: float = Field(0, ge=0, description="费用/税费（元）")
    date: Optional[str] = Field(None, description="交易日期 YYYY-MM-DD，默认当前时间")
    note: Optional[str] = Field("", description="备注")


class ClosedPositionItem(BaseModel):
    """已清仓条目"""
    code: str
    name: str
    total_buy: float
    total_sell: float
    profit: float
    profit_pct: float
    last_sell_date: str


class ClosedPositionsResponse(BaseModel):
    """已清仓列表响应"""
    items: List[ClosedPositionItem]


class TradeResponse(BaseModel):
    """买卖操作响应"""
    message: str
    holding: Optional[HoldingItem] = None
    transaction: TransactionItem
