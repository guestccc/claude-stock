"""
ETF 数据获取器
支持：基础信息同步、日线行情拉取、实时行情获取
"""
import time
import json
import re
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy import func
from a_stock_db.database import db, to_json, ETFBasic, ETFDaily
from a_stock_db.config import REQUEST_DELAY


def _build_etf_daily_dict(code: str, row: pd.Series) -> dict:
    """将 akshare ETF 日线记录构建为数据库写入格式"""
    trade_date = pd.to_datetime(row['日期'])
    return {
        "code": code,
        "日期": trade_date,
        "开盘": float(row['开盘']) if pd.notna(row['开盘']) else None,
        "收盘": float(row['收盘']) if pd.notna(row['收盘']) else None,
        "最高": float(row['最高']) if pd.notna(row['最高']) else None,
        "最低": float(row['最低']) if pd.notna(row['最低']) else None,
        "成交量": float(row['成交量']) if pd.notna(row['成交量']) else None,
        "成交额": float(row['成交额']) if pd.notna(row['成交额']) else None,
        "振幅": float(row['振幅']) if pd.notna(row['振幅']) else None,
        "涨跌幅": float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else None,
        "涨跌额": float(row['涨跌额']) if pd.notna(row['涨跌额']) else None,
        "换手率": float(row['换手率']) if pd.notna(row['换手率']) else None,
        "created_at": datetime.now(),
        "raw_data": to_json(row.to_dict()),
    }


def _upsert_etf_daily(session, daily: dict):
    """ETF 日线数据 upsert"""
    stmt = insert(ETFDaily).values(**daily)
    stmt = stmt.on_conflict_do_update(
        index_elements=['code', '日期'],
        set_={
            "开盘": daily["开盘"],
            "收盘": daily["收盘"],
            "最高": daily["最高"],
            "最低": daily["最低"],
            "成交量": daily["成交量"],
            "成交额": daily["成交额"],
            "振幅": daily["振幅"],
            "涨跌幅": daily["涨跌幅"],
            "涨跌额": daily["涨跌额"],
            "换手率": daily["换手率"],
            "raw_data": daily["raw_data"],
        }
    )
    session.execute(stmt)


def _parse_pct(value) -> float | None:
    """解析百分比字符串（如 '-1.66%' → -1.66）"""
    if value is None or value == '---' or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        # 去掉 % 符号
        cleaned = str(value).replace('%', '').strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def fetch_etf_basic() -> dict:
    """
    全量同步 ETF 基础信息
    来源: akshare.fund_etf_fund_daily_em()
    :return: {'success': 成功写入数, 'total': 总数}
    """
    import akshare as ak

    print("=" * 50)
    print("同步 ETF 基础信息...")
    print("=" * 50)

    try:
        df = ak.fund_etf_fund_daily_em()
    except Exception as e:
        print(f"  获取失败: {e}")
        return {'success': 0, 'total': 0, 'error': str(e)}

    if df is None or df.empty:
        print("  返回空数据")
        return {'success': 0, 'total': 0}

    # 确定净值日期列（列名格式: 'YYYY-MM-DD-单位净值'）
    date_cols = [c for c in df.columns if re.match(r'^\d{4}-\d{2}-\d{2}-单位净值$', str(c))]
    nav_date = date_cols[0].replace('-单位净值', '') if date_cols else None

    session = db.get_session()
    success_count = 0

    try:
        for _, row in df.iterrows():
            # 基金简称列名可能不同版本有差异
            name = row.get('基金简称', '')
            etf_type = row.get('类型', '')

            # 净值字段
            nav_col = f'{nav_date}-单位净值' if nav_date else None
            acc_nav_col = f'{nav_date}-累计净值' if nav_date else None
            prev_nav_col = None
            for c in df.columns:
                if re.match(r'^\d{4}-\d{2}-\d{2}-单位净值$', str(c)) and c != nav_col:
                    prev_nav_col = c
                    break

            nav = None
            acc_nav = None
            if nav_col and nav_col in row.index:
                v = row[nav_col]
                nav = float(v) if pd.notna(v) and str(v) != '---' else None
            if acc_nav_col and acc_nav_col in row.index:
                v = row[acc_nav_col]
                acc_nav = float(v) if pd.notna(v) and str(v) != '---' else None

            # 市价和折价率
            market_price = None
            discount_rate = None
            if '市价' in row.index:
                v = row['市价']
                market_price = float(v) if pd.notna(v) and str(v) != '---' else None
            if '折价率' in row.index:
                discount_rate = _parse_pct(row['折价率'])

            fund = {
                'code': str(row['基金代码']).strip(),
                'name': str(name).strip() if name else '',
                'etf_type': str(etf_type).strip() if etf_type else '',
                'nav': nav,
                'acc_nav': acc_nav,
                'market_price': market_price,
                'discount_rate': discount_rate,
                'updated_at': datetime.now(),
                'raw_data': to_json(row.to_dict()),
            }

            stmt = insert(ETFBasic).values(**fund)
            stmt = stmt.on_conflict_do_update(
                index_elements=['code'],
                set_={
                    'name': fund['name'],
                    'etf_type': fund['etf_type'],
                    'nav': fund['nav'],
                    'acc_nav': fund['acc_nav'],
                    'market_price': fund['market_price'],
                    'discount_rate': fund['discount_rate'],
                    'updated_at': fund['updated_at'],
                    'raw_data': fund['raw_data'],
                }
            )
            session.execute(stmt)
            success_count += 1

        session.commit()
        print(f"  写入 {success_count}/{len(df)} 只 ETF")
        return {'success': success_count, 'total': len(df)}

    except Exception as e:
        session.rollback()
        print(f"  数据库写入失败: {e}")
        return {'success': 0, 'total': len(df), 'error': str(e)}
    finally:
        session.close()


