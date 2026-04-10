"""
股票基本信息获取
数据来源: akshare.stock_info_a_code_name()
"""
import time
import json
import pandas as pd
import akshare as ak
from datetime import datetime
from sqlalchemy.dialects.sqlite import insert
from a_stock_db.database import db, to_json, StockBasic
from a_stock_db.config import ENABLED_EXCHANGES


def get_stock_type(code: str) -> str:
    """根据股票代码判断所属市场"""
    if code.startswith('688'):
        return 'KC'  # 科创板
    elif code.startswith('6'):
        return 'SH'  # 沪市主板
    elif code.startswith('3'):
        return 'CY'  # 创业板
    elif code.startswith('0'):
        return 'SZ'  # 深市主板
    elif code.startswith('4') or code.startswith('8') or code.startswith('92'):
        return 'BJ'  # 北交所
    else:
        return 'OTHER'


def is_enabled(code: str) -> bool:
    """根据配置判断是否需要拉取"""
    stock_type = get_stock_type(code)
    return ENABLED_EXCHANGES.get(stock_type, True)


def fetch_stock_basic() -> int:
    """
    获取A股股票基本信息（只获取可交易的）
    :return: 获取的股票数量
    """
    print("=" * 50)
    print("获取A股股票基本信息...")
    print("=" * 50)

    try:
        # 调用akshare获取数据
        df = ak.stock_info_a_code_name()
        print(f"成功获取 {len(df)} 只股票")

        session = db.get_session()
        count = 0
        skip_count = 0

        for _, row in df.iterrows():
            code = str(row['code']).zfill(6)
            stock_type = get_stock_type(code)

            # 根据配置过滤
            if not is_enabled(code):
                skip_count += 1
                continue

            # 原始数据备份
            raw_data = {
                "source": "akshare.stock_info_a_code_name",
                "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "original_data": row.to_dict()
            }

            stock = {
                "code": code,
                "股票代码": code,
                "股票简称": row['name'],
                "type": stock_type,
                "status": "上市",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "raw_data": to_json(raw_data)
            }

            # UPSERT
            stmt = insert(StockBasic).values(**stock)
            stmt = stmt.on_conflict_do_update(
                index_elements=['code'],
                set_={
                    "股票简称": stock["股票简称"],
                    "updated_at": datetime.now()
                }
            )
            session.execute(stmt)
            count += 1

        session.commit()
        session.close()

        print(f"成功写入 {count} 只股票（跳过 {skip_count} 只不可交易的）")
        print(f"  SH: {ENABLED_EXCHANGES.get('SH', False)}")
        print(f"  SZ: {ENABLED_EXCHANGES.get('SZ', False)}")
        print(f"  CY: {ENABLED_EXCHANGES.get('CY', False)}")
        print(f"  KC: {ENABLED_EXCHANGES.get('KC', False)}")
        print(f"  BJ: {ENABLED_EXCHANGES.get('BJ', False)}")
        return count

    except Exception as e:
        print(f"获取股票基本信息失败: {e}")
        return 0


if __name__ == '__main__':
    fetch_stock_basic()
