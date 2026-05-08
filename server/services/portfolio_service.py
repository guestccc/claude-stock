"""持仓服务：买入/卖出/查询（_fifo）"""
import re
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from server.db.models import Holding, Transaction, CostLot
from a_stock_db import StockBasic
from server.services.market_service import get_stock_name, get_quotes


# ---------- 持仓查询 ----------

def get_all_holdings() -> List[dict]:
    """获取所有持仓（含实时行情）"""
    session = _get_session()
    try:
        holdings = session.query(Holding).order_by(Holding.created_at.desc()).all()
        if not holdings:
            return []

        codes = [h.code for h in holdings]
        quotes = get_quotes(codes)
        quotes_map = {q["code"]: q for q in quotes}

        result = []
        for h in holdings:
            q = quotes_map.get(h.code, {})
            current_price = q.get("close")
            profit_pct = None
            profit_amount = None
            if current_price and h.avg_cost > 0:
                profit_amount = (current_price - h.avg_cost) * h.shares
                profit_pct = (current_price - h.avg_cost) / h.avg_cost * 100

            result.append({
                "id": h.id,
                "code": h.code,
                "name": h.name,
                "shares": h.shares,
                "avg_cost": h.avg_cost,
                "total_cost": h.total_cost,
                "current_price": current_price,
                "market_value": (current_price * h.shares) if current_price else None,
                "profit_amount": profit_amount,
                "profit_pct": profit_pct,
                "first_buy_date": h.first_buy_date.strftime("%Y-%m-%d") if h.first_buy_date else None,
                "note": h.note,
                "created_at": h.created_at.strftime("%Y-%m-%d %H:%M"),
                "updated_at": h.updated_at.strftime("%Y-%m-%d %H:%M"),
            })
        return result
    finally:
        session.close()


def get_summary() -> dict:
    """持仓汇总统计"""
    session = _get_session()
    try:
        holdings = session.query(Holding).all()
        if not holdings:
            return {"total_cost": 0, "total_market_value": 0, "total_profit_amount": 0, "total_profit_pct": 0, "holding_count": 0}

        codes = [h.code for h in holdings]
        quotes = get_quotes(codes)
        quotes_map = {q["code"]: q for q in quotes}

        total_cost = 0.0
        total_market_value = 0.0

        for h in holdings:
            total_cost += h.total_cost
            q = quotes_map.get(h.code, {})
            current_price = q.get("close")
            if current_price:
                total_market_value += current_price * h.shares

        profit_amount = total_market_value - total_cost
        profit_pct = (profit_amount / total_cost * 100) if total_cost > 0 else 0

        return {
            "total_cost": round(total_cost, 2),
            "total_market_value": round(total_market_value, 2),
            "total_profit_amount": round(profit_amount, 2),
            "total_profit_pct": round(profit_pct, 2),
            "holding_count": len(holdings),
        }
    finally:
        session.close()


def get_transactions(code: Optional[str] = None, limit: int = 50) -> List[dict]:
    """获取交易记录"""
    session = _get_session()
    try:
        query = session.query(Transaction)
        if code:
            query = query.filter(Transaction.code == code)
        rows = query.order_by(Transaction.date.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "code": r.code,
                "name": r.name,
                "type": r.type,
                "shares": r.shares,
                "price": r.price,
                "amount": r.amount,
                "fee": r.fee,
                "date": r.date.strftime("%Y-%m-%d"),
                "note": r.note,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for r in rows
        ]
    finally:
        session.close()


# ---------- 持仓同步（根据累计买卖计算） ----------

def _sync_holding(session: Session, code: str, name: str) -> Optional[Holding]:
    """根据累计买卖记录同步 Holding：
    总成本 = 累计买入(含买费) - 累计卖出(扣卖费)
    持仓均价 = 总成本 / 净持仓股数
    """
    # 累计买入
    buy_shares = 0
    buy_cost = 0.0
    buy_rows = session.query(Transaction).filter(
        Transaction.code == code, Transaction.type == "buy"
    ).all()
    for r in buy_rows:
        buy_shares += r.shares
        buy_cost += r.amount + r.fee  # 买入金额 + 买费

    # 累计卖出
    sell_shares = 0
    sell_proceeds = 0.0
    sell_rows = session.query(Transaction).filter(
        Transaction.code == code, Transaction.type == "sell"
    ).all()
    for r in sell_rows:
        sell_shares += r.shares
        sell_proceeds += r.amount - r.fee  # 卖出金额扣卖费

    net_shares = buy_shares - sell_shares

    if net_shares <= 0:
        # 无持仓，删除 Holding
        holding = session.query(Holding).filter(Holding.code == code).first()
        if holding:
            session.delete(holding)
        return None

    net_cost = buy_cost - sell_proceeds
    avg_cost = net_cost / net_shares

    # 首买日
    first_buy = session.query(Transaction).filter(
        Transaction.code == code, Transaction.type == "buy"
    ).order_by(Transaction.date.asc()).first()

    holding = session.query(Holding).filter(Holding.code == code).first()
    if not holding:
        holding = Holding(
            code=code,
            name=name,
            shares=net_shares,
            avg_cost=round(avg_cost, 6),
            total_cost=round(net_cost, 2),
            first_buy_date=first_buy.date if first_buy else datetime.now(),
        )
        session.add(holding)
    else:
        holding.name = name
        holding.shares = net_shares
        holding.avg_cost = round(avg_cost, 6)
        holding.total_cost = round(net_cost, 2)
        if first_buy:
            holding.first_buy_date = first_buy.date
        holding.updated_at = datetime.now()

    return holding


