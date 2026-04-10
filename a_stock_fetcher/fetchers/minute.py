"""
1分钟分时数据获取
数据来源:
  - 历史数据: akshare.stock_zh_a_minute(symbol="sh600519", period="1", adjust="qfq")
  - 当日数据: akshare.stock_intraday_sina(symbol="sz000001", date="20260408")
数据保留: 近5个交易日
"""
import time
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from sqlalchemy.dialects.sqlite import insert
from a_stock_db.database import db, to_json, StockBasic, StockMinute
from a_stock_db.config import REQUEST_DELAY, MINUTE_KEEP_DAYS, MINUTE_STOCK_LIMIT


def get_symbol_with_prefix(code: str) -> str:
    """获取带前缀的股票���码"""
    if code.startswith('6'):
        return f'sh{code}'
    elif code.startswith(('0', '3')):
        return f'sz{code}'
    elif code.startswith(('8', '4')):
        return f'bj{code}'
    return code


def _write_minute_data(session, code: str, trade_time: datetime, open_: float, close: float,
                       high: float, low: float, volume: float, amount: float, source: str, raw_data: dict):
    """写入分时数据"""
    trade_date = trade_time.date()

    minute = {
        "code": code,
        "日期": datetime.combine(trade_date, datetime.min.time()),
        "时间": trade_time,
        "开盘": open_,
        "收盘": close,
        "最高": high,
        "最低": low,
        "成交量": volume,
        "成交额": amount,
        "created_at": datetime.now(),
        "raw_data": to_json(raw_data)
    }

    stmt = insert(StockMinute).values(**minute)
    stmt = stmt.on_conflict_do_update(
        index_elements=['code', '时间'],
        set_={
            "开盘": minute["开盘"],
            "收盘": minute["收盘"],
            "最高": minute["最高"],
            "最低": minute["最低"],
            "成交量": minute["成交量"],
            "成交额": minute["成交额"],
        }
    )
    session.execute(stmt)


def fetch_stock_minute_history(code: str) -> str:
    """
    获取单只股票历史1分钟分时数据（排除今日）
    :param code: 股票代码
    :return: 成功返回 True，失败返回失败原因
    """
    session = db.get_session()

    try:
        symbol = get_symbol_with_prefix(code)
        today = datetime.now().date()

        df = ak.stock_zh_a_minute(symbol=symbol, period='1', adjust='qfq')

        if df is None or df.empty:
            session.close()
            return "无数据"

        count = 0
        for _, row in df.iterrows():
            time_str = str(row['day'])
            try:
                trade_time = pd.to_datetime(time_str)
                if trade_time.date() >= today:
                    continue
            except:
                continue

            raw_data = {
                "source": "akshare.stock_zh_a_minute",
                "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "original_data": row.to_dict()
            }

            _write_minute_data(
                session, code, trade_time,
                float(row['open']) if pd.notna(row.get('open')) else None,
                float(row['close']) if pd.notna(row.get('close')) else None,
                float(row['high']) if pd.notna(row.get('high')) else None,
                float(row['low']) if pd.notna(row.get('low')) else None,
                float(row['volume']) if pd.notna(row.get('volume')) else None,
                float(row['amount']) if pd.notna(row.get('amount')) else None,
                "akshare.stock_zh_a_minute",
                raw_data
            )
            count += 1

        session.commit()
        session.close()
        return True

    except Exception as e:
        session.rollback()
        session.close()
        return f"{type(e).__name__}: {str(e)[:50]}"


