"""基金回测策略引擎 — 6 种仓位管理策略"""
import math
from datetime import datetime
from typing import List, Tuple, Optional
from a_stock_db import db, FundNavHistory, FundBasic
from server.models.fund_backtest import (
    FundBacktestRequest, FundBacktestResponse, FundBacktestStats,
    FundTradeRecord, FundEquityPoint, FundStrategyInfo, StrategyParams,
)

# ---------- 手续费 ----------
BUY_FEE_RATE = 0          # C类基金无申购费

def _sell_fee_rate(holding_days: int) -> float:
    """赎回费率：持有 <7天 1.5%, 7-30天 0.5%, >30天 0%"""
    if holding_days < 7:
        return 0.015
    if holding_days < 30:
        return 0.005
    return 0.0


# ---------- 数据获取 ----------
def _get_nav_data(code: str, start_date: str, end_date: Optional[str]) -> list[dict]:
    """从 fund_nav_history 缓存表查询净值数据"""
    session = db.get_session()
    try:
        q = session.query(FundNavHistory).filter(
            FundNavHistory.code == code,
            FundNavHistory.date >= start_date,
        )
        if end_date:
            q = q.filter(FundNavHistory.date <= end_date)
        rows = q.order_by(FundNavHistory.date.asc()).all()
        return [
            {'date': r.date, 'nav': r.nav, 'pct_change': r.pct_change}
            for r in rows
        ]
    finally:
        session.close()


def _get_fund_name(code: str) -> str:
    session = db.get_session()
    try:
        basic = session.query(FundBasic).filter(FundBasic.code == code).first()
        return basic.name if basic else code
    finally:
        session.close()


def _calc_max_drawdown_before(code: str, before_date: str, lookback_days: int = 365) -> float:
    """
    计算指定日期前 lookback_days 天内的最大回撤百分比（负数）。
    用于金字塔策略动态计算补仓梯度。
    """
    from datetime import timedelta
    before = datetime.strptime(before_date, '%Y-%m-%d')
    cutoff = (before - timedelta(days=lookback_days)).strftime('%Y-%m-%d')

    session = db.get_session()
    try:
        rows = (
            session.query(FundNavHistory)
            .filter(
                FundNavHistory.code == code,
                FundNavHistory.date >= cutoff,
                FundNavHistory.date < before_date,
            )
            .order_by(FundNavHistory.date.asc())
            .all()
        )
        if not rows:
            return -15.0  # 无历史数据时默认 -15%
    finally:
        session.close()

    peak = 0
    max_dd = 0
    for r in rows:
        if r.nav and r.nav > peak:
            peak = r.nav
        if peak > 0 and r.nav:
            dd = (r.nav - peak) / peak * 100
            if dd < max_dd:
                max_dd = dd
    return max_dd if max_dd < 0 else -15.0


def _build_dynamic_levels(
    max_drawdown_pct: float,
    initial_capital: float,
    interval_pct: float = 4.0,
    min_levels: int = 3,
    pyramid: bool = True,
) -> list[dict]:
    """
    根据最大回撤动态生成金字塔/倒金字塔梯度。
    :param max_drawdown_pct: 最大回撤（负数，如 -20.0）
    :param initial_capital: 初始资金
    :param interval_pct: 每档间距（默认 4%）
    :param min_levels: 最少档位数
    :param pyramid: True=金字塔（递增），False=倒金字塔（递减）
    :return: [{drop_pct, amount}, ...]
    """
    import math

    abs_dd = abs(max_drawdown_pct)
    n_levels = max(min_levels, math.ceil(abs_dd / interval_pct))

    # 每档浮亏百分比
    drop_pcts = []
    for i in range(1, n_levels + 1):
        drop = min(interval_pct * i, abs_dd)
        drop_pcts.append(-drop)

    # 金额分配：首档为建仓金额（从 initial_capital 中取一部分）
    # 建仓金额 = initial_capital / (n_levels + 1)，剩余分配给补仓档位
    build_amount = initial_capital / (n_levels + 1)
    remaining = initial_capital - build_amount

    if pyramid:
        # 金字塔：1:2:3:...:n 递增
        weights = list(range(1, n_levels + 1))
    else:
        # 倒金字塔：n:...:3:2:1 递减
        weights = list(range(n_levels, 0, -1))
    total_weight = sum(weights)

    levels = []
    for i, (dp, w) in enumerate(zip(drop_pcts, weights)):
        amount = round(remaining * w / total_weight, 2)
        levels.append({'drop_pct': dp, 'amount': amount})

    return levels, build_amount


