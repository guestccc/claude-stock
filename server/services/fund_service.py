"""基金服务"""
from datetime import datetime
from typing import List, Optional
from a_stock_db import db, FundBasic, FundWatchlist, FundEstimation
from a_stock_fetcher.fetchers.fund import (
    fetch_fund_basic,
    fetch_fund_estimation,
    ensure_nav_history,
    get_recent_nav,
    get_nav_history_from_db,
    remove_watchlist as fetcher_remove_watchlist,
)


def get_watchlist() -> List[dict]:
    """获取自选基金列表 — 实时拉估值 + 按需刷新历史净值缓存"""
    session = db.get_session()
    try:
        watchlist = session.query(FundWatchlist).all()
        if not watchlist:
            return []

        codes = [w.code for w in watchlist]

        # 实时拉取天天基金估值（每只0.3s）
        for code in codes:
            fetch_fund_estimation(code)

        # 按需刷新历史净值缓存（缓存过期才调 akshare）
        for code in codes:
            ensure_nav_history(code)

        # 查基本信息
        basics = {
            b.code: b for b in
            session.query(FundBasic).filter(FundBasic.code.in_(codes)).all()
        }

        # 查最新估值
        latest = {}
        for code in codes:
            est = (
                session.query(FundEstimation)
                .filter(FundEstimation.code == code)
                .order_by(FundEstimation.date.desc())
                .first()
            )
            if est:
                latest[code] = est

        # 查近10日历史净值（从缓存表，纯 DB 查询）
        history = {}
        for code in codes:
            hist = get_recent_nav(code, 10)
            if hist:
                history[code] = hist

        results = []
        for w in watchlist:
            code = w.code
            basic = basics.get(code)
            est = latest.get(code)
            hist = history.get(code, [])

            nav_change = None
            if hist and len(hist) >= 2:
                first_nav = hist[0]['nav']
                last_nav = hist[-1]['nav']
                if last_nav and first_nav and last_nav != 0:
                    nav_change = (first_nav - last_nav) / last_nav * 100

            results.append({
                'code': code,
                'name': basic.name if basic else code,
                'fund_type': basic.fund_type if basic else '',
                'company': basic.company if basic else '',
                'manager': basic.manager if basic else '',
                'remark': w.remark or '',
                'added_at': w.added_at.strftime('%Y-%m-%d') if w.added_at else '',
                'nav': est.nav if est else None,
                'nav_date': est.date if est else '',
                'est_nav': est.est_nav if est else None,
                'est_pct': est.est_pct if est else None,
                'update_time': est.update_time if est else '',
                'history': hist,
                'nav_change_pct': nav_change,
            })

        return results
    finally:
        session.close()


def add_watchlist(code: str, remark: str = '') -> dict:
    """添加自选基金（同时获取基本信息和最新估值）"""
    session = db.get_session()
    try:
        # 获取基金基本信息
        fetch_fund_basic(code)
        # 写入自选表
        from sqlalchemy.dialects.sqlite import insert
        stmt = insert(FundWatchlist).values(code=code, remark=remark)
        stmt = stmt.on_conflict_do_update(index_elements=['code'], set_={'remark': remark})
        session.execute(stmt)
        session.commit()
        # 拉取一次实时估值
        fetch_fund_estimation(code)
        return {'success': True, 'code': code}
    except Exception as e:
        session.rollback()
        return {'success': False, 'error': str(e)}
    finally:
        session.close()


def remove_watchlist(code: str) -> dict:
    """移除自选基金"""
    return {'success': fetcher_remove_watchlist(code)}


def get_fund_detail(code: str) -> Optional[dict]:
    """获取基金详情（基本信息 + 最新估值），优先读本地数据库，不存在则触发一次拉取"""
    session = db.get_session()
    try:
        basic = session.query(FundBasic).filter(FundBasic.code == code).first()

        # 本地无基本信息，触发一次拉取
        if not basic:
            fetch_fund_basic(code)
            basic = session.query(FundBasic).filter(FundBasic.code == code).first()

        if not basic:
            return None

        # 查最新估值
        est = (
            session.query(FundEstimation)
            .filter(FundEstimation.code == code)
            .order_by(FundEstimation.date.desc())
            .first()
        )

        # 本地无估值，触发一次拉取
        if not est:
            fetch_fund_estimation(code)
            est = (
                session.query(FundEstimation)
                .filter(FundEstimation.code == code)
                .order_by(FundEstimation.date.desc())
                .first()
            )

        return {
            'code': code,
            'name': basic.name or '',
            'full_name': basic.full_name or '',
            'fund_type': basic.fund_type or '',
            'company': basic.company or '',
            'manager': basic.manager or '',
            'setup_date': basic.setup_date or '',
            'scale': basic.scale or '',
            'benchmark': basic.benchmark or '',
            'strategy': basic.strategy or '',
            'nav': est.nav if est else None,
            'nav_date': est.date if est else '',
            'est_nav': est.est_nav if est else None,
            'est_pct': est.est_pct if est else None,
            'update_time': est.update_time if est else '',
        }
    finally:
        session.close()


def get_fund_nav_history(code: str, period: str = '1年') -> List[dict]:
    """获取基金历史净值 — 先确保缓存新鲜，再从 DB 查询"""
    ensure_nav_history(code)
    return get_nav_history_from_db(code, period)
