"""
日线行情数据获取
数据来源: BaoStock
"""
import time
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta, date
from sqlalchemy.dialects.sqlite import insert
from a_stock_db.database import db, StockBasic, StockDaily
from a_stock_db.config import REQUEST_DELAY, DAILY_HISTORY_DAYS


# 全局登录状态
_bs_logged_in = False


def _ensure_bs_login():
    """确保 BaoStock 已登录"""
    global _bs_logged_in
    if not _bs_logged_in:
        bs.login()
        _bs_logged_in = True


def get_bs_symbol(code: str) -> str:
    """获取 BaoStock 格式的股票代码"""
    if code.startswith('6'):
        return f'sh.{code}'
    elif code.startswith(('0', '3')):
        return f'sz.{code}'
    else:
        return f'sz.{code}'


def fetch_stock_daily(code: str, start_date: str = None, end_date: str = None) -> bool:
    """
    获取单只股票日线数据
    :param code: 股票代码
    :param start_date: 开始日期 YYYYMMDD
    :param end_date: 结束日期 YYYYMMDD
    """
    session = db.get_session()

    try:
        symbol = get_bs_symbol(code)

        # BaoStock 日期格式
        if start_date:
            bs_start = f'{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}'
        else:
            bs_start = (datetime.now() - timedelta(days=DAILY_HISTORY_DAYS)).strftime('%Y-%m-%d')

        if end_date:
            bs_end = f'{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}'
        else:
            bs_end = datetime.now().strftime('%Y-%m-%d')

        _ensure_bs_login()

        # BaoStock: adjustflag 1=不复权 2=前复权 3=后复权
        adjustflag = '2' if True else '1'

        rs = bs.query_history_k_data_plus(
            symbol,
            'date,code,open,high,low,close,volume,amount',
            start_date=bs_start,
            end_date=bs_end,
            frequency='d',
            adjustflag=adjustflag
        )

        if rs.error_code != '0':
            session.close()
            return False

        # 转换为 DataFrame
        data_list = []
        while rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            session.close()
            return False

        df = pd.DataFrame(data_list, columns=rs.fields)

        count = 0
        for _, row in df.iterrows():
            trade_date = pd.to_datetime(row['date'])

            daily = {
                "code": code,
                "日期": trade_date,
                "开盘": float(row['open']) if row['open'] else None,
                "收盘": float(row['close']) if row['close'] else None,
                "最高": float(row['high']) if row['high'] else None,
                "最低": float(row['low']) if row['low'] else None,
                "成交量": float(row['volume']) if row['volume'] else None,
                "成交额": float(row['amount']) if row['amount'] else None,
                "振幅": None,
                "涨跌幅": None,
                "涨跌额": None,
                "换手率": None,
                "created_at": datetime.now(),
            }

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
                }
            )
            session.execute(stmt)
            count += 1

        session.commit()
        session.close()
        return True

    except Exception as e:
        session.rollback()
        session.close()
        return False


