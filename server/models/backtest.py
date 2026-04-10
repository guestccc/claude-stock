"""回测 Pydantic schemas"""
from typing import Optional, List
from pydantic import BaseModel


class BacktestRequest(BaseModel):
    """回测请求参数"""
    code: str
    start_date: str = "2024-01-01"
    end_date: Optional[str] = None
    initial_capital: float = 100000
    exit_strategy: str = "fixed"
    tp_multiplier: float = 2.0
    trailing_atr_k: float = 1.0
    half_exit_pct: float = 50


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
    upper_band: float
    breakout_close: float
    breakout_exceed_pct: float
    exit_formula: str


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
    rr_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    avg_holding_days: float


class BacktestResponse(BaseModel):
    """回测响应"""
    code: str
    name: str
    request: BacktestRequest
    stats: BacktestStats
    trades: List[TradeResult]
    equity_curve: List[EquityPoint]
    klines: List[KlineBar]


class ExitStrategyInfo(BaseModel):
    """出场策略信息"""
    key: str
    name: str


class ExitStrategyListResponse(BaseModel):
    """出场策略列表"""
    strategies: List[ExitStrategyInfo]
