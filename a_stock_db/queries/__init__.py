"""
查询工具
提供常用的股票数据查询接口
"""
from ..database import db, StockBasic, StockDaily, StockMinute, StockFinancial, StockConcept
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import List, Optional


class StockQuery:
    """股票数据查询类"""

    def __init__(self):
        self.session = db.get_session()

    def __del__(self):
        self.session.close()

    def get_stock_info(self, code: str) -> Optional[StockBasic]:
        """根据代码查询股票基本信息"""
        return self.session.query(StockBasic).filter(StockBasic.code == code).first()

    def search_stocks(self, keyword: str) -> List[StockBasic]:
        """搜索股票（代码或名称模糊匹配）"""
        pattern = f"%{keyword}%"
        return self.session.query(StockBasic).filter(
            (StockBasic.code.like(pattern)) | (StockBasic.股票简称.like(pattern))
        ).all()

    def get_stock_count_by_type(self) -> List[tuple]:
        """按类型统计股票数量"""
        return self.session.query(
            StockBasic.type,
            func.count(StockBasic.code).label('count')
        ).group_by(StockBasic.type).all()

    def get_stock_daily(self, code: str, days: int = 30) -> List[StockDaily]:
        """查询股票日线数据"""
        start_date = datetime.now() - timedelta(days=days)
        return self.session.query(StockDaily).filter(
            StockDaily.code == code,
            StockDaily.日期 >= start_date
        ).order_by(StockDaily.日期.desc()).all()

    def get_stock_minute(self, code: str, days: int = 1) -> List[StockMinute]:
        """查询股票1分钟分时数据"""
        start_date = datetime.now() - timedelta(days=days)
        return self.session.query(StockMinute).filter(
            StockMinute.code == code,
            StockMinute.日期 >= start_date
        ).order_by(StockMinute.时间.desc()).all()

    def get_stock_financial(self, code: str) -> List[StockFinancial]:
        """查询股票财务数据"""
        return self.session.query(StockFinancial).filter(
            StockFinancial.code == code
        ).order_by(StockFinancial.报告日期.desc()).all()

    def get_concept_boards(self, limit: int = 20) -> List[StockConcept]:
        """查询概念板块，按涨跌幅排序"""
        return self.session.query(StockConcept).filter(
            StockConcept.涨跌幅.isnot(None)
        ).order_by(desc(StockConcept.涨跌幅)).limit(limit).all()

    def get_minute_count(self, code: str) -> int:
        """获取某股票的1分钟数据条数"""
        return self.session.query(func.count(StockMinute.id)).filter(
            StockMinute.code == code
        ).scalar()

    def get_all_stocks_count(self) -> int:
        """获取股票总数"""
        return self.session.query(func.count(StockBasic.code)).scalar()


def demo():
    """演示查询"""
    query = StockQuery()

    print("=" * 60)
    print("A股数据库查询演示")
    print("=" * 60)

    # 1. 股票总数
    total = query.get_all_stocks_count()
    print(f"\n[1] 股票总数: {total} 只")

    # 2. 按类型统计
    print("\n[2] 按类型统计:")
    for stype, count in query.get_stock_count_by_type():
        print(f"    {stype}: {count} 只")

    # 3. 搜索股票
    print("\n[3] 搜索 '茅台':")
    results = query.search_stocks("茅台")
    for stock in results[:5]:
        print(f"    {stock.code} {stock.股票简称}")

    # 4. 查询概念板块
    print("\n[4] 概念板块涨跌幅 TOP5:")
    concepts = query.get_concept_boards(5)
    for concept in concepts:
        print(f"    {concept.板块名称} 涨跌幅: {concept.涨跌幅:.2f}%")


if __name__ == '__main__':
    demo()
