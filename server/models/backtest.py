"""回测 Pydantic schemas"""
from typing import Optional, List, Dict, Any
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


# ============================================================
# 组合回测（多股票）
# ============================================================

class PortfolioBacktestRequest(BaseModel):
    """组合回测请求"""
    codes: List[str] = Field(..., description="候选股票池代码列表")
    start_date: str = Field("2024-01-01", description="回测开始日期")
    end_date: Optional[str] = Field(None, description="回测结束日期，默认当天")
    initial_capital: float = Field(100000, gt=0, description="初始本金")
    max_positions: int = Field(3, ge=1, le=10, description="最多同时持仓数")
    exit_strategy: str = Field("fixed", description="出场策略")
    tp_multiplier: float = Field(2.0, gt=0, description="止盈倍数")
    trailing_atr_k: float = Field(1.0, ge=0, description="跟踪止损 ATR 系数")
    half_exit_pct: float = Field(50, ge=0, le=100, description="半仓止盈比例（组合模式保留参数）")
    score_config: Optional[Dict[str, Any]] = Field(None, description="评分配置覆盖")


class StockResult(BaseModel):
    """单只股票在组合中的回测结果"""
    code: str
    name: str
    trades: List[TradeResult]
    equity_curve: List[EquityPoint]
    stats: BacktestStats


class PortfolioBacktestResponse(BaseModel):
    """组合回测响应"""
    portfolio_stats: BacktestStats
    overall_equity: List[EquityPoint]
    stock_results: List[StockResult]


class ScoreDimension(BaseModel):
    """评分维度配置"""
    key: str
    name: str
    weight: float = Field(0, ge=0, le=100)
    enabled: bool = True
    params: Dict[str, Any] = {}


class ScoreConfigResponse(BaseModel):
    """评分配置响应"""
    dimensions: List[ScoreDimension]


# ---------- 候选股票池 ----------

class PortfolioPool(BaseModel):
    """候选股票池"""
    id: int
    name: str
    codes: List[str]
    code_names: Dict[str, str] = Field(default_factory=dict, description="code→名称映射")
    created_at: str


class PortfolioPoolListResponse(BaseModel):
    """候选池列表响应"""
    items: List[PortfolioPool]


class PortfolioPoolCreate(BaseModel):
    """创建候选池"""
    name: str = Field(..., min_length=1, max_length=50)
    codes: List[str] = Field(..., min_length=1)


class PortfolioPoolUpdate(BaseModel):
    """更新候选池"""
    name: Optional[str] = None
    codes: Optional[List[str]] = None
