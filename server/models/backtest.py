"""回测 Pydantic schemas"""
from typing import Optional, List
from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    """回测请求参数"""
    code: str = Field(..., description="股票代码")
    start_date: str = Field("2024-01-01", description="回测开始日期 YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="回测结束日期 YYYY-MM-DD，默认当天")
    initial_capital: float = Field(100000, gt=0, description="初始本金")
    exit_strategy: str = Field("fixed", description="出场策略 fixed/trailing/boll_middle/trailing_boll/half_exit/half_exit_low3")
    tp_multiplier: float = Field(2.0, gt=0, description="止盈倍数")
    trailing_atr_k: float = Field(1.0, ge=0, description="跟踪止损ATR系数")
    half_exit_pct: float = Field(50, ge=0, le=100, description="半仓止盈比例%")


class TradeResult(BaseModel):
    """单笔交易结果"""
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    shares: int
    pnl: float
    pnl_r: float
    holding_days: int
    reason: str
    atr: float
    upper_band: float = 0
    breakout_close: float = 0
    breakout_exceed_pct: float = 0
    exit_formula: str = ""


class EquityPoint(BaseModel):
    """净值曲线数据点"""
    date: str
    total: float
    equity: float
    position_value: float
    peak: float
    dd: float
    dd_pct: float


class KlineBar(BaseModel):
    """K 线数据"""
    date: str
    open: Optional[float] = None
    close: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None
    turnover: Optional[float] = None


class BacktestStats(BaseModel):
    """回测统计指标"""
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    num_trades: int
    win_trades: int
    loss_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    avg_pnl: float
    rr_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    max_dd_date: Optional[str] = None
    sharpe_ratio: float
    avg_holding_days: float
    daily_return_pct: float = 0


class BacktestResponse(BaseModel):
    """回测响应"""
    code: str
    name: str
    request: BacktestRequest
    stats: BacktestStats
    trades: List[TradeResult]
    equity_curve: List[EquityPoint]
    klines: List[KlineBar]


class SaveBacktestRequest(BaseModel):
    """保存回测结果请求（复用运行时的请求和响应数据）"""
    code: str
    name: str
    request: BacktestRequest
    stats: BacktestStats
    trades: List[TradeResult]
    equity_curve: List[EquityPoint]
    klines: List[KlineBar]


class BacktestHistoryItem(BaseModel):
    """历史回测列表项"""
    id: int
    code: str
    name: str
    start_date: str
    end_date: str
    exit_strategy: str
    total_return_pct: float
    num_trades: int
    win_rate: float
    max_drawdown_pct: float
    created_at: str


class BacktestHistoryListResponse(BaseModel):
    """历史回测列表响应"""
    items: List[BacktestHistoryItem]
    total: int


class BacktestDetailResponse(BaseModel):
    """历史回测详情响应"""
    id: int
    code: str
    name: str
    start_date: str
    end_date: str
    initial_capital: float
    exit_strategy: str
    tp_multiplier: float
    trailing_atr_k: float
    half_exit_pct: float
    stats: BacktestStats
    trades: List[TradeResult]
    equity_curve: List[EquityPoint]
    klines: List[KlineBar]
    created_at: str


class ExitStrategyInfo(BaseModel):
    """出场策略信息"""
    key: str
    name: str
    description: str = ""


class ExitStrategyListResponse(BaseModel):
    """出场策略列表"""
    strategies: List[ExitStrategyInfo]
