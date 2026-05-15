"""ETF 业务服务"""
from typing import List, Optional
from sqlalchemy import func
from a_stock_db.database import db, ETFBasic, ETFDaily


def get_etf_list(
    search: Optional[str] = None,
    etf_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """获取 ETF 列表（支持搜索、类型筛选、分页）"""
    session = db.get_session()
    try:
        query = session.query(ETFBasic)

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                (ETFBasic.code.like(pattern)) | (ETFBasic.name.like(pattern))
            )

        if etf_type:
            query = query.filter(ETFBasic.etf_type.like(f"%{etf_type}%"))

        total = query.count()

        offset = (page - 1) * page_size
        rows = query.offset(offset).limit(page_size).all()

        data = [
            {
                "code": r.code,
                "name": r.name,
                "etf_type": r.etf_type,
                "nav": r.nav,
                "market_price": r.market_price,
                "discount_rate": r.discount_rate,
            }
            for r in rows
        ]

        return {
            "data": data,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    finally:
        session.close()


def get_etf_detail(code: str) -> Optional[dict]:
    """获取 ETF 详情（基础信息 + 最新日线快照）"""
    session = db.get_session()
    try:
        etf = session.query(ETFBasic).filter(ETFBasic.code == code).first()
        if not etf:
            return None

        # 最新日线：先查最新日期，再查对应记录
        latest_date = (
            session.query(func.max(ETFDaily.日期))
            .filter(ETFDaily.code == code)
            .scalar()
        )
        if latest_date:
            latest = (
                session.query(ETFDaily)
                .filter(ETFDaily.code == code, ETFDaily.日期 == latest_date)
                .first()
            )
        else:
            latest = None

        return {
            "code": etf.code,
            "name": etf.name,
            "etf_type": etf.etf_type,
            "nav": etf.nav,
            "acc_nav": etf.acc_nav,
            "market_price": etf.market_price,
            "discount_rate": etf.discount_rate,
            "latest_date": latest.日期.strftime("%Y-%m-%d") if latest and latest.日期 else None,
            "open": latest.开盘 if latest else None,
            "close": latest.收盘 if latest else None,
            "high": latest.最高 if latest else None,
            "low": latest.最低 if latest else None,
            "volume": latest.成交量 if latest else None,
            "turnover": latest.成交额 if latest else None,
            "pct_change": latest.涨跌幅 if latest else None,
            "amplitude": latest.振幅 if latest else None,
            "turnover_rate": latest.换手率 if latest else None,
        }
    finally:
        session.close()


def search_etfs(keyword: str, limit: int = 20) -> List[dict]:
    """搜索 ETF：按代码或名称模糊匹配"""
    session = db.get_session()
    try:
        pattern = f"%{keyword}%"
        rows = (
            session.query(ETFBasic)
            .filter(
                (ETFBasic.code.like(pattern)) | (ETFBasic.name.like(pattern))
            )
            .limit(limit)
            .all()
        )
        return [
            {"code": r.code, "name": r.name, "etf_type": r.etf_type}
            for r in rows
        ]
    finally:
        session.close()