# ---------- 买入 ----------

def buy_stock(
    code: str,
    shares: int,
    price: float,
    fee: float = 0,
    date: Optional[str] = None,
    note: str = "",
) -> tuple[Holding, Transaction]:
    if shares <= 0:
        raise ValueError("买入数量必须大于 0")
    if price <= 0:
        raise ValueError("买入价格必须大于 0")

    name = get_stock_name(code)
    if not name:
        raise ValueError(f"股票代码 {code} 不存在")

    trade_date = datetime.now() if not date else datetime.strptime(date, "%Y-%m-%d")
    amount = round(shares * price, 2)

    session = _get_session()
    session.expire_on_commit = False
    try:
        tx = Transaction(
            code=code,
            name=name,
            type="buy",
            shares=shares,
            price=round(price, 6),
            amount=amount,
            fee=fee,
            date=trade_date,
            note=note,
        )
        session.add(tx)
        session.flush()

        holding = _sync_holding(session, code, name)
        session.commit()
        return holding, tx
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


# ---------- 卖出 ----------

def sell_stock(
    code: str,
    shares: int,
    price: float,
    fee: float = 0,
    date: Optional[str] = None,
    note: str = "",
) -> tuple[Optional[Holding], Transaction]:
    if shares <= 0:
        raise ValueError("卖出数量必须大于 0")
    if price <= 0:
        raise ValueError("卖出价格必须大于 0")

    name = get_stock_name(code)
    if not name:
        raise ValueError(f"股票代码 {code} 不存在")

    trade_date = datetime.now() if not date else datetime.strptime(date, "%Y-%m-%d")
    amount = round(shares * price, 2)

    session = _get_session()
    session.expire_on_commit = False
    try:
        # 检查可卖数量
        buy_shares = sum(
            r.shares for r in session.query(Transaction).filter(
                Transaction.code == code, Transaction.type == "buy"
            ).all()
        )
        sell_shares = sum(
            r.shares for r in session.query(Transaction).filter(
                Transaction.code == code, Transaction.type == "sell"
            ).all()
        )
        available = buy_shares - sell_shares
        if available < shares:
            raise ValueError(f"可卖出数量不足：当前持仓 {available} 股，尝试卖出 {shares} 股")

        tx = Transaction(
            code=code,
            name=name,
            type="sell",
            shares=shares,
            price=round(price, 6),
            amount=amount,
            fee=fee,
            date=trade_date,
            note=note,
        )
        session.add(tx)
        session.flush()

        holding = _sync_holding(session, code, name)
        session.commit()
        return holding, tx
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


# ---------- 已清仓列表 ----------

def get_closed_positions() -> List[dict]:
    """获取已清仓股票：曾经交易过但现在持仓为0的，含累计盈亏"""
    session = _get_session()
    try:
        # 当前有持仓的股票
        current_codes = {h.code for h in session.query(Holding.code).all()}
        # 所有有过交易的股票
        all_codes = {t.code for t in session.query(Transaction.code).distinct().all()}
        closed_codes = sorted(all_codes - current_codes)

        result = []
        for code in closed_codes:
            buys = session.query(Transaction).filter(
                Transaction.code == code, Transaction.type == "buy"
            ).all()
            sells = session.query(Transaction).filter(
                Transaction.code == code, Transaction.type == "sell"
            ).all()
            total_buy_cost = sum(t.amount + t.fee for t in buys)
            total_sell_proceeds = sum(t.amount - t.fee for t in sells)
            profit = total_sell_proceeds - total_buy_cost

            # 股票名称
            name = session.query(StockBasic).filter(StockBasic.code == code).first()
            name = name.股票简称 if name else code

            result.append({
                "code": code,
                "name": name,
                "total_buy": round(total_buy_cost, 2),
                "total_sell": round(total_sell_proceeds, 2),
                "profit": round(profit, 2),
                "profit_pct": round(profit / total_buy_cost * 100, 2) if total_buy_cost else 0,
                "last_sell_date": sells[-1].date.strftime("%Y-%m-%d") if sells else "",
            })
        return result
    finally:
        session.close()


