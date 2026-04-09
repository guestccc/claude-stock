"""
多因子选股系统演示
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# 设置中文
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

print("=" * 60)
print("多因子选股系统演示")
print("=" * 60)

# 1. 加载配置
print("\n[1] 加载配置...")
from config import load_config
config = load_config('config/config.yaml')
print(f"    数据源: {config.get('data_source.provider')}")
print(f"    回测期间: {config.get('backtest.start_date')} - {config.get('backtest.end_date')}")
print(f"    持仓数量: {config.get('portfolio.top_n')}")

# 2. 获取因子信息
print("\n[2] 可用因子列表...")
from factors import FactorEngine
engine = FactorEngine(config)
factor_info = engine.get_factor_info()

print("\n    基础因子:")
for cat in ['size', 'value', 'quality']:
    cats = factor_info[factor_info['category'] == cat]
    for _, row in cats.iterrows():
        print(f"      - {row['display_name']} ({row['name']})")

print("\n    技术因子:")
for cat in ['momentum', 'volatility', 'liquidity']:
    cats = factor_info[factor_info['category'] == cat]
    for _, row in cats.iterrows():
        print(f"      - {row['display_name']} ({row['name']})")

# 3. 模拟数据回测演示
print("\n[3] 运行模拟回测演示...")

# 生成模拟数据
np.random.seed(42)
dates = pd.date_range('2018-01-01', '2023-12-31', freq='ME')
n_stocks = 100
n_dates = len(dates)

# 模拟股票代码
stock_codes = [f'{600000 + i:06d}.SH' if i < 50 else f'{1 + i-50:06d}.SZ'
               for i in range(n_stocks)]

# 生成模拟价格数据
price_data = []
for date in dates:
    for code in stock_codes:
        price_data.append({
            'date': date,
            'code': code,
            'close': np.random.uniform(5, 50),
            'volume': np.random.uniform(1e6, 1e8),
            'amount': np.random.uniform(1e7, 1e9),
            'turnover_rate': np.random.uniform(0.5, 5),
            'daily_return': np.random.normal(0.01, 0.03)
        })

df = pd.DataFrame(price_data)
df['pct_change'] = df['daily_return'] * 100

print(f"    模拟数据: {len(df)} 条记录, {n_stocks} 只股票, {n_dates} 个月")

# 4. 计算模拟因子
print("\n[4] 计算模拟因子...")

# 生成有规律的因子数据（模拟真实因子的预测能力）
factor_returns = {}
factor_names = ['momentum_1m', 'volatility_20d', 'turnover_rate']

for factor_name in factor_names:
    factor_data = []
    for date in dates:
        for code in stock_codes:
            # 模拟因子值与未来收益有一定相关性
            true_signal = np.random.normal(0, 1)
            factor_value = true_signal + np.random.normal(0, 0.5)

            factor_data.append({
                'date': date,
                'code': code,
                factor_name: factor_value
            })

    factor_df = pd.DataFrame(factor_data)
    factor_returns[factor_name] = factor_df.set_index(['date', 'code'])[factor_name]

factors = pd.DataFrame(factor_returns)
print(f"    因子计算完成: {factors.columns.tolist()}")

# 5. 模拟IC分析
print("\n[5] IC分析...")
from analysis import ICAnalyzer
ic_analyzer = ICAnalyzer(config)

# 模拟IC结果
ic_results = {
    'momentum_1m': {'mean_ic': 0.05, 'ir': 0.8},
    'volatility_20d': {'mean_ic': -0.03, 'ir': -0.5},
    'turnover_rate': {'mean_ic': 0.02, 'ir': 0.3}
}

print("\n    因子IC分析结果:")
print("    " + "-" * 50)
print(f"    {'因子名称':<20} {'IC均值':<12} {'IC_IR':<12}")
print("    " + "-" * 50)
for name, result in ic_results.items():
    print(f"    {name:<20} {result['mean_ic']:>+.4f}      {result['ir']:>+.2f}")

# 6. 模拟回测结果
print("\n[6] 回测结果...")

# 模拟回测净值曲线
nav = (1 + np.cumsum(np.random.normal(0.008, 0.02, n_dates)))
benchmark = (1 + np.cumsum(np.random.normal(0.005, 0.015, n_dates)))

# 计算绩效指标
final_nav = nav[-1]
total_return = (final_nav - 1) * 100
annual_return = ((final_nav ** (12/n_dates)) - 1) * 100
volatility = np.std(np.diff(nav)/nav[:-1]) * np.sqrt(12) * 100
max_drawdown = 15.5  # 模拟值
sharpe_ratio = (annual_return/100 - 0.03) / (volatility/100)

print("\n    " + "=" * 50)
print("    绩效摘要")
print("    " + "=" * 50)
print(f"    总收益率:     {total_return:>8.2f}%")
print(f"    年化收益率:   {annual_return:>8.2f}%")
print(f"    年化波动率:   {volatility:>8.2f}%")
print(f"    最大回撤:     {max_drawdown:>8.2f}%")
print(f"    夏普比率:     {sharpe_ratio:>8.2f}")
print("    " + "=" * 50)

# 7. 生成图表
print("\n[7] 生成可视化图表...")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 净值曲线
ax1 = axes[0, 0]
ax1.plot(dates, nav, 'b-', linewidth=2, label='策略')
ax1.plot(dates, benchmark, 'r--', linewidth=1.5, alpha=0.7, label='基准(沪深300)')
ax1.set_title('组合净值曲线', fontsize=14, fontweight='bold')
ax1.set_xlabel('日期')
ax1.set_ylabel('净值')
ax1.legend()
ax1.grid(True, alpha=0.3)

# 回撤图
ax2 = axes[0, 1]
cummax = np.maximum.accumulate(nav)
drawdown = (nav - cummax) / cummax * 100
ax2.fill_between(dates, 0, drawdown, color='red', alpha=0.5)
ax2.set_title('回撤分析', fontsize=14, fontweight='bold')
ax2.set_xlabel('日期')
ax2.set_ylabel('回撤 (%)')
ax2.grid(True, alpha=0.3)

# IC对比
ax3 = axes[1, 0]
factor_names_plot = list(ic_results.keys())
ic_values = [ic_results[k]['mean_ic'] for k in factor_names_plot]
colors = ['green' if v > 0 else 'red' for v in ic_values]
bars = ax3.bar(factor_names_plot, ic_values, color=colors, alpha=0.7)
ax3.axhline(y=0, color='black', linewidth=0.5)
ax3.set_title('因子IC均值', fontsize=14, fontweight='bold')
ax3.set_ylabel('IC')
ax3.grid(True, alpha=0.3, axis='y')

# 月度收益热力图
ax4 = axes[1, 1]
monthly_returns = np.random.normal(0.8, 3, n_dates)
monthly_matrix = monthly_returns.reshape(6, 12)  # 6年 x 12个月
im = ax4.imshow(monthly_matrix, cmap='RdYlGn', aspect='auto')
ax4.set_title('月度收益热力图 (%)', fontsize=14, fontweight='bold')
ax4.set_xlabel('月份')
ax4.set_ylabel('年份')
plt.colorbar(im, ax=ax4)

plt.tight_layout()
plt.savefig('demo_output.png', dpi=150, bbox_inches='tight')
print("    图表已保存: demo_output.png")

print("\n" + "=" * 60)
print("演示完成！")
print("=" * 60)
print("\n下一步:")
print("1. 安装 akshare: pip3 install akshare")
print("2. 运行完整回测: python3 main.py --mode full")
print("3. 查看Jupyter notebook: jupyter notebook notebooks/exploratory.ipynb")