# ---------- 策略列表 ----------
STRATEGIES = [
    FundStrategyInfo(
        id='dca', name='定投法',
        description='每隔 N 天固定投入 X 元',
        params_desc='interval_days: 间隔天数(默认7) | amount: 每次金额(默认500)',
    ),
    FundStrategyInfo(
        id='equal_buy', name='等额补仓法',
        description='日跌幅超过阈值时，投入固定金额；累计收益超止盈线全部卖出',
        params_desc='drop_pct: 跌幅阈值%(默认-2) | amount: 补仓金额(默认1000) | take_profit_pct: 止盈%(默认20)',
    ),
    FundStrategyInfo(
        id='pyramid', name='金字塔补仓法',
        description='跌得越多补得越多，按梯度加倍投入',
        params_desc='levels: 梯度列表如[{"drop_pct":-3,"amount":500},{"drop_pct":-5,"amount":1000}] | take_profit_pct: 止盈%(默认20)',
    ),
    FundStrategyInfo(
        id='reverse_pyramid', name='倒金字塔法',
        description='跌得越多补得越少（保守补仓）',
        params_desc='levels: 梯度列表如[{"drop_pct":-3,"amount":1000},{"drop_pct":-5,"amount":500}] | take_profit_pct: 止盈%(默认20)',
    ),
    FundStrategyInfo(
        id='constant_value', name='市值恒定法',
        description='保持持仓市值恒定，涨了卖多余部分，跌了补缺口',
        params_desc='target_value: 目标市值(默认5000) | rebalance_days: 调仓间隔天(默认30)',
    ),
    FundStrategyInfo(
        id='grid', name='网格交易法',
        description='以首次买入净值为基准，每跌一格买入，每涨一格卖出',
        params_desc='grid_pct: 每格涨跌幅%(默认3) | amount_per_grid: 每格金额(默认500)',
    ),
]


# ---------- 通用交易执行 ----------
class _Account:
    """模拟账户"""
    def __init__(self, cash: float):
        self.cash = cash
        self.shares = 0.0       # 持有份额
        self.cost_basis = 0.0   # 累计投入成本
        self.trades: list[dict] = []
        self.equity_curve: list[dict] = []
        self.last_buy_date: Optional[str] = None  # 上次买入日期（计算持有天数用）

    def buy(self, date: str, nav: float, amount: float, reason: str):
        """买入，amount 为投入金额（含手续费）"""
        if amount <= 0 or self.cash < amount:
            return
        fee = round(amount * BUY_FEE_RATE, 2)
        actual = amount - fee
        shares = round(actual / nav, 2)
        if shares <= 0:
            return
        self.cash = round(self.cash - amount, 2)
        self.shares = round(self.shares + shares, 2)
        self.cost_basis = round(self.cost_basis + amount, 2)
        self.last_buy_date = date
        self.trades.append({
            'date': date, 'type': 'buy', 'nav': nav,
            'shares': shares, 'amount': round(amount, 2),
            'fee': fee, 'cash_after': self.cash,
            'position_value_after': round(self.shares * nav, 2),
            'reason': reason,
        })

    def sell(self, date: str, nav: float, shares: Optional[float] = None, reason: str = ''):
        """卖出，shares=None 表示全部卖出"""
        if self.shares <= 0:
            return
        sell_shares = shares if shares is not None else self.shares
        sell_shares = min(sell_shares, self.shares)
        if sell_shares <= 0:
            return
        # 计算持有天数
        holding_days = 999
        if self.last_buy_date:
            d1 = datetime.strptime(self.last_buy_date, '%Y-%m-%d')
            d2 = datetime.strptime(date, '%Y-%m-%d')
            holding_days = (d2 - d1).days
        fee_rate = _sell_fee_rate(holding_days)
        gross = round(sell_shares * nav, 2)
        fee = round(gross * fee_rate, 2)
        net = round(gross - fee, 2)
        self.cash = round(self.cash + net, 2)
        self.shares = round(self.shares - sell_shares, 2)
        if self.shares <= 0.01:
            self.shares = 0
            self.cost_basis = 0
        self.trades.append({
            'date': date, 'type': 'sell', 'nav': nav,
            'shares': round(sell_shares, 2), 'amount': round(gross, 2),
            'fee': fee, 'cash_after': self.cash,
            'position_value_after': round(self.shares * nav, 2),
            'reason': reason,
        })

    def record_equity(self, date: str, nav: float):
        """记录每日净值曲线"""
        pos_val = round(self.shares * nav, 2)
        total = round(self.cash + pos_val, 2)
        self.equity_curve.append({
            'date': date, 'nav': nav,
            'total': total, 'cash': self.cash,
            'position_value': pos_val,
            'shares': self.shares,
            'cost_basis': self.cost_basis,
        })

    @property
    def position_value(self) -> float:
        if not self.equity_curve:
            return 0
        return self.equity_curve[-1]['position_value']


