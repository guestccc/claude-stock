"""板块行情服务 — 行业板块(新浪) + 概念板块(同花顺)"""
import re
import json
import time
import requests
import akshare as ak
import pandas as pd
from typing import List, Optional
from datetime import datetime, timedelta
from lxml import html as lxml_html
from a_stock_db import StockBasic
from a_stock_db.database import db
from server.db.models import BoardWatchlist, BoardConceptDaily


# ---------- 缓存 ----------
_industry_cache: dict = {'data': [], 'updated_at': 0}
_concept_cache: dict = {'data': [], 'updated_at': 0}

HEADERS_SINA = {
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://finance.sina.com.cn',
}
HEADERS_THS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    'Referer': 'https://q.10jqka.com.cn/',
}

SINA_HY_URL = 'https://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php'
THS_GN_URL = 'https://q.10jqka.com.cn/gn/'


# ---------- 行业板块 ----------
def _fetch_industry_boards() -> List[dict]:
    """从新浪拉取行业板块实时数据"""
    resp = requests.get(SINA_HY_URL, headers=HEADERS_SINA, timeout=10)
    resp.raise_for_status()
    match = re.search(r'= ({.+})', resp.text)
    if not match:
        return []
    data = json.loads(match.group(1))

    results = []
    for key, val in data.items():
        parts = val.split(',')
        if len(parts) < 13:
            continue
        try:
            results.append({
                'code': key,
                'name': parts[1],
                'stock_count': int(parts[2]),
                'avg_price': round(float(parts[3]), 2),
                'change': round(float(parts[4]), 2),
                'change_pct': round(float(parts[5]), 2),
                'volume': int(parts[6]),
                'amount': int(parts[7]),
                'lead_stock_code': parts[8],
                'lead_stock_price': round(float(parts[9]), 2),
                'lead_stock_change': round(float(parts[10]), 2),
                'lead_stock_change_pct': round(float(parts[11]), 2),
                'lead_stock_name': parts[12],
            })
        except (ValueError, IndexError):
            continue

    results.sort(key=lambda x: x['change_pct'], reverse=True)
    return results


def get_industry_boards(cache_minutes: int = 2) -> List[dict]:
    """获取行业板块数据（带缓存）"""
    now = time.time()
    if _industry_cache['data'] and _industry_cache['updated_at'] > now - cache_minutes * 60:
        return _industry_cache['data']

    data = _fetch_industry_boards()
    if data:
        _industry_cache['data'] = data
        _industry_cache['updated_at'] = now
    return data


# ---------- 概念板块 ----------
def _fetch_concept_boards() -> List[dict]:
    """从同花顺拉取概念板块实时数据（解析 gnSection input value）"""
    resp = requests.get(THS_GN_URL, headers=HEADERS_THS, timeout=10)
    resp.encoding = 'gbk'
    tree = lxml_html.fromstring(resp.text)
    inputs = tree.xpath('//input[@id="gnSection"]')
    if not inputs:
        return []

    val = inputs[0].get('value', '')
    if not val:
        return []

    data = json.loads(val)
    results = []
    for key, item in data.items():
        try:
            lead_code = item.get('cid', '').strip()
            results.append({
                'code': item.get('platecode', ''),
                'name': item.get('platename', ''),
                'change_pct': float(item.get('199112', 0)),
                'net_inflow': float(item.get('zjjlr', 0)),
                'strength': int(item.get('zfl', 0)),
                'lead_stock_code': lead_code,
            })
        except (ValueError, TypeError):
            continue

    results.sort(key=lambda x: x['change_pct'], reverse=True)

    # 从数据库批量补全领涨股名称
    lead_codes = [r['lead_stock_code'] for r in results if r['lead_stock_code']]
    if lead_codes:
        session = db.get_session()
        try:
            rows = session.query(StockBasic.code, StockBasic.股票简称).filter(
                StockBasic.code.in_(lead_codes)
            ).all()
            name_map = {r.code: r.股票简称 for r in rows}
        finally:
            session.close()
        for r in results:
            if r['lead_stock_code'] in name_map:
                r['lead_stock_name'] = name_map[r['lead_stock_code']]

    return results


