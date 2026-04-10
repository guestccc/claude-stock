#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTA 回测报告生成器 - HTML 格式
"""

import os
from pathlib import Path
from datetime import datetime

DONCHIAN_PERIOD = 20
ATR_PERIOD = 14
BOLL_PERIOD = 20
BOLL_STD = 2

PROJECT_ROOT = Path(__file__).parent.parent
BACKTEST_DIR = PROJECT_ROOT / "backtest"


def _fix_hl(r):
    """数据库 high/low 有时颠倒，强制修正"""
    h = r["high"] or 0
    l = r["low"] or 0
    if h < l:
        h, l = l, h
    return h, l


def calc_donchian_upper_single(rows, period, idx):
    """计算某日上轨（排除当天），使用修正后的 high 值"""
    if idx < period:
        return 0.0
    recent = rows[max(0, idx - period):idx]
    if len(recent) < period:
        return 0.0
    return max(_fix_hl(r)[0] for r in recent)


def calc_donchian_lower_single(rows, period, idx):
    """计算某日下轨（排除当天），使用修正后的 low 值"""
    if idx < period:
        return 0.0
    recent = rows[max(0, idx - period):idx]
    if len(recent) < period:
        return 0.0
    return min(_fix_hl(r)[1] for r in recent)


def gen_equity_chart_config(equity_dates, equity_values, dd_values, initial_capital):
    """生成资金曲线 ECharts 配置"""
    if not equity_dates or not equity_values:
        return ""
    import json
    cfg = {
        "animation": False,
        "dataZoom": [
            {"type": "inside", "start": 0, "end": 100, "xAxisIndex": 0},
            {"type": "slider", "start": 0, "end": 100, "xAxisIndex": 0, "height": 18, "bottom": 5},
        ],
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "line"},
            "formatter": """
function(params) {
    var date = params[0].axisValue;
    var lines = ['<b>' + date + '</b>'];
    for (var i = 0; i < params.length; i++) {
        var p = params[i];
        if (p.seriesName === '资金曲线' && p.value != null) {
            lines.push('资金: <b>¥' + p.value.toLocaleString('en-US', {minimumFractionDigits: 2}) + '</b>');
        }
        if (p.seriesName === '回撤基准' && p.value != null) {
            lines.push('回撤基准: ¥' + p.value.toLocaleString('en-US', {minimumFractionDigits: 2}));
        }
    }
    return lines.join('<br>');
}""",
        },
        "grid": {"left": 55, "right": 20, "top": 15, "bottom": 45},
        "xAxis": {
            "type": "category",
            "data": equity_dates,
            "axisLabel": {"fontSize": 10, "color": "#aaa", "rotate": 30},
            "axisLine": {"lineStyle": {"color": "#ccc"}},
            "axisTick": {"show": False},
            "splitLine": {"show": False},
        },
        "yAxis": {
            "type": "value",
            "scale": True,
            "axisLabel": {
                "fontSize": 10,
                "color": "#888",
                "formatter": "¥{value.toLocaleString('en-US', {minimumFractionDigits: 0})}",
            },
            "axisLine": {"show": False},
            "axisTick": {"show": False},
            "splitLine": {"lineStyle": {"color": "#f0f0f0"}},
        },
        "series": [
            # 资金曲线
            {
                "name": "资金曲线",
                "type": "line",
                "data": equity_values,
                "smooth": True,
                "symbol": "none",
                "lineStyle": {"color": "#ef4444", "width": 2},
                "areaStyle": {
                    "color": {
                        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "rgba(239,68,68,0.25)"},
                            {"offset": 1, "color": "rgba(239,68,68,0.02)"},
                        ],
                    }
                },
            },
            # 回撤基准（峰值 - 回撤）
            {
                "name": "回撤基准",
                "type": "line",
                "data": dd_values,
                "smooth": False,
                "symbol": "none",
                "lineStyle": {"color": "#10b981", "type": "dashed", "width": 1, "opacity": 0.6},
                "areaStyle": {
                    "color": {
                        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "rgba(16,185,129,0.15)"},
                            {"offset": 1, "color": "rgba(16,185,129,0.02)"},
                        ],
                    }
                },
            },
            # 初始本金水平线
            {
                "type": "line",
                "silent": True,
                "symbol": "none",
                "lineStyle": {"color": "#888", "type": "dotted", "width": 1},
                "markLine": {
                    "silent": True,
                    "data": [{"yAxis": round(initial_capital, 2)}],
                    "label": {
                        "formatter": f"本金 ¥{initial_capital:,.0f}",
                        "color": "#888",
                        "fontSize": 10,
                    },
                },
                "data": [[0, round(initial_capital, 2)], [0, round(initial_capital, 2)]],
            },
        ],
    }
    return json.dumps(cfg, ensure_ascii=False)


def calc_boll_upper_single(rows, period, std_k, idx):
    """计算某日 BOLL 上轨（排除当天）"""
    if idx < period:
        return 0.0
    recent = rows[max(0, idx - period):idx]
    if len(recent) < period:
        return 0.0
    closes = [r["close"] or 0 for r in recent]
    ma = sum(closes) / len(closes)
    import math
    variance = sum((c - ma) ** 2 for c in closes) / len(closes)
    std = math.sqrt(variance)
    return ma + std_k * std


def calc_boll_lower_single(rows, period, std_k, idx):
    """计算某日 BOLL 下轨（排除当天）"""
    if idx < period:
        return 0.0
    recent = rows[max(0, idx - period):idx]
    if len(recent) < period:
        return 0.0
    closes = [r["close"] or 0 for r in recent]
    ma = sum(closes) / len(closes)
    import math
    variance = sum((c - ma) ** 2 for c in closes) / len(closes)
    std = math.sqrt(variance)
    return ma - std_k * std


def gen_main_chart_config(klines, trades):
    """生成全量K线 ECharts 配置（支持缩放 + 买卖点 + 唐奇安通道）
    返回 (config_json, dates_json, candle_json) 三部分���避免 tooltip formatter 依赖 params 顺序。
    """
    if not klines or len(klines) < 5:
        return "", "[]", "[]"
    import json

    # K线数据：ECharts candlestick = [open, close, high, low]
    candle_data = []
    for r in klines:
        o = round(r["open"] or 0, 3)
        c = round(r["close"] or 0, 3)
        h = round(r["high"] or 0, 3)
        l = round(r["low"] or 0, 3)
        if h < l:  # 数据库 high/low 颠倒，强制修正
            h, l = l, h
        candle_data.append([o, c, h, l])
    dates = [r["date"] for r in klines]  # YYYY-MM-DD

    # 买卖点：找入场日和出场日
    buy_idx_map = {}
    sell_idx_map = {}
    for i, k in enumerate(klines):
        d = k["date"]
        for t in trades:
            if d == t.entry_date and i not in buy_idx_map:
                buy_idx_map[i] = t
            if d == t.exit_date and i not in sell_idx_map:
                sell_idx_map[i] = t

    # 买卖点 markPoint（自定义 label 样式）
    mark_points = []
    for i in sorted(buy_idx_map.keys()):
        t = buy_idx_map[i]
        price = round(klines[i]["close"] or 0, 2)
        mark_points.append({
            "coord": [dates[i], price],
            "value": price,
            "symbolSize": 1,
            "symbolOffset": [0, "50%"],
            "label": {
                "formatter": "买",
                "color": "#fff",
                "backgroundColor": "#ef4444",
                "padding": [3, 6],
                "borderRadius": 3,
                "fontSize": 11,
                "fontWeight": "bold",
                "position": "top",
                "distance": 5,
            },
        })
    for i in sorted(sell_idx_map.keys()):
        t = sell_idx_map[i]
        price = round(klines[i]["close"] or 0, 2)
        mark_points.append({
            "coord": [dates[i], price],
            "value": price,
            "symbolSize": 1,
            "symbolOffset": [0, "50%"],
            "label": {
                "formatter": "卖",
                "color": "#fff",
                "backgroundColor": "#3b82f6",
                "padding": [3, 6],
                "borderRadius": 3,
                "fontSize": 11,
                "fontWeight": "bold",
                "position": "bottom",
                "distance": 5,
            },
        })

    # 唐奇安通道线
    donchian_upper = []
    donchian_lower = []
    for i in range(len(klines)):
        u = calc_donchian_upper_single(klines, DONCHIAN_PERIOD, i)
        l = calc_donchian_lower_single(klines, DONCHIAN_PERIOD, i)
        donchian_upper.append(round(u, 3) if u > 0 else None)
        donchian_lower.append(round(l, 3) if l > 0 else None)

    # BOLL 通道线
    boll_upper = []
    boll_lower = []
    for i in range(len(klines)):
        u = calc_boll_upper_single(klines, BOLL_PERIOD, BOLL_STD, i)
        l = calc_boll_lower_single(klines, BOLL_PERIOD, BOLL_STD, i)
        boll_upper.append(round(u, 3) if u > 0 else None)
        boll_lower.append(round(l, 3) if l > 0 else None)

    # 买卖突破价按日期建索引
    entry_prices = {}
    exit_prices = {}
    breakout_prices = {}
    for i, k in enumerate(klines):
        d = k["date"]
        for t in trades:
            if d == t.entry_date:
                entry_prices[d] = round(t.entry_price, 2)
            if d == t.exit_date:
                exit_prices[d] = round(t.exit_price, 2)
            if d == t.breakout_upper_date:
                breakout_prices[d] = round(t.upper_band, 2)

    buy_data = [entry_prices.get(dates[i]) for i in range(len(dates))]
    sell_data = [exit_prices.get(dates[i]) for i in range(len(dates))]
    breakout_data = [breakout_prices.get(dates[i]) for i in range(len(dates))]

    cfg = {
        "animation": False,
        "legend": {
            "data": ["K线", "唐奇安上轨", "唐奇安下轨", "BOLL上轨", "BOLL下轨"],
            "top": 0,
            "right": 60,
            "textStyle": {"fontSize": 11},
        },
        "dataZoom": [
            {"type": "inside", "start": 0, "end": 100, "xAxisIndex": 0},
            {"type": "slider", "start": 0, "end": 100, "xAxisIndex": 0, "height": 20, "bottom": 30},
        ],
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            # 固定通过全局变量 _mainDates / _mainCandle / _mainBuy / _mainSell / _mainBreakout 查值
            # 不依赖 params 顺序，避免多 series 时取错数据
            "formatter": """