# ---------- 策略实现 ----------

def _strategy_dca(nav_data: list[dict], params: StrategyParams, initial_capital: float, _code: str = '') -> Tuple[list, list]:
    """定投法：每隔 N 天固定投入"""
    acc = _Account(initial_capital)
    interval = params.interval_days
    amount = min(params.amount, initial_capital)
    last_buy_idx = -interval  # 保证第一个交易日就投

    for i, d in enumerate(nav_data):
        # 定期买入
        if i - last_buy_idx >= interval and acc.cash >= amount:
            acc.buy(d['date'], d['nav'], amount, f'定投（每{interval}天）')
            last_buy_idx = i
        acc.record_equity(d['date'], d['nav'])

    # 回测结束，按最后净值清仓
    if acc.shares > 0 and nav_data:
        last = nav_data[-1]
        acc.sell(last['date'], last['nav'], reason='回测结束清仓')

    return acc.trades, acc.equity_curve


def _strategy_equal_buy(nav_data: list[dict], params: StrategyParams, initial_capital: float, _code: str = '') -> Tuple[list, list]:
    """等额补仓法：日跌幅超阈值时买入，累计收益超止盈线卖出"""
    acc = _Account(initial_capital)
    drop_pct = params.drop_pct
    buy_amount = min(params.amount, initial_capital)
    tp_pct = params.take_profit_pct

    for d in nav_data:
        pct = d.get('pct_change')
        # 买入：日跌幅超阈值
        if pct is not None and pct <= drop_pct and acc.cash >= buy_amount:
            acc.buy(d['date'], d['nav'], buy_amount, f'补仓（日跌{pct:.2f}%）')

        # 卖出：持仓累计收益超止盈线
        if acc.shares > 0 and acc.cost_basis > 0:
            pos_val = acc.shares * d['nav']
            profit_pct = (pos_val - acc.cost_basis) / acc.cost_basis * 100
            if profit_pct >= tp_pct:
                acc.sell(d['date'], d['nav'], reason=f'止盈（收益{profit_pct:.1f}%）')

        acc.record_equity(d['date'], d['nav'])

    if acc.shares > 0 and nav_data:
        last = nav_data[-1]
        acc.sell(last['date'], last['nav'], reason='回测结束清仓')

    return acc.trades, acc.equity_curve