def _get_sina_symbol(code: str) -> str:
    """ETF 代码 → 新浪 symbol"""
    if code.startswith(('51', '56', '58')):
        return f'sh{code}'
    return f'sz{code}'


def fetch_etf_daily(code: str, start_date: str = None, end_date: str = None) -> bool:
    """
    获取单只 ETF 日线数据（新浪财经，东方财富易限流）
    :param code: ETF 代码（如 510300）
    :param start_date: 开始日期 YYYY-MM-DD
    :param end_date: 结束日期 YYYY-MM-DD
    """
    import akshare as ak

    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    sina_symbol = _get_sina_symbol(code)

    try:
        df = ak.fund_etf_hist_sina(symbol=sina_symbol)
    except Exception as e:
        print(f"  {code} 获取失败: {e}")
        return False

    if df is None or df.empty:
        return False

    # 日期范围过滤（确保类型一致）
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    if df.empty:
        return False

    # 计算涨跌幅/涨跌额/振幅（需要 prev_close）
    prev_close = None

    session = db.get_session()
    try:
        for _, row in df.iterrows():
            close_p = float(row['close']) if pd.notna(row['close']) else None

            pct_change = None
            change = None
            amplitude = None
            if prev_close and prev_close > 0 and close_p is not None:
                pct_change = (close_p - prev_close) / prev_close * 100
                change = close_p - prev_close
                high_p = float(row['high']) if pd.notna(row['high']) else None
                low_p = float(row['low']) if pd.notna(row['low']) else None
                if high_p is not None and low_p is not None:
                    amplitude = (high_p - low_p) / prev_close * 100

            if close_p is not None:
                prev_close = close_p

            daily = {
                "code": code,
                "日期": pd.to_datetime(row['date']),
                "开盘": float(row['open']) if pd.notna(row['open']) else None,
                "收盘": close_p,
                "最高": float(row['high']) if pd.notna(row['high']) else None,
                "最低": float(row['low']) if pd.notna(row['low']) else None,
                "成交量": float(row['volume']) if pd.notna(row['volume']) else None,
                "成交额": float(row['amount']) if pd.notna(row['amount']) else None,
                "振幅": amplitude,
                "涨跌幅": pct_change,
                "涨跌额": change,
                "换手率": None,
                "created_at": datetime.now(),
                "raw_data": to_json(row.to_dict()),
            }
            _upsert_etf_daily(session, daily)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"  {code} 写入失败: {e}")
        return False
    finally:
        session.close()