def fetch_all_stocks_daily(limit: int = None, delay: float = REQUEST_DELAY) -> int:
    """批量获取所有股票日线数据"""
    print("=" * 50)
    print("批量获取日线行情数据...")
    print("=" * 50)

    _ensure_bs_login()

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
    from sqlalchemy import func

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
            # 如果已有今天的数据，跳过
            if latest_date_only >= today:
                session.close()
                print(f"  {latest_date_only} 已有，跳过({time.time()-t0:.4f}s)")
                return True

        symbol = get_bs_symbol(code)

        # 确定日期范围（最多获取30天）
        if latest_date:
            start = (latest_date.date() + timedelta(days=1)).strftime('%Y%m%d')
            end = today.strftime('%Y%m%d')
            print(f"  {latest_date.date()}→增量...", end=' ')
        else:
            start = (today - timedelta(days=30)).strftime('%Y%m%d')
            end = today.strftime('%Y%m%d')
            print(f"  无历史→近30天...", end=' ')

        bs_start = f'{start[:4]}-{start[4:6]}-{start[6:8]}'
        bs_end = f'{end[:4]}-{end[4:6]}-{end[6:8]}'

        t2 = time.time()
        _ensure_bs_login()

        rs = bs.query_history_k_data_plus(
            symbol,
            'date,code,open,high,low,close,volume,amount',
            start_date=bs_start,
            end_date=bs_end,
            frequency='d',
            adjustflag='2'
        )
        t_api = time.time() - t2

        if rs.error_code != '0':
            session.close()
            print(f"API失败({t_api:.4f}s): {rs.error_msg}")
            return f"API失败: {rs.error_msg}"

        # 转换为 DataFrame
        data_list = []
        while rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            session.close()
            print(f"无数据({t_api:.4f}s)")
            return "无数据"

        df = pd.DataFrame(data_list, columns=rs.fields)

        # 过滤新数据
        if latest_date:
            df['date'] = pd.to_datetime(df['date'])
            df = df[df['date'] > latest_date]

        if df.empty:
            session.close()
            print(f"无新数据({t_api:.4f}s)")
            return True

        t_write_start = time.time()
        count = 0
        for _, row in df.iterrows():
            trade_date = pd.to_datetime(row['date'])

            daily = {
                "code": code,
                "日期": trade_date,
                "开盘": float(row['open']) if row['open'] else None,
                "收盘": float(row['close']) if row['close'] else None,
                "最高": float(row['high']) if row['high'] else None,
                "最低": float(row['low']) if row['low'] else None,
                "成交量": float(row['volume']) if row['volume'] else None,
                "成交额": float(row['amount']) if row['amount'] else None,
                "振幅": None,
                "涨跌幅": None,
                "涨跌额": None,
                "换手率": None,
                "created_at": datetime.now(),
            }

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
                }
            )
            session.execute(stmt)
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
    :param codes: 指定股票代码列表
    :param limit: 限制数量
    :param delay: 请求间隔
    :return: {'success': 成功数, 'failed': [...]}
    """
    print("=" * 50)
    print("批量增量获取日线行情数据...")
    print("=" * 50)

    _ensure_bs_login()

    session = db.get_session()

    if codes:
        stocks = session.query(StockBasic).filter(StockBasic.code.in_(codes)).all()
        print(f"指定股票: {len(codes)} 只")
    else:
        stocks = session.query(StockBasic).all()
        if limit:
            stocks = stocks[:limit]
            print(f"限制数量: {limit} 只")
        else:
            print(f"全量: {len(stocks)} 只")

    session.close()

    success_count = 0
    failed = []

    for i, stock in enumerate(stocks):
        print(f"[{i+1}/{len(stocks)}] {stock.code} {stock.股票简称}...", end=' ')
        result = fetch_stock_daily_incremental(stock.code)
        if result is True:
            success_count += 1
        elif result not in ("无数据",):
            failed.append({'code': stock.code, 'name': stock.股票简称, 'reason': result})
        time.sleep(delay)

    print(f"\n成功: {success_count}/{len(stocks)}")
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
    :param code: 股票代码
    :param delay: 请求间隔
    :return: 成功返回 True，失败返回失败原因
    """
    from a_stock_db.config import ADJUST

    t0 = time.time()
    session = db.get_session()

    try:
        symbol = get_bs_symbol(code)

        _ensure_bs_login()

        # 获取股票的上市日期（从 BaoStock 获取）
        rs = bs.query_stock_basic(code=symbol)
        listed_date = None
        while rs.next():
            row = rs.get_row_data()
            # BaoStock 返回: [code, code_name, ipoDate, outDate, stock_type]
            if len(row) >= 3 and row[2]:
                listed_date = row[2]  # YYYY-MM-DD
                break

        if not listed_date:
            session.close()
            return "未找到上市日期"

        # BaoStock 最大单次查询 2500 条，按年分段
        start_year = int(listed_date[:4])
        end_year = datetime.now().year
        total_years = end_year - start_year + 1

        print(f"  上市日期: {listed_date}, 共 {total_years} 年数据")
        print(f"  进度: 0/{total_years} 年", end='', flush=True)

        total_count = 0
        for year in range(start_year, end_year + 1):
            bs_start = f'{year}-01-01'
            bs_end = f'{year}-12-31'

            rs = bs.query_history_k_data_plus(
                symbol,
                'date,open,high,low,close,volume,amount',
                start_date=bs_start,
                end_date=bs_end,
                frequency='d',
                adjustflag='2' if ADJUST == 'qfq' else '1'
            )

            if rs.error_code != '0':
                print(f"\n  API失败 {year}年: {rs.error_msg}")
                continue

            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())

            if not data_list:
                time.sleep(delay)
                print(f' 0', end='', flush=True)
                continue

            count = 0
            for row in data_list:
                trade_date = pd.to_datetime(row[0])
                daily = {
                    "code": code,
                    "日期": trade_date,
                    "开盘": float(row[1]) if row[1] else None,
                    "收盘": float(row[2]) if row[2] else None,
                    "最高": float(row[3]) if row[3] else None,
                    "最低": float(row[4]) if row[4] else None,
                    "成交量": float(row[5]) if row[5] else None,
                    "成交额": float(row[6]) if row[6] else None,
                    "振幅": None,
                    "涨跌幅": None,
                    "涨跌额": None,
                    "换手率": None,
                    "created_at": datetime.now(),
                }
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
                    }
                )
                session.execute(stmt)
                count += 1

            session.commit()
            total_count += count
            print(f' {year}:{count}', end='', flush=True)
            time.sleep(delay)

        t_total = time.time() - t0
        session.close()
        print(f"\n  完成: {total_count} 条, 耗时 {t_total:.1f}s")
        return True

    except Exception as e:
        session.rollback()
        session.close()
        return f"{type(e).__name__}: {str(e)[:80]}"


if __name__ == '__main__':
    fetch_all_stocks_daily(limit=10)
