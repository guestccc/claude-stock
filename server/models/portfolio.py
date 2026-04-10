"""持仓管理 Pydantic schemas"""
from typing import Optional, List
from pydantic import BaseModel


class BuyRequest(BaseModel):
    """买入请求"""
    code: str
    shares: int
    price: float
    date: Optional[str] = None
    note: Optional[str] = None


class SellRequest(BaseModel):
    """卖出请求"""
    code: str
    shares: int
    price: float
    date: Optional[str] = None
    note: Optional[str] = None


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
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None
    first_buy_date: str
    note: Optional[str] = None


class TransactionItem(BaseModel):
    """交易记录条目"""
    id: int
    code: str
    name: str
    type: str
    shares: int
    price: float
    amount: float
    date: str
    note: Optional[str] = None
    created_at: str


class PortfolioSummary(BaseModel):
    """持仓汇总"""
    total_cost: float
    total_market_value: Optional[float] = None
    total_unrealized_pnl: Optional[float] = None
    total_unrealized_pnl_pct: Optional[float] = None
    holding_count: int


class HoldingsResponse(BaseModel):
    """持仓列表响应"""
    holdings: List[HoldingItem]
    summary: PortfolioSummary


class TransactionResponse(BaseModel):
    """交易记录响应"""
    transactions: List[TransactionItem]


class TradeResultResponse(BaseModel):
    """买卖操作响应"""
    holding: HoldingItem
    transaction: TransactionItem
    realized_pnl: Optional[float] = None