def _strategy_pyramid(nav_data: list[dict], params: StrategyParams, initial_capital: float, code: str = '') -> Tuple[list, list]:
    """
    金字塔补仓法：动态梯度，相对持仓成本浮亏触发，跌得越多补得越多。
    梯度基于建仓前一年最大回撤自动计算。
    """
    acc = _Account(initial_capital)
    tp_pct = params.take_profit_pct
    triggered = set()
    has_position = False
    levels = []
    build_amount = initial_capital / 4  # 默认建仓金额，后续会动态覆盖

    for i, d in enumerate(nav_data):
        # 首次建仓时，动态计算梯度
        if not has_position:
            if params.levels:
                # 手动指定梯度
                levels = params.levels
                build_amount = min(levels[0]['amount'], acc.cash) if levels else acc.cash
            else:
                # 动态计算：取前一年最大回撤
                max_dd = _calc_max_drawdown_before(code, d['date'])
                levels, build_amount = _build_dynamic_levels(
                    max_dd, initial_capital,
                    params.level_interval_pct, params.min_levels,
                    pyramid=True,
                )
            ba = min(build_amount, acc.cash)
            if ba > 0:
                dd_info = f'（前一年最大回撤{max_dd:.1f}%, {len(levels)}档）' if not params.levels else ''
                acc.buy(d['date'], d['nav'], ba, f'金字塔建仓{dd_info}')
                has_position = True

        if acc.shares > 0 and acc.cost_basis > 0:
            avg_cost = acc.cost_basis / acc.shares
            loss_pct = (d['nav'] - avg_cost) / avg_cost * 100

            matched = None
            for level in levels:
                if loss_pct <= level['drop_pct'] and level['drop_pct'] not in triggered:
                    matched = level
            if matched:
                la = min(matched['amount'], acc.cash)
                if acc.cash >= la:
                    acc.buy(d['date'], d['nav'], la, f'金字塔补仓（浮亏{loss_pct:.1f}%, 档位{matched["drop_pct"]}%）')
                    triggered.add(matched['drop_pct'])

            pos_val = acc.shares * d['nav']
            profit_pct = (pos_val - acc.cost_basis) / acc.cost_basis * 100
            if profit_pct >= tp_pct:
                acc.sell(d['date'], d['nav'], reason=f'止盈（收益{profit_pct:.1f}%）')
                triggered.clear()
                has_position = False

        acc.record_equity(d['date'], d['nav'])

    if acc.shares > 0 and nav_data:
        last = nav_data[-1]
        acc.sell(last['date'], last['nav'], reason='回测结束清仓')

    return acc.trades, acc.equity_curve


def _strategy_reverse_pyramid(nav_data: list[dict], params: StrategyParams, initial_capital: float, code: str = '') -> Tuple[list, list]:
    """
    倒金字塔法：动态梯度，相对持仓成本浮亏触发，跌得越多补得越少。
    """
    acc = _Account(initial_capital)
    tp_pct = params.take_profit_pct
    triggered = set()
    has_position = False
    levels = []
    build_amount = initial_capital / 4

    for i, d in enumerate(nav_data):
        if not has_position:
            if params.levels:
                levels = params.levels
                build_amount = min(levels[0]['amount'], acc.cash) if levels else acc.cash
            else:
                max_dd = _calc_max_drawdown_before(code, d['date'])
                levels, build_amount = _build_dynamic_levels(
                    max_dd, initial_capital,
                    params.level_interval_pct, params.min_levels,
                    pyramid=False,
                )
            ba = min(build_amount, acc.cash)
            if ba > 0:
                dd_info = f'（前一年最大回撤{max_dd:.1f}%, {len(levels)}档）' if not params.levels else ''
                acc.buy(d['date'], d['nav'], ba, f'倒金字塔建仓{dd_info}')
                has_position = True

        if acc.shares > 0 and acc.cost_basis > 0:
            avg_cost = acc.cost_basis / acc.shares
            loss_pct = (d['nav'] - avg_cost) / avg_cost * 100

            matched = None
            for level in levels:
                if loss_pct <= level['drop_pct'] and level['drop_pct'] not in triggered:
                    matched = level
            if matched:
                la = min(matched['amount'], acc.cash)
                if acc.cash >= la:
                    acc.buy(d['date'], d['nav'], la, f'倒金字塔补仓（浮亏{loss_pct:.1f}%, 档位{matched["drop_pct"]}%）')
                    triggered.add(matched['drop_pct'])

            pos_val = acc.shares * d['nav']
            profit_pct = (pos_val - acc.cost_basis) / acc.cost_basis * 100
            if profit_pct >= tp_pct:
                acc.sell(d['date'], d['nav'], reason=f'止盈（收益{profit_pct:.1f}%）')
                triggered.clear()
                has_position = False

        acc.record_equity(d['date'], d['nav'])

    if acc.shares > 0 and nav_data:
        last = nav_data[-1]
        acc.sell(last['date'], last['nav'], reason='回测结束清仓')

    return acc.trades, acc.equity_curve


