"""
基金实时估值获取
数据来源: 天天基金 fundgz.1234567.com.cn
盘中每分钟更新自选基金估算净值
"""
import re
import time
import json
import pandas as pd
import requests
import akshare as ak
from datetime import datetime
from sqlalchemy.dialects.sqlite import insert
from a_stock_db.database import db, to_json, FundBasic, FundWatchlist, FundEstimation, FundNavHistory

# 天天基金实时估值接口
TTFUND_API = 'https://fundgz.1234567.com.cn/js/{code}.js'
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://fund.eastmoney.com/',
}


def _parse_jsonpgz(text: str) -> dict | None:
    """解析 jsonpgz({...}) 格式响应"""
    match = re.search(r'jsonpgz\((.+)\)', text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def fetch_fund_basic(code: str) -> bool:
    """
    获取单只基金基本信息（蛋卷基金）
    :param code: 基金代码
    :return: 成功返回 True
    """
    session = db.get_session()
    try:
        df = ak.fund_individual_basic_info_xq(symbol=code)
        if df is None or df.empty:
            session.close()
            return False

        info = {str(row['item']): row['value'] for _, row in df.iterrows()}

        fund = {
            'code': code,
            'name': info.get('基金名称', ''),
            'full_name': info.get('基金全称', ''),
            'fund_type': info.get('基金类型', ''),
            'company': info.get('基金公司', ''),
            'manager': info.get('基金经理', ''),
            'setup_date': info.get('成立时间', ''),
            'scale': info.get('最新规模', ''),
            'benchmark': info.get('业绩比较基准', ''),
            'strategy': info.get('投资策略', ''),
            'updated_at': datetime.now(),
            'raw_data': to_json(info)
        }

        stmt = insert(FundBasic).values(**fund)
        stmt = stmt.on_conflict_do_update(
            index_elements=['code'],
            set_={
                'name': fund['name'],
                'full_name': fund['full_name'],
                'fund_type': fund['fund_type'],
                'company': fund['company'],
                'manager': fund['manager'],
                'scale': fund['scale'],
                'benchmark': fund['benchmark'],
                'strategy': fund['strategy'],
                'updated_at': fund['updated_at'],
            }
        )
        session.execute(stmt)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"  基金基本信息获取失败 {code}: {e}")
        return False
    finally:
        session.close()


def fetch_fund_estimation(code: str) -> str:
    """
    获取单只基金实时估值（天天基金）
    :param code: 基金代码
    :return: 成功返回 True，失败返回失败原因字符串
    """
    session = db.get_session()
    try:
        url = TTFUND_API.format(code=code)
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=10)

        data = _parse_jsonpgz(resp.text)
        if data is None:
            session.close()
            return "解析失败"

        # 判断是否有估算数据（有些基金会返回 "--"）
        est_nav = None
        est_pct = None
        if data.get('gsz') and data['gsz'] != '--':
            est_nav = float(data['gsz'])
        if data.get('gszzl') and data['gszzl'] != '--':
            est_pct = float(data['gszzl'])

        estimation = {
            'code': data['fundcode'],
            'name': data['name'],
            'date': data['jzrq'],
            'nav': float(data['dwjz']),
            'acc_nav': None,
            'last_nav': None,
            'est_nav': est_nav,
            'est_pct': est_pct,
            'update_time': data.get('gztime', '').split(' ')[-1] if data.get('gztime') else None,
            'created_at': datetime.now(),
            'raw_data': to_json(data)
        }

        stmt = insert(FundEstimation).values(**estimation)
        stmt = stmt.on_conflict_do_update(
            index_elements=['code', 'date'],
            set_={
                'est_nav': estimation['est_nav'],
                'est_pct': estimation['est_pct'],
                'update_time': estimation['update_time'],
                'raw_data': estimation['raw_data'],
            }
        )
        session.execute(stmt)

        # 同时更新 fund_basic 的名称（天天基金有名称，蛋卷接口可能失败）
        fund_name = data.get('name', '')
        if fund_name:
            basic_stmt = insert(FundBasic).values(code=code, name=fund_name, updated_at=datetime.now())
            basic_stmt = basic_stmt.on_conflict_do_update(
                index_elements=['code'],
                set_={'name': fund_name, 'updated_at': datetime.now()}
            )
            session.execute(basic_stmt)

        session.commit()
        return True

    except Exception as e:
        session.rollback()
        reason = f"{type(e).__name__}: {str(e)[:50]}"
        return reason
    finally:
        session.close()


def fetch_watchlist_estimations() -> dict:
    """
    获取所有自选基金的实时估值
    :return: {'success': 成功数, 'failed': [...], 'total': 总数}
    """
    session = db.get_session()
    try:
        watchlist = session.query(FundWatchlist).all()
        session.close()

        if not watchlist:
            return {'success': 0, 'failed': [], 'total': 0}

        success_count = 0
        failed = []

        for i, item in enumerate(watchlist):
            result = fetch_fund_estimation(item.code)
            if result is True:
                success_count += 1
                print(f"  [{i+1}/{len(watchlist)}] {item.code} ✓")
            else:
                failed.append({'code': item.code, 'reason': result})
                print(f"  [{i+1}/{len(watchlist)}] {item.code} ✗ ({result})")
            time.sleep(0.3)

        return {'success': success_count, 'failed': failed, 'total': len(watchlist)}
    except Exception as e:
        return {'success': 0, 'failed': [{'reason': str(e)}], 'total': 0}


