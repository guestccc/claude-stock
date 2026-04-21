"""持仓路由"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from server.services import portfolio_service
from server.models.portfolio import (
    HoldingsResponse,
    TransactionsResponse,
    BuyRequest,
    SellRequest,
    TradeResponse,
    HoldingItem,
    HoldingSummary,
    TransactionItem,
)

router = APIRouter(prefix="/portfolio", tags=["持仓"])


def _holding_to_item(h) -> HoldingItem:
    return HoldingItem(
        id=h.id,
        code=h.code,
        name=h.name,
        shares=h.shares,
        avg_cost=h.avg_cost,
        total_cost=h.total_cost,
        current_price=getattr(h, 'current_price', None),
        market_value=getattr(h, 'market_value', None),
        profit_amount=getattr(h, 'profit_amount', None),
        profit_pct=getattr(h, 'profit_pct', None),
        first_buy_date=h.first_buy_date.strftime("%Y-%m-%d") if h.first_buy_date else None,
        note=h.note,
        created_at=h.created_at.strftime("%Y-%m-%d %H:%M"),
        updated_at=h.updated_at.strftime("%Y-%m-%d %H:%M"),
    )


@router.get("/holdings", response_model=HoldingsResponse)
async def list_holdings():
    """获取当前持仓列表（含盈亏统计）"""
    holdings = portfolio_service.get_all_holdings()
    summary = portfolio_service.get_summary()

    holding_items = []
    for h in holdings:
        holding_items.append(HoldingItem(**h))

    return HoldingsResponse(
        holdings=holding_items,
        summary=HoldingSummary(**summary),
    )


@router.post("/buy", response_model=TradeResponse)
async def buy_stock(body: BuyRequest):
    """买入股票"""
    try:
        holding, tx = portfolio_service.buy_stock(
            code=body.code,
            shares=body.shares,
            price=body.price,
            fee=body.fee,
            date=body.date,
            note=body.note or "",
        )

        holding_item = HoldingItem(
            id=holding.id,
            code=holding.code,
            name=holding.name,
            shares=holding.shares,
            avg_cost=holding.avg_cost,
            total_cost=holding.total_cost,
            first_buy_date=holding.first_buy_date.strftime("%Y-%m-%d") if holding.first_buy_date else None,
            note=holding.note,
            created_at=holding.created_at.strftime("%Y-%m-%d %H:%M"),
            updated_at=holding.updated_at.strftime("%Y-%m-%d %H:%M"),
        )

        return TradeResponse(
            message="买入成功",
            holding=holding_item,
            transaction=TransactionItem(
                id=tx.id,
                code=tx.code,
                name=tx.name,
                type=tx.type,
                shares=tx.shares,
                price=tx.price,
                amount=tx.amount,
                fee=tx.fee,
                date=tx.date.strftime("%Y-%m-%d"),
                note=tx.note,
                created_at=tx.created_at.strftime("%Y-%m-%d %H:%M"),
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"买入失败: {e}")


@router.post("/sell", response_model=TradeResponse)
async def sell_stock(body: SellRequest):
    """卖出股票"""
    try:
        holding, tx = portfolio_service.sell_stock(
            code=body.code,
            shares=body.shares,
            price=body.price,
            fee=body.fee,
            date=body.date,
            note=body.note or "",
        )

        holding_item = None
        if holding:
            holding_item = HoldingItem(
                id=holding.id,
                code=holding.code,
                name=holding.name,
                shares=holding.shares,
                avg_cost=holding.avg_cost,
                total_cost=holding.total_cost,
                first_buy_date=holding.first_buy_date.strftime("%Y-%m-%d") if holding.first_buy_date else None,
                note=holding.note,
                created_at=holding.created_at.strftime("%Y-%m-%d %H:%M"),
                updated_at=holding.updated_at.strftime("%Y-%m-%d %H:%M"),
            )

        return TradeResponse(
            message="卖出成功",
            holding=holding_item,
            transaction=TransactionItem(
                id=tx.id,
                code=tx.code,
                name=tx.name,
                type=tx.type,
                shares=tx.shares,
                price=tx.price,
                amount=tx.amount,
                fee=tx.fee,
                date=tx.date.strftime("%Y-%m-%d"),
                note=tx.note,
                created_at=tx.created_at.strftime("%Y-%m-%d %H:%M"),
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"卖出失败: {e}")


@router.delete("/holdings/{code}", status_code=204)
async def remove_holding(code: str):
    """清仓（删除持仓记录，不记入交易）"""
    try:
        portfolio_service.remove_holding(code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions", response_model=TransactionsResponse)
async def list_transactions(
    code: Optional[str] = Query(None, description="股票代码过滤"),
    limit: int = Query(50, ge=1, le=500, description="返回条数"),
):
    """获取交易记录"""
    rows = portfolio_service.get_transactions(code=code, limit=limit)
    return TransactionsResponse(
        transactions=[TransactionItem(**r) for r in rows]
    )
