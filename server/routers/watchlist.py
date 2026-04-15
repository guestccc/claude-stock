"""自选股路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from sqlalchemy import func
from server.deps import get_session
from server.models.watchlist import WatchlistCreate, WatchlistUpdate, WatchlistItem, WatchlistResponse
from server.db.models import WatchlistItem as DBWatchlist
from server.services.market_service import get_stock_name  # 内部自己管 session


router = APIRouter(prefix="/watchlist", tags=["自选股"])


@router.get("", response_model=WatchlistResponse)
async def list_watchlist(session: Session = Depends(get_session)):
    """获取自选股列表"""
    items = session.query(DBWatchlist).order_by(DBWatchlist.sort_order, DBWatchlist.added_at).all()
    return WatchlistResponse(items=[
        WatchlistItem(
            id=item.id,
            code=item.code,
            name=item.name,
            added_at=item.added_at.strftime("%Y-%m-%d %H:%M"),
            sort_order=item.sort_order,
            note=item.note,
        )
        for item in items
    ])


@router.post("", response_model=WatchlistItem, status_code=201)
async def add_to_watchlist(body: WatchlistCreate, session: Session = Depends(get_session)):
    """添加自选股"""
    # 根据代码查询股票名称
    name = get_stock_name(body.code)
    if not name:
        raise HTTPException(status_code=404, detail=f"股票代码 {body.code} 不存在")

    # 查最大 sort_order
    max_order = session.query(func.max(DBWatchlist.sort_order)).scalar() or 0
    sort_order = max_order + 1

    item = DBWatchlist(
        code=body.code,
        name=name,
        sort_order=sort_order,
        note='',
        added_at=datetime.now(),
    )
    session.add(item)
    try:
        session.commit()
        session.refresh(item)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail=f"{body.code} 已在自选股中")

    return WatchlistItem(
        id=item.id,
        code=item.code,
        name=item.name,
        added_at=item.added_at.strftime("%Y-%m-%d %H:%M"),
        sort_order=item.sort_order,
        note=item.note,
    )


@router.delete("/{item_id}", status_code=204)
async def remove_from_watchlist(item_id: int, session: Session = Depends(get_session)):
    """删除自选股"""
    item = session.get(DBWatchlist, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="记录不存在")
    session.delete(item)
    session.commit()


@router.put("/{item_id}", response_model=WatchlistItem)
async def update_watchlist(
    item_id: int,
    body: WatchlistUpdate,
    session: Session = Depends(get_session),
):
    """更新自选股备注/排序"""
    item = session.get(DBWatchlist, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="记录不存在")

    if body.note is not None:
        item.note = body.note
    if body.sort_order is not None:
        item.sort_order = body.sort_order

    session.commit()
    session.refresh(item)

    return WatchlistItem(
        id=item.id,
        code=item.code,
        name=item.name,
        added_at=item.added_at.strftime("%Y-%m-%d %H:%M"),
        sort_order=item.sort_order,
        note=item.note,
    )
