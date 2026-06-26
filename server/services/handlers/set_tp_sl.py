"""止盈止损 handler — 保存到 position_tp_sl 表"""
from server.db.models import PositionTPSL
from a_stock_db.database import db


async def handle(data: dict) -> dict:
    code = data.get("stock_code")
    tp = data.get("tp_price")
    sl = data.get("sl_price")

    if not code or tp is None or sl is None:
        return {"success": False, "message": "缺少必要参数: stock_code/tp_price/sl_price"}

    try:
        session = db.get_session()
        try:
            record = PositionTPSL(
                code=code,
                tp_price=float(tp),
                sl_price=float(sl),
                cost_price=data.get("cost_price"),
                quantity=data.get("quantity"),
                strategy=data.get("strategy", ""),
                reason=data.get("reason", ""),
            )
            session.add(record)
            session.commit()
            session.refresh(record)

            return {
                "success": True,
                "message": f"已保存止盈止损：止盈 {tp} / 止损 {sl}",
                "data": {
                    "id": record.id,
                    "code": code,
                    "tp_price": tp,
                    "sl_price": sl,
                    "cost_price": data.get("cost_price"),
                    "quantity": data.get("quantity"),
                },
            }
        finally:
            session.close()
    except Exception as e:
        return {"success": False, "message": f"保存失败: {str(e)}"}