def get_concept_boards(cache_minutes: int = 2) -> List[dict]:
    """获取概念板块数据（带缓存）"""
    now = time.time()
    if _concept_cache['data'] and _concept_cache['updated_at'] > now - cache_minutes * 60:
        return _concept_cache['data']

    data = _fetch_concept_boards()
    if data:
        _concept_cache['data'] = data
        _concept_cache['updated_at'] = now
    return data


# ---------- 刷新 ----------
def refresh_industry_boards() -> dict:
    """强制刷新行业板块"""
    data = _fetch_industry_boards()
    if data:
        _industry_cache['data'] = data
        _industry_cache['updated_at'] = time.time()
    return {'total': len(data), 'updated_at': datetime.now().strftime('%H:%M:%S')}


def refresh_concept_boards() -> dict:
    """强制刷新概念板块"""
    data = _fetch_concept_boards()
    if data:
        _concept_cache['data'] = data
        _concept_cache['updated_at'] = time.time()
    return {'total': len(data), 'updated_at': datetime.now().strftime('%H:%M:%S')}


# ---------- 概念板块 K 线 ----------
_kline_cache: dict = {}  # key: name_period -> {data, updated_at}

# platecode → akshare 概念名称映射（懒加载，1小时缓存）
_ths_name_map: dict = {'map': {}, 'updated_at': 0}


def _ensure_ths_name_map():
    """确保 platecode → akshare_name 映射已加载"""
    now = time.time()
    if _ths_name_map['map'] and _ths_name_map['updated_at'] > now - 3600:
        return _ths_name_map['map']
    df = ak.stock_board_concept_name_ths()
    m = {}
    for _, row in df.iterrows():
        m[str(row['code'])] = row['name']
    _ths_name_map['map'] = m
    _ths_name_map['updated_at'] = now
    return m


def _resolve_concept_name(name: str, code: str) -> str:
    """将 gnSection 的名称解析为 akshare 的概念名称

    仅做安全匹配：platecode 精确匹配 > 精确同名 > 返回原名
    （不做模糊匹配，因为可能匹配到完全无关的板块）
    """
    m = _ensure_ths_name_map()
    # 1. 精确 platecode 匹配
    if code in m:
        return m[code]
    # 2. 精确同名匹配
    if name in m.values():
        return name
    # 3. 返回原名（akshare 大概率无数据，前端友好提示）
    return name


# 周期 → 开始日期映射
_PERIOD_MAP = {
    'Y1': 365,
    'Y3': 365 * 3,
    'Y5': 365 * 5,
    'ALL': 365 * 20,  # 够大就行
}


def _query_kline_from_db(name: str, start_date: str, end_date: str) -> List[dict]:
    """从 DB 查询板块 K 线（日期格式 YYYY-MM-DD）"""
    session = db.get_session()
    try:
        rows = session.query(BoardConceptDaily).filter(
            BoardConceptDaily.name == name,
            BoardConceptDaily.date >= start_date,
            BoardConceptDaily.date <= end_date,
        ).order_by(BoardConceptDaily.date.asc()).all()
        return [{
            'date': r.date,
            'open': r.open,
            'close': r.close,
            'high': r.high,
            'low': r.low,
            'volume': r.volume,
            'turnover': r.turnover,
            'pct_change': None,
        } for r in rows]
    finally:
        session.close()