def fetch_stock_minute_today(code: str) -> str:
    """
    获取单只股票当日1分钟分时数据（从逐笔聚合）
    :param code: 股票代码
    :return: 成功返回 True，失败返回失败原因
    """
    session = db.get_session()

    try:
        symbol = get_symbol_with_prefix(code)
        today = datetime.now()
        today_str = today.strftime('%Y%m%d')

        df = ak.stock_intraday_sina(symbol=symbol, date=today_str)

        if df is None or df.empty:
            session.close()
            return "今日无数据"

        df = df[(df['volume'] > 0) & (df['price'] > 0)]

        if len(df) == 0:
            session.close()
            return "今日无成交"

        df['datetime'] = pd.to_datetime(f'{today_str} ' + df['ticktime'])
        df['minute'] = df['datetime'].dt.floor('min')
        agg = df.groupby('minute').agg({
            'price': ['first', 'max', 'min', 'last'],
            'volume': 'sum'
        }).reset_index()
        agg.columns = ['时间', '开盘', '最高', '最低', '收盘', '成交量']

        count = 0
        for _, row in agg.iterrows():
            trade_time = row['时间']

            raw_data = {
                "source": "akshare.stock_intraday_sina",
                "fetch_time": today.strftime("%Y-%m-%d %H:%M:%S"),
                "aggregation": "1min",
                "original_data": row.to_dict()
            }

            _write_minute_data(
                session, code, trade_time,
                float(row['开盘']) if pd.notna(row['开盘']) else None,
                float(row['收盘']) if pd.notna(row['收盘']) else None,
                float(row['最高']) if pd.notna(row['最高']) else None,
                float(row['最低']) if pd.notna(row['最低']) else None,
                float(row['成交量']) if pd.notna(row['成交量']) else None,
                None,
                "akshare.stock_intraday_sina",
                raw_data
            )
            count += 1

        session.commit()
        session.close()
        return True

    except Exception as e:
        session.rollback()
        session.close()
        return f"{type(e).__name__}: {str(e)[:50]}"


def fetch_stock_minute(code: str) -> str:
    """
    获取单只股票1分钟分时数据（历史 + 当日）
    :param code: 股票代码
    :return: 成功返回 True，失败返回失败原因
    """
    hist_result = fetch_stock_minute_history(code)
    today_result = fetch_stock_minute_today(code)

    # 至少一个成功
    if hist_result is True or today_result is True:
        return True

    # 都失败
    return f"历史:{hist_result}, 今日:{today_result}"


def fetch_all_stocks_minute(limit: int = None, delay: float = REQUEST_DELAY) -> int:
    """
    批量获取股票1分钟分时数据
    :param limit: 限制数量，None表示全部
    :param delay: 请求间隔（秒）
    """
    print("=" * 50)
    print("批量获取1分钟分时数据...")
    print(f"保留策略: 近{MINUTE_KEEP_DAYS}个交易日")
    print("=" * 50)

    session = db.get_session()
    stocks = session.query(StockBasic).all()
    session.close()

    if limit:
        stocks = stocks[:limit]
    elif MINUTE_STOCK_LIMIT:
        stocks = stocks[:MINUTE_STOCK_LIMIT]

    success_count = 0
    failed = []

    for i, stock in enumerate(stocks):
        import sys
        print(f"[{i+1}/{len(stocks)}] {stock.code} {stock.股票简称}...", end=' ', flush=True)
        result = fetch_stock_minute(stock.code)
        if result is True:
            success_count += 1
            print("✓", flush=True)
        else:
            print(f"✗ ({result})", flush=True)
            failed.append({'code': stock.code, 'name': stock.股票简称, 'reason': result})
        time.sleep(delay)

    print(f"\n成功: {success_count}/{len(stocks)}")
    if failed:
        print(f"\n失败 {len(failed)} 只:")
        for f in failed[:20]:  # 最多显示20个
            print(f"  {f['code']} {f['name']}: {f['reason']}")
        if len(failed) > 20:
            print(f"  ... 还有 {len(failed) - 20} 只")
    return {'success': success_count, 'failed': failed}


def cleanup_old_minute_data():
    """清理过期的分时数据"""
    print("=" * 50)
    print("清理过期分时数据...")
    print("=" * 50)

    session = db.get_session()

    try:
        cutoff_date = datetime.now() - timedelta(days=MINUTE_KEEP_DAYS * 2)
        result = session.query(StockMinute).filter(StockMinute.日期 < cutoff_date).delete()
        session.commit()
        print(f"已删除 {result} 条过期分时数据")
        print(f"保留策略: 近 {MINUTE_KEEP_DAYS} 个交易日")

    except Exception as e:
        session.rollback()
        print(f"清理失败: {e}")
    finally:
        session.close()


if __name__ == '__main__':
    fetch_stock_minute('600519')
