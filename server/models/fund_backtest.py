"""基金回测 Pydantic 模型"""
from pydantic import BaseModel
from typing import Optional, List


class StrategyParams(BaseModel):
    """策略参数 — 不同策略使用不同字段"""
    # 定投法
    interval_days: int = 7
    amount: float = 500
    # 补仓法通用
    drop_pct: float = -2.0
    # 金字塔/倒金字塔 — 动态梯度
    level_interval_pct: float = 4.0  # 每档间距%
    min_levels: int = 3              # 最少档位数
    levels: List[dict] = []          # 手动指定梯度（为空时自动计算）
    # 市值恒定
    target_value: float = 5000
    rebalance_days: int = 30
    # 网格
    grid_pct: float = 3.0
    amount_per_grid: float = 500
    # 止盈（补仓类策略通用）
    take_profit_pct: float = 20.0


class FundBacktestRequest(BaseModel):
    """基金回测请求"""
    code: str
    start_date: str = '2024-01-01'
    end_date: Optional[str] = None
    initial_capital: float = 5000
    strategy: str  # dca/equal_buy/pyramid/reverse_pyramid/constant_value/grid
    params: StrategyParams = StrategyParams()


class FundTradeRecord(BaseModel):
    """单笔交易记录"""
    date: str
    type: str  # buy/sell
    nav: float
    shares: float
    amount: float
    fee: float
    cash_after: float
    position_value_after: float
    reason: str


class FundEquityPoint(BaseModel):
    """每日净值曲线数据点"""
    date: str
    nav: float             # 基金当日净值
    total: float           # 组合总资产
    cash: float            # 剩余现金
    position_value: float  # 持仓市值
    shares: float          # 持有份额
    cost_basis: float      # 累计投入成本


class FundBacktestStats(BaseModel):
    """回测统计指标"""
    initial_capital: float
    total_invested: float
    final_value: float
    total_return: float
    total_return_pct: float
    annualized_return_pct: float
    max_drawdown_pct: float
    max_drawdown_date: str
    sharpe_ratio: Optional[float] = None
    num_trades: int
    num_buys: int
    num_sells: int
    avg_buy_amount: float
    final_shares: float
    final_nav: float


class FundBacktestResponse(BaseModel):
    """基金回测完整响应"""
    code: str
    name: str
    strategy: str
    params: StrategyParams
    stats: FundBacktestStats
    trades: List[FundTradeRecord]
    equity_curve: List[FundEquityPoint]


class FundStrategyInfo(BaseModel):
    """策略描述信息"""
    id: str
    name: str
    description: str
    params_desc: str  # 参数说明文本