def _strategy_constant_value(nav_data: list[dict], params: StrategyParams, initial_capital: float, _code: str = '') -> Tuple[list, list]:
    """市值恒定法：保持持仓市值接近目标值"""
    acc = _Account(initial_capital)
    target = params.target_value
    rebalance_days = params.rebalance_days
    last_rebalance_idx = -rebalance_days

    # 首次买入到目标市值
    if nav_data:
        first = nav_data[0]
        acc.buy(first['date'], first['nav'], target, f'建仓（目标市值{target}）')

    for i, d in enumerate(nav_data):
        # 每隔 rebalance_days 调仓
        if i - last_rebalance_idx >= rebalance_days and acc.shares > 0:
            pos_val = acc.shares * d['nav']
            diff = pos_val - target
            if abs(diff) > target * 0.02:  # 偏差超过 2% 才调仓
                if diff > 0:
                    # 市值超标，卖出多余份额
                    sell_shares = round(diff / d['nav'], 2)
                    acc.sell(d['date'], d['nav'], sell_shares, f'调仓减仓（超目标{diff:.0f}）')
                else:
                    # 市值不足，补仓
                    buy_amount = min(-diff, acc.cash)
                    if buy_amount > 0:
                        acc.buy(d['date'], d['nav'], buy_amount, f'调仓补仓（差{-diff:.0f}）')
                last_rebalance_idx = i

        acc.record_equity(d['date'], d['nav'])

    if acc.shares > 0 and nav_data:
        last = nav_data[-1]
        acc.sell(last['date'], last['nav'], reason='回测结束清仓')

    return acc.trades, acc.equity_curve


def _strategy_grid(nav_data: list[dict], params: StrategyParams, initial_capital: float, _code: str = '') -> Tuple[list, list]:
    """网格交易法：基准价上下设网格，每跌一格买入，每涨一格卖出"""
    acc = _Account(initial_capital)
    grid_pct = params.grid_pct
    amount_per_grid = min(params.amount_per_grid, initial_capital)

    # 以首次买入净值为基准价
    base_price = None
    current_grid = 0  # 当前所在网格档位

    for d in nav_data:
        if base_price is None:
            # 首次买入建立基准
            acc.buy(d['date'], d['nav'], amount_per_grid, '网格建仓')
            base_price = d['nav']
            acc.record_equity(d['date'], d['nav'])
            continue

        # 计算当前应处网格档位
        grid_level = math.floor(math.log(d['nav'] / base_price) / math.log(1 + grid_pct / 100))

        # 跌到更低网格 → 买入
        if grid_level < current_grid:
            for g in range(current_grid - 1, grid_level - 1, -1):
                if acc.cash >= amount_per_grid:
                    acc.buy(d['date'], d['nav'], amount_per_grid, f'网格买入（档位{g}）')
            current_grid = grid_level

        # 涨到更高网格 → 卖出
        elif grid_level > current_grid and acc.shares > 0:
            for g in range(current_grid + 1, grid_level + 1):
                # 卖出一格对应的份额
                grid_price = base_price * ((1 + grid_pct / 100) ** (g - 1))
                sell_shares = round(amount_per_grid / grid_price, 2)
                if sell_shares > 0 and sell_shares <= acc.shares:
                    acc.sell(d['date'], d['nav'], sell_shares, f'网格卖出（档位{g}）')
            current_grid = grid_level

        acc.record_equity(d['date'], d['nav'])

    if acc.shares > 0 and nav_data:
        last = nav_data[-1]
        acc.sell(last['date'], last['nav'], reason='回测结束清仓')

    return acc.trades, acc.equity_curve


# ---------- 策略分发 ----------
STRATEGY_MAP = {
    'dca': _strategy_dca,
    'equal_buy': _strategy_equal_buy,
    'pyramid': _strategy_pyramid,
    'reverse_pyramid': _strategy_reverse_pyramid,
    'constant_value': _strategy_constant_value,
    'grid': _strategy_grid,
}


