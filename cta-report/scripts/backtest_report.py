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

PROJECT_ROOT = Path(__file__).parent.parent
BACKTEST_DIR = PROJECT_ROOT / "backtest"


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


def format_pnl(pnl):
    """格式化盈亏"""
    sign = "+" if pnl >= 0 else ""
    return f"{sign}{pnl:.2f}"


def format_r(r):
    sign = "+" if r >= 0 else ""
    return f"{sign}{r:.2f}R"


def generate_html_report(code, name, trades, equity_curve, stats, klines=None):
    """生成 HTML 报告"""
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"{today}_{code}_{name}.html"
    out_path = BACKTEST_DIR / filename
    BACKTEST_DIR.mkdir(parents=True, exist_ok=True)

    # 资金曲线数据（SVG）
    equity_data = []
    dd_data = []  # 最大回撤区间
    if equity_curve:
        values = [e["total"] for e in equity_curve]
        min_v = min(values) * 0.90
        max_v = max(values) * 1.02
        width = 700
        height = 200
        n = len(values)
        for e in equity_curve:
            idx = equity_curve.index(e)
            x = (idx / max(n - 1, 1)) * width
            y = height - ((e["total"] - min_v) / (max_v - min_v)) * height
            equity_data.append(f"{x:.1f},{max(0, y):.1f}")
            # 最大回撤线
            peak = e.get("peak", e["total"])
            dd_y = height - ((peak - e["dd"] - min_v) / (max_v - min_v)) * height
            dd_data.append(f"{x:.1f},{max(0, dd_y):.1f}")

        svg_path = " ".join(equity_data)
        dd_path = " ".join(dd_data)
        svg_height = height
        svg_width = width
        svg_min = min_v
        svg_max = max_v
        initial = values[0] if values else stats["initial_capital"]

        # 最大回撤区间填充区域
        # 从最大回撤点到当前资金曲线之间
        dd_fill_points = ""
        for i, (eq, dd) in enumerate(zip(equity_data, dd_data)):
            if i == 0:
                dd_fill_points += eq + " "
            dd_fill_points += dd + " "
        dd_fill_points += equity_data[-1]
        dd_fill = dd_fill_points
    else:
        svg_path = ""
        dd_path = ""
        dd_fill = ""
        svg_height = 200
        svg_width = 700
        svg_min = stats["initial_capital"] * 0.9
        svg_max = stats["initial_capital"] * 1.1
        initial = stats["initial_capital"]

    # 最大回撤标注
    max_dd_date = stats.get("max_dd_date", None)
    max_dd_val = stats.get("max_drawdown", 0)
    max_dd_pct = stats.get("max_drawdown_pct", 0)
    dd_annotation = f"最大回撤: ¥{max_dd_val:,.0f} ({max_dd_pct:.1f}%)" if max_dd_val > 0 else ""

    # 交易明细行
    trade_rows = ""
    for t in trades:
        cls = "win" if t.pnl > 0 else "loss"
        reason_map = {
            "stop_loss": "止损",
            "take_profit": "止盈",
            "force_close": "强制平仓",
            "breakout": "突破",
        }
        reason_text = reason_map.get(t.reason, t.reason)
        max_dd_text = f"¥{t.max_dd:,.0f}" if t.max_dd and t.max_dd > 0 else "-"
        trade_rows += f"""
        <tr class="{cls}">
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
            <td>{reason_text}</td>
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
</style>
</head>
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
                <div class="info-value">海龟唐奇安突破</div>
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
        <div class="svg-wrap">
            <svg width="100%" height="{svg_height + 60}" viewBox="0 0 {svg_width} {svg_height + 60}" style="max-width:{svg_width}px;">
                <defs>
                    <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="#ef4444" stop-opacity="0.3"/>
                        <stop offset="100%" stop-color="#ef4444" stop-opacity="0"/>
                    </linearGradient>
                    <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="#10b981" stop-opacity="0.4"/>
                        <stop offset="100%" stop-color="#10b981" stop-opacity="0.1"/>
                    </linearGradient>
                </defs>
                <!-- 背景网格 -->
                <line x1="0" y1="{svg_height/2}" x2="{svg_width}" y2="{svg_height/2}" stroke="#eee" stroke-width="1"/>
                <line x1="0" y1="{svg_height/4}" x2="{svg_width}" y2="{svg_height/4}" stroke="#f5f5f5" stroke-width="1"/>
                <line x1="0" y1="{svg_height*3/4}" x2="{svg_width}" y2="{svg_height*3/4}" stroke="#f5f5f5" stroke-width="1"/>
                <!-- 初始本金线 -->
                <line x1="0" y1="{svg_height - ((initial - svg_min) / (svg_max - svg_min)) * svg_height}" x2="{svg_width}" y2="{svg_height - ((initial - svg_min) / (svg_max - svg_min)) * svg_height}" stroke="#888" stroke-width="1" stroke-dasharray="4,4"/>
                <!-- 最大回撤阴影 -->
                <polygon points="{dd_fill}" fill="url(#ddGrad)" stroke="none"/>
                <!-- 回撤线 -->
                <polyline points="{dd_path}" fill="none" stroke="#10b981" stroke-width="1" stroke-dasharray="3,3" opacity="0.6"/>
                <!-- 资金曲线 -->
                <polyline points="{svg_path}" fill="none" stroke="#ef4444" stroke-width="2"/>
                <!-- 最大回撤标注 -->
            </svg>
            <div style="display:flex;justify-content:space-between;color:#888;font-size:12px;margin-top:4px;">
                <span>¥{svg_min:,.0f}</span>
                <span>¥{svg_max:,.0f}</span>
            </div>
            <div style="color:#10b981;font-size:12px;margin-top:4px;">{dd_annotation}</div>
        </div>
    </div>

    <!-- K线图 -->
    <div class="card">
        <h2>K线图</h2>
        <div style="overflow-x:auto;">
            {gen_candlestick_svg(klines or [], trades) if klines else '<div class="no-data">无K线数据</div>'}
        </div>
        <div style="display:flex;gap:20px;margin-top:8px;font-size:12px;color:#888;">
            <span><span style="color:#ef4444;font-weight:bold;">B</span> = 买入信号</span>
            <span><span style="color:#ef4444;font-weight:bold;">S</span> = 卖出（盈利）</span>
            <span><span style="color:#10b981;font-weight:bold;">S</span> = 卖出（亏损）</span>
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
                </tr>
            </thead>
            <tbody>
                {trade_rows if trade_rows else '<tr><td colspan="12" class="no-data">暂无交易记录</td></tr>'}
            </tbody>
        </table>
    </div>
</div>
</body>
</html>"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    return out_path
