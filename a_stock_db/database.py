"""
A股数据库 - ORM模型定义
所有字段使用akshare原始中文名称，便于追溯
"""
import os
import json
import numpy as np
from datetime import datetime, date
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Index, UniqueConstraint, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import DB_PATH

Base = declarative_base()


class JSONEncoder(json.JSONEncoder):
    """支持datetime和numpy类型的JSON编码器"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(obj, date):
            return obj.strftime("%Y-%m-%d")
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.datetime64,)):
            return str(obj)
        return super().default(obj)


def to_json(data):
    """将数据转换为JSON字符串"""
    if data is None:
        return None
    return json.dumps(data, cls=JSONEncoder, ensure_ascii=False)


class StockBasic(Base):
    """
    股票基本信息表
    数据来源: akshare.stock_info_a_code_name()
    """
    __tablename__ = 'stock_basic'

    code = Column(String(10), primary_key=True, comment='股票代码')
    股票代码 = Column(String(10), comment='股票代码-akshare原始字段')
    股票简称 = Column(String(50), comment='股票简称-akshare原始字段')
    type = Column(String(10), comment='股票类型 SH/SZ/BJ-派生字段')
    status = Column(String(20), comment='上市状态-派生字段')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    raw_data = Column(Text, comment='原始JSON数据备份')

    __table_args__ = (
        Index('idx_type', 'type'),
        Index('idx_status', 'status'),
    )


class StockDaily(Base):
    """
    日线行情表
    数据来源: akshare.stock_zh_a_hist(symbol=code, adjust="qfq")
    """
    __tablename__ = 'stock_daily'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, comment='股票代码')
    日期 = Column(DateTime, nullable=False, comment='日期-akshare原始字段')
    开盘 = Column(Float, comment='开盘价(元)-akshare原始字段')
    收盘 = Column(Float, comment='收盘价(元)-akshare原始字段')
    最高 = Column(Float, comment='最高价(元)-akshare原始字段')
    最低 = Column(Float, comment='最低价(元)-akshare原始字段')
    成交量 = Column(Float, comment='成交量(手)-akshare原始字段')
    成交额 = Column(Float, comment='成交额(元)-akshare原始字段')
    振幅 = Column(Float, comment='振幅(%)-akshare原始字段')
    涨跌幅 = Column(Float, comment='涨跌幅(%)-akshare原始字段')
    涨跌额 = Column(Float, comment='涨跌额(元)-akshare原始字段')
    换手率 = Column(Float, comment='换手率(%)-akshare原始字段')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    raw_data = Column(Text, comment='原始JSON数据备份')

    __table_args__ = (
        UniqueConstraint('code', '日期', name='uq_code_date'),
        Index('idx_trade_date', '日期'),
    )


class StockMinute(Base):
    """
    1分钟分时数据表
    数据来源: akshare.stock_zh_a_minute(symbol=code, period="1", adjust="qfq")
    数据保留: 近5个交易日
    """
    __tablename__ = 'stock_minute'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, comment='股票代码')
    日期 = Column(DateTime, nullable=False, comment='交易日期')
    时间 = Column(DateTime, nullable=False, comment='精确时间-akshare原始字段')
    开盘 = Column(Float, comment='开盘价-akshare原始字段')
    收盘 = Column(Float, comment='收盘价-akshare原始字段')
    最高 = Column(Float, comment='最高价-akshare原始字段')
    最低 = Column(Float, comment='最低价-akshare原始字段')
    成交量 = Column(Float, comment='成交量-akshare原始字段')
    成交额 = Column(Float, comment='成交额-akshare原始字段')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    raw_data = Column(Text, comment='原始JSON数据备份')

    __table_args__ = (
        UniqueConstraint('code', '时间', name='uq_code_time'),
        Index('idx_code_date', 'code', '日期'),
    )


class StockFinancial(Base):
    """
    财务数据表
    数据来源: akshare.stock_financial_report_sina(stock=code, symbol="利润表")
    """
    __tablename__ = 'stock_financial'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, comment='股票代码')
    报告日期 = Column(DateTime, nullable=False, comment='报告日期-akshare原始字段')
    报表类型 = Column(String(20), comment='报表类型-派生字段(利润表/资产负债表/现金流量表)')
    营业总收入 = Column(Float, comment='营业总收入-akshare原始字段')
    营业总成本 = Column(Float, comment='营业总成本-akshare原始字段')
    营业利润 = Column(Float, comment='营业利润-akshare原始字段')
    利润总额 = Column(Float, comment='利润总额-akshare原始字段')
    净利润 = Column(Float, comment='净利润-akshare原始字段')
    基本每股收益 = Column(Float, comment='基本每股收益-akshare原始字段')
    稀释每股收益 = Column(Float, comment='稀释每股收益-akshare原始字段')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    raw_data = Column(Text, comment='原始JSON数据备份')

    __table_args__ = (
        UniqueConstraint('code', '报告日期', '报表类型', name='uq_code_report_type'),
        Index('idx_code', 'code'),
    )


class StockIndexComponents(Base):
    """
    指数成分股权重表
    数据来源: akshare.index_weight_cons(symbol=index_code)
    """
    __tablename__ = 'stock_index_components'

    id = Column(Integer, primary_key=True, autoincrement=True)
    指数代码 = Column(String(20), nullable=False, comment='指数代码-akshare原始字段')
    指数名称 = Column(String(50), comment='指数名称-派生字段')
    股票代码 = Column(String(10), nullable=False, comment='成分股代码-akshare原始字段')
    股票名称 = Column(String(50), comment='成分股名称-akshare原始字段')
    权重 = Column(Float, comment='权重(%)-akshare原始字段')
    更新日期 = Column(DateTime, nullable=False, comment='更新日期')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    raw_data = Column(Text, comment='原始JSON数据备份')

    __table_args__ = (
        Index('idx_index_date', '指数代码', '更新日期'),
        Index('idx_stock_code', '股票代码'),
    )


class StockConcept(Base):
    """
    概念板块表
    数据来源: akshare.stock_board_concept_name_em()
    """
    __tablename__ = 'stock_concept'

    板块代码 = Column(String(20), primary_key=True, comment='板块代码')
    板块名称 = Column(String(100), nullable=False, comment='板块名称-akshare原始字段')
    涨跌幅 = Column(Float, comment='涨跌幅(%)-akshare原始字段')
    总市值 = Column(Float, comment='总市值(元)-akshare原始字段')
    成交额 = Column(Float, comment='成交额(元)-akshare原始字段')
    上涨家数 = Column(Integer, comment='上涨家数-akshare原始字段')
    下跌家数 = Column(Integer, comment='下跌家数-akshare原始字段')
    updated_at = Column(DateTime, default=datetime.now, comment='更新时间')
    raw_data = Column(Text, comment='原始JSON数据备份')

    __table_args__ = (
        Index('idx_concept_name', '板块名称'),
    )


class StockRealtime(Base):
    """
    实时行情表
    数据来源: akshare.stock_zh_a_spot_em()
    """
    __tablename__ = 'stock_realtime'

    code = Column(String(10), primary_key=True, comment='股票代码')
    序号 = Column(Integer, comment='序号-akshare原始字段')
    股票代码 = Column(String(10), comment='股票代码-akshare原始字段')
    股票名称 = Column(String(50), comment='股票名称-akshare原始字段')
    开盘 = Column(Float, comment='开盘价-akshare原始字段')
    最高 = Column(Float, comment='最高价-akshare原始字段')
    最低 = Column(Float, comment='最低价-akshare原始字段')
    收盘 = Column(Float, comment='收盘/最新价-akshare原始字段')
    成交量 = Column(Float, comment='成交量(手)-akshare原始字段')
    成交额 = Column(Float, comment='成交额(元)-akshare原始字段')
    振幅 = Column(Float, comment='振幅(%)-akshare原始字段')
    涨跌幅 = Column(Float, comment='涨跌幅(%)-akshare原始字段')
    涨跌额 = Column(Float, comment='涨跌额(元)-akshare原始字段')
    换手率 = Column(Float, comment='换手率(%)-akshare原始字段')
    市盈率 = Column(Float, comment='市盈率-akshare原始字段')
    市净率 = Column(Float, comment='市净率-akshare原始字段')
    总市值 = Column(Float, comment='总市值(元)-akshare原始字段')
    流通市值 = Column(Float, comment='流通市值(元)-akshare原始字段')
    更新时间 = Column(DateTime, default=datetime.now, comment='更新时间')
    raw_data = Column(Text, comment='原始JSON数据备份')


class FundBasic(Base):
    """
    基金基本信息表
    数据来源: akshare.fund_individual_basic_info_xq()
    """
    __tablename__ = 'fund_basic'

    code = Column(String(10), primary_key=True, comment='基金代码')
    name = Column(String(100), nullable=False, comment='基金名称')
    full_name = Column(String(200), comment='基金全称')
    fund_type = Column(String(50), comment='基金类型(混合型/股票型/债券型...)')
    company = Column(String(100), comment='基金公司')
    manager = Column(String(50), comment='基金经理')
    setup_date = Column(String(20), comment='成立日期')
    scale = Column(String(50), comment='基金规模')
    benchmark = Column(Text, comment='业绩比较基准')
    strategy = Column(Text, comment='投资策略')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    raw_data = Column(Text, comment='原始JSON数据备份')


class FundWatchlist(Base):
    """
    自选基金表
    """
    __tablename__ = 'fund_watchlist'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, unique=True, comment='基金代码')
    added_at = Column(DateTime, default=datetime.now, comment='添加时间')
    remark = Column(String(200), comment='备注')


class FundEstimation(Base):
    """
    基金实时估值表
    数据来源: 天天基金 fundgz.1234567.com.cn
    """
    __tablename__ = 'fund_estimation'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, comment='基金代码')
    name = Column(String(100), comment='基金名称')
    date = Column(String(10), nullable=False, comment='净值日期 YYYY-MM-DD')
    update_time = Column(String(20), comment='估值时间 14:13')
    nav = Column(Float, comment='单位净值(最新)')
    acc_nav = Column(Float, comment='累计净值')
    last_nav = Column(Float, comment='上日净值')
    est_nav = Column(Float, comment='估算净值')
    est_pct = Column(Float, comment='估算增长率%')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    raw_data = Column(Text, comment='原始JSON数据备份')

    __table_args__ = (
        UniqueConstraint('code', 'date', name='uq_fund_date'),
        Index('idx_code', 'code'),
    )


class FundNavHistory(Base):
    """
    基金历史净值缓存表
    数据来源: akshare fund_open_fund_info_em（全量拉取，按需刷新）
    """
    __tablename__ = 'fund_nav_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, comment='基金代码')
    date = Column(String(10), nullable=False, comment='净值日期 YYYY-MM-DD')
    nav = Column(Float, comment='单位净值')
    pct_change = Column(Float, comment='日增长率%')

    __table_args__ = (
        UniqueConstraint('code', 'date', name='uq_fund_nav_date'),
        Index('idx_fund_nav_code', 'code'),
    )


class CTADonchianScan(Base):
    """
    CTA 唐奇安扫描结果表
    记录每日全市场股票的唐奇安突破情况
    """
    __tablename__ = 'cta_donchian_scan'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, comment='股票代码')
    股票名称 = Column(String(50), comment='股票名称')
    scan_date = Column(DateTime, nullable=False, comment='扫描日期')
    收盘价 = Column(Float, comment='收盘价')
    上轨 = Column(Float, comment='唐奇安上轨(20日最高)')
    下轨 = Column(Float, comment='唐奇安下轨(20日最低)')
    突破强度 = Column(Float, comment='突破强度%')
    突破天数 = Column(Integer, comment='连续突破天数')
    突破幅度 = Column(Float, comment='突破幅度%(超出上轨部分)')
    距下轨_pct = Column(Float, comment='距下轨百分比(安全垫)')
    atr = Column(Float, comment='ATR波动率')
    量比 = Column(Float, comment='量比(当日量/5日均量)')
    综合分 = Column(Integer, comment='综合评分')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        UniqueConstraint('code', 'scan_date', name='uq_code_scan_date'),
        Index('idx_scan_date', 'scan_date'),
    )


class DatabaseManager:
    """数据库管理类"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = DB_PATH
        self.db_path = db_path
        # SQLite 配置：WAL模式 + 超时30秒
        self.engine = create_engine(
            f'sqlite:///{db_path}',
            echo=False,
            connect_args={
                'timeout': 30,
                'check_same_thread': False,
            }
        )
        # 启用 WAL 模式，提升并发性能
        with self.engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA busy_timeout=30000"))
            conn.commit()
        self.Session = sessionmaker(bind=self.engine)

    def create_all(self):
        """创建所有表"""
        Base.metadata.create_all(self.engine)
        print(f"数据库表创建成功: {self.db_path}")

    def drop_all(self):
        """删除所有表"""
        Base.metadata.drop_all(self.engine)
        print("所有表已删除")

    def get_session(self):
        """获取数据库会话"""
        return self.Session()


# 全局实例
db = DatabaseManager()


if __name__ == '__main__':
    # 测试数据库连接
    db.create_all()

    # 显示表结构
    print("\n=== 数据库表 ===")
    for table in Base.metadata.tables:
        print(f"  - {table}")
