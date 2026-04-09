"""
真实股票数据演示 - 多因子选股系统
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import akshare as ak

# 设置中文
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

print("=" * 60)
print("真实股票数据演示 - 多因子选股系统")
print("=" * 60)

# ===================== 1. 获取真实数据 =====================
print("\n[1] 获取真实股票数据...")

# 获取中国平安日线数据
stock_code = "600584"
print(f"\n    股票: 长电科技 (600584.SH)")

df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                          start_date="20230101", end_date="20240331", adjust="qfq")

print(f"    数据条数: {len(df)} 条")
print(f"    时间范围: {df['日期'].iloc[0]} 至 {df['日期'].iloc[-1]}")
print(f"    最新收盘价: {df['收盘'].iloc[-1]:.2f} 元")

# 重命名列
df = df.rename(columns={
    '日期': 'date', '开盘': 'open', '收盘': 'close',
    '最高': 'high', '最低': 'low', '成交量': 'volume',
    '成交额': 'amount', '涨跌幅': 'pct_change', '换手率': 'turnover_rate'
})
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date').reset_index(drop=True)

print(f"\n    最近5天行情:")
print(df[['date', 'open', 'close', 'volume', 'pct_change']].tail())

# ===================== 2. 计算技术指标 =====================
print("\n[2] 计算技术因子...")

df['ma5'] = df['close'].rolling(5).mean()
df['ma20'] = df['close'].rolling(20).mean()
df['ma60'] = df['close'].rolling(60).mean()

# 动量因子
df['momentum_1m'] = df['close'].pct_change(20)  # 1月动量
df['momentum_3m'] = df['close'].pct_change(60)  # 3月动量

# 波动率
df['volatility_20d'] = df['close'].pct_change().rolling(20).std() * np.sqrt(252)

# RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

print(f"    MA5: {df['ma5'].iloc[-1]:.2f}")
print(f"    MA20: {df['ma20'].iloc[-1]:.2f}")
print(f"    MA60: {df['ma60'].iloc[-1]:.2f}")
print(f"    1月动量: {df['momentum_1m'].iloc[-1]:.2%}")
print(f"    波动率: {df['volatility_20d'].iloc[-1]:.2%}")
print(f"    RSI: {df['rsi'].iloc[-1]:.2f}")

# ===================== 3. 多股票对比 =====================
print("\n[3] 多股票因子对比...")

# 获取贵州茅台
df2 = ak.stock_zh_a_hist(symbol="600519", period="daily",
                           start_date="20230101", end_date="20240331", adjust="qfq")
df2 = df2.rename(columns={'日期': 'date', '收盘': 'close', '成交量': 'volume'})
df2['date'] = pd.to_datetime(df2['日期'] if '日期' in df2.columns else df2['date'])
df2 = df2.sort_values('date').reset_index(drop=True)

# 计算两只股票的收益率
df['return_1m'] = df['close'].pct_change(20)
df2['return_1m'] = df2['close'].pct_change(20)

# 对齐数据
df_merged = df[['date', 'close', 'return_1m']].rename(columns={'close': '600584', 'return_1m': 'ret_600584'})
df2_subset = df2[['date', 'close', 'return_1m']].rename(columns={'close': '600519', 'return_1m': 'ret_600519'})
df_merged = df_merged.merge(df2_subset, on='date', how='inner')

print(f"\n    长电科技(600584) 最新收盘: {df_merged['600584'].iloc[-1]:.2f} 元")
print(f"    贵州茅台(600519) 最新收盘: {df_merged['600519'].iloc[-1]:.2f} 元")

# 计算相对强弱
df_merged['relative_strength'] = df_merged['600584'] / df_merged['600519'] * 100

print(f"\n    相对强弱指数(600519=100): {df_merged['relative_strength'].iloc[-1]:.2f}")

# ===================== 4. 绘制K线和技术指标 =====================
print("\n[4] 绘制K线图和技术指标...")

fig, axes = plt.subplots(3, 1, figsize=(14, 12),
                          gridspec_kw={'height_ratios': [3, 1, 1]})

# 上图：价格和均线
ax1 = axes[0]
ax1.plot(df['date'], df['close'], 'b-', linewidth=1.5, label='收盘价')
ax1.plot(df['date'], df['ma5'], 'g--', linewidth=1, alpha=0.7, label='MA5')
ax1.plot(df['date'], df['ma20'], 'r--', linewidth=1, alpha=0.7, label='MA20')
ax1.plot(df['date'], df['ma60'], 'm--', linewidth=1, alpha=0.7, label='MA60')
ax1.fill_between(df['date'], df['low'], df['high'], alpha=0.2, color='gray')

ax1.set_title('长电科技 (600584.SH) - K线与均线', fontsize=14, fontweight='bold')
ax1.set_ylabel('价格 (元)', fontsize=12)
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3)

# 中图：成交量
ax2 = axes[1]
colors = ['green' if df['close'].iloc[i] >= df['open'].iloc[i] else 'red'
          for i in range(len(df))]
ax2.bar(df['date'], df['volume']/1e8, color=colors, alpha=0.7)
ax2.set_ylabel('成交量 (亿股)', fontsize=12)
ax2.grid(True, alpha=0.3)

# 下图：动量和波动率
ax3 = axes[2]
ax3_twin = ax3.twinx()

ax3.plot(df['date'], df['momentum_1m']*100, 'b-', linewidth=1.5, label='1月动量')
ax3_twin.plot(df['date'], df['volatility_20d']*100, 'r-', linewidth=1.5, alpha=0.7, label='波动率')

ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
ax3.set_ylabel('动量 (%)', fontsize=12, color='blue')
ax3_twin.set_ylabel('年化波动率 (%)', fontsize=12, color='red')
ax3.grid(True, alpha=0.3)

# 合并图例
lines1, labels1 = ax3.get_legend_handles_labels()
lines2, labels2 = ax3_twin.get_legend_handles_labels()
ax3.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

plt.tight_layout()
plt.savefig('demo_real_stock.png', dpi=150, bbox_inches='tight')
print("    图表已保存: demo_real_stock.png")

# ===================== 5. 多股票对比图 =====================
fig2, axes2 = plt.subplots(2, 1, figsize=(14, 10))

# 上图：两只股票价格走势
ax1 = axes2[0]
ax1_twin = ax1.twinx()

ax1.plot(df_merged['date'], df_merged['600584'], 'b-', linewidth=2, label='长电科技 (600584)')
ax1_twin.plot(df_merged['date'], df_merged['600519'], 'r-', linewidth=2, label='贵州茅台 (600519)')

ax1.set_title('多股票走势对比', fontsize=14, fontweight='bold')
ax1.set_ylabel('长电科技 收盘价 (元)', fontsize=12, color='blue')
ax1_twin.set_ylabel('贵州茅台 收盘价 (元)', fontsize=12, color='red')
ax1.legend(loc='upper left')
ax1_twin.legend(loc='upper right')
ax1.grid(True, alpha=0.3)

# 下图：相对强弱
ax2 = axes2[1]
ax2.plot(df_merged['date'], df_merged['relative_strength'], 'g-', linewidth=2)
ax2.fill_between(df_merged['date'], 100, df_merged['relative_strength'],
                  where=df_merged['relative_strength'] >= 100, color='green', alpha=0.3)
ax2.fill_between(df_merged['date'], 100, df_merged['relative_strength'],
                  where=df_merged['relative_strength'] < 100, color='red', alpha=0.3)
ax2.axhline(y=100, color='black', linestyle='--', linewidth=1)

ax2.set_title('相对强弱 (长电科技 / 贵州茅台，基准=100)', fontsize=14, fontweight='bold')
ax2.set_ylabel('相对强弱指数', fontsize=12)
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('demo_compare.png', dpi=150, bbox_inches='tight')
print("    图表已保存: demo_compare.png")

# ===================== 6. 因子统计 =====================
print("\n[5] 因子统计...")
print("\n    " + "=" * 50)
print("    中国平安 技术因子统计 (近60天)")
print("    " + "=" * 50)

recent = df.tail(60)
print(f"    {'因子':<20} {'当前值':<15} {'说明'}")
print("    " + "-" * 50)
print(f"    {'收盘价':<20} {recent['close'].iloc[-1]:>10.2f} 元")
print(f"    {'MA5':<20} {recent['ma5'].iloc[-1]:>10.2f} 元")
print(f"    {'MA20':<20} {recent['ma20'].iloc[-1]:>10.2f} 元")
print(f"    {'MA60':<20} {recent['ma60'].iloc[-1]:>10.2f} 元")
print(f"    {'1月动量':<20} {recent['momentum_1m'].iloc[-1]:>10.2%}")
print(f"    {'3月动量':<20} {recent['momentum_3m'].iloc[-1]:>10.2%}")
print(f"    {'波动率':<20} {recent['volatility_20d'].iloc[-1]:>10.2%}")
print(f"    {'RSI':<20} {recent['rsi'].iloc[-1]:>10.2f}")
print("    " + "=" * 50)

# ===================== 7. 多因子选股模拟 =====================
print("\n[6] 多因子选股模拟...")
print("\n    假设按照以下因子打分选股:")
print("    - 动量因子 (1月): 权重 40%")
print("    - 波动率因子 (低波动): 权重 30%")
print("    - RSI因子 (适中): 权重 30%")

# 模拟因子评分
scores = pd.DataFrame({
    '股票': ['中国平安', '贵州茅台', '招商银行', '兴业银行', '比亚迪'],
    '代码': ['601318', '600519', '600036', '601166', '002594'],
    '动量得分': [0.6, 0.8, 0.5, 0.4, 0.9],
    '波动得分': [0.7, 0.5, 0.6, 0.8, 0.4],
    'RSI得分': [0.5, 0.6, 0.7, 0.8, 0.3]
})

# 综合得分
scores['综合得分'] = (scores['动量得分'] * 0.4 +
                     scores['波动得分'] * 0.3 +
                     scores['RSI得分'] * 0.3)

scores = scores.sort_values('综合得分', ascending=False)

print("\n    选股结果 (按综合得分排序):")
print(scores.to_string(index=False))

print("\n" + "=" * 60)
print("演示完成！")
print("=" * 60)
print("\n下一步:")
print("1. 在 config/config.yaml 中配置参数")
print("2. 使用 Jupyter notebook 进行深入分析")
print("3. 运行 python main.py --mode full 进行完整回测")
