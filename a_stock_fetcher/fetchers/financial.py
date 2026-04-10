"""
财务数据获取
数据来源: akshare.stock_financial_report_sina(stock=code, symbol="利润表")
"""
import time
import pandas as pd
import akshare as ak
from datetime import datetime
from sqlalchemy.dialects.sqlite import insert
from a_stock_db.database import db, to_json, StockBasic, StockFinancial
from a_stock_db.config import REQUEST_DELAY


def fetch_stock_financial(code: str) -> bool:
    """
    获取单只股票财务数据
    :param code: 股票代码
    """
    session = db.get_session()

    try:
        df_profit = ak.stock_financial_report_sina(stock=code, symbol="利润表")

        if df_profit is not None and not df_profit.empty:
            for _, row in df_profit.iterrows():
                raw_data = {
                    "source": "akshare.stock_financial_report_sina",
                    "symbol": "利润表",
                    "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "original_data": row.to_dict()
                }

                financial = {
                    "code": code,
                    "报告日期": pd.to_datetime(row['报告日期']) if pd.notna(row.get('报告日期')) else None,
                    "报表类型": "利润表",
                    "营业总收入": float(row['营业总收入']) if pd.notna(row.get('营业总收入')) else None,
                    "营业总成本": float(row['营业总成本']) if pd.notna(row.get('营业总成本')) else None,
                    "营业利润": float(row['营业利润']) if pd.notna(row.get('营业利润')) else None,
                    "利润总额": float(row['利润总额']) if pd.notna(row.get('利润总额')) else None,
                    "净利润": float(row['净利润']) if pd.notna(row.get('净利润')) else None,
                    "基本每股收益": float(row['基本每股收益']) if pd.notna(row.get('基本每股收益')) else None,
                    "稀释每股收益": float(row['稀释每股收益']) if pd.notna(row.get('稀释每股收益')) else None,
                    "created_at": datetime.now(),
                    "raw_data": to_json(raw_data)
                }

                stmt = insert(StockFinancial).values(**financial)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['code', '报告日期', '报表类型'],
                    set_={
                        "营业总收入": financial["营业总收入"],
                        "营业利润": financial["营业利润"],
                        "净利润": financial["净利润"],
                    }
                )
                session.execute(stmt)

        session.commit()
        session.close()
        return True

    except Exception as e:
        session.rollback()
        session.close()
        print(f"  错误: {e}")
        return False


def fetch_all_stocks_financial(limit: int = 100, delay: float = REQUEST_DELAY) -> int:
    """
    批量获取股票财务数据
    """
    print("=" * 50)
    print("批量获取财务数据...")
    print("=" * 50)

    session = db.get_session()
    stocks = session.query(StockBasic).limit(limit).all()
    session.close()

    success_count = 0
    for i, stock in enumerate(stocks):
        print(f"[{i+1}/{len(stocks)}] {stock.code}...", end=' ')
        if fetch_stock_financial(stock.code):
            success_count += 1
            print("✓")
        else:
            print("✗")
        time.sleep(delay)

    print(f"\n成功: {success_count}/{len(stocks)}")
    return success_count


if __name__ == '__main__':
    fetch_all_stocks_financial(limit=10)
