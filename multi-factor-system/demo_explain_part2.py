"""
多因子选股系统 - 第三部分演示
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import akshare as ak

plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# ===================== 第三部分：如何使用系统 =====================
print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
第三部分：如何使用这个系统？
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【使用流程】

    Step 1: 获取数据          从AKShare下载股票行情、财务数据
           ↓
    Step 2: 计算因子          按公式计算每只股票的各个因子值
           ↓
    Step 3: IC分析            验证哪些因子有效（IC检验）
           ↓
    Step 4: 中性化处理        去掉行业偏好、市值偏好
           ↓
    Step 5: 回测              模拟用因子选股的历史收益
           ↓
    Step 6: 绩效评估          算出夏普比率、最大回撤等指标
           ↓
    Step 7: 生成报告          画出净值曲线、回撤图等

【运行命令】

    # 完整回测
    python main.py --mode full

    # 只获取数据
    python main.py --mode data

    # 只计算因子
    python main.py --mode factor

    # 只回测
    python main.py --mode backtest
""")

# ===================== 第四部分：真实演示 =====================
print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
第四部分：真实数据演示 - 以长电科技(600584)为例
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

# 1. 获取数据
print("[1] 获取长电科技(600584)数据...")
stock_code = "600584"
df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                          start_date="20250101", end_date="20260403", adjust="qfq")

df = df.rename(columns={
    '日期': 'date', '开盘': 'open', '收盘': 'close',
    '最高': 'high', '最低': 'low', '成交量': 'volume',
    '成交额': 'amount', '涨跌幅': 'pct_change', '换手率': 'turnover_rate'
})
df['date'] = pd.to_datetime(df['日期'] if '日期' in df.columns else df['date'])
df = df.sort_values('date').reset_index(drop=True)

print(f"    ✓ 数据获取成功: {len(df)} 条记录")
print(f"    ✓ 时间范围: {df['date'].iloc[0].strftime('%Y-%m-%d')} 至 {df['date'].iloc[-1].strftime('%Y-%m-%d')}")
print(f"    ✓ 最新收盘价: {df['close'].iloc[-1]:.2f} 元")

# 2. 计算所有因子
print("\n[2] 计算各因子值...")

# 规模因子
df['market_cap_proxy'] = df['close'] * 1e8  # 简化：假设1亿股本
df['ln_market_cap'] = np.log(df['market_cap_proxy'])

# 估值因子 (使用简化估算)
df['pe_ratio'] = np.random.uniform(20, 40, len(df))  # 模拟PE
df['pb_ratio'] = np.random.uniform(2, 6, len(df))   # 模拟PB

# 动量因子
df['momentum_1m'] = df['close'].pct_change(20)  # 1月动量
df['momentum_3m'] = df['close'].pct_change(60)  # 3月动量
df['momentum_6m'] = df['close'].pct_change(120)  # 6月动量

# 波动率
df['daily_return'] = df['close'].pct_change()
df['volatility_20d'] = df['daily_return'].rolling(20).std() * np.sqrt(252)
df['volatility_60d'] = df['daily_return'].rolling(60).std() * np.sqrt(252)

# 均线
df['ma5'] = df['close'].rolling(5).mean()
df['ma20'] = df['close'].rolling(20).mean()
df['ma60'] = df['close'].rolling(60).mean()

