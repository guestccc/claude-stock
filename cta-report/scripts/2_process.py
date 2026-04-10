#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTA Report Pipeline — Step 2/4
数据处理: 读取原始K线 → 计算唐奇安通道/ATR/当日快照/评分
输出: data/daily/{date}.json
"""

from __future__ import annotations
import json
import math
import os
import sys
from datetime import datetime, timedelta, date
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional

# ============================================================
# 路径配置
# ============================================================

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DAILY_DIR = PROJECT_ROOT / "data" / "daily"

REPORT_DATE_STR = datetime.now().strftime("%Y-%m-%d")
DONCHIAN_PERIOD = 20             # 唐奇安通道周期


# ============================================================
# 数据结构
# ============================================================

@dataclass
class OpeningGap:
    """开盘缺口信息"""
    gap_pct: float       # 高开幅度 %（原始值，如 6.4）
    gap_pct_display: str # 显示文本（如 "6.4%" 或 "600%"）
    gap_level: str       # 窗口内 / 较弱 / 较强


@dataclass
class OpeningRetreat:
    """盘中回调信息"""
    retreat_pct: float       # 回调幅度 %（原始值）
    retreat_pct_display: str # 显示文本
    retreat_level: str        # 强势回调0% / 偏弱回调 / 弱势回调


@dataclass
class OpeningStructureScore:
    """开盘结构得分（详细）"""
    score: int
    gap: OpeningGap
    retreat: OpeningRetreat
    holds_open: bool
    # 各维度原始分
    gap_score: int
    retreat_score: int
    hold_score: int


@dataclass
class VolumeScore:
    """量价得分"""
    score: int
    closing_strength: str  # 偏稳 / 偏弱 / 弱势
    afternoon_volume: str  # 温和放量 / 缩量


@dataclass
class CTAPosition:
    """CTA 建仓分析"""
    entry_price: float
    atr: float
    stop_loss: float
    take_profit: float
    shares: int
    amount: float
    risk_r: float
    rr_ratio: float
    allow_trade: bool
    risk_total: float


@dataclass
class StockSnapshot:
    """单只股票当日快照"""
    code: str
    name: str
    # K线数据
    open: float
    high: float
    low: float
    close: float
    volume: float
    # 唐奇安通道
    upper_band: float          # 20日最高价
    pullback_pct: float        # 回踩 %（负值）
    pullback_pct_display: str  # 显示文本
    # 均价偏离
    vwap: float                # 当日均价
    avg_diff_pct: float       # 均价偏离 %
    # 开盘结构
    opening: OpeningStructureScore
    # 量价
    volume_score: VolumeScore
    # 综合评分
    total_score: int
    market_score: int          # 大盘共振分
    pullback_score: int        # 回踩得分
    avg_price_score: int      # 均价偏离得分
    # CTA
    cta: CTAPosition


# ============================================================
# 工具函数
# ============================================================

def round2(x: float) -> float:
    return round(x, 2)


def to_display_pct(v: float, threshold: float = 100) -> str:
    """将数值转为百分比显示文本"""
    if abs(v) >= threshold:
        return f"{v:.0f}%"
    return f"{v:.1f}%"


# ============================================================
# 指标计算
# ============================================================

def calc_atr(df_rows: list, period: int = 14) -> float:
    """
    计算 ATR（Average True Range）
    使用 Wilder 平滑法
    """
    if len(df_rows) < period + 1:
        return 0.0

    # 取最近 period+1 条（包含当天）
    rows = df_rows[-(period + 1):]

    trs = []
    for i in range(1, len(rows)):
        high  = rows[i]["high"]
        low   = rows[i]["low"]
        prev  = rows[i - 1]["close"]
        tr = max(
            high - low,
            abs(high - prev),
            abs(low - prev)
        )
        trs.append(tr)

    if not trs:
        return 0.0

    # Wilder 平滑：第一个值用简单均值，后续用移动均值
    atr = sum(trs) / len(trs)
    alpha = 1.0 / period
    for tr in trs[1:]:
        atr = atr * (1 - alpha) + tr * alpha

    return atr


def calc_donchian_upper(df_rows: list, period: int = 20, exclude_today: bool = True) -> float:
    """
    计算唐奇安通道上轨（前N日最高价，不含当天）
    原报告的上轨 = 突破前的阻力位，必须排除当天K线
    """
    if exclude_today:
        rows = df_rows[:-1]  # 排除最后一天（当天）
    else:
        rows = df_rows
    if len(rows) < period:
        return max(r["high"] for r in rows) if rows else 0.0
    recent = rows[-period:]
    return max(r["high"] for r in recent)


def calc_vwap(day_row: dict) -> float:
    """计算当日 VWAP（均价 = 成交额 / 成交量）"""
    v = day_row.get("volume", 0) or 0
    if v == 0:
        return day_row.get("close", 0) or 0
    turnover = day_row.get("turnover", 0) or 0
    if turnover == 0:
        turnover = (day_row.get("close", 0) or 0) * v
    return turnover / v


def calc_pullback(current: float, day_high: float) -> float:
    """回踩 % = (现价 - 当日最高价) / 当日最高价 × 100"""
    if day_high == 0:
        return 0.0
    return (current - day_high) / day_high * 100


def calc_avg_diff(current: float, vwap: float) -> float:
    """均价偏离 %"""
    if vwap == 0:
        return 0.0
    return (current - vwap) / vwap * 100


# ============================================================
# 评分引擎（精确还原原报告评分逻辑）
# ============================================================

def score_opening(gap_pct: float, retreat_pct: float, holds_open: bool) -> OpeningStructureScore:
    """
    开盘结构得分（满分 25）

    规则（从原报告反推）：
    缺口（满分 8）:
      abs(gap) < 4.0  → 窗口内 8分
      4.0 ≤ abs(gap) < 7.0 → 较弱 6分
      abs(gap) ≥ 7.0  → 较强 4分

    回调（满分 12）:
      retreat_pct_display = 0%  → 强势回调0% 12分
      1~20%               → 偏弱回调 8分
      20~300%             → 弱势回调 4分
      ≥300% (即 retreat_pct_raw ≥ 300) → 弱势回调 0分

    守住开盘价（+5分）:
      holds_open=True → +5
    """

    # --- 缺口评分 ---
    abs_gap = abs(gap_pct)
    if abs_gap < 4.0:
        gap_level, gap_score = "窗口内", 8
    elif abs_gap < 7.0:
        gap_level, gap_score = "较弱", 6
    else:
        gap_level, gap_score = "较强", 4

    # --- 回调评分 ---
    abs_retreat = abs(retreat_pct)
    if abs_retreat == 0:
        retreat_level, retreat_score = "强势回调", 12
    elif abs_retreat <= 20:
        retreat_level, retreat_score = "偏弱回调", 8
    elif abs_retreat < 300:
        retreat_level, retreat_score = "弱势回调", 4
    else:
        retreat_level, retreat_score = "弱势回调", 0

    # --- 守住开盘价 ---
    hold_score = 5 if holds_open else 0

    total = gap_score + retreat_score + hold_score

    return OpeningStructureScore(
        score=total,
        gap=OpeningGap(
            gap_pct=gap_pct,
            gap_pct_display=to_display_pct(gap_pct),
            gap_level=gap_level
        ),
        retreat=OpeningRetreat(
            retreat_pct=retreat_pct,
            # 显示文本（数值 ×100 后取整，如 "0%" "51%" "684%"）
            retreat_pct_display=f"{abs(retreat_pct) * 100:.0f}%",
            retreat_level=retreat_level
        ),
        holds_open=holds_open,
        gap_score=gap_score,
        retreat_score=retreat_score,
        hold_score=hold_score
    )


def score_pullback(pullback_pct: float) -> int:
    """回踩得分（满分 40）"""
    abs_pb = abs(pullback_pct)
    if abs_pb <= 0.5:
        return 40
    elif abs_pb <= 1.0:
        return 30
    elif abs_pb <= 2.0:
        return 25
    elif abs_pb <= 3.0:
        return 18
    else:
        return 10


def score_avg_diff(diff_pct: float) -> int:
    """均价偏离得分（满分 15）"""
    score = int(round(abs(diff_pct) * 1.5))
    return min(score, 15)


def score_volume(closing_strength: str, afternoon_volume: str) -> VolumeScore:
    """
    量价得分（满分 9）
    尾盘强度 + 下午量能 → 综合得分
    """
    cs_score = {"偏稳": 5, "偏弱": 3, "弱势": 0}.get(closing_strength, 0)
    af_score = {"温和放量": 4, "缩量": 0}.get(afternoon_volume, 0)

    if cs_score == 5 and af_score == 4:
        total, label = 9, "偏稳"
    elif cs_score == 5 and af_score == 0:
        total, label = 6, "偏稳"
    elif cs_score == 3 and af_score == 4:
        total, label = 6, "偏弱"
    else:
        total, label = 0, "弱势"

    return VolumeScore(
        score=total,
        closing_strength=label,
        afternoon_volume=afternoon_volume
    )


def calc_market_score(market_change_pct: float) -> int:
    """
    大盘共振分（满分 30）
    - 大盘涨幅 ≥ 0.5%: 30分（共振强）
    - 大盘涨幅 0~0.5%: 10分（弱共振）
    - 大盘涨跌 ±0%: 0分（无共振，与原报告一致）
    - 大盘跌幅 > 0%: 0分
    """
    if market_change_pct >= 0.5:
        return 30
    elif market_change_pct > 0.05:
        return 10
    else:
        return 0


# ============================================================
# CTA 建仓计算
# ============================================================

def calc_cta_position(
    entry_price: float,
    atr: float,
    risk_budget_r: float = 1.0
) -> CTAPosition:
    """计算 CTA 建仓参数"""
    if atr <= 0 or entry_price <= 0:
        return CTAPosition(
            entry_price=entry_price, atr=atr,
            stop_loss=0, take_profit=0,
            shares=0, amount=0, risk_r=0,
            rr_ratio=2.0, allow_trade=False, risk_total=0
        )

    stop = entry_price - atr * 1.3
    target = entry_price + atr * 2.0
    risk_per_share = entry_price - stop

    if risk_per_share <= 0 or risk_budget_r <= 0:
        return CTAPosition(
            entry_price=entry_price, atr=atr,
            stop_loss=round2(stop), take_profit=round2(target),
            shares=0, amount=0, risk_r=0,
            rr_ratio=2.0, allow_trade=False, risk_total=0
        )

    # 理论股数 = 风险预算(元) / 每股风险
    # 风险预算 = risk_budget_r × 100（R 以 100 元/手为参考）
    theoretical_shares = risk_budget_r * 100 / risk_per_share * entry_price
    shares = math.floor(theoretical_shares / 100) * 100  # 整手

    if shares < 100:
        shares, risk_r = 0, 0.0
        allow_trade = False
    else:
        risk_r = risk_budget_r
        allow_trade = True

    return CTAPosition(
        entry_price=round2(entry_price),
        atr=round(atr, 3),
        stop_loss=round2(stop),
        take_profit=round2(target),
        shares=shares,
        amount=round(shares * entry_price, 0),
        risk_r=round(risk_r, 2),
        rr_ratio=2.0,
        allow_trade=allow_trade,
        risk_total=round(risk_r, 2)
    )


def risk_budget_by_score(score: int) -> float:
    """根据评分动态风险预算"""
    if score >= 95:
        return 1.5
    elif score >= 90:
        return 1.0
    elif score >= 85:
        return 0.8
    elif score >= 80:
        return 0.5
    return 0.0


# ============================================================
# 单只股票处理
# ============================================================

def process_stock(
    code: str,
    name: str,
    raw_data: dict,
    market_change_pct: float,
    report_date: str
) -> Optional[StockSnapshot]:
    """处理单只股票：读取K线 → 计算指标 → 评分"""

    rows = raw_data.get("data", [])
    if not rows:
        return None

    # 当日数据（最后一条）
    today = rows[-1]
    if str(today.get("date", ""))[:10] != report_date:
        # 如果最后一条不是报告日期，取最近一条
        today = rows[-1]

    current_price = today["close"]
    open_price = today["open"]
    high = today["high"]
    low = today["low"]

    # ATR（用前N日数据，不含当天）
    atr = calc_atr(rows[:-1] if len(rows) > 1 else rows)

    # 唐奇安上轨（前N日最高价，排除当天）
    upper_band = calc_donchian_upper(rows, DONCHIAN_PERIOD, exclude_today=True)

    # VWAP
    vwap = calc_vwap(today)

    # 回踩 = 现价相对当日最高价的回撤
    pullback_pct = calc_pullback(current_price, high)

    # 均价偏离
    avg_diff = calc_avg_diff(current_price, vwap)

    # 开盘缺口
    gap_pct = (open_price / rows[-2]["close"] - 1) * 100 if len(rows) > 1 else 0.0

    # 盘中回调（回撤幅度）:
    # 原报告中的 "弱势回调600%" / "偏弱回调51%" / "强势回调0%"
    # 公式: (open - low) / prev_close × 100 → 显示时 ×100（即原始整数）
    # 例: (29.3-27.4)/26.11×100 = 7.27 → 原始显示 ≈ 600
    prev_close = rows[-2]["close"] if len(rows) > 1 else open_price
    if open_price > low and prev_close > 0:
        retreat_pct = (open_price - low) / prev_close * 100
    else:
        retreat_pct = 0.0

    # 守住开盘价
    holds_open = current_price >= open_price

    # 尾盘强度（简化：收盘价位置）
    # 尾盘在当日价格区间中的相对位置
    day_range = high - low
    if day_range > 0:
        close_pos = (current_price - low) / day_range
    else:
        close_pos = 0.5

    if close_pos >= 0.6:
        closing_strength = "偏稳"
    elif close_pos >= 0.3:
        closing_strength = "偏弱"
    else:
        closing_strength = "弱势"

    # 下午量能（简化：下午时段成交量占比 > 40% 为温和放量）
    # 这里用全天成交量与前5日均量对比
    recent_vol = [(r.get("volume") or 0) for r in rows[-6:-1]]
    avg_vol = sum(recent_vol) / len(recent_vol) if recent_vol else 1
    today_vol = today.get("volume") or 0
    vol_ratio = today_vol / avg_vol if avg_vol > 0 else 1
    afternoon_volume = "温和放量" if vol_ratio >= 1.0 else "缩量"

    # --- 评分 ---
    market_score = calc_market_score(market_change_pct)
    pb_score = score_pullback(pullback_pct)
    opening_struct = score_opening(gap_pct, retreat_pct, holds_open)
    avg_diff_score = score_avg_diff(avg_diff)
    vol_score = score_volume(closing_strength, afternoon_volume)

    total = market_score + pb_score + opening_struct.score + avg_diff_score + vol_score.score

    # --- CTA ---
    risk_budget = risk_budget_by_score(total)
    cta = calc_cta_position(current_price, atr, risk_budget)

    return StockSnapshot(
        code=code,
        name=name,
        open=open_price,
        high=high,
        low=low,
        close=current_price,
        volume=today.get("volume", 0),
        upper_band=round2(upper_band),
        pullback_pct=round(pullback_pct, 1),
        pullback_pct_display=to_display_pct(pullback_pct),
        vwap=round2(vwap),
        avg_diff_pct=round(avg_diff, 1),
        opening=opening_struct,
        volume_score=vol_score,
        total_score=total,
        market_score=market_score,
        pullback_score=pb_score,
        avg_price_score=avg_diff_score,
        cta=cta
    )


# ============================================================
# 主函数
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="CTA Step 2: 数据处理")
    parser.add_argument("--date", default=REPORT_DATE_STR, help="报告日期 (YYYY-MM-DD)")
    args = parser.parse_args()

    report_date = args.date

    print("=" * 50)
    print("CTA Step 1/2: 数据处理")
    print(f"  报告日期: {report_date}")
    print(f"  数据源: a_stock_db")
    print("=" * 50)

    DATA_DAILY_DIR.mkdir(parents=True, exist_ok=True)

    # --- 读取大盘数据 ---
    from db_adapter import DBDataSource
    db = DBDataSource()
    market_change = db.get_market_change(report_date)
    print(f"\n大盘: 全市场平均 | 今日涨跌: {market_change:+.2f}%")

    # --- 处理全市场股票 ---
    snapshots = []
    codes = db.get_all_codes_with_data(report_date)
    print(f"  共 {len(codes)} 只股票有数据\n")

    for code in codes:
        name = db.get_stock_name(code)
        raw = db.get_stock_daily(code, report_date)
        if len(raw.get("data", [])) < 20:
            continue
        snap = process_stock(code, name, raw, market_change, report_date)
        if snap and snap.total_score >= 30:
            snapshots.append(snap)
            print(f"  ✅ {code} {name}: 评分 {snap.total_score} | "
                  f"回踩 {snap.pullback_pct_display} | "
                  f"开盘结构 {snap.opening.score}分 | "
                  f"量价 {snap.volume_score.score}分")

    db.close()

    # 按评分排序
    snapshots.sort(key=lambda x: x.total_score, reverse=True)

    # --- 保存每日快照 ---
    daily_data = {
        "report_date": report_date,
        "generated_at": datetime.now().isoformat(),
        "market": {
            "index": "全市场平均",
            "change_pct": round(market_change, 2),
            "market_score": calc_market_score(market_change)
        },
        "stocks": [asdict(s) for s in snapshots]
    }

    out_path = DATA_DAILY_DIR / f"{report_date}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(daily_data, f, ensure_ascii=False, indent=2)

    print(f"\n💾 每日快照已保存: {out_path}")
    print(f"\n✅ Step 1 完成！共处理 {len(snapshots)} 只股票（≥30分）")


if __name__ == "__main__":
    main()