def _save_kline_to_db(name: str, bars: List[dict]):
    """批量写入 K 线，已存在的日期跳过"""
    if not bars:
        return
    session = db.get_session()
    try:
        # 查已存在的日期
        existing_dates = {r.date for r in session.query(BoardConceptDaily.date).filter(
            BoardConceptDaily.name == name,
            BoardConceptDaily.date.in_([b['date'] for b in bars]),
        ).all()}
        new_rows = [
            BoardConceptDaily(
                name=name, date=b['date'],
                open=b['open'], close=b['close'],
                high=b['high'], low=b['low'],
                volume=b['volume'], turnover=b['turnover'],
            )
            for b in bars if b['date'] not in existing_dates
        ]
        if new_rows:
            session.bulk_save_objects(new_rows)
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _fetch_kline_from_akshare(name: str, start_date: str, end_date: str) -> List[dict]:
    """从 akshare 拉取板块 K 线（日期入参格式 YYYYMMDD）"""
    df: pd.DataFrame = ak.stock_board_concept_index_ths(
        symbol=name, start_date=start_date, end_date=end_date
    )
    df = df.dropna(subset=['开盘价', '收盘价', '最高价', '最低价'])

    bars = []
    for _, row in df.iterrows():
        bars.append({
            'date': str(row['日期']),  # akshare 已返回 YYYY-MM-DD
            'open': float(row['开盘价']),
            'close': float(row['收盘价']),
            'high': float(row['最高价']),
            'low': float(row['最低价']),
            'volume': float(row['成交量']),
            'turnover': float(row['成交额']),
            'pct_change': None,
        })
    return bars


def get_concept_kline(name: str, period: str = 'Y1', code: str = '') -> dict:
    """获取概念板块指数日 K 线 — DB 优先，缺数据时调 akshare 增量更新

    name: 概念板块名称（来自 gnSection）
    code: 概念板块代码（platecode），用于映射 akshare 名称
    """
    # 解析 akshare 名称（用于调 akshare 接口和 DB 存储）
    akshare_name = _resolve_concept_name(name, code) if code else name
    cache_key = f'{akshare_name}_{period}'
    now = time.time()
    cached = _kline_cache.get(cache_key)
    if cached and cached['updated_at'] > now - 300:  # 5 分钟内存缓存
        return cached['data']

    days = _PERIOD_MAP.get(period, 365)
    today = datetime.now().strftime('%Y-%m-%d')
    start_dt = datetime.now() - timedelta(days=days)
    start_date = start_dt.strftime('%Y-%m-%d')

    # 1. 查 DB
    db_bars = _query_kline_from_db(akshare_name, start_date, today)

    # 2. 判断是否需要从 akshare 更新
    weekday = datetime.now().weekday()
    is_weekend = weekday >= 5
    db_latest = db_bars[-1]['date'] if db_bars else None
    need_fetch = (not db_bars) or (db_latest < today and not is_weekend)

    if need_fetch:
        if db_bars:
            fetch_start = (datetime.strptime(db_latest, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y%m%d')
        else:
            fetch_start = start_dt.strftime('%Y%m%d')
        fetch_end = datetime.now().strftime('%Y%m%d')

        try:
            new_bars = _fetch_kline_from_akshare(akshare_name, fetch_start, fetch_end)
            if new_bars:
                _save_kline_to_db(akshare_name, new_bars)
                db_bars.extend([b for b in new_bars if b['date'] not in {x['date'] for x in db_bars}])
                db_bars.sort(key=lambda b: b['date'])
        except Exception:
            pass

    result = {'name': name, 'data': db_bars}
    _kline_cache[cache_key] = {'data': result, 'updated_at': now}
    return result


# ---------- 板块关注 ----------
def get_watched_board_codes() -> set:
    """获取所有已关注板块的 code 集合"""
    session = db.get_session()
    try:
        rows = session.query(BoardWatchlist.code).all()
        return {r.code for r in rows}
    finally:
        session.close()


def add_board_watch(code: str, name: str) -> dict:
    """关注板块"""
    session = db.get_session()
    try:
        existing = session.query(BoardWatchlist).filter(BoardWatchlist.code == code).first()
        if existing:
            return {'ok': True, 'msg': 'already exists'}
        session.add(BoardWatchlist(code=code, name=name))
        session.commit()
        return {'ok': True}
    finally:
        session.close()


def remove_board_watch(code: str) -> dict:
    """取消关注板块"""
    session = db.get_session()
    try:
        session.query(BoardWatchlist).filter(BoardWatchlist.code == code).delete()
        session.commit()
        return {'ok': True}
    finally:
        session.close()
