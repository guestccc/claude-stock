"""压力支撑位 handler — 保存到 position_support_resistance 表"""
from server.db.models import SupportResistance
from a_stock_db.database import db


async def handle(data: dict) -> dict:
    code = data.get("stock_code")
    pressure = data.get("pressure_price")
    support = data.get("support_price")

    if not code or pressure is None or support is None:
        return {"success": False, "message": "缺少必要参数: stock_code/pressure_price/support_price"}

    try:
        session = db.get_session()
        try:
            record = SupportResistance(
                code=code,
                pressure_price=float(pressure),
                support_price=float(support),
                reason=data.get("reason", ""),
            )
            session.add(record)
            session.commit()
            session.refresh(record)

            return {
                "success": True,
                "message": f"已保存压力支撑位：压力 {pressure} / 支撑 {support}",
                "data": {
                    "id": record.id,
                    "code": code,
                    "pressure_price": pressure,
                    "support_price": support,
                },
            }
        finally:
            session.close()
    except Exception as e:
        return {"success": False, "message": f"保存失败: {str(e)}"}