function(params) {
    var date = params[0].axisValue;
    var idx = _mainDates.indexOf(date);
    var lines = ['<b>' + date + '</b>'];
    if (idx >= 0) {
        var v = _mainCandle[idx];
        if (v) {
            lines.push('开&nbsp;&nbsp;:' + v[0].toFixed(2));
            lines.push('收&nbsp;&nbsp;:' + v[1].toFixed(2));
            lines.push('高&nbsp;&nbsp;:' + v[2].toFixed(2));
            lines.push('低&nbsp;&nbsp;:' + v[3].toFixed(2));
        }
        var bp = _mainBreakout[idx];
        if (bp) lines.push('<span style="color:#fde047">突破&nbsp;:</span> ' + bp);
        var b = _mainBuy[idx];
        if (b) lines.push('<span style="color:#ef4444">买价&nbsp;:</span> ' + b);
        var s = _mainSell[idx];
        if (s) lines.push('<span style="color:#3b82f6">卖价&nbsp;:</span> ' + s);
    }
    return lines.join('<br>');
}""",
        },
        "grid": {"left": 50, "right": 20, "top": 10, "bottom": 60},
        "xAxis": {
            "type": "category", "data": dates,
            "axisLabel": {"fontSize": 10, "color": "#aaa"},
            "axisLine": {"lineStyle": {"color": "#ccc"}},
            "axisTick": {"show": False},
            "splitLine": {"show": False},
        },
        "yAxis": {
            "type": "value", "scale": True,
            "axisLabel": {"fontSize": 10, "color": "#888"},
            "axisLine": {"show": False}, "axisTick": {"show": False},
            "splitLine": {"lineStyle": {"color": "#f0f0f0"}},
        },
        "series": [
            # K线 + 买卖点
            {
                "name": "K线",
                "type": "candlestick", "data": candle_data,
                "itemStyle": {
                    "color": "#ef4444", "color0": "#10b981",
                    "borderColor": "#ef4444", "borderColor0": "#10b981",
                },
                "markPoint": {
                    "data": mark_points,
                    "label": {"show": True},
                },
            },
            # 买（隐藏，传值给 tooltip）
            {
                "name": "买", "type": "scatter", "symbolSize": 0,
                "data": buy_data,
            },
            # 卖（隐藏，传值给 tooltip）
            {
                "name": "卖", "type": "scatter", "symbolSize": 0,
                "data": sell_data,
            },
            # 突破（隐藏，传值给 tooltip）
            {
                "name": "突破", "type": "scatter", "symbolSize": 0,
                "data": breakout_data,
            },
            # 唐奇安上轨
            {
                "name": "唐奇安上轨", "type": "line", "symbol": "none",
                "color": "#ffa39e",
                "lineStyle": {"color": "#ffa39e", "type": "dashed", "width": 1},
                "data": [[i, v] for i, v in enumerate(donchian_upper)],
                "connectNulls": False,
            },
            # 唐奇安下轨
            {
                "name": "唐奇安下轨", "type": "line", "symbol": "none",
                "color": "#cf1322",
                "lineStyle": {"color": "#cf1322", "type": "dashed", "width": 1},
                "data": [[i, v] for i, v in enumerate(donchian_lower)],
                "connectNulls": False,
            },
            # BOLL上轨
            {
                "name": "BOLL上轨", "type": "line", "symbol": "none",
                "color": "#91d5ff",
                "lineStyle": {"color": "#91d5ff", "type": "dashed", "width": 1},
                "data": [[i, v] for i, v in enumerate(boll_upper)],
                "connectNulls": False,
            },
            # BOLL下轨
            {
                "name": "BOLL下轨", "type": "line", "symbol": "none",
                "color": "#096dd9",
                "lineStyle": {"color": "#096dd9", "type": "dashed", "width": 1},
                "data": [[i, v] for i, v in enumerate(boll_lower)],
                "connectNulls": False,
            },
        ],
    }
    cfg_json = json.dumps(cfg, ensure_ascii=False)
    dates_json = json.dumps(dates, ensure_ascii=False)
    candle_json = json.dumps(candle_data, ensure_ascii=False)
    buy_json = json.dumps(buy_data, ensure_ascii=False)
    sell_json = json.dumps(sell_data, ensure_ascii=False)
    breakout_json = json.dumps(breakout_data, ensure_ascii=False)
    return cfg_json, dates_json, candle_json, buy_json, sell_json, breakout_json


def gen_candlestick_svg(klines, trades, width=900, height=280):
    """生成 K 线 SVG 图"""
    if not klines or len(klines) < 5:
        return ""

    n = len(klines)
    chart_w = width - 60
    chart_h = height - 40

    # 价格范围
    lows = [(r["low"] or 0) for r in klines]
    highs = [(r["high"] or 0) for r in klines]
    price_min = min(lows)
    price_max = max(highs)
    price_range = price_max - price_min or 1
    margin = price_range * 0.05
    p_min = price_min - margin
    p_max = price_max + margin
    p_range = p_max - p_min

    def price_y(p):
        return chart_h - ((p - p_min) / p_range) * chart_h

    def bar_x(i):
        return 30 + (i / max(n - 1, 1)) * chart_w

    # K线实体宽度
    body_w = max(2, chart_w / n * 0.6)

    # 找出买卖点日期索引
    buy_dates = {t.entry_date for t in trades}
    sell_dates = {t.exit_date for t in trades}

    # 生成 SVG
    lines = []
    shapes = []
    markers = []

    for i, k in enumerate(klines):
        o = k.get("open") or k.get("close") or 0
        c = k.get("close") or 0
        h = k.get("high") or 0
        l = k.get("low") or 0
        d = k.get("date", "")

        x = bar_x(i)

        # K线颜色
        if c >= o:
            color = "#ef4444"  # 涨 红
            body_top = price_y(c)
            body_bot = price_y(o)
        else:
            color = "#10b981"  # 跌 绿
            body_top = price_y(o)
            body_bot = price_y(c)

        # 影线（上下影线）
        lines.append(
            f'<line x1="{x:.1f}" y1="{price_y(h):.1f}" x2="{x:.1f}" y2="{price_y(l):.1f}" stroke="{color}" stroke-width="1"/>'
        )

        # 实体
        bh = max(1, abs(price_y(c) - price_y(o)))
        shapes.append(
            f'<rect x="{(x - body_w/2):.1f}" y="{body_top:.1f}" width="{body_w:.1f}" height="{bh:.1f}" fill="{color}" stroke="{color}" stroke-width="1"/>'
        )

        # 买卖点标记
        if d in buy_dates:
            markers.append(
                f'<text x="{x:.1f}" y="{price_y(h) - 8:.1f}" text-anchor="middle" '
                f'font-size="14" font-weight="bold" fill="#ef4444">B</text>'
            )
        if d in sell_dates:
            # 找对应交易判断盈亏
            pnl_val = 0
            for t in trades:
                if t.exit_date == d:
                    pnl_val = t.pnl
                    break
            sell_color = "#ef4444" if pnl_val >= 0 else "#10b981"
            markers.append(
                f'<text x="{x:.1f}" y="{price_y(l) + 16:.1f}" text-anchor="middle" '
                f'font-size="14" font-weight="bold" fill="{sell_color}">S</text>'
            )

    # Y轴标签
    y_labels = []
    num_y = 5
    for i in range(num_y + 1):
        p = p_min + (p_range * i / num_y)
        y = price_y(p)
        y_labels.append(f'<text x="{chart_w + 35:.0f}" y="{y + 4:.1f}" font-size="11" fill="#888">{p:.2f}</text>')
        y_labels.append(f'<line x1="30" y1="{y:.1f}" x2="{chart_w + 30:.0f}" y2="{y:.1f}" stroke="#eee" stroke-width="1"/>')

    # X轴标签（日期，每隔几个显示）
    x_step = max(1, n // 8)
    x_labels = []
    for i in range(0, n, x_step):
        x = bar_x(i)
        d = klines[i].get("date", "")[5:]  # MM-DD
        x_labels.append(f'<text x="{x:.1f}" y="{chart_h + 18:.0f}" text-anchor="middle" font-size="11" fill="#888">{d}</text>')

    svg = f"""
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
        <!-- 背景 -->
        <rect width="{width}" height="{height}" fill="#fff"/>
        <!-- Y轴网格线 -->
        {"".join(y_labels)}
        <!-- K线影线 -->
        {"".join(lines)}
        <!-- K线实体 -->
        {"".join(shapes)}
        <!-- 买卖点 -->
        {"".join(markers)}
        <!-- X轴日期 -->
        {"".join(x_labels)}
        <!-- Y轴标题 -->
        <text x="5" y="12" font-size="11" fill="#aaa">价格</text>
    </svg>"""
    return svg


def gen_trade_chart_svg(trade, idx):
    """生成交易 K 线图（ECharts）：买入前21日 ~ 卖出后5日，标注买卖点"""
    ohlc_list = trade.trade_chart_ohlc
    if not ohlc_list or len(ohlc_list) < 3:
        return ""

    n = len(ohlc_list)

    # 找买入日/卖出日在 ohlc_list 中的索引（用日期字符串匹配）
    buy_idx = None
    sell_idx = None
    for i, k in enumerate(ohlc_list):
        if k["date"] == trade.entry_date and buy_idx is None:
            buy_idx = i
        if k["date"] == trade.exit_date and sell_idx is None:
            sell_idx = i

    breakout_idx = (buy_idx - 1) if (buy_idx and buy_idx > 0) else None
    sell_color = "#10b981" if trade.pnl < 0 else "#ef4444"

    # 日期标签（用于 xAxis category）
    dates = [r["date"] for r in ohlc_list]  # YYYY-MM-DD

    # K线数据：ECharts candlestick = [open, close, high, low]，high/low 颠倒则修正
    candle_data = []
    for r in ohlc_list:
        o = round(r["open"] or 0, 3)
        c = round(r["close"] or 0, 3)
        h = round(r["high"] or 0, 3)
        l = round(r["low"] or 0, 3)
        if h < l:
            h, l = l, h
        candle_data.append([o, c, h, l])

    # 价格范围，用于标记偏移
    all_prices = [r["high"] or 0 for r in ohlc_list] + [r["low"] or 0 for r in ohlc_list]
    # 纵轴从最低价-5开始
    y_min = round(min(all_prices) - 5, 2)
    # 突破/买/卖 的日期字符串（xAxis 是 category）
    breakout_date = ohlc_list[breakout_idx]["date"] if breakout_idx is not None else None
    buy_date = trade.entry_date
    sell_date = trade.exit_date

    # 构建 K 线 series 的 markPoint（自定义 label 样式）
    mark_points = []
    if breakout_date:
        breakout_price = round(ohlc_list[breakout_idx]["high"] or 0, 2)
        mark_points.append({
            "coord": [breakout_date, breakout_price],
            "value": breakout_price,
            "symbolSize": 1,
            "symbolOffset": [0, "50%"],
            "label": {
                "formatter": "突破",
                "color": "#fff",
                "backgroundColor": "#fde047",
                "padding": [3, 6],
                "borderRadius": 3,
                "fontSize": 10,
                "fontWeight": "bold",
                "position": "top",
                "distance": 5,
            },
        })
    mark_points.append({
        "coord": [buy_date, round(trade.entry_price, 2)],
        "value": round(trade.entry_price, 2),
        "symbolSize": 1,
        "symbolOffset": [0, "50%"],
        "label": {
            "formatter": "买",
            "color": "#fff",
            "backgroundColor": "#ef4444",
            "padding": [3, 6],
            "borderRadius": 3,
            "fontSize": 11,
            "fontWeight": "bold",
            "position": "top",
            "distance": 5,
        },
    })
    mark_points.append({
        "coord": [sell_date, round(trade.exit_price, 2)],
        "value": round(trade.exit_price, 2),
        "symbolSize": 1,
        "symbolOffset": [0, "50%"],
        "label": {
            "formatter": "卖",
            "color": "#fff",
            "backgroundColor": "#3b82f6",
            "padding": [3, 6],
            "borderRadius": 3,
            "fontSize": 11,
            "fontWeight": "bold",
            "position": "bottom",
            "distance": 5,
        },
    })

    cfg = {
        "animation": False,
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "formatter": f"""
function(params) {{
    var date = params[0].axisValue;
    var lines = ['<b>' + date + '</b>'];
    for (var i = 0; i < params.length; i++) {{
        var p = params[i];
        var v = p.value;
        if (p.seriesName === 'K线' && Array.isArray(v)) {{
            lines.push('开&nbsp;&nbsp;:' + v[0].toFixed(2));
            lines.push('收&nbsp;&nbsp;:' + v[1].toFixed(2));
            lines.push('高&nbsp;&nbsp;:' + v[2].toFixed(2));
            lines.push('低&nbsp;&nbsp;:' + v[3].toFixed(2));
        }}
        if (p.seriesName === '买') lines.push('<span style="color:#ef4444">买价&nbsp;:</span> ' + v);
        if (p.seriesName === '卖') lines.push('<span style="color:#3b82f6">卖价&nbsp;:</span> ' + v);
        if (p.seriesName === '突破') lines.push('<span style="color:#fde047">突破&nbsp;:</span> ' + v);
    }}
    return lines.join('<br>');
}}""",
        },
        "grid": {"left": 50, "right": 60, "top": 20, "bottom": 40},
        "xAxis": {
            "type": "category",
            "data": dates,
            "axisLabel": {"fontSize": 10, "color": "#aaa"},
            "axisLine": {"lineStyle": {"color": "#ccc"}},
            "axisTick": {"show": False},
            "splitLine": {"show": False},
        },
        "yAxis": {
            "type": "value",
            "scale": True,
            "min": y_min,
            "axisLabel": {"fontSize": 10, "color": "#888"},
            "axisLine": {"show": False},
            "axisTick": {"show": False},
            "splitLine": {"lineStyle": {"color": "#f0f0f0"}},
        },
        "series": [
            # K线
            {
                "name": "K线",
                "type": "candlestick",
                "data": candle_data,
                "itemStyle": {
                    "color": "#ef4444",
                    "color0": "#10b981",
                    "borderColor": "#ef4444",
                    "borderColor0": "#10b981",
                },
                "markPoint": {
                    "data": mark_points,
                    "label": {"show": True},
                },
            },
            # 买（隐藏，传值给 tooltip）
            {
                "name": "买", "type": "scatter", "symbolSize": 0,
                "data": [round(trade.entry_price, 2) if d == buy_date else None for d in dates],
            },
            # 卖（隐藏，传值给 tooltip）
            {
                "name": "卖", "type": "scatter", "symbolSize": 0,
                "data": [round(trade.exit_price, 2) if d == sell_date else None for d in dates],
            },
            # 突破（隐藏，传值给 tooltip）
            {
                "name": "突破", "type": "scatter", "symbolSize": 0,
                "data": [round(ohlc_list[breakout_idx]["high"], 2) if breakout_date and d == breakout_date else None for d in dates] if breakout_date else [None] * len(dates),
            },
            # 水平线：止损、止盈、上轨、入场
            {
                "type": "line",
                "silent": True,
                "symbol": "none",
                "lineStyle": {"type": "dashed", "width": 1.5},
                "markLine": {
                    "silent": True,
                    "data": [
                        {"yAxis": round(trade.stop_loss, 3),
                         "lineStyle": {"color": "#10b981"},
                         "label": {"formatter": f"止损 {trade.stop_loss:.2f}", "color": "#10b981", "fontSize": 10}},
                        {"yAxis": round(trade.take_profit, 3),
                         "lineStyle": {"color": "#ef4444"},
                         "label": {"formatter": f"止盈 {trade.take_profit:.2f}", "color": "#ef4444", "fontSize": 10}},
                        {"yAxis": round(trade.upper_band, 3),
                         "lineStyle": {"color": "#3b82f6"},
                         "label": {"formatter": f"上轨 {trade.upper_band:.2f}", "color": "#3b82f6", "fontSize": 10}},
                        {"yAxis": round(trade.entry_price, 3),
                         "lineStyle": {"color": "#ef4444", "type": "dotted"},
                         "label": {"formatter": f"入场 {trade.entry_price:.2f}", "color": "#ef4444", "fontSize": 9}},
                    ]
                },
                "data": [[0, 0], [0, 0]],
            },
        ],
    }

    import json
    js_cfg = json.dumps(cfg, ensure_ascii=False)
    return f"_tradeChartConfigs[{idx}] = {js_cfg};"



def format_pnl(pnl):
    """格式化盈亏"""
    sign = "+" if pnl >= 0 else ""
    return f"{sign}{pnl:.2f}"


def format_r(r):
    sign = "+" if r >= 0 else ""
    return f"{sign}{r:.2f}R"


def generate_html_report(code, name, trades, equity_curve, stats, klines=None, report_filename=None):
    """生成 HTML 报告"""
    today = datetime.now().strftime("%Y-%m-%d")
    filename = report_filename or f"{today}_{code}_{name}.html"
    out_path = BACKTEST_DIR / filename
    BACKTEST_DIR.mkdir(parents=True, exist_ok=True)

    # 资金曲线数据（ECharts）
    equity_dates = []
    equity_values = []
    dd_values = []
    if equity_curve:
        for e in equity_curve:
            equity_dates.append(e["date"][:10])
            equity_values.append(round(e["total"], 2))
            peak = e.get("peak", e["total"])
            dd_values.append(round(peak - e["dd"], 2))
        initial = equity_values[0] if equity_values else stats["initial_capital"]
    else:
        equity_dates = []
        equity_values = []
        dd_values = []
        initial = stats["initial_capital"]

    # 最大回撤标注
    max_dd_date = stats.get("max_dd_date", None)
    max_dd_val = stats.get("max_drawdown", 0)
    max_dd_pct = stats.get("max_drawdown_pct", 0)
    dd_annotation = f"最大回撤: ¥{max_dd_val:,.0f} ({max_dd_pct:.1f}%)" if max_dd_val > 0 else ""

    # 资金曲线 ECharts 配置
    equity_cfg_json = gen_equity_chart_config(equity_dates, equity_values, dd_values, initial)
    if equity_cfg_json:
        equity_chart_script = f'<script>\nvar _equityChartConfig = {equity_cfg_json};\n</script>'
    else:
        equity_chart_script = ""

    # 主K线图 ECharts 配置（返回 cfg + 全局数据，避免 tooltip 依赖 params 顺序）
    main_chart_result = gen_main_chart_config(klines or [], trades)
    if main_chart_result[0]:
        cfg_json, dates_json, candle_json, buy_json, sell_json, breakout_json = main_chart_result
        main_chart_script = (
            f'<script>\n'
            f'var _mainDates = {dates_json};\n'
            f'var _mainCandle = {candle_json};\n'
            f'var _mainBuy = {buy_json};\n'
            f'var _mainSell = {sell_json};\n'
            f'var _mainBreakout = {breakout_json};\n'
            f'var _mainChartConfig = {cfg_json};\n'
            f'</script>'
        )
    else:
        main_chart_script = ""

    # 交易明细行（含展开详情）
    trade_rows = ""
    trade_chart_scripts = []
    for idx, t in enumerate(trades):
        cls = "win" if t.pnl > 0 else "loss"
        reason_map = {
            "stop_loss": "止损",
            "take_profit": "止盈",
            "force_close": "强制平仓",
            "breakout": "突破",
        }
        reason_text = reason_map.get(t.reason, t.reason)
        max_dd_text = f"¥{t.max_dd:,.0f}" if t.max_dd and t.max_dd > 0 else "-"

        # 突破区间明细
        upper_band_text = f"{t.upper_band:.3f}" if t.upper_band else "-"
        exceed_pct_text = f"+{t.breakout_exceed_pct:.3f}%" if t.breakout_exceed_pct else ""
        breakout_dates_text = ", ".join(
            [f"{d}({h:.3f})" for d, h in (t.breakout_range_highs or [])]
        )
        # BOLL 信息
        boll_text = ""
        if hasattr(t, 'boll_upper') and t.boll_upper > 0:
            boll_exceed = round((t.breakout_close - t.boll_upper) / t.boll_upper * 100, 3) if t.boll_upper > 0 else 0
            boll_exceed_text = f"+{boll_exceed:.3f}%" if boll_exceed > 0 else f"{boll_exceed:.3f}%"
            boll_text = (
                f"BOLL上轨 = {t.boll_upper:.3f}（{BOLL_PERIOD}日MA + {BOLL_STD}×std）<br>"
                f"突破日收盘 = {t.breakout_close:.3f}，高出BOLL上轨 {boll_exceed_text}<br>"
            )
        breakout_detail = (
            f"<b>【买入逻辑】</b><br>"
            f"唐奇安上轨 = {upper_band_text}（{DONCHIAN_PERIOD}日最高）<br>"
            f"区间最高日：{t.breakout_upper_date}<br>"
            f"突破日收盘 = {t.breakout_close:.3f}，高出上轨 {exceed_pct_text}<br>"
            f"{boll_text}"
            f"入场价（次日开盘）= {t.entry_price:.3f}<br>"
            f"止损 = {t.stop_loss:.3f}（入场 - ATR {t.atr:.3f} × 1.3）<br>"
            f"止盈 = {t.take_profit:.3f}（入场 + ATR {t.atr:.3f} × 2.0）<br>"
            f"ATR = {t.atr:.3f}，持仓 {t.shares} 股"
        )

        # 卖出触发明细
        trigger_price_text = f"{t.exit_trigger_price:.3f}" if t.exit_trigger_price else "-"
        exit_formula_text = t.exit_formula if t.exit_formula else (
            f"以 {t.exit_price:.3f} 平仓"
        )
        exit_detail = (
            f"<b>【卖出逻辑】</b><br>"
            f"{exit_formula_text}<br>"
            f"实际卖出价 = {t.exit_price:.3f}，持有 {t.holding_days} 天<br>"
            f"盈亏 = ({t.exit_price:.3f} - {t.entry_price:.3f}) × {t.shares} = {format_pnl(t.pnl)}<br>"
            f"R值 = {format_r(t.pnl_r)}，最大浮亏 = {max_dd_text}"
        )

        detail_id = f"detail-{idx}"
        # 交易 K 线图（买入前21日 ~ 卖出后5日）
        chart_js = gen_trade_chart_svg(t, idx) if t.trade_chart_ohlc else ""
        if chart_js:
            trade_chart_scripts.append(chart_js)

        trade_rows += f"""
        <tr class="{cls}" onclick="toggleDetail('{detail_id}', {idx})" style="cursor:pointer;">
            <td>{t.entry_date}</td>
            <td>{t.exit_date}</td>
            <td>{t.holding_days}</td>
            <td>{t.entry_price:.2f}</td>
            <td>{t.exit_price:.2f}</td>
            <td>{t.stop_loss:.2f}</td>
            <td>{t.take_profit:.2f}</td>
            <td>{t.shares}</td>
            <td class="pnl">{format_pnl(t.pnl)}</td>
            <td class="pnl">{format_r(t.pnl_r)}</td>
            <td>{max_dd_text}</td>
            <td><span class="badge badge-{'win' if t.pnl > 0 else 'loss'}">{reason_text}</span></td>
            <td>🔽</td>
        </tr>
        <tr class="detail-row" id="{detail_id}" style="display:none;">
            <td colspan="13" style="text-align:left;padding:12px 16px;background:#fafafa;">
                <div style="display:flex;gap:16px;align-items:flex-start;">
                    <div style="font-size:12px;line-height:1.8;flex:1;">{breakout_detail}</div>
                    <div style="font-size:12px;line-height:1.8;flex:1;">{exit_detail}</div>
                    <div style="flex:0 0 auto;">
                        <div id="trade-chart-{idx}" style="width:560px;height:280px;"></div>
                        <div style="font-size:11px;color:#aaa;margin-top:4px;">
                            <span style="color:#fde047;font-weight:bold;">突破</span> =
                            <span style="color:#ef4444;font-weight:bold;">买</span> =
                            <span style="color:#10b981;font-weight:bold;">卖</span> |
                            <span style="color:#3b82f6">━</span> 上轨
                            <span style="color:#ef4444">━</span> 止盈
                            <span style="color:#10b981">━</span> 止损
                        </div>
                    </div>
                </div>
            </td>
        </tr>"""

    # 月度统计
    monthly_stats = {}
    for t in trades:
        ym = t.exit_date[:7]
        if ym not in monthly_stats:
            monthly_stats[ym] = {"count": 0, "pnl": 0, "wins": 0}
        monthly_stats[ym]["count"] += 1
        monthly_stats[ym]["pnl"] += t.pnl
        if t.pnl > 0:
            monthly_stats[ym]["wins"] += 1

    monthly_rows = ""
    for ym in sorted(monthly_stats.keys()):
        m = monthly_stats[ym]
        win_rate = m["wins"] / m["count"] * 100 if m["count"] > 0 else 0
        cls = "win" if m["pnl"] > 0 else "loss"
        monthly_rows += f"""
        <tr class="{cls}">
            <td>{ym}</td>
            <td>{m["count"]}</td>
            <td>{m["wins"]}</td>
            <td>{win_rate:.0f}%</td>
            <td class="pnl">{format_pnl(m["pnl"])}</td>
        </tr>"""

    # 夏普比色
    sharpe = stats["sharpe_ratio"]
    sharpe_cls = "good" if sharpe >= 1 else ("warn" if sharpe >= 0 else "bad")
    
    # ECharts 脚本（放在 f-string 外部避免 {} 被 f-string 解析）
    chart_script_block = """<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <script>
    var _tradeChartConfigs = {};
    // 把 tooltip.formatter 字符串转为真正的函数（json.dumps 无法序列化函数）
    function applyTooltipFormatter(cfg) {
        if (cfg && cfg.tooltip && typeof cfg.tooltip.formatter === 'string') {
            try {
                var src = cfg.tooltip.formatter.trim();
                // 找到 function(params) { 的位置，取其后的内容
                var idx = src.indexOf('function(params) {');
                if (idx < 0) { idx = src.indexOf('function (params) {'); }
                if (idx < 0) { idx = src.indexOf('function ( params ) {'); }
                if (idx >= 0) {
                    // 从 { 开始匹配括号对，找到对应的 }
                    var body = src.substring(idx + 18); // 'function(params) {' = 18
                    var depth = 1, i = 0;
                    while (i < body.length && depth > 0) {
                        if (body[i] === '{') depth++;
                        else if (body[i] === '}') depth--;
                        i++;
                    }
                    body = body.substring(0, i - 1);
                    cfg.tooltip.formatter = new Function('params', body);
                }
            } catch (e) { /* ignore */ }
        }
    }
    function toggleDetail(id, idx) {
    var el = document.getElementById(id);
    if (el.style.display === 'none') {
        el.style.display = 'table-row';
        if (!_tradeChartConfigs[idx]) return;
        var dom = document.getElementById('trade-chart-' + idx);
        if (!dom) return;
        var chart = echarts.init(dom);
        var cfg = _tradeChartConfigs[idx];
        applyTooltipFormatter(cfg);
        chart.setOption(cfg);
        setTimeout(function() { chart.resize(); }, 100);
    } else {
        el.style.display = 'none';
    }
    }
    // 初始化资金曲线 + 主K线图
    window.addEventListener('load', function() {
        // 资金曲线
        if (typeof _equityChartConfig !== 'undefined') {
            var equityDom = document.getElementById('equity-chart');
            if (equityDom) {
                var equityChart = echarts.init(equityDom);
                var eqCfg = _equityChartConfig;
                applyTooltipFormatter(eqCfg);
                equityChart.setOption(eqCfg);
            }
        }
        // 主K线图
        if (typeof _mainChartConfig !== 'undefined') {
            var mainChartDom = document.getElementById('main-chart');
            if (mainChartDom) {
                var mainChart = echarts.init(mainChartDom);
                var cfg = _mainChartConfig;
                applyTooltipFormatter(cfg);
                mainChart.setOption(cfg);
            }
        }
    });
    </script>
    """


    # 注入所有 ECharts 图表配置
    trade_chart_script_block = (
        "<script>" + "".join(trade_chart_scripts) + "</script>"
        if trade_chart_scripts else ""
    )

    html = f"""<!DOCTYPE html>
    <html lang="zh">
    <head>
    <meta charset="utf-8">
    <title>CTA 回测报告 - {code} {name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; background: #f5f7fa; color: #333; font-size: 14px; }}
        .container {{ max-width: 1100px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1a1a2e; margin-bottom: 5px; }}
        .subtitle {{ color: #666; margin-bottom: 20px; }}
        .card {{ background: #fff; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        h2 {{ color: #16213e; border-left: 4px solid #0f3460; padding-left: 12px; margin-bottom: 16px; font-size: 16px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 16px; }}
        .stat-item {{ text-align: center; padding: 12px; background: #f8f9fb; border-radius: 8px; }}
        .stat-label {{ color: #888; font-size: 12px; margin-bottom: 4px; }}
        .stat-value {{ font-size: 20px; font-weight: bold; color: #1a1a2e; }}
        .stat-value.win {{ color: #ef4444; }}
        .stat-value.loss {{ color: #10b981; }}
        .stat-sub {{ font-size: 11px; color: #999; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
        th {{ background: #16213e; color: #fff; padding: 10px 8px; text-align: center; }}
        td {{ padding: 8px; text-align: center; border-bottom: 1px solid #f0f0f0; }}
        tr:hover {{ background: #f8f9fb; }}
        tr.win td {{ color: #ef4444; }}
        tr.loss td {{ color: #10b981; }}
        .pnl {{ font-weight: bold; }}
        .svg-wrap {{ padding: 10px 0; }}
        .strategy-info {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }}
        .info-item {{ background: #f8f9fb; padding: 10px 14px; border-radius: 6px; }}
        .info-label {{ font-size: 12px; color: #888; }}
        .info-value {{ font-size: 14px; font-weight: 600; color: #333; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
        .badge-win {{ background: #fee2e2; color: #991b1b; }}
        .badge-loss {{ background: #d1fae5; color: #065f46; }}
        .no-data {{ color: #999; text-align: center; padding: 30px; }}
        .detail-row td {{ padding: 0 !important; border: none !important; }}
    </style>
    {equity_chart_script}
    {main_chart_script}
    {chart_script_block}</head>
    <body>
    <div class="container">
        <h1>CTA 唐奇安突破回测报告</h1>
        <div class="subtitle">{code} {name} | 回测区间: {stats['start_date']} ~ {stats['end_date']} | 生成时间: {today}</div>
    
        <!-- 策略说明 -->
        <div class="card">
            <h2>策略说明</h2>
            <div class="strategy-info">
                <div class="info-item">
                    <div class="info-label">策略</div>
                    <div class="info-value">唐奇安 + BOLL 双突破</div>
                </div>
                <div class="info-item">
                    <div class="info-label">初始本金</div>
                    <div class="info-value">¥{stats['initial_capital']:,.0f}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">唐奇安周期</div>
                    <div class="info-value">{DONCHIAN_PERIOD} 日</div>
                </div>
                <div class="info-item">
                    <div class="info-label">BOLL 参数</div>
                    <div class="info-value">MA({BOLL_PERIOD}) + {BOLL_STD}×std</div>
                </div>
                <div class="info-item">
                    <div class="info-label">ATR 周期</div>
                    <div class="info-value">{ATR_PERIOD} 日</div>
                </div>
                <div class="info-item">
                    <div class="info-label">止损系数</div>
                    <div class="info-value">ATR × 1.3</div>
                </div>
                <div class="info-item">
                    <div class="info-label">止盈系数</div>
                    <div class="info-value">ATR × 2.0</div>
                </div>
            </div>
        </div>
    
        <!-- 整体统计 -->
        <div class="card">
            <h2>整体绩效</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-label">最终资金</div>
                    <div class="stat-value {'win' if stats['total_return'] >= 0 else 'loss'}">¥{stats['final_capital']:,.0f}</div>
                    <div class="stat-sub">本金 ¥{stats['initial_capital']:,.0f}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">总收益率</div>
                    <div class="stat-value {'win' if stats['total_return_pct'] >= 0 else 'loss'}">{stats['total_return_pct']:+.1f}%</div>
                    <div class="stat-sub">¥{stats['total_return']:+,.0f}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">日均收益率</div>
                    <div class="stat-value {'win' if stats.get('daily_return_pct', 0) >= 0 else 'loss'}">{stats.get('daily_return_pct', 0):+.4f}%</div>
                    <div class="stat-sub">总收益/交易日</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">交易次数</div>
                    <div class="stat-value">{stats['num_trades']}</div>
                    <div class="stat-sub">盈利{stats['win_trades']} 亏损{stats['loss_trades']}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">胜率</div>
                    <div class="stat-value {'win' if stats['win_rate'] >= 50 else 'loss'}">{stats['win_rate']:.0f}%</div>
                    <div class="stat-sub">盈{stats['avg_win']:.0f}/亏{stats['avg_loss']:.0f}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">盈亏比</div>
                    <div class="stat-value">{stats['rr_ratio']:.2f}</div>
                    <div class="stat-sub">平均持仓{stats['avg_holding_days']:.0f}天</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">夏普比率</div>
                    <div class="stat-value">{stats['sharpe_ratio']:.2f}</div>
                    <div class="stat-sub">最大回撤{stats['max_drawdown_pct']:.1f}%</div>
                </div>
            </div>
        </div>
    
        <!-- 资金曲线 -->
        <div class="card">
            <h2>资金曲线</h2>
            <div id="equity-chart" style="width:100%;height:240px;"></div>
            <div style="display:flex;gap:20px;margin-top:8px;font-size:12px;color:#888;">
                <span><span style="color:#ef4444;font-weight:bold;">━</span> 资金曲线</span>
                <span><span style="color:#10b981;font-weight:bold;">--</span> 回撤基准</span>
                <span><span style="color:#888;font-weight:bold;">··</span> 初始本金</span>
            </div>
            <div style="color:#10b981;font-size:12px;margin-top:4px;">{dd_annotation}</div>
        </div>

        <!-- K线图 -->
        <div class="card">
            <h2>K线图</h2>
            <div id="main-chart" style="width:100%;height:320px;"></div>
            <div style="display:flex;gap:20px;margin-top:8px;font-size:12px;color:#888;flex-wrap:wrap;">
                <span><span style="color:#ef4444;font-weight:bold;">买</span> = 买入日</span>
                <span><span style="color:#ef4444;font-weight:bold;">卖</span> = 卖出（盈利）</span>
                <span><span style="color:#10b981;font-weight:bold;">卖</span> = 卖出（亏损）</span>
                <span><span style="color:#ffa39e;">━━</span> 唐奇安上轨</span>
                <span><span style="color:#cf1322;">━━</span> 唐奇安下轨</span>
                <span><span style="color:#91d5ff;">━━</span> BOLL上轨</span>
                <span><span style="color:#096dd9;">━━</span> BOLL下轨</span>
                <span style="margin-left:auto;">滚轮/滑动条可缩放</span>
            </div>
        </div>
    
        <!-- 最佳/最差交易 -->
        <div class="card">
            <h2>最佳 / 最差交易</h2>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                <div>
                    <div style="font-weight:bold;color:#ef4444;margin-bottom:8px;">🏆 最佳交易</div>
                    {f"""
                    <div class="info-item">
                        <div class="info-label">买入 / 卖出</div>
                        <div class="info-value">{stats['best_trade'].entry_date} → {stats['best_trade'].exit_date}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">价格</div>
                        <div class="info-value">{stats['best_trade'].entry_price:.2f} → {stats['best_trade'].exit_price:.2f}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">盈亏</div>
                        <div class="info-value" style="color:#10b981">{format_pnl(stats['best_trade'].pnl)} ({format_r(stats['best_trade'].pnl_r)})</div>
                    </div>
                    """ if stats['best_trade'] else '<div class="no-data">无交易</div>'}
                </div>
                <div>
                    <div style="font-weight:bold;color:#10b981;margin-bottom:8px;">💔 最差交易</div>
                    {f"""
                    <div class="info-item">
                        <div class="info-label">买入 / 卖出</div>
                        <div class="info-value">{stats['worst_trade'].entry_date} → {stats['worst_trade'].exit_date}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">价格</div>
                        <div class="info-value">{stats['worst_trade'].entry_price:.2f} → {stats['worst_trade'].exit_price:.2f}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">盈亏</div>
                        <div class="info-value" style="color:#ef4444">{format_pnl(stats['worst_trade'].pnl)} ({format_r(stats['worst_trade'].pnl_r)})</div>
                    </div>
                    """ if stats['worst_trade'] else '<div class="no-data">无交易</div>'}
                </div>
            </div>
        </div>
    
        <!-- 月度统计 -->
        <div class="card">
            <h2>月度统计</h2>
            <table>
                <thead>
                    <tr>
                        <th>月份</th>
                        <th>交易次数</th>
                        <th>盈利次数</th>
                        <th>胜率</th>
                        <th>月盈亏</th>
                    </tr>
                </thead>
                <tbody>
                    {monthly_rows if monthly_rows else '<tr><td colspan="5" class="no-data">暂无月度数据</td></tr>'}
                </tbody>
            </table>
        </div>
    
        <!-- 交易明细 -->
        <div class="card">
            <h2>交易明细</h2>
            <table>
                <thead>
                    <tr>
                        <th>买入日期</th>
                        <th>卖出日期</th>
                        <th>持有天数</th>
                        <th>买入价</th>
                        <th>卖出价</th>
                        <th>止损价</th>
                        <th>止盈价</th>
                        <th>股数</th>
                        <th>盈亏</th>
                        <th>R值</th>
                        <th>最大浮亏</th>
                        <th>原因</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {trade_rows if trade_rows else '<tr><td colspan="13" class="no-data">暂无交易记录</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
    </body>
    </html>"""

    # 拼接：HTML + ECharts 图表脚本
    full_html = html + trade_chart_script_block + "\n"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    return out_path