# ---------- 清仓 ----------
def remove_holding(code: str) -> None:
    session = _get_session()
    try:
        session.query(CostLot).filter(CostLot.code == code).delete()
        holding = session.query(Holding).filter(Holding.code == code).first()
        if holding:
            session.delete(holding)
        session.commit()
    finally:
        session.close()


# ---------- 批量导入 ----------

def _build_name_to_code_map() -> dict:
    """构建 股票名称 → 代码 的映射"""
    from a_stock_db.database import db
    session = db.get_session()
    try:
        rows = session.query(StockBasic).all()
        return {r.股票简称: r.code for r in rows if r.股票简称}
    finally:
        session.close()


def _parse_trade_text(text: str) -> list[dict]:
    """解析交易记录文本为结构化列表。
    支持格式：YYYY-MM-DD HH:MM 买入/卖出 股票名 价格 数量 金额 费用
    """
    # 匹配: 日期 时间 类型 名称 价格 数量 金额 费用
    pattern = re.compile(
        r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s+'   # 日期 + 时间
        r'(买入|卖出)\s+'                              # 交易类型
        r'(\S+)\s+'                                    # 股票名称
        r'([\d,]+\.?\d*)\s+'                           # 价格（可能含千分位逗号）
        r'(\d+)\s+'                                    # 数量
        r'([\d,]+\.?\d*)\s+'                           # 金额（可能含千分位逗号）
        r'([\d,]+\.?\d*)'                              # 费用（可能含千分位逗号）
    )

    trades = []
    for line in text.strip().splitlines():
        line = line.strip()
        m = pattern.search(line)
        if not m:
            continue

        date_str = m.group(1)       # 2026-04-23
        time_str = m.group(2)       # 14:17
        trade_type = m.group(3)     # 买入 / 卖出
        stock_name = m.group(4)     # 天创时尚
        price = float(m.group(5).replace(',', ''))    # 13.000
        shares = int(m.group(6))                       # 100
        # amount = float(m.group(7).replace(',', ''))  # 不用，由 shares * price 计算
        fee = float(m.group(8).replace(',', ''))       # 0.78

        trades.append({
            'date': date_str,
            'time': time_str,
            'type': 'buy' if trade_type == '买入' else 'sell',
            'name': stock_name,
            'price': price,
            'shares': shares,
            'fee': fee,
            'note': f"{time_str}{trade_type}",
        })

    # 按日期+时间正序（先发生的先录入，保证卖出校验正确）
    trades.sort(key=lambda t: f"{t['date']} {t['time']}")
    return trades


def batch_import(text: str) -> dict:
    """批量解析并录入交易记录。
    返回 { total, success_count, fail_count, results: [...] }
    """
    trades = _parse_trade_text(text)
    if not trades:
        return {"total": 0, "success_count": 0, "fail_count": 0, "results": []}

    # 构建名称→代码映射
    name_map = _build_name_to_code_map()

    results = []
    for t in trades:
        code = name_map.get(t['name'])
        if not code:
            results.append({
                "success": False,
                "name": t['name'],
                "code": "",
                "type": t['type'],
                "price": t['price'],
                "shares": t['shares'],
                "fee": t['fee'],
                "date": t['date'],
                "error": f"未找到股票「{t['name']}」的代码",
            })
            continue

        try:
            if t['type'] == 'buy':
                buy_stock(
                    code=code,
                    shares=t['shares'],
                    price=t['price'],
                    fee=t['fee'],
                    date=t['date'],
                    note=t['note'],
                )
            else:
                sell_stock(
                    code=code,
                    shares=t['shares'],
                    price=t['price'],
                    fee=t['fee'],
                    date=t['date'],
                    note=t['note'],
                )
            results.append({
                "success": True,
                "name": t['name'],
                "code": code,
                "type": t['type'],
                "price": t['price'],
                "shares": t['shares'],
                "fee": t['fee'],
                "date": t['date'],
                "error": "",
            })
        except Exception as e:
            results.append({
                "success": False,
                "name": t['name'],
                "code": code,
                "type": t['type'],
                "price": t['price'],
                "shares": t['shares'],
                "fee": t['fee'],
                "date": t['date'],
                "error": str(e),
            })

    success_count = sum(1 for r in results if r['success'])
    return {
        "total": len(results),
        "success_count": success_count,
        "fail_count": len(results) - success_count,
        "results": results,
    }


# ---------- 内部工具 ----------
def _get_session():
    from a_stock_db.database import db
    return db.get_session()
