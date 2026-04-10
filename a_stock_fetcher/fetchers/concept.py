"""
概念板块和行业板块数据获取
概念: akshare.stock_board_concept_name_em()
行业: akshare.stock_board_industry_name_em()
"""
import time
import pandas as pd
import akshare as ak
from datetime import datetime
from sqlalchemy.dialects.sqlite import insert
from a_stock_db.database import db, to_json, StockConcept
from a_stock_db.config import REQUEST_DELAY


def fetch_concept() -> int:
    """
    获取概念板块信息
    :return: 获取的概念板块数量
    """
    print("=" * 50)
    print("获取概念板块数据...")
    print("=" * 50)

    try:
        df = ak.stock_board_concept_name_em()
        print(f"成功获取 {len(df)} 个概念板块")

        session = db.get_session()
        count = 0

        for _, row in df.iterrows():
            raw_data = {
                "source": "akshare.stock_board_concept_name_em",
                "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "original_data": row.to_dict()
            }

            concept = {
                "板块代码": f"C{row['板块代码']}" if pd.notna(row.get('板块代码')) else None,
                "板块名称": row['板块名称'] if pd.notna(row.get('板块名称')) else None,
                "涨跌幅": float(row['涨跌幅']) if pd.notna(row.get('涨跌幅')) else None,
                "总市值": float(row['总市值']) if pd.notna(row.get('总市值')) else None,
                "成交额": float(row['成交额']) if pd.notna(row.get('成交额')) else None,
                "上涨家数": int(row['上涨家数']) if pd.notna(row.get('上涨家数')) else None,
                "下跌家数": int(row['下跌家数']) if pd.notna(row.get('下跌家数')) else None,
                "updated_at": datetime.now(),
                "raw_data": to_json(raw_data)
            }

            stmt = insert(StockConcept).values(**concept)
            stmt = stmt.on_conflict_do_update(
                index_elements=['板块代码'],
                set_={
                    "板块名称": concept["板块名称"],
                    "涨跌幅": concept["涨跌幅"],
                    "updated_at": concept["updated_at"],
                }
            )
            session.execute(stmt)
            count += 1

        session.commit()
        session.close()

        print(f"成功写入 {count} 个概念板块")
        return count

    except Exception as e:
        print(f"获取概念板块失败: {e}")
        return 0


def fetch_industry() -> int:
    """
    获取行业板块信息
    :return: 获取的行业板块数量
    """
    print("=" * 50)
    print("获取行业板块数据...")
    print("=" * 50)

    try:
        df = ak.stock_board_industry_name_em()
        print(f"成功获取 {len(df)} 个行业板块")

        session = db.get_session()
        count = 0

        for _, row in df.iterrows():
            raw_data = {
                "source": "akshare.stock_board_industry_name_em",
                "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "original_data": row.to_dict()
            }

            concept = {
                "板块代码": f"I{row['板块代码']}" if pd.notna(row.get('板块代码')) else None,
                "板块名称": row['板块名称'] if pd.notna(row.get('板块名称')) else None,
                "涨跌幅": float(row['涨跌幅']) if pd.notna(row.get('涨跌幅')) else None,
                "总市值": float(row['总市值']) if pd.notna(row.get('总市值')) else None,
                "成交额": float(row['成交额']) if pd.notna(row.get('成交额')) else None,
                "上涨家数": int(row['上涨家数']) if pd.notna(row.get('上涨家数')) else None,
                "下跌家数": int(row['下跌家数']) if pd.notna(row.get('下跌家数')) else None,
                "updated_at": datetime.now(),
                "raw_data": to_json(raw_data)
            }

            stmt = insert(StockConcept).values(**concept)
            stmt = stmt.on_conflict_do_update(
                index_elements=['板块代码'],
                set_={
                    "板块名称": concept["板块名称"],
                    "涨跌幅": concept["涨跌幅"],
                    "updated_at": concept["updated_at"],
                }
            )
            session.execute(stmt)
            count += 1

        session.commit()
        session.close()

        print(f"成功写入 {count} 个行业板块")
        return count

    except Exception as e:
        print(f"获取行业板块失败: {e}")
        return 0


def fetch_all_boards() -> int:
    """获取概念和行业板块"""
    c = fetch_concept()
    i = fetch_industry()
    return c + i


if __name__ == '__main__':
    fetch_all_boards()
