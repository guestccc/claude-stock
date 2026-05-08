"""
日线行情数据获取
数据源通过 provider 适配层切换，默认使用 mxdata（妙想），可配置为 baostock
数据库写入逻辑与数据源解耦
"""
import time
import json
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy import func
from a_stock_db.database import db, StockBasic, StockDaily
from a_stock_db.config import REQUEST_DELAY, DAILY_HISTORY_DAYS
from a_stock_fetcher.providers import get_provider
from .basic import is_enabled


def _build_daily_dict(code: str, record: dict, source: str) -> dict:
    """
    将标准化记录构建为数据库写入格式
    :param code: 股票代码
    :param record: provider 返回的标准化记录 {date, open, close, high, low, volume, amount}
    :param source: 数据源名称（如 "baostock", "mxdata"）
    :return: 数据库记录字典
    """
    trade_date = pd.to_datetime(record['date'])
    return {
        "code": code,
        "日期": trade_date,
        "开盘": record.get('open'),
        "收盘": record.get('close'),
        "最高": record.get('high'),
        "最低": record.get('low'),
        "成交量": record.get('volume'),
        "成交额": record.get('amount'),
        "振幅": None,
        "涨跌幅": None,
        "涨跌额": None,
        "换手率": None,
        "created_at": datetime.now(),
        "raw_data": json.dumps({
            "source": source,
            "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "original_data": record,
        }, ensure_ascii=False),
    }


def _upsert_daily(session, daily: dict):
    """
    单条日线数据 upsert（INSERT OR REPLACE）
    :param session: 数据库会话
    :param daily: _build_daily_dict 返回的记录
    """
    stmt = insert(StockDaily).values(**daily)
    stmt = stmt.on_conflict_do_update(
        index_elements=['code', '日期'],
        set_={
            "开盘": daily["开盘"],
            "收盘": daily["收盘"],
            "最高": daily["最高"],
            "最低": daily["最低"],
            "成交量": daily["成交量"],
            "成交额": daily["成交额"],
            "raw_data": daily["raw_data"],
        }
    )
    session.execute(stmt)


def fetch_stock_daily(code: str, start_date: str = None, end_date: str = None) -> bool:
    """
    获取单只股票日线数据
    :param code: 股票代码
    :param start_date: 开始日期 YYYYMMDD
    :param end_date: 结束日期 YYYYMMDD
    """
    provider = get_provider()

    if start_date:
        ds_start = f'{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}'
    else:
        ds_start = (datetime.now() - timedelta(days=DAILY_HISTORY_DAYS)).strftime('%Y-%m-%d')

    if end_date:
        ds_end = f'{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}'
    else:
        ds_end = datetime.now().strftime('%Y-%m-%d')

    session = db.get_session()

    try:
        records = provider.fetch_daily(code, ds_start, ds_end)
        if not records:
            session.close()
            return False

        for record in records:
            daily = _build_daily_dict(code, record, provider.name())
            _upsert_daily(session, daily)

        session.commit()
        session.close()
        return True

    except Exception as e:
        session.rollback()
        session.close()
        return False


def fetch_all_stocks_daily(limit: int = None, delay: float = REQUEST_DELAY) -> int:
    """批量获取所有股票日线数据"""
    provider = get_provider()
    print("=" * 50)
    print(f"批量获取日线行情数据 (数据源: {provider.name()})...")
    print("=" * 50)

    session = db.get_session()
    stocks = session.query(StockBasic).all()
    session.close()

    if limit:
        stocks = stocks[:limit]

    success_count = 0
    for i, stock in enumerate(stocks):
        print(f"[{i+1}/{len(stocks)}] {stock.code} {stock.股票简称}...", end=' ')
        if fetch_stock_daily(stock.code):
            success_count += 1
            print("✓")
        else:
            print("✗")
        time.sleep(delay)

    print(f"\n成功: {success_count}/{len(stocks)}")
    return success_count


