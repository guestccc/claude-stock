"""服务端 ORM 模型 — 自选股、持仓、交易记录、回测结果"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Index, Text, ForeignKey
from sqlalchemy.orm import relationship
from a_stock_db.database import Base

# 复用 a_stock_db 的 Base 和 db 实例，同一个 SQLite 数据库文件
from a_stock_db.database import db


class WatchlistItem(Base):
    """自选股列表"""
    __tablename__ = 'watchlist'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, unique=True, comment='股票代码')
    name = Column(String(50), nullable=False, comment='股票名称')
    sort_order = Column(Integer, default=0, comment='排序顺序')
    note = Column(String(200), default='', comment='备注')
    added_at = Column(DateTime, default=datetime.now, comment='添加时间')

    __table_args__ = (
        Index('idx_sort_order', 'sort_order'),
    )


class Holding(Base):
    """持仓记录"""
    __tablename__ = 'holdings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, unique=True, comment='股票代码')
    name = Column(String(50), nullable=False, comment='股票名称')
    shares = Column(Integer, nullable=False, comment='持股数量')
    avg_cost = Column(Float, nullable=False, comment='平均成本价')
    total_cost = Column(Float, nullable=False, comment='总买入成本')
    first_buy_date = Column(DateTime, nullable=False, comment='首次买入日期')
    note = Column(String(200), default='', comment='备注')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')


class CostLot(Base):
    """成本批次 — FIFO 追踪每次买入的股数和成本"""
    __tablename__ = 'cost_lots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, comment='股票代码')
    tx_id = Column(Integer, nullable=False, comment='关联 Transaction.id')
    price = Column(Float, nullable=False, comment='买入价格')
    shares = Column(Integer, nullable=False, comment='剩余股数')
    cost = Column(Float, nullable=False, comment='剩余成本')
    date = Column(DateTime, nullable=False, comment='买入日期')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_lot_code', 'code'),
    )


class Transaction(Base):
    """交易记录"""
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, comment='股票代码')
    name = Column(String(50), nullable=False, comment='股票名称')
    type = Column(String(10), nullable=False, comment='交易类型 buy/sell')
    shares = Column(Integer, nullable=False, comment='成交数量')
    price = Column(Float, nullable=False, comment='成交价格')
    amount = Column(Float, nullable=False, comment='成交金额')
    fee = Column(Float, default=0, comment='费用/税费')
    date = Column(DateTime, nullable=False, comment='交易日期')
    note = Column(String(200), default='', comment='备注')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_tx_code', 'code'),
        Index('idx_tx_date', 'date'),
    )


class BacktestResult(Base):
    """回测结果（用户手动保存）"""
    __tablename__ = 'backtest_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, comment='股票代码')
    name = Column(String(50), nullable=False, comment='股票名称')
    start_date = Column(String(10), nullable=False, comment='回测开始日期')
    end_date = Column(String(10), nullable=False, comment='回测结束日期')
    initial_capital = Column(Float, nullable=False, default=100000, comment='初始本金')
    exit_strategy = Column(String(30), nullable=False, comment='出场策略')
    tp_multiplier = Column(Float, nullable=False, default=2.0, comment='止盈倍数')
    trailing_atr_k = Column(Float, nullable=False, default=1.0, comment='跟踪止损ATR系数')
    half_exit_pct = Column(Float, nullable=False, default=50, comment='半仓止盈比例%')

    # 统计指标 JSON
    stats_json = Column(Text, nullable=False, default='{}', comment='统计指标JSON')
    # 净值曲线 JSON
    equity_curve_json = Column(Text, nullable=False, default='[]', comment='净值曲线JSON')
    # K线数据 JSON（可选，可能较大）
    klines_json = Column(Text, nullable=True, comment='K线数据JSON')

    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    # 关联交易明细
    trades = relationship('BacktestTrade', backref='result',
                          cascade='all, delete-orphan',
                          lazy='select')

    __table_args__ = (
        Index('idx_bt_code', 'code'),
        Index('idx_bt_strategy', 'exit_strategy'),
        Index('idx_bt_created', 'created_at'),
    )


class BacktestTrade(Base):
    """回测单笔交易明细"""
    __tablename__ = 'backtest_trades'

    id = Column(Integer, primary_key=True, autoincrement=True)
    backtest_id = Column(Integer, ForeignKey('backtest_results.id'), nullable=False, comment='关联回测ID')

    entry_date = Column(String(10), nullable=False, comment='买入日期')
    exit_date = Column(String(10), nullable=False, comment='卖出日期')
    entry_price = Column(Float, nullable=False, comment='买入价')
    exit_price = Column(Float, nullable=False, comment='卖出价')
    stop_loss = Column(Float, nullable=False, comment='止损价')
    take_profit = Column(Float, nullable=False, comment='止盈价')
    shares = Column(Integer, nullable=False, comment='股数')
    pnl = Column(Float, nullable=False, comment='盈亏金额')
    pnl_r = Column(Float, nullable=False, comment='R值')
    holding_days = Column(Integer, nullable=False, comment='持有天数')
    reason = Column(String(20), nullable=False, comment='平仓原因')
    atr = Column(Float, nullable=False, comment='入场时ATR')
    upper_band = Column(Float, nullable=False, default=0, comment='唐奇安上轨')
    breakout_close = Column(Float, nullable=False, default=0, comment='突破日收盘价')
    breakout_exceed_pct = Column(Float, nullable=False, default=0, comment='突破超幅%')
    exit_formula = Column(Text, nullable=False, default='', comment='卖出触发公式说明')

    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_bt_trade_backtest_id', 'backtest_id'),
    )


class BacktestRecentStock(Base):
    """回测最近运行的股票（每次运行自动更新）"""
    __tablename__ = 'backtest_recent_stocks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, unique=True, comment='股票代码')
    name = Column(String(50), nullable=False, comment='股票名称')
    last_run_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='最近运行时间')


def init_tables():
    """初始化所有表（启动时调用一次）"""
    Base.metadata.create_all(bind=db.engine)
    # 兼容已有数据库：补充新增列
    _safe_add_column('fund_watchlist', 'tags', 'TEXT DEFAULT ""')


def _safe_add_column(table: str, column: str, col_type: str):
    """安全添加列，已存在则跳过"""
    from sqlalchemy import text
    with db.engine.connect() as conn:
        try:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
            conn.commit()
        except Exception:
            pass