# ---------- 统计计算 ----------
def _calc_stats(trades: list[dict], equity_curve: list[dict], initial_capital: float) -> FundBacktestStats:
    """计算回测统计指标"""
    if not equity_curve:
        return FundBacktestStats(
            initial_capital=initial_capital, total_invested=0, final_value=0,
            total_return=0, total_return_pct=0, annualized_return_pct=0,
            max_drawdown_pct=0, max_drawdown_date='', sharpe_ratio=None,
            num_trades=0, num_buys=0, num_sells=0, avg_buy_amount=0,
            final_shares=0, final_nav=0,
        )

    final = equity_curve[-1]
    buys = [t for t in trades if t['type'] == 'buy']
    sells = [t for t in trades if t['type'] == 'sell']
    total_invested = sum(b['amount'] + b['fee'] for b in buys)
    total_return = final['total'] - initial_capital
    total_return_pct = total_return / initial_capital * 100 if initial_capital else 0

    # 年化收益率
    if len(equity_curve) >= 2:
        days = (datetime.strptime(equity_curve[-1]['date'], '%Y-%m-%d') -
                datetime.strptime(equity_curve[0]['date'], '%Y-%m-%d')).days
        if days > 0:
            annualized_return_pct = ((1 + total_return_pct / 100) ** (365 / days) - 1) * 100
        else:
            annualized_return_pct = 0
    else:
        annualized_return_pct = 0

    # 最大回撤
    max_dd_pct = 0
    max_dd_date = ''
    peak = 0
    for ep in equity_curve:
        if ep['total'] > peak:
            peak = ep['total']
        if peak > 0:
            dd = (peak - ep['total']) / peak * 100
            if dd > max_dd_pct:
                max_dd_pct = dd
                max_dd_date = ep['date']

    # 夏普比率（按日收益计算）
    sharpe = None
    if len(equity_curve) >= 2:
        daily_returns = []
        for i in range(1, len(equity_curve)):
            prev_total = equity_curve[i - 1]['total']
            if prev_total > 0:
                daily_returns.append((equity_curve[i]['total'] - prev_total) / prev_total)
        if len(daily_returns) >= 10:
            avg_r = sum(daily_returns) / len(daily_returns)
            var_r = sum((r - avg_r) ** 2 for r in daily_returns) / len(daily_returns)
            std_r = var_r ** 0.5
            if std_r > 0:
                sharpe = round(avg_r / std_r * (252 ** 0.5), 2)

    avg_buy_amount = sum(b['amount'] for b in buys) / len(buys) if buys else 0

    return FundBacktestStats(
        initial_capital=initial_capital,
        total_invested=round(total_invested, 2),
        final_value=round(final['total'], 2),
        total_return=round(total_return, 2),
        total_return_pct=round(total_return_pct, 2),
        annualized_return_pct=round(annualized_return_pct, 2),
        max_drawdown_pct=round(max_dd_pct, 2),
        max_drawdown_date=max_dd_date,
        sharpe_ratio=sharpe,
        num_trades=len(trades),
        num_buys=len(buys),
        num_sells=len(sells),
        avg_buy_amount=round(avg_buy_amount, 2),
        final_shares=final['shares'],
        final_nav=final['nav'],
    )


# ---------- 主入口 ----------
def run_fund_backtest(req: FundBacktestRequest) -> FundBacktestResponse:
    """运行基金回测"""
    nav_data = _get_nav_data(req.code, req.start_date, req.end_date)
    if not nav_data:
        raise ValueError(f'基金 {req.code} 在 {req.start_date}~{req.end_date or "今"} 无净值数据')

    strategy_fn = STRATEGY_MAP.get(req.strategy)
    if not strategy_fn:
        raise ValueError(f'未知策略: {req.strategy}')

    trades, equity_curve = strategy_fn(nav_data, req.params, req.initial_capital, req.code)
    stats = _calc_stats(trades, equity_curve, req.initial_capital)

    return FundBacktestResponse(
        code=req.code,
        name=_get_fund_name(req.code),
        strategy=req.strategy,
        params=req.params,
        stats=stats,
        trades=[FundTradeRecord(**t) for t in trades],
        equity_curve=[FundEquityPoint(**ep) for ep in equity_curve],
    )