def add_watchlist(code: str, remark: str = '') -> dict:
    """
    添加自选基金
    :param code: 基金代码
    :param remark: 备注
    :return: 结果
    """
    session = db.get_session()
    try:
        # 先获取基金基本信息
        fetch_fund_basic(code)

        # 写入自选
        stmt = insert(FundWatchlist).values(code=code, remark=remark)
        stmt = stmt.on_conflict_do_update(
            index_elements=['code'],
            set_={'remark': remark}
        )
        session.execute(stmt)
        session.commit()

        # 立即获取一次估值
        result = fetch_fund_estimation(code)
        return {'success': True, 'code': code, 'estimation': result}

    except Exception as e:
        session.rollback()
        return {'success': False, 'error': str(e)}
    finally:
        session.close()


def remove_watchlist(code: str) -> bool:
    """移除自选基金"""
    session = db.get_session()
    try:
        n = session.query(FundWatchlist).filter(FundWatchlist.code == code).delete()
        session.commit()
        return n > 0
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()


def get_watchlist_codes() -> list:
    """获取所有自选基金代码"""
    session = db.get_session()
    try:
        items = session.query(FundWatchlist).all()
        return [item.code for item in items]
    finally:
        session.close()


def _fetch_and_cache_nav_history(code: str) -> bool:
    """
    从 akshare 拉取基金全量历史净值，写入 fund_nav_history 缓存表。
    akshare 的 period 参数不生效，始终返回全量，所以这里固定传 '成立来'。
    """
    session = db.get_session()
    try:
        df = ak.fund_open_fund_info_em(symbol=code, indicator='单位净值走势', period='成立来')
        if df is None or df.empty:
            return False

        for _, row in df.iterrows():
            stmt = insert(FundNavHistory).values(
                code=code,
                date=str(row['净值日期'])[:10],
                nav=round(float(row['单位净值']), 4),
                pct_change=round(float(row['日增长率']), 2) if pd.notna(row['日增长率']) else None,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=['code', 'date'],
                set_={'nav': round(float(row['单位净值']), 4)},
            )
            session.execute(stmt)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"基金历史净值缓存失败 {code}: {e}")
        return False
    finally:
        session.close()


def _latest_trading_date() -> str:
    """估算最近一个交易日的日期（简单判断：跳过周末，不考虑节假日）"""
    from datetime import timedelta
    now = datetime.now()
    # 收盘前（15:00 前）取前一交易日，收盘后取当天
    if now.hour >= 15:
        d = now.date()
    else:
        d = (now - timedelta(days=1)).date()
    # 跳过周末
    while d.weekday() >= 5:
        d = d - timedelta(days=1)
    return d.strftime('%Y-%m-%d')


def ensure_nav_history(code: str) -> None:
    """
    检查缓存是否过期，过期则从 akshare 拉取全量数据写库。
    判断标准：fund_nav_history 中该基金最大日期 < 最近交易日。
    """
    session = db.get_session()
    try:
        latest = (
            session.query(FundNavHistory.date)
            .filter(FundNavHistory.code == code)
            .order_by(FundNavHistory.date.desc())
            .first()
        )
        threshold = _latest_trading_date()
        if latest is None or latest[0] < threshold:
            _fetch_and_cache_nav_history(code)
    finally:
        session.close()


def get_recent_nav(code: str, limit: int = 10) -> list[dict]:
    """从缓存表获取最近 N 条历史净值（列表页专用）"""
    session = db.get_session()
    try:
        rows = (
            session.query(FundNavHistory)
            .filter(FundNavHistory.code == code)
            .order_by(FundNavHistory.date.desc())
            .limit(limit)
            .all()
        )
        return [
            {'date': r.date, 'nav': r.nav, 'pct_change': r.pct_change}
            for r in reversed(rows)
        ]
    finally:
        session.close()


def get_nav_history_from_db(code: str, period: str = '1年') -> list[dict]:
    """从缓存表获取历史净值，按 period 裁剪（详情页专用）"""
    from datetime import timedelta

    period_days_map = {
        '1月': 30, '3月': 90, '6月': 180,
        '1年': 365, '3年': 365 * 3, '5年': 365 * 5,
    }

    session = db.get_session()
    try:
        rows = (
            session.query(FundNavHistory)
            .filter(FundNavHistory.code == code)
            .order_by(FundNavHistory.date.asc())
            .all()
        )
        if not rows:
            return []

        all_data = [
            {'date': r.date, 'nav': r.nav, 'pct_change': r.pct_change}
            for r in rows
        ]

        # 按 period 裁剪
        if period == '成立来':
            return all_data
        if period == '今年来':
            year_start = f"{datetime.now().year}-01-01"
            return [d for d in all_data if d['date'] >= year_start]

        days = period_days_map.get(period)
        if days is None:
            return all_data
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        return [d for d in all_data if d['date'] >= cutoff]
    finally:
        session.close()


if __name__ == '__main__':
    # 测试
    result = fetch_fund_nav_history('018957', '1年')
    print(f"结果数量: {len(result)}")
    if result:
        print(f"第一条: {result[0]}")
        print(f"最后一条: {result[-1]}")
