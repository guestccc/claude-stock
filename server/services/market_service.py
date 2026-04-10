"""行情服务：桥接 a_stock_db 查询层"""
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import desc

from a_stock_db import StockBasic, StockDaily, StockMinute, StockRealtime
from a_stock_db.database import db


def search_stocks(keyword: str, limit: int = 20) -> List[dict]:
    """搜索股票：按代码或名称模糊匹配"""
    session = db.get_session()
    try:
        pattern = f"%{keyword}%"
        rows = (
            session.query(StockBasic)
            .filter(
                (StockBasic.code.like(pattern))
                | (StockBasic.股票简称.like(pattern))
            )
            .limit(limit)
            .all()
        )
        return [
            {"code": r.code, "name": r.股票简称 or "", "type": r.type}
            for r in rows
        ]
    finally:
        session.close()


def get_stock_name(code: str) -> Optional[str]:
    """获取股票名称"""
    session = db.get_session()
    try:
        row = session.query(StockBasic).filter(StockBasic.code == code).first()
        return row.股票简称 if row else None
    finally:
        session.close()


def get_daily(
    code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 120,
) -> List[dict]:
    """获取日 K 线数据（日期升序，用于图表渲染）"""
    session = db.get_session()
    try:
        query = session.query(StockDaily).filter(StockDaily.code == code)
        if start_date:
            query = query.filter(StockDaily.日期 >= start_date)
        if end_date:
            query = query.filter(StockDaily.日期 <= end_date)
        rows = query.order_by(desc(StockDaily.日期)).limit(limit).all()
        # 反转为日期升序
        rows = list(reversed(rows))
        return [
            {
                "date": (r.日期.strftime("%Y-%m-%d") if r.日期 else ""),
                "open": r.开盘,
                "close": r.收盘,
                "high": r.最高,
                "low": r.最低,
                "volume": r.成交量,
                "turnover": r.成交额,
                "pct_change": r.涨跌幅,
            }
            for r in rows
        ]
    finally:
        session.close()


def get_quotes(codes: List[str]) -> List[dict]:
    """批量获取股票行情（从 StockDaily 取最新收盘数据）"""
    session = db.get_session()
    try:
        results = []
        for code in codes:
            # 获取股票名称
            basic = (
                session.query(StockBasic)
                .filter(StockBasic.code == code)
                .first()
            )
            name = basic.股票简称 if basic else code

            # 获取最新日 K
            latest = (
                session.query(StockDaily)
                .filter(StockDaily.code == code)
                .order_by(desc(StockDaily.日期))
                .first()
            )

            if not latest:
                results.append(
                    {"code": code, "name": name, "close": None, "change_pct": None}
                )
                continue

            # 获取前一日用于计算涨跌幅
            prev = (
                session.query(StockDaily)
                .filter(
                    StockDaily.code == code,
                    StockDaily.日期 < latest.日期,
                )
                .order_by(desc(StockDaily.日期))
                .first()
            )

            results.append(
                {
                    "code": code,
                    "name": name,
                    "close": latest.收盘,
                    "open": latest.开盘,
                    "high": latest.最高,
                    "low": latest.最低,
                    "prev_close": prev.收盘 if prev else None,
                    "change_pct": latest.涨跌幅,
                    "volume": latest.成交量,
                    "turnover": latest.成交额,
                }
            )
        return results
    finally:
        session.close()


def get_minute(code: str, date: Optional[str] = None) -> List[dict]:
    """获取分钟 K 线数据"""
    session = db.get_session()
    try:
        query = session.query(StockMinute).filter(StockMinute.code == code)
        if date:
            query = query.filter(StockMinute.日期 >= date)
        rows = query.order_by(StockMinute.时间).limit(240).all()
        return [
            {
                "time": (r.时间.strftime("%Y-%m-%d %H:%M") if r.时间 else ""),
                "open": r.开盘,
                "close": r.收盘,
                "high": r.最高,
                "low": r.最低,
                "volume": r.成交量,
                "turnover": r.成交额,
            }
            for r in rows
        ]
    finally:
        session.close()
