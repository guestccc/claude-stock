"""服务端 ORM 模型 — 自选股、持仓、交易记录"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Index
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
    date = Column(DateTime, nullable=False, comment='交易日期')
    note = Column(String(200), default='', comment='备注')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_tx_code', 'code'),
        Index('idx_tx_date', 'date'),
    )


def init_tables():
    """初始化所有表（启动时调用一次）"""
    Base.metadata.create_all(bind=db.engine)
