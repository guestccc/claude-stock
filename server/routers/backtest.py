"""回测路由"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session

from server.services.backtest_service import backtest_stock, get_stock_name
from server.models.backtest import (
    BacktestRequest,
    BacktestResponse,
    BacktestStats,
    TradeResult,
    EquityPoint,
    KlineBar,
    SaveBacktestRequest,
    BacktestHistoryItem,
    BacktestHistoryListResponse,
    BacktestDetailResponse,
    ExitStrategyListResponse,
    ExitStrategyInfo,
)
from server.db.models import BacktestResult as BacktestResultORM, BacktestTrade as BacktestTradeORM, BacktestRecentStock as BacktestRecentStockORM
from a_stock_db.database import db

router = APIRouter(prefix="/backtest", tags=["回测"])


def _record_recent_stock(code: str, name: str):
    """记录近期回测过的股票（upsert）"""
    session = db.get_session()
    try:
        existing = session.query(BacktestRecentStockORM).filter(
            BacktestRecentStockORM.code == code
        ).first()
        if existing:
            existing.name = name
            existing.last_run_at = datetime.now()
        else:
            session.add(BacktestRecentStockORM(code=code, name=name))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


# ---------- 策略列表 ----------

STRATEGIES = [
    {"key": "fixed", "name": "固定止盈止损", "description": "触及固定止盈或止损价即平仓"},
    {"key": "trailing", "name": "移动止盈", "description": "先到目标位，再回撤ATR系数倍止盈"},
    {"key": "boll_middle", "name": "BOLL中轨止盈", "description": "收盘价跌破BOLL中轨时止盈"},
    {"key": "trailing_boll", "name": "移动止盈+BOLL中轨", "description": "跟踪止损与BOLL中轨双条件止盈"},
    {"key": "ma5_exit", "name": "跌破5日线止盈", "description": "收盘跌破5日均线，次日开盘价卖出"},
    {"key": "half_exit", "name": "半仓止盈", "description": "半仓固定止盈，剩余仓位移动止损"},
    {"key": "half_exit_ma5", "name": "半仓止盈+5日线", "description": "半仓固定止盈，剩余跌破5日均线次日开盘卖出"},
    {"key": "half_exit_low3", "name": "半仓止盈+前3日低点", "description": "半仓固定止盈，剩余跌破前3日最低收盘价清仓"},
    {"key": "turtle", "name": "经典海龟交易", "description": "ATR(20)，2×ATR止损，0.5×ATR加仓（最多4仓），10日低点出场，1%风险仓位"},
]


@router.get("/strategies", response_model=ExitStrategyListResponse)
async def list_strategies():
    """获取出场策略列表"""
    return {"strategies": [ExitStrategyInfo(**s) for s in STRATEGIES]}


@router.get("/recent-stocks")
async def recent_stocks(limit: int = Query(10, ge=1, le=50)):
    """获取近期回测过的股票列表（按最近运行时间排序）"""
    session = db.get_session()
    try:
        rows = (
            session.query(BacktestRecentStockORM)
            .order_by(BacktestRecentStockORM.last_run_at.desc())
            .limit(limit)
            .all()
        )
        return {
            "stocks": [
                {"code": r.code, "name": r.name}
                for r in rows
            ]
        }
    finally:
        session.close()


# ---------- 运行回测 ----------

@router.post("/run", response_model=BacktestResponse)
async def run_backtest(req: BacktestRequest):
    """运行回测（不保存到数据库）"""
    end_date = req.end_date or datetime.now().strftime("%Y-%m-%d")
    name = get_stock_name(req.code)

    try:
        trades, equity_curve, stats, klines = backtest_stock(
            code=req.code,
            start_date=req.start_date,
            end_date=end_date,
            initial_capital=req.initial_capital,
            tp_multiplier=req.tp_multiplier,
            exit_strategy=req.exit_strategy,
            trailing_atr_k=req.trailing_atr_k,
            half_exit_pct=req.half_exit_pct,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"回测执行失败: {e}")

    resp = BacktestResponse(
        code=req.code,
        name=name,
        request=req,
        stats=BacktestStats(**stats),
        trades=[TradeResult(**t) for t in trades],
        equity_curve=[EquityPoint(**e) for e in equity_curve],
        klines=[KlineBar(**k) for k in klines],
    )

    # 自动记录到近期回测股票表
    _record_recent_stock(req.code, name)

    return resp


# ---------- 保存回测 ----------

@router.post("/save", response_model=dict)
async def save_backtest(req: SaveBacktestRequest):
    """保存回测结果到数据库（用户手动触发）"""
    session: Session = db.get_session()
    session.expire_on_commit = False
    try:
        result = BacktestResultORM(
            code=req.code,
            name=req.name,
            start_date=req.request.start_date,
            end_date=req.request.end_date or datetime.now().strftime("%Y-%m-%d"),
            initial_capital=req.request.initial_capital,
            exit_strategy=req.request.exit_strategy,
            tp_multiplier=req.request.tp_multiplier,
            trailing_atr_k=req.request.trailing_atr_k,
            half_exit_pct=req.request.half_exit_pct,
            stats_json=json.dumps(req.stats.model_dump(), ensure_ascii=False),
            equity_curve_json=json.dumps(
                [e.model_dump() for e in req.equity_curve], ensure_ascii=False
            ),
            klines_json=json.dumps(
                [k.model_dump() for k in req.klines], ensure_ascii=False
            ) if req.klines else None,
        )
        session.add(result)
        session.flush()

        # 保存交易明细
        for t in req.trades:
            trade_orm = BacktestTradeORM(
                backtest_id=result.id,
                entry_date=t.entry_date,
                exit_date=t.exit_date,
                entry_price=t.entry_price,
                exit_price=t.exit_price,
                stop_loss=t.stop_loss,
                take_profit=t.take_profit,
                shares=t.shares,
                pnl=t.pnl,
                pnl_r=t.pnl_r,
                holding_days=t.holding_days,
                reason=t.reason,
                atr=t.atr,
                upper_band=t.upper_band,
                breakout_close=t.breakout_close,
                breakout_exceed_pct=t.breakout_exceed_pct,
                exit_formula=t.exit_formula,
            )
            session.add(trade_orm)

        session.commit()
        return {"id": result.id, "message": "保存成功"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"保存失败: {e}")
    finally:
        session.close()


# ---------- 历史列表 ----------

@router.get("/history", response_model=BacktestHistoryListResponse)
async def list_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
):
    """获取历史回测列表"""
    session: Session = db.get_session()
    try:
        total = session.query(BacktestResultORM).count()
        offset = (page - 1) * page_size
        rows = (
            session.query(BacktestResultORM)
            .order_by(BacktestResultORM.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        items = []
        for r in rows:
            stats = json.loads(r.stats_json or "{}")
            items.append(BacktestHistoryItem(
                id=r.id,
                code=r.code,
                name=r.name,
                start_date=r.start_date,
                end_date=r.end_date,
                exit_strategy=r.exit_strategy,
                total_return_pct=stats.get("total_return_pct", 0),
                num_trades=stats.get("num_trades", 0),
                win_rate=stats.get("win_rate", 0),
                max_drawdown_pct=stats.get("max_drawdown_pct", 0),
                created_at=r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            ))

        return BacktestHistoryListResponse(items=items, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")
    finally:
        session.close()


# ---------- 历史详情 ----------

@router.get("/history/{backtest_id}", response_model=BacktestDetailResponse)
async def get_history_detail(backtest_id: int):
    """获取某次回测的完整详情"""
    session: Session = db.get_session()
    try:
        r = session.query(BacktestResultORM).filter(BacktestResultORM.id == backtest_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="回测记录不存在")

        stats = json.loads(r.stats_json or "{}")
        equity_curve = json.loads(r.equity_curve_json or "[]")
        klines = json.loads(r.klines_json or "[]")
        trades = session.query(BacktestTradeORM).filter(
            BacktestTradeORM.backtest_id == backtest_id
        ).order_by(BacktestTradeORM.entry_date).all()

        return BacktestDetailResponse(
            id=r.id,
            code=r.code,
            name=r.name,
            start_date=r.start_date,
            end_date=r.end_date,
            initial_capital=r.initial_capital,
            exit_strategy=r.exit_strategy,
            tp_multiplier=r.tp_multiplier,
            trailing_atr_k=r.trailing_atr_k,
            half_exit_pct=r.half_exit_pct,
            stats=BacktestStats(**stats),
            trades=[TradeResult(
                entry_date=t.entry_date,
                exit_date=t.exit_date,
                entry_price=t.entry_price,
                exit_price=t.exit_price,
                stop_loss=t.stop_loss,
                take_profit=t.take_profit,
                shares=t.shares,
                pnl=t.pnl,
                pnl_r=t.pnl_r,
                holding_days=t.holding_days,
                reason=t.reason,
                atr=t.atr,
                upper_band=t.upper_band,
                breakout_close=t.breakout_close,
                breakout_exceed_pct=t.breakout_exceed_pct,
                exit_formula=t.exit_formula,
            ) for t in trades],
            equity_curve=[EquityPoint(**e) for e in equity_curve],
            klines=[KlineBar(**k) for k in klines],
            created_at=r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")
    finally:
        session.close()


# ---------- 删除历史 ----------

@router.delete("/history/{backtest_id}", status_code=204)
async def delete_history(backtest_id: int):
    """删除历史回测记录"""
    session: Session = db.get_session()
    try:
        r = session.query(BacktestResultORM).filter(BacktestResultORM.id == backtest_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="回测记录不存在")
        session.delete(r)
        session.commit()
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {e}")
    finally:
        session.close()