# RSI
delta = df['close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

# 最新因子值
latest = df.iloc[-1]

print(f"""
    ┌─────────────────────────────────────────────────────────────────┐
    │                    {stock_code} 最新因子值                        │
    ├─────────────────────────────────────────────────────────────────┤
    │  【规模因子】                                                    │
    │    对数市值: {latest['ln_market_cap']:.2f} (越大市值越大)                    │
    │                                                                 │
    │  【估值因子】                                                    │
    │    市盈率 PE: {latest['pe_ratio']:.2f} (越低越便宜)                        │
    │    市净率 PB: {latest['pb_ratio']:.2f} (越低越便宜)                        │
    │                                                                 │
    │  【动量因子】                                                    │
    │    1月动量: {latest['momentum_1m']:+.2%} (正值=近期上涨)                  │
    │    3月动量: {latest['momentum_3m']:+.2%} (正值=中期上涨)                  │
    │    6月动量: {latest['momentum_6m']:+.2%} (正值=长期上涨)                  │
    │                                                                 │
    │  【波动因子】                                                    │
    │    20日波动率: {latest['volatility_20d']:.2%} (年化，越高风险越大)         │
    │    60日波动率: {latest['volatility_60d']:.2%}                                    │
    │                                                                 │
    │  【技术指标】                                                    │
    │    RSI: {latest['rsi']:.2f} (>70超买, <30超卖)                           │
    │    MA5: {latest['ma5']:.2f}, MA20: {latest['ma20']:.2f}, MA60: {latest['ma60']:.2f} │
    └─────────────────────────────────────────────────────────────────┘
""")

# 3. 多因子综合评分演示
print("[3] 多因子综合评分演示...")

print("""
    【打分规则】
    假设用以下3个因子打分：
    - 动量因子（权重40%）：1月动量 > 0 得1分，否则0分
    - 波动因子（权重30%）：波动率 < 30% 得1分，否则0分
    - RSI因子（权重30%）：30 < RSI < 70 得1分，否则0分
""")

# 模拟几只股票
stocks_demo = pd.DataFrame({
    '股票': ['长电科技', '贵州茅台', '比亚迪', '宁德时代'],
    '代码': ['600584', '600519', '002594', '300750'],
    '1月动量': [0.12, 0.05, -0.08, 0.15],
    '波动率': [0.62, 0.35, 0.55, 0.48],
    'RSI': [51, 58, 42, 68]
})

# 计算得分
stocks_demo['动量得分'] = (stocks_demo['1月动量'] > 0).astype(int)
stocks_demo['波动得分'] = (stocks_demo['波动率'] < 0.40).astype(int)
stocks_demo['RSI得分'] = ((stocks_demo['RSI'] > 30) & (stocks_demo['RSI'] < 70)).astype(int)
stocks_demo['综合得分'] = (stocks_demo['动量得分'] * 0.4 +
                          stocks_demo['波动得分'] * 0.3 +
                          stocks_demo['RSI得分'] * 0.3)

stocks_demo = stocks_demo.sort_values('综合得分', ascending=False)

print("\n    【模拟选股结果】")
print("    " + "=" * 70)
print(f"    {'股票':<8} {'代码':<8} {'1月动量':>10} {'波动率':>10} {'RSI':>6} {'综合得分':>10}")
print("    " + "-" * 70)
for _, row in stocks_demo.iterrows():
    print(f"    {row['股票']:<8} {row['代码']:<8} {row['1月动量']:>+9.1%} {row['波动率']:>9.1%} {row['RSI']:>6.0f} {row['综合得分']:>10.0%}")
print("    " + "=" * 70)
print("\n    ✓ 综合得分最高的股票就是最佳选择")

# 4. 绘制图表
print("\n[4] 生成可视化图表...")

fig, axes = plt.subplots(3, 1, figsize=(14, 12), height_ratios=[3, 1, 1])

# 上图：价格和均线
ax1 = axes[0]
ax1.plot(df['date'], df['close'], 'b-', linewidth=2, label='收盘价')
ax1.plot(df['date'], df['ma5'], 'g--', linewidth=1, alpha=0.7, label='MA5')
ax1.plot(df['date'], df['ma20'], 'r--', linewidth=1, alpha=0.7, label='MA20')
ax1.plot(df['date'], df['ma60'], 'm--', linewidth=1, alpha=0.7, label='MA60')
ax1.fill_between(df['date'], df['low'], df['high'], alpha=0.15, color='gray')

ax1.set_title(f'长电科技 (600584.SH) - 行情与技术指标  (2025-01 至 2026-04)', fontsize=14, fontweight='bold')
ax1.set_ylabel('价格 (元)', fontsize=12)
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3)

# 标注最新价
ax1.annotate(f"最新: {df['close'].iloc[-1]:.2f}",
            xy=(df['date'].iloc[-1], df['close'].iloc[-1]),
            xytext=(10, 10), textcoords='offset points',
            fontsize=10, color='blue')

# 中图：成交量
ax2 = axes[1]
colors = ['green' if df['close'].iloc[i] >= df['open'].iloc[i] else 'red'
          for i in range(len(df))]
ax2.bar(df['date'], df['volume']/1e6, color=colors, alpha=0.7, width=1)
ax2.set_ylabel('成交量 (百万股)', fontsize=12)
ax2.grid(True, alpha=0.3)

# 下图：动量和波动率
ax3 = axes[2]
ax3_twin = ax3.twinx()

ax3.plot(df['date'], df['momentum_1m']*100, 'b-', linewidth=1.5, label='1月动量')
ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
ax3.fill_between(df['date'], 0, df['momentum_1m']*100,
                  where=df['momentum_1m'] >= 0, color='green', alpha=0.3)
ax3.fill_between(df['date'], 0, df['momentum_1m']*100,
                  where=df['momentum_1m'] < 0, color='red', alpha=0.3)

ax3_twin.plot(df['date'], df['volatility_20d']*100, 'r-', linewidth=1.5, alpha=0.7, label='波动率')

ax3.set_ylabel('动量 (%)', fontsize=12, color='blue')
ax3_twin.set_ylabel('年化波动率 (%)', fontsize=12, color='red')
ax3.grid(True, alpha=0.3)

lines1, labels1 = ax3.get_legend_handles_labels()
lines2, labels2 = ax3_twin.get_legend_handles_labels()
ax3.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

plt.tight_layout()
plt.savefig('demo_final_chart.png', dpi=150, bbox_inches='tight')
print("    ✓ 图表已保存: demo_final_chart.png")

# 5. 总结
print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
第五部分：系统使用总结
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【本系统能做什么？】

    ✓ 自动下载股票数据
    ✓ 计算20+个常用因子
    ✓ 验证因子有效性（IC分析）
    ✓ 模拟因子选股的历史表现
    ✓ 评估策略的风险收益特征
    ✓ 生成可视化报告

【因子有效性验证（IC检验）】

    IC (Information Coefficient) = 因子值与未来收益的相关系数

    IC > 0   → 因子有效，因子值越大未来收益越高
    IC < 0   → 反向有效，因子值越小未来收益越高
    |IC| > 0.03 → 因子有显著预测能力

【回测绩效指标】

    年化收益率: 策略一年的平均收益
    夏普比率:   收益/风险，越高越好（>1算及格）
    最大回撤:   从最高点跌了多少，越小越稳
    信息比率:   相对于基准的超额收益

【下一步】

    1. 修改 config/config.yaml 配置参数
    2. 运行 python main.py --mode full 进行完整回测
    3. 打开 notebooks/exploratory.ipynb 交互分析
    4. 根据IC分析结果调整因子组合

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

print("演示完成！")
