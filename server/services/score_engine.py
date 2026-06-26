#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可配置评分引擎 — 组合回测信号排序用

设计原则:
  - 每个维度 = 评分函数 + 权重 + 启用开关 + 参数
  - 配置可 JSON 持久化，方便新增/修改/删除维度
  - 评分函数签名统一: func(rows, idx, params) -> float (0~100)
  - 复用 backtest_service 的指标计算函数，避免重复造轮子
"""

import os
import json
from typing import Dict, Any, Tuple, Optional, List

from server.services.backtest_service import (
    calc_donchian_upper,
    calc_donchian_lower,
    calc_atr,
    calc_boll_upper,
    calc_boll_middle,
)

DONCHIAN_PERIOD = 20
ATR_PERIOD = 14
BOLL_PERIOD = 20
BOLL_STD = 2

# 评分配置持久化路径
_SCORE_CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config",
    "score_config.json",
)


# ============================================================
# 评分函数（每个返回 0~100）
# ============================================================

def score_breakout_strength(rows, idx, params):
    """突破力度：收盘价相对唐奇安上轨的超出 %，1~3% 最优（过低动能不足，过高追高风险）"""
    upper = calc_donchian_upper(rows[:idx + 1], DONCHIAN_PERIOD, exclude_today=True)
    if upper <= 0:
        return 0
    close = rows[idx]["close"] or 0
    if close <= 0:
        return 0
    pct = (close - upper) / upper * 100
    opt_min = params.get("optimal_min", 1.0)
    opt_max = params.get("optimal_max", 3.0)
    if opt_min <= pct <= opt_max:
        return 100
    if pct < opt_min:
        # 突破力度不足，按比例给分
        return pct / opt_min * 80 if opt_min > 0 else 0
    if pct <= opt_max * 2:
        # 追高区间，递减
        return max(0, 80 - (pct - opt_max) / opt_max * 80) if opt_max > 0 else 0
    return 0  # 追高超 2 倍最优区间


def score_volume_ratio(rows, idx, params):
    """量能配合：当日成交量 / N 日均量，放量配合突破得分高"""
    period = int(params.get("period", 5))
    if idx < period:
        return 50
    today_vol = rows[idx]["volume"] or 0
    avg = sum((rows[i]["volume"] or 0) for i in range(idx - period, idx)) / period
    if avg <= 0:
        return 50
    vr = today_vol / avg
    optimal_min = params.get("optimal_min", 1.5)
    if vr >= optimal_min:
        return 100
    if vr >= 1.0:
        return 60
    return max(0, vr / optimal_min * 50) if optimal_min > 0 else 0


def score_intraday_strength(rows, idx, params):
    """日内强度：(收盘-最低)/(最高-最低)，收在最高附近得满分"""
    r = rows[idx]
    h = r["high"] or 0
    l = r["low"] or 0
    c = r["close"] or 0
    if h == l:
        return 50
    return (c - l) / (h - l) * 100


def score_breakout_days(rows, idx, params):
    """突破持续性：收盘价连续高于唐奇安上轨的天数，2~3 天最优（刚突破最强势，太久可能动力衰竭）"""
    upper = calc_donchian_upper(rows[:idx + 1], DONCHIAN_PERIOD, exclude_today=True)
    if upper <= 0:
        return 0
    days = 0
    for i in range(idx, max(0, idx - 10), -1):
        if (rows[i]["close"] or 0) > upper:
            days += 1
        else:
            break
    opt_min = params.get("optimal_min", 2)
    opt_max = params.get("optimal_max", 3)
    if opt_min <= days <= opt_max:
        return 100
    if days == 1:
        return 60
    if days > opt_max:
        return max(0, 80 - (days - opt_max) * 15)
    return 0


def score_ma_alignment(rows, idx, params):
    """均线排列：MA5 > MA10 > MA20 多头排列得满分"""
    periods = params.get("periods", [5, 10, 20])
    mas = []
    for p in periods:
        if idx < p:
            return 0
        ma = sum((rows[i]["close"] or 0) for i in range(idx - p, idx)) / p
        mas.append(ma)
    # 全多头排列
    if all(mas[i] > mas[i + 1] for i in range(len(mas) - 1)):
        return 100
    # 部分多头：短周期在长周期上方
    if len(mas) >= 2 and mas[0] > mas[-1]:
        return 50
    return 0


def score_safety_margin(rows, idx, params):
    """安全垫：收盘价离唐奇安下轨的距离比例，距离越远越安全"""
    lower = calc_donchian_lower(rows[:idx + 1], DONCHIAN_PERIOD, exclude_today=True)
    close = rows[idx]["close"] or 0
    if lower <= 0 or close <= 0:
        return 50
    pct = (close - lower) / lower * 100
    if pct >= 50:
        return 100
    if pct >= 30:
        return 80
    if pct >= 20:
        return 60
    if pct >= 10:
        return 30
    return 0


def score_volatility(rows, idx, params):
    """波动率控制：ATR/close 比例越低越稳（低波动适合突破）"""
    atr = calc_atr(rows[:idx + 1], int(params.get("atr_period", ATR_PERIOD)))
    close = rows[idx]["close"] or 0
    if close <= 0:
        return 50
    vol = atr / close * 100
    if vol <= 2:
        return 100
    if vol <= 3:
        return 80
    if vol <= 5:
        return 50
    if vol <= 8:
        return 20
    return 0


def score_pre_breakout_momentum(rows, idx, params):
    """突破前动量：前 N 天涨幅越小越好（盘整末端突破爆发力强）"""
    lb = int(params.get("lookback", 5))
    if idx < lb:
        return 50
    start_close = rows[idx - lb]["close"] or 0
    end_close = rows[idx - 1]["close"] or 0
    if start_close <= 0:
        return 50
    pct = (end_close - start_close) / start_close * 100
    optimal_max = params.get("optimal_max", 10)
    if pct <= optimal_max:
        return 100
    if pct <= 20:
        return 60
    return 20


def score_boll_squeeze(rows, idx, params):
    """布林带收窄：带宽越小（盘整越久）爆发力越强"""
    period = int(params.get("period", BOLL_PERIOD))
    std_k = params.get("std", BOLL_STD)
    boll_u = calc_boll_upper(rows[:idx + 1], period, std_k, exclude_today=True)
    boll_m = calc_boll_middle(rows[:idx + 1], period, exclude_today=True)
    if boll_m <= 0:
        return 50
    # 下轨 = 2*中轨 - 上轨
    boll_l = 2 * boll_m - boll_u
    width = (boll_u - boll_l) / boll_m * 100
    if width <= 5:
        return 100
    if width <= 10:
        return 80
    if width <= 15:
        return 50
    return 20


# ============================================================
# 维度注册表（默认配置）
# ============================================================

def _default_registry() -> Dict[str, Dict[str, Any]]:
    """默认评分维度配置（不含 func，func 在调用时从函数映射表查找）"""
    return {
        "breakout_strength": {
            "name": "突破力度",
            "weight": 25,
            "enabled": True,
            "params": {"optimal_min": 1.0, "optimal_max": 3.0},
        },
        "volume_ratio": {
            "name": "量能配合",
            "weight": 20,
            "enabled": True,
            "params": {"period": 5, "optimal_min": 1.5},
        },
        "intraday_strength": {
            "name": "日内强度",
            "weight": 15,
            "enabled": True,
            "params": {},
        },
        "breakout_days": {
            "name": "突破持续性",
            "weight": 15,
            "enabled": True,
            "params": {"optimal_min": 2, "optimal_max": 3},
        },
        "ma_alignment": {
            "name": "均线排列",
            "weight": 10,
            "enabled": True,
            "params": {"periods": [5, 10, 20]},
        },
        "safety_margin": {
            "name": "安全垫",
            "weight": 10,
            "enabled": True,
            "params": {},
        },
        "volatility": {
            "name": "波动率控制",
            "weight": 5,
            "enabled": True,
            "params": {"atr_period": ATR_PERIOD},
        },
        # === 可选维度（默认关闭）===
        "pre_breakout_momentum": {
            "name": "突破前动量",
            "weight": 0,
            "enabled": False,
            "params": {"lookback": 5, "optimal_max": 10},
        },
        "boll_squeeze": {
            "name": "布林带收窄",
            "weight": 0,
            "enabled": False,
            "params": {"period": BOLL_PERIOD, "std": BOLL_STD},
        },
    }


# 评分函数映射表（key → callable）
_SCORE_FUNCS = {
    "breakout_strength": score_breakout_strength,
    "volume_ratio": score_volume_ratio,
    "intraday_strength": score_intraday_strength,
    "breakout_days": score_breakout_days,
    "ma_alignment": score_ma_alignment,
    "safety_margin": score_safety_margin,
    "volatility": score_volatility,
    "pre_breakout_momentum": score_pre_breakout_momentum,
    "boll_squeeze": score_boll_squeeze,
}


# ============================================================
# 配置持久化
# ============================================================

def get_score_config() -> List[Dict[str, Any]]:
    """读取评分配置（合并持久化文件与默认值），返回维度列表"""
    registry = _default_registry()
    saved = _load_config_file()
    if saved:
        # 用持久化配置覆盖默认值（只覆盖已知维度）
        for key, dim in saved.items():
            if key in registry:
                registry[key]["weight"] = dim.get("weight", registry[key]["weight"])
                registry[key]["enabled"] = dim.get("enabled", registry[key]["enabled"])
                if "params" in dim and isinstance(dim["params"], dict):
                    registry[key]["params"].update(dim["params"])
    # 转为列表形式（不含 func）
    return [
        {
            "key": key,
            "name": dim["name"],
            "weight": dim["weight"],
            "enabled": dim["enabled"],
            "params": dim["params"],
        }
        for key, dim in registry.items()
    ]


def save_score_config(dimensions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """保存评分配置到 JSON 文件，返回保存后的完整配置"""
    current = {d["key"]: d for d in get_score_config()}
    for dim in dimensions:
        key = dim.get("key")
        if key in current:
            current[key]["weight"] = float(dim.get("weight", current[key]["weight"]))
            current[key]["enabled"] = bool(dim.get("enabled", current[key]["enabled"]))
            if "params" in dim and isinstance(dim["params"], dict):
                current[key]["params"] = dim["params"]
    # 持久化（只存 key/weight/enabled/params/name）
    to_save = {
        key: {
            "name": d["name"],
            "weight": d["weight"],
            "enabled": d["enabled"],
            "params": d["params"],
        }
        for key, d in current.items()
    }
    _save_config_file(to_save)
    return list(current.values())


def _load_config_file() -> Optional[Dict[str, Any]]:
    """从 JSON 文件加载配置"""
    if not os.path.exists(_SCORE_CONFIG_FILE):
        return None
    try:
        with open(_SCORE_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_config_file(config: Dict[str, Any]):
    """保存配置到 JSON 文件"""
    os.makedirs(os.path.dirname(_SCORE_CONFIG_FILE), exist_ok=True)
    with open(_SCORE_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ============================================================
# 统一评分入口
# ============================================================

def _build_merged_registry(config_override: Optional[Dict] = None) -> Dict[str, Dict[str, Any]]:
    """
    合并持久化配置 + 用户传入的覆盖配置，得到最终维度配置（含 func）
    config_override 形如: {"breakout_strength": {"weight": 30}, "volatility": {"enabled": False}}
    """
    # 从最新持久化配置开始
    persisted = {d["key"]: d for d in get_score_config()}
    # 注入 func
    registry = {}
    for key, dim in persisted.items():
        registry[key] = {
            "name": dim["name"],
            "weight": dim["weight"],
            "enabled": dim["enabled"],
            "params": dict(dim["params"]),
            "func": _SCORE_FUNCS.get(key),
        }
    # 应用用户覆盖
    if config_override:
        for key, override in config_override.items():
            if key in registry and isinstance(override, dict):
                if "weight" in override:
                    registry[key]["weight"] = float(override["weight"])
                if "enabled" in override:
                    registry[key]["enabled"] = bool(override["enabled"])
                if "params" in override and isinstance(override["params"], dict):
                    registry[key]["params"].update(override["params"])
    return registry


def score_signal(rows, idx: int, config_override: Optional[Dict] = None) -> Tuple[float, Dict[str, Dict[str, float]]]:
    """
    对某只股票在某日的突破信号打分

    参数:
        rows: K 线数据列表（与 backtest_service 同格式）
        idx: 当日在 rows 中的索引（信号日）
        config_override: 覆盖默认配置，形如 {"breakout_strength": {"weight": 30}}

    返回: (total_score 0~100, detail_dict)
        detail_dict[key] = {"raw": 原始分, "weighted": 加权分, "name": 维度名}
    """
    registry = _build_merged_registry(config_override)
    total_weight = sum(
        d["weight"] for d in registry.values()
        if d["enabled"] and d["weight"] > 0 and d["func"] is not None
    )
    if total_weight <= 0:
        return 0.0, {}

    total = 0.0
    detail: Dict[str, Dict[str, float]] = {}
    for key, dim in registry.items():
        if not dim["enabled"] or dim["weight"] <= 0 or dim["func"] is None:
            continue
        try:
            raw = dim["func"](rows, idx, dim["params"])
        except Exception:
            raw = 0.0
        raw = max(0.0, min(100.0, float(raw)))
        weighted = raw * dim["weight"] / total_weight
        total += weighted
        detail[key] = {
            "name": dim["name"],
            "raw": round(raw, 1),
            "weighted": round(weighted, 1),
        }

    return round(total, 1), detail
