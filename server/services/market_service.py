"""行情服务：桥接 a_stock_db 查询层"""
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Optional, Set
from sqlalchemy import desc, func, text

from a_stock_db import StockBasic, StockDaily, StockMinute, StockRealtime, ETFBasic, ETFDaily, StockIndexComponents
from a_stock_db.database import db


# ---------- 指数成分股筛选缓存 ----------
_INDEX_CACHE_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'index_components_cache.json')
_index_components_cache: dict = {'codes': set(), 'updated_at': 0}


def _load_index_cache_from_file() -> Set[str]:
    """从本地JSON缓存文件加载成分股代码"""
    try:
        with open(_INDEX_CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get('codes', []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def _save_index_cache_to_file(codes: Set[str]):
    """保存成分股代码到本地JSON缓存文件"""
    os.makedirs(os.path.dirname(_INDEX_CACHE_FILE), exist_ok=True)
    with open(_INDEX_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump({'codes': sorted(list(codes)), 'updated_at': datetime.now().isoformat()}, f)


def _get_index_component_codes() -> Set[str]:
    """获取中证500 + 沪深300 成分股代码（带1小时缓存）"""
    now = time.time()
    if _index_components_cache['codes'] and _index_components_cache['updated_at'] > now - 3600:
        return _index_components_cache['codes']

    index_codes = {'000300', '000905'}  # 沪深300, 中证500
    codes = set()

    # 1. 先查DB
    session = db.get_session()
    try:
        rows = session.query(StockIndexComponents.股票代码).filter(
            StockIndexComponents.指数代码.in_(index_codes)
        ).distinct().all()
        codes = {r[0] for r in rows}
    finally:
        session.close()

    # 2. DB为空时，查本地JSON缓存
    if not codes:
        codes = _load_index_cache_from_file()

    # 3. 本地缓存也为空时，从akshare获取并保存
    if not codes:
        try:
            import akshare as ak
            for symbol in index_codes:
                df = ak.index_stock_cons_weight_csindex(symbol=symbol)
                codes.update(str(c).zfill(6) for c in df['成分券代码'].tolist())
            _save_index_cache_to_file(codes)
        except Exception:
            pass

    _index_components_cache['codes'] = codes
    _index_components_cache['updated_at'] = now
    return codes


def search_stocks(keyword: str, limit: int = 20) -> List[dict]:
    """搜索股票/ETF：按代码或名称模糊匹配"""
    session = db.get_session()
    try:
        pattern = f"%{keyword}%"
        # 查股票
        stock_rows = (
            session.query(StockBasic)
            .filter(
                (StockBasic.code.like(pattern))
                | (StockBasic.股票简称.like(pattern))
            )
            .limit(limit)
            .all()
        )
        results = [
            {"code": r.code, "name": r.股票简称 or "", "type": r.type}
            for r in stock_rows
        ]
        # 查 ETF（数量不足 limit 时补充）
        remaining = limit - len(results)
        if remaining > 0:
            etf_rows = (
                session.query(ETFBasic)
                .filter(
                    (ETFBasic.code.like(pattern))
                    | (ETFBasic.name.like(pattern))
                )
                .limit(remaining)
                .all()
            )
            for r in etf_rows:
                results.append({"code": r.code, "name": r.name or "", "type": "etf"})
        return results
    finally:
        session.close()


def get_stock_name(code: str) -> Optional[str]:
    """获取股票/ETF名称：先查 StockBasic，fallback 查 ETFBasic"""
    session = db.get_session()
    try:
        row = session.query(StockBasic).filter(StockBasic.code == code).first()
        if row and row.股票简称:
            return row.股票简称
        # fallback: ETF
        etf = session.query(ETFBasic).filter(ETFBasic.code == code).first()
        return etf.name if etf else None
    finally:
        session.close()


def get_daily(
    code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 120,
) -> List[dict]:
    """获取日 K 线数据（日期升序，用于图表渲染）
    先查 StockDaily，fallback 查 ETFDaily
    """
    session = db.get_session()
    try:
        # 先尝试股票日线
        model = StockDaily
        query = session.query(StockDaily).filter(StockDaily.code == code)
        if start_date:
            query = query.filter(StockDaily.日期 >= start_date)
        if end_date:
            query = query.filter(StockDaily.日期 <= end_date)
        rows = query.order_by(desc(StockDaily.日期)).limit(limit).all()

        # fallback: ETF
        if not rows:
            query = session.query(ETFDaily).filter(ETFDaily.code == code)
            if start_date:
                query = query.filter(ETFDaily.日期 >= start_date)
            if end_date:
                query = query.filter(ETFDaily.日期 <= end_date)
            rows = query.order_by(desc(ETFDaily.日期)).limit(limit).all()

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
    """批量获取股票/ETF行情（从 StockDaily/ETFDaily 取最新收盘数据）"""
    session = db.get_session()
    try:
        results = []
        for code in codes:
            # 获取名称：先查 StockBasic，fallback ETFBasic
            basic = (
                session.query(StockBasic)
                .filter(StockBasic.code == code)
                .first()
            )
            if basic and basic.股票简称:
                name = basic.股票简称
            else:
                etf_basic = session.query(ETFBasic).filter(ETFBasic.code == code).first()
                name = etf_basic.name if etf_basic else code

            # 获取最新日 K：先查 StockDaily，fallback ETFDaily
            latest = (
                session.query(StockDaily)
                .filter(StockDaily.code == code)
                .order_by(desc(StockDaily.日期))
                .first()
            )
            prev = None
            if latest:
                prev = (
                    session.query(StockDaily)
                    .filter(
                        StockDaily.code == code,
                        StockDaily.日期 < latest.日期,
                    )
                    .order_by(desc(StockDaily.日期))
                    .first()
                )
            else:
                # fallback: ETF
                latest = (
                    session.query(ETFDaily)
                    .filter(ETFDaily.code == code)
                    .order_by(desc(ETFDaily.日期))
                    .first()
                )
                if latest:
                    prev = (
                        session.query(ETFDaily)
                        .filter(
                            ETFDaily.code == code,
                            ETFDaily.日期 < latest.日期,
                        )
                        .order_by(desc(ETFDaily.日期))
                        .first()
                    )

            if not latest:
                results.append(
                    {"code": code, "name": name, "close": None, "change_pct": None}
                )
                continue

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


# ---------- 字段映射：sort_by 参数 → StockDaily 列 ----------
_SORT_MAP = {
    "pct_change": StockDaily.涨跌幅,
    "close": StockDaily.收盘,
    "volume": StockDaily.成交量,
    "turnover": StockDaily.成交额,
    "open": StockDaily.开盘,
    "high": StockDaily.最高,
    "low": StockDaily.最低,
}


# ---------- 唐奇安通道筛选 ----------
def _filter_boll_breakout(session, codes: Set[str], target_date: datetime, recent_3_dates: set) -> Set[str]:
    """从唐奇安突破股票中，筛选近3天同时突破布林上轨(MA20+2*STD20)的代码"""
    if not codes:
        return set()

    target_str = target_date.strftime('%Y-%m-%d')
    start_3d = (target_date - timedelta(days=5)).strftime('%Y-%m-%d')

    code_list = list(codes)
    placeholders = ','.join(f':c{i}' for i in range(len(code_list)))
    params = {f'c{i}': c for i, c in enumerate(code_list)}
    params['start_3d'] = start_3d
    params['target_date'] = target_str

    # 布林上轨 = MA(20) + 2 * STD(20)，利用 VAR = E[X²] - (E[X])²
    sql_boll = text(f"""
        SELECT t.code, date(t.日期) as dt, t.收盘 as close,
          (SELECT ma + 2.0 * CASE WHEN var > 0 THEN SQRT(var) ELSE 0 END
           FROM (SELECT AVG(sd.收盘) as ma,
                        AVG(sd.收盘 * sd.收盘) - AVG(sd.收盘) * AVG(sd.收盘) as var
                 FROM stock_daily sd
                 WHERE sd.code = t.code AND sd.日期 < t.日期
                   AND sd.日期 >= date(t.日期, '-40 days'))) as boll_upper
        FROM stock_daily t
        WHERE t.code IN ({placeholders})
          AND t.日期 >= :start_3d AND t.日期 <= :target_date
    """)
    rows = session.execute(sql_boll, params).fetchall()

    result = set()
    for r in rows:
        if r.dt in recent_3_dates and r.boll_upper is not None:
            if r.close >= r.boll_upper:
                result.add(r.code)
    return result


def get_donchian_breakout_codes(target_date: datetime, filter_type: str) -> Set[str]:
    """返回符合唐奇安通道突破条件的股票代码集合

    filter_type:
      breakout_3d        — 近3个交易日收盘价突破20日Donchian上轨
      boll_breakout_3d   — 近3个交易日收盘价同时突破唐奇安上轨+布林上轨
      first_breakout     — 在 breakout_3d 基础上，之前有过破位(跌破下轨)且本次是破位后首次突破
      first_boll_breakout — 在 first_breakout 基础上，同时突破布林上轨
    """
    session = db.get_session()
    try:
        target_str = target_date.strftime('%Y-%m-%d')
        # 近3个交易日（用 -5 日历天覆盖周末/节假日）
        start_3d = (target_date - timedelta(days=5)).strftime('%Y-%m-%d')

        # 第一步：获取近3天数据 + 唐奇安上/下轨
        # 使用相关子查询，利用 uq_code_date 唯一索引加速
        sql_3d = text("""
            SELECT t.code, date(t.日期) as dt, t.收盘 as close,
              (SELECT MAX(sd.最高) FROM stock_daily sd
               WHERE sd.code = t.code AND sd.日期 < t.日期
                 AND sd.日期 >= date(t.日期, '-40 days')) as upper_band,
              (SELECT MIN(sd.最低) FROM stock_daily sd
               WHERE sd.code = t.code AND sd.日期 < t.日期
                 AND sd.日期 >= date(t.日期, '-40 days')) as lower_band
            FROM stock_daily t
            WHERE t.日期 >= :start_3d AND t.日期 <= :target_date
        """)
        rows = session.execute(sql_3d, {'start_3d': start_3d, 'target_date': target_str}).fetchall()

        # 按股票分组，找近3天突破的代码
        stock_data = defaultdict(list)
        for r in rows:
            if r.upper_band is not None:
                stock_data[r.code].append({
                    'date': r.dt,
                    'close': r.close,
                    'upper': r.upper_band,
                    'lower': r.lower_band,
                })

        # 获取最近3个交易日（从所有数据中取最大的3个日期）
        all_dates = sorted({r.dt for r in rows}, reverse=True)
        recent_3_dates = set(all_dates[:3])

        breakout_codes = set()
        for code, bars in stock_data.items():
            for bar in bars:
                if bar['date'] in recent_3_dates and bar['close'] > bar['upper']:
                    breakout_codes.add(code)
                    break

        if filter_type == 'breakout_3d':
            return breakout_codes

        if filter_type == 'boll_breakout_3d':
            return _filter_boll_breakout(session, breakout_codes, target_date, recent_3_dates)

        # 第二步：first_breakout — 对突破股票回查60天历史
        if not breakout_codes:
            return set()

        lookback_60 = (target_date - timedelta(days=90)).strftime('%Y-%m-%d')
        code_list = list(breakout_codes)
        placeholders = ','.join(f':c{i}' for i in range(len(code_list)))
        params = {f'c{i}': c for i, c in enumerate(code_list)}
        params['lookback'] = lookback_60
        params['target_date'] = target_str

        sql_60_final = text(f"""
            SELECT t.code, date(t.日期) as dt, t.收盘 as close,
              (SELECT MAX(sd.最高) FROM stock_daily sd
               WHERE sd.code = t.code AND sd.日期 < t.日期
                 AND sd.日期 >= date(t.日期, '-40 days')) as upper_band,
              (SELECT MIN(sd.最低) FROM stock_daily sd
               WHERE sd.code = t.code AND sd.日期 < t.日期
                 AND sd.日期 >= date(t.日期, '-40 days')) as lower_band
            FROM stock_daily t
            WHERE t.code IN ({placeholders})
              AND t.日期 >= :lookback AND t.日期 <= :target_date
            ORDER BY t.code, t.日期
        """)
        rows_60 = session.execute(sql_60_final, params).fetchall()

        # 按股票分组
        history = defaultdict(list)
        for r in rows_60:
            if r.upper_band is not None:
                history[r.code].append({
                    'date': r.dt,
                    'close': r.close,
                    'upper': r.upper_band,
                    'lower': r.lower_band,
                })

        # 对每个突破股票，检查破位后首次突破条件
        result = set()
        for code in breakout_codes:
            bars = history.get(code, [])
            if len(bars) < 2:
                continue

            # 找最近3天中的第一个突破日期
            first_breakout_idx = None
            for i in range(len(bars) - 1, -1, -1):
                if bars[i]['date'] in recent_3_dates and bars[i]['close'] > bars[i]['upper']:
                    first_breakout_idx = i

            if first_breakout_idx is None:
                continue

            # 从突破日往前找：必须先遇到破位，且中间没有突破
            found_breakdown = False
            for i in range(first_breakout_idx - 1, -1, -1):
                bar = bars[i]
                if bar['close'] > bar['upper']:
                    # 中间有突破 → 不是首次突破
                    found_breakdown = False
                    break
                if bar['lower'] is not None and bar['close'] < bar['lower']:
                    # 找到破位
                    found_breakdown = True
                    break

            if found_breakdown:
                result.add(code)

        if filter_type == 'first_breakout':
            return result

        if filter_type == 'first_boll_breakout':
            return _filter_boll_breakout(session, result, target_date, recent_3_dates)

        return result
    finally:
        session.close()


def get_stock_list(
    date: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "pct_change",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 50,
    donchian_filter: Optional[str] = None,
    index_filter: Optional[str] = None,
) -> dict:
    """获取股票列表（支持搜索、排序、分页、唐奇安通道筛选、指数成分股筛选）"""
    session = db.get_session()
    try:
        # 日期：默认取数据库最新交易日
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            latest = session.query(func.max(StockDaily.日期)).scalar()
            target_date = latest or datetime.now()

        # 唐奇安通道筛选：获取符合条件的股票代码集合
        donchian_codes = None
        if donchian_filter and donchian_filter != 'all':
            donchian_codes = get_donchian_breakout_codes(target_date, donchian_filter)
            if not donchian_codes:
                return {"data": [], "total": 0, "page": page, "page_size": page_size}

        # 指数成分股筛选
        index_codes = None
        if index_filter and index_filter == 'csi500_hs300':
            index_codes = _get_index_component_codes()
            if not index_codes:
                return {"data": [], "total": 0, "page": page, "page_size": page_size}

        # 基础查询：StockDaily JOIN StockBasic
        query = (
            session.query(StockDaily, StockBasic)
            .join(StockBasic, StockDaily.code == StockBasic.code)
            .filter(StockDaily.日期 == target_date)
        )

        # 唐奇安通道代码过滤
        if donchian_codes is not None:
            query = query.filter(StockDaily.code.in_(donchian_codes))

        # 指数成分股代码过滤
        if index_codes is not None:
            query = query.filter(StockDaily.code.in_(index_codes))

        # 搜索：代码或名称模糊匹配
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                (StockDaily.code.like(pattern))
                | (StockBasic.股票简称.like(pattern))
            )

        # 总数
        total = query.count()

        # 排序
        sort_col = _SORT_MAP.get(sort_by, StockDaily.涨跌幅)
        if sort_order == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        # 分页
        offset = (page - 1) * page_size
        rows = query.offset(offset).limit(page_size).all()

        data = []
        for daily, basic in rows:
            data.append({
                "code": daily.code,
                "name": basic.股票简称 or "",
                "date": daily.日期.strftime("%Y-%m-%d") if daily.日期 else "",
                "open": daily.开盘,
                "close": daily.收盘,
                "high": daily.最高,
                "low": daily.最低,
                "volume": daily.成交量,
                "turnover": daily.成交额,
                "pct_change": daily.涨跌幅,
            })

        return {
            "data": data,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    finally:
        session.close()