def fetch_stock_daily_incremental(code: str) -> str:
    """
    增量获取单只股票日线数据
    :param code: 股票代码
    :return: 成功返回 True，失败返回失败原因字符串
    """
    provider = get_provider()

    t0 = time.time()
    session = db.get_session()

    try:
        # 查询该股票在数据库中的最新日期
        latest_date = session.query(func.max(StockDaily.日期)).filter(
            StockDaily.code == code
        ).scalar()

        today = datetime.now().date()

        # 判断是否需要获取数据
        if latest_date:
            latest_date_only = latest_date.date()
            if latest_date_only >= today:
                session.close()
                print(f"  {latest_date_only} 已有，跳过({time.time()-t0:.4f}s)")
                return True

        # 确定日期范围（最多获取30天）
        if latest_date:
            start = (latest_date.date() + timedelta(days=1)).strftime('%Y-%m-%d')
            end = today.strftime('%Y-%m-%d')
            print(f"  {latest_date.date()}→增量...", end=' ')
        else:
            start = (today - timedelta(days=30)).strftime('%Y-%m-%d')
            end = today.strftime('%Y-%m-%d')
            print(f"  无历史→近30天...", end=' ')

        t2 = time.time()
        records = provider.fetch_daily(code, start, end)
        t_api = time.time() - t2

        if not records:
            session.close()
            print(f"无数据({t_api:.4f}s)")
            return "无数据"

        # 过滤新数据
        if latest_date:
            records = [r for r in records if pd.to_datetime(r['date']) > latest_date]

        if not records:
            session.close()
            print(f"无新数据({t_api:.4f}s)")
            return True

        t_write_start = time.time()
        count = 0
        for record in records:
            daily = _build_daily_dict(code, record, provider.name())
            _upsert_daily(session, daily)
            count += 1

        t3 = time.time()
        session.commit()
        session.close()
        t_write = t3 - t_write_start
        t_total = time.time() - t0

        per_write = t_write / count if count > 0 else 0
        print(f"新增{count}条({t_total:.4f}s api:{t_api:.4f}s write:{t_write:.4f}s {per_write:.4f}s/条)")
        return True

    except Exception as e:
        session.rollback()
        session.close()
        reason = f"{type(e).__name__}: {str(e)[:50]}"
        print(f"失败: {reason}")
        return reason


def fetch_all_stocks_daily_incremental(codes: list = None, limit: int = None, delay: float = REQUEST_DELAY) -> dict:
    """
    批量增量获取股票日线数据
    支持数据源的批量优化（如妙想可一次查多只）
    :param codes: 指定股票代码列表
    :param limit: 限制数量
    :param delay: 请求间隔
    :return: {'success': 成功数, 'failed': [...]}
    """
    provider = get_provider()
    print("=" * 50)
    print(f"批量增量获取日线行情数据 (数据源: {provider.name()})...")
    print("=" * 50)

    session = db.get_session()

    if codes:
        stocks = session.query(StockBasic).filter(StockBasic.code.in_(codes)).all()
        stocks = [s for s in stocks if is_enabled(s.code)]
        print(f"指定股票: {len(stocks)} 只")
    else:
        all_stocks = session.query(StockBasic).all()
        stocks = [s for s in all_stocks if is_enabled(s.code)]
        skipped = len(all_stocks) - len(stocks)
        if limit:
            stocks = stocks[:limit]
            print(f"限制数量: {limit} 只（已跳过 {skipped} 只北证/创业板/科创板）")
        else:
            print(f"全量: {len(stocks)} 只（已跳过 {skipped} 只北证/创业板/科创板）")

    session.close()

    stock_codes = [s.code for s in stocks]
    stock_map = {s.code: s.股票简称 for s in stocks}

    # 查询每只股票的最新日期
    session = db.get_session()
    latest_dates = {}
    for code in stock_codes:
        latest = session.query(func.max(StockDaily.日期)).filter(
            StockDaily.code == code
        ).scalar()
        latest_dates[code] = latest.date() if latest else None
    session.close()

    today = datetime.now().date()

    # 按需更新分组（跳过已有最新数据的）
    need_update = []
    for code in stock_codes:
        latest = latest_dates.get(code)
        if latest and latest >= today:
            continue
        need_update.append(code)

    if not need_update:
        print(f"所有股票数据已是最新，无需更新")
        return {'success': len(stocks), 'failed': []}

    skipped_fresh = len(stock_codes) - len(need_update)
    if skipped_fresh:
        print(f"已是最新跳过: {skipped_fresh} 只，需更新: {len(need_update)} 只")

    # 确定统一日期范围（取所有需更新股票的最宽范围）
    start_dates = []
    for code in need_update:
        latest = latest_dates.get(code)
        if latest:
            start_dates.append((latest + timedelta(days=1)))
        else:
            start_dates.append(today - timedelta(days=30))

    query_start = min(start_dates).strftime('%Y-%m-%d')
    query_end = today.strftime('%Y-%m-%d')

    # 批量获取数据
    print(f"  查询范围: {query_start} ~ {query_end}, 股票数: {len(need_update)}")
    t_batch_start = time.time()

    try:
        batch_data = provider.fetch_daily_batch(need_update, query_start, query_end)
    except Exception as e:
        print(f"  批量获取失败: {e}")
        return {'success': 0, 'failed': [{'code': c, 'name': stock_map.get(c, ''), 'reason': str(e)} for c in need_update]}

    t_batch = time.time() - t_batch_start
    print(f"  批量 API 完成 ({t_batch:.2f}s), 获取 {len(batch_data)} 只股票数据")

    # 写入数据库
    session = db.get_session()
    success_count = skipped_fresh
    failed = []
    total_written = 0

    try:
        for code in need_update:
            records = batch_data.get(code, [])
            if not records:
                failed.append({'code': code, 'name': stock_map.get(code, ''), 'reason': '无数据'})
                continue

            # 过滤新数据
            latest = latest_dates.get(code)
            if latest:
                records = [r for r in records if pd.to_datetime(r['date']).date() > latest]

            if not records:
                success_count += 1
                continue

            count = 0
            for record in records:
                try:
                    daily = _build_daily_dict(code, record, provider.name())
                    _upsert_daily(session, daily)
                    count += 1
                except Exception:
                    continue

            total_written += count
            success_count += 1
            print(f"  {code} {stock_map.get(code, '')} 新增{count}条 ✓")

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"  数据库写入失败: {e}")
    finally:
        session.close()

    t_total = time.time() - t_batch_start
    print(f"\n成功: {success_count}/{len(stocks)} (写入{total_written}条, 总耗时{t_total:.2f}s)")
    if failed:
        print(f"\n失败 {len(failed)} 只:")
        for f in failed[:20]:
            print(f"  {f['code']} {f['name']}: {f['reason']}")
        if len(failed) > 20:
            print(f"  ... 还有 {len(failed) - 20} 只")

    return {'success': success_count, 'failed': failed}


