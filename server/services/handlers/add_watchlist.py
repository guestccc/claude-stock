"""加入自选股 handler"""
from server.db.models import WatchlistItem
from server.services.market_service import get_stock_name
from a_stock_db.database import db


async def handle(data: dict) -> dict:
    code = data.get("stock_code")
    if not code:
        return {"success": False, "message": "缺少参数: stock_code"}

    try:
        session = db.get_session()
        try:
            exists = session.query(WatchlistItem).filter(WatchlistItem.code == code).first()
            if exists:
                return {"success": True, "message": f"✅ {code} 已在自选股中"}

            name = get_stock_name(code) or code
            item = WatchlistItem(code=code, name=name, sort_order=0, note="")
            session.add(item)
            session.commit()
            return {"success": True, "message": f"✅ {name}({code}) 已加入自选股"}
        finally:
            session.close()
    except Exception as e:
        return {"success": False, "message": f"加入自选失败: {str(e)}"}
