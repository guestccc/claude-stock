#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTA Report Pipeline — 数据库适配器
从 a_stock_db SQLite 读取数据，返回与 JSON 格式一致的字典
"""

import sqlite3
from datetime import datetime, timedelta

DB_PATH = "/Users/jschen/Desktop/person/claude-study/a_stock_db/a_stock.db"


class DBDataSource:
    """SQLite 数据源适配器"""

    def __init__(self, db_path: str = DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def get_stock_daily(self, code: str, report_date: str, lookback: int = 45) -> dict:
        """
        获取单只股票近 N 日数据
        返回格式与 JSON raw data 一致
        """
        end = datetime.strptime(report_date, "%Y-%m-%d")
        # 乘 1.5 考虑非交易日
        start = end - timedelta(days=int(lookback * 1.5))

        # 日期字段格式为 "YYYY-MM-DD HH:MM:SS.ffffff"，用 LIKE 匹配
        start_str = start.strftime("%Y-%m-%d")
        end_str = report_date + "%"  # 包含当天所有记录

        cursor = self.conn.execute("""
            SELECT 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 涨跌幅
            FROM stock_daily
            WHERE code = ? AND 日期 >= ? AND 日期 <= ?
            ORDER BY 日期
        """, (code, start_str, report_date + " 23:59:59"))

        rows = cursor.fetchall()
        data = []
        for row in rows:
            # 日期可能是 "2026-04-07 00:00:00" 格式，截取前10位
            date_val = row["日期"]
            if date_val and len(str(date_val)) > 10:
                date_str = str(date_val)[:10]
            else:
                date_str = str(date_val) if date_val else None

            data.append({
                "date": date_str,
                "open": row["开盘"],
                "close": row["收盘"],
                "high": row["最高"],
                "low": row["最低"],
                "volume": row["成交量"],
                "turnover": row["成交额"],
                "pct_change": row["涨跌幅"],
            })

        return {"code": code, "data": data, "report_date": report_date}

    def get_stock_name(self, code: str) -> str:
        """获取股票名称"""
        cursor = self.conn.execute(
            "SELECT 股票简称 FROM stock_basic WHERE code = ?", (code,)
        )
        row = cursor.fetchone()
        return row["股票简称"] if row else code

    def get_all_codes_with_data(self, report_date: str) -> list:
        """获取某日有数据的所有股票代码"""
        cursor = self.conn.execute("""
            SELECT DISTINCT code FROM stock_daily WHERE 日期 LIKE ?
        """, (report_date + "%",))
        return [row[0] for row in cursor.fetchall()]

    def get_market_change(self, report_date: str) -> float:
        """计算全市场平均涨跌幅（作为大盘共振依据）"""
        cursor = self.conn.execute("""
            SELECT AVG(涨跌幅) FROM stock_daily WHERE 日期 LIKE ?
        """, (report_date + "%",))
        row = cursor.fetchone()
        return row[0] if row and row[0] else 0.0

    def close(self):
        self.conn.close()