def fetch_stock_daily_full_history(code: str, delay: float = REQUEST_DELAY) -> str:
    """
    获取单只股票所有历史日线数据（从上市至今）
    检查数据库已有数据，完整则跳过，不完整则一次性拉取全部
    :param code: 股票代码
    :param delay: 请求间隔
    :return: 成功返回 True，已有数据完整返回 "已有完整数据"，失败返回失败原因
    """
    from a_stock_db.config import ADJUST

    provider = get_provider()
    t0 = time.time()
    session = db.get_session()

    try:
        # 查数据库中已有的年份
        existing_years = set(
            r[0] for r in session.query(func.extract('year', StockDaily.日期)).filter(
                StockDaily.code == code
            ).distinct().all()
        )

        end_year = datetime.now().year
        start_year = min(existing_years) if existing_years else end_year

        # 如果有数据，检查是否完整（简单判断：今年数据是否存在）
        if existing_years and end_year in existing_years:
            session.close()
            print(f"  已有 {min(existing_years)}~{max(existing_years)} 年数据，跳过")
            return "已有完整数据"

        # 拉取近5年数据（妙想单次最多约3个月，需分批）
        # BaoStock 可以一次拉全部，妙想需分批
        if provider.name() == "baostock":
            from a_stock_fetcher.providers.baostock_provider import _ensure_bs_login, _bs_query, _get_bs_symbol
            import baostock as bs
            _ensure_bs_login()
            symbol = _get_bs_symbol(code)

            # 获取上市日期
            listed_date = None
            for attempt in range(3):
                try:
                    rs = _bs_query(bs.query_stock_basic, code=symbol)
                    if rs.error_code == '0':
                        while rs.next():
                            row = rs.get_row_data()
                            if len(row) >= 3 and row[2]:
                                listed_date = row[2]
                                break
                    if listed_date:
                        break
                except Exception:
                    pass
                time.sleep(1)

            if not listed_date:
                session.close()
                return "未找到上市日期"

            listed_dt = datetime.strptime(listed_date, '%Y-%m-%d')
            bs_start = listed_date
            bs_end = datetime.now().strftime('%Y-%m-%d')
            missing_years = sorted(set(range(listed_dt.year, end_year + 1)) - existing_years)

            if not missing_years:
                session.close()
                print(f"  上市{listed_date}至今已有完整数据，跳过")
                return "已有完整数据"

            print(f"  上市{listed_date}，缺{len(missing_years)}年，一次拉取 {bs_start}~{bs_end}", end='', flush=True)

            records = provider.fetch_daily(code, bs_start, bs_end)
        else:
            # 妙想：分批拉取（每次约3个月）
            today = datetime.now().date()
            start_dt = today - timedelta(days=365*5)  # 默认拉5年
            print(f"  拉取近5年数据 {start_dt}~{today}", end='', flush=True)

            all_records = []
            current_start = start_dt
            while current_start < today:
                current_end = min(current_start + timedelta(days=90), today)
                batch = provider.fetch_daily(
                    code,
                    current_start.strftime('%Y-%m-%d'),
                    current_end.strftime('%Y-%m-%d')
                )
                all_records.extend(batch)
                current_start = current_end + timedelta(days=1)

            records = all_records

        if not records:
            session.close()
            print(" 无数据")
            return "无数据"

        count = 0
        for record in records:
            daily = _build_daily_dict(code, record, provider.name())
            _upsert_daily(session, daily)
            count += 1

        session.commit()
        t_total = time.time() - t0
        session.close()
        print(f" 写入{count}条 ({t_total:.1f}s)")
        time.sleep(delay)
        return True

    except Exception as e:
        session.rollback()
        session.close()
        return f"{type(e).__name__}: {str(e)[:80]}"


if __name__ == '__main__':
    fetch_all_stocks_daily(limit=10)
