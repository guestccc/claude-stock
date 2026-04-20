# CTA 唐奇安报告系统

## 项目路径
`/Users/jschen/Desktop/person/claude-study/cta-report`

## 架构
```
a_stock_fetcher → a_stock_db → cta_report
```

## 命令（统一入口 cli.py）

```bash
cd /Users/jschen/Desktop/person/claude-study/cta-report

# 1. 生成报告（Top 20 评分）
python3 cli.py run
python3 cli.py run --date 2026-04-07

# 2. 扫描唐奇安突破（全市场）
python3 cli.py scan
python3 cli.py scan --date 2026-04-07 --top 100 --save

# 3. 回测
python3 cli.py backtest --code 000001 --start 2024-01-01
python3 cli.py backtest --codes 000001,002382 --capital 50000

# 4. 查看回测规则
python3 cli.py rules

# 5. 运行测试
python3 cli.py test
```

### 命令列表

| 命令 | 说明 |
|------|------|
| `run [--date]` | 生成唐奇安突破信号报告 |
| `scan [--date] [--top N] [--save]` | 扫描全市场唐奇安突破 |
| `backtest [--code/--codes] [--start] [--end] [--capital]` | 回测指定股票 |
| `rules` | 查看现有回测规则 |
| `test` | 运行测试 |

## 输出
- `output/{日期}_signal_report.md` — Top 20 评分报告
- `backtest/{日期}_{code}_{name}.html` — 单股回测报告
- `cta_donchian_scan` 表 — 唐奇安扫描结果（需加 --save）

## 评分体系

| 信号报告 | 满分 | 扫描评分 | 满分 |
|---|---|---|---|
| 大盘共振 | 30 | 突破强度 | 35 |
| 回踩 | 40 | 突破天数 | 25 |
| 开盘结构 | 25 | 距下轨安全垫 | 20 |
| 均价偏离 | 15 | 量比 | 10 |
| 量价配合 | 9 | | |

## 回测规则
- 信号：收盘价突破 20 日上轨
- 买入：次日开盘价
- 止损：入场价 - ATR × 1.3
- 止盈：入场价 + ATR × 2.0