def fetch_etf_daily_incremental(code: str, delay: float = REQUEST_DELAY) -> str:
    """
    增量获取单只 ETF 日线数据
    :param code: ETF 代码
    :param delay: 请求间隔
    :return: 成功返回 True，失败返回原因
    """
    session = db.get_session()
    try:
        latest_date = session.query(func.max(ETFDaily.日期)).filter(
            ETFDaily.code == code
        ).scalar()

        today = datetime.now().date()

        if latest_date:
            latest_date_only = latest_date.date()
            if latest_date_only >= today:
                session.close()
                return "已是最新"

        if latest_date:
            start = (latest_date.date() + timedelta(days=1)).strftime('%Y-%m-%d')
            end = today.strftime('%Y-%m-%d')
        else:
            start = (today - timedelta(days=365)).strftime('%Y-%m-%d')  # ETF 历史比股票短，默认拉1年
            end = today.strftime('%Y-%m-%d')

        session.close()

        result = fetch_etf_daily(code, start, end)
        time.sleep(delay)
        return True if result else "无数据"

    except Exception as e:
        session.close()
        return f"{type(e).__name__}: {str(e)[:50]}"


def fetch_all_etf_daily(
    limit: int = None,
    delay: float = REQUEST_DELAY,
) -> dict:
    """
    批量增量获取全部 ETF 日线数据
    :param limit: 限制数量
    :param delay: 请求间隔
    :return: {'success': 成功数, 'failed': [...], 'total': 总数}
    """
    session = db.get_session()
    etfs = session.query(ETFBasic).all()
    session.close()

    if not etfs:
        print("ETF 基础信息为空，请先运行: python3 -m a_stock_fetcher.cli etf-basic")
        return {'success': 0, 'failed': [], 'total': 0}

    if limit:
        etfs = etfs[:limit]

    print("=" * 50)
    print(f"批量增量获取 ETF 日线数据: {len(etfs)} 只")
    print("=" * 50)

    success_count = 0
    failed = []

    for i, etf in enumerate(etfs):
        print(f"[{i+1}/{len(etfs)}] {etf.code} {etf.name} ...", end=' ', flush=True)
        result = fetch_etf_daily_incremental(etf.code, delay=delay)
        if result is True or result == "已是最新":
            success_count += 1
            print("已是最新" if result == "已是最新" else "OK")
        else:
            failed.append({'code': etf.code, 'name': etf.name, 'reason': str(result)})
            print(f"FAIL ({result})")
        time.sleep(delay)

    print(f"\n成功: {success_count}/{len(etfs)}")
    if failed:
        print(f"失败 {len(failed)} 只:")
        for f in failed[:10]:
            print(f"  {f['code']} {f['name']}: {f['reason']}")

    return {'success': success_count, 'failed': failed, 'total': len(etfs)}


def fetch_etf_daily_full_history(code: str, delay: float = REQUEST_DELAY) -> str:
    """
    获取单只 ETF 全部历史日线数据
    :param code: ETF 代码
    :param delay: 请求间隔
    :return: 成功返回 True，已有完整数据返回提示，失败返回原因
    """
    session = db.get_session()
    try:
        # 检查已有数据
        latest_date = session.query(func.max(ETFDaily.日期)).filter(
            ETFDaily.code == code
        ).scalar()

        today = datetime.now().date()

        if latest_date and latest_date.date() >= today:
            count = session.query(ETFDaily).filter(ETFDaily.code == code).count()
            session.close()
            return f"已有完整数据 ({count} 条)"

        session.close()
    except Exception:
        session.close()

    # 新浪接口直接返回全部历史，无需指定起始日期
    start_date = '2000-01-01'
    end_date = today.strftime('%Y-%m-%d')

    print(f"  {code} 拉取全部历史 ...", end=' ', flush=True)
    result = fetch_etf_daily(code, start_date, end_date)
    if result:
        print("OK")
        time.sleep(delay)
        return True
    else:
        print("FAIL")
        return "无数据"


def fetch_etf_realtime_ths() -> pd.DataFrame | None:
    """
    获取 ETF 实时行情（同花顺）
    :return: DataFrame 或 None
    """
    import akshare as ak
    try:
        df = ak.fund_etf_spot_ths()
        return df
    except Exception as e:
        print(f"获取 ETF 实时行情失败: {e}")
        return None


if __name__ == '__main__':
    # 测试
    print("测试 fetch_etf_basic...")
    result = fetch_etf_basic()
    print(result)
