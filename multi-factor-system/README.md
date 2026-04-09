# A股多因子量化选股系统

基于Python的A股多因子量化选股系统，支持因子分析、回测和绩效评估。

## 功能特性

- **数据获取**: 支持Akshare/Tushare数据源
- **因子库**: 包含基础因子、技术因子、财务因子
- **因子分析**: IC/IR分析、行业中性化
- **回测系统**: 事件驱动回测框架
- **绩效评估**: 完整的风险收益指标
- **可视化报告**: 净值曲线、回撤分析、收益分布等

## 项目结构

```
multi-factor-system/
├── config/              # 配置文件
├── data/                # 数据模块
│   ├── downloader.py    # 数据下载
│   ├── processor.py     # 数据处理
│   └── cache.py        # 缓存管理
├── factors/             # 因子模块
│   ├── base.py        # 因子基类
│   ├── fundamental.py  # 基础因子
│   ├── technical.py    # 技术因子
│   ├── financial.py    # 财务因子
│   └── factor_engine.py # 因子引擎
├── analysis/            # 分析模块
│   ├── ic_analyzer.py  # IC分析
│   ├── neutralization.py # 中性化
│   └── factor_test.py  # 单因子测试
├── backtest/            # 回测模块
│   ├── engine.py       # 回测引擎
│   ├── portfolio.py    # 组合构建
│   └── rebalance.py    # 调仓逻辑
├── evaluation/          # 评估模块
│   ├── metrics.py      # 绩效指标
│   └── report.py       # 报告生成
├── notebooks/           # Jupyter notebooks
└── main.py             # 主入口
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

编辑 `config/config.yaml` 文件，配置数据源、回测参数等。

### 3. 运行回测

```bash
# 完整流程
python main.py --mode full

# 仅数据获取
python main.py --mode data

# 仅因子计算
python main.py --mode factor

# 仅回测
python main.py --mode backtest
```

### 4. Jupyter Notebook

打开 `notebooks/exploratory.ipynb` 进行交互式分析。

## 核心因子

### 基础因子
- **规模因子**: ln_market_cap, circulating_market_cap
- **估值因子**: pe_ratio, pb_ratio, ps_ratio
- **质量因子**: roe, roa, gross_margin

### 技术因子
- **动量因子**: momentum_1m/3m/6m/12m
- **波动因子**: volatility_20d/60d, beta
- **流动性因子**: turnover_rate, amihud_illiquidity
- **均线因子**: ma20_deviation

### 财务因子
- **成长因子**: revenue_growth, profit_growth
- **财务健康**: debt_ratio, current_ratio
- **现金流**: cash_flow_ratio

## 绩效指标

- **收益率**: 总收益、年化收益、超额收益
- **风险**: 波动率、最大回撤、VaR
- **风险调整**: 夏普比率、索提诺比率、Calmar比率
- **交易**: 换手率、交易次数

## 使用示例

```python
from config import load_config
from data import DataDownloader, DataProcessor
from factors import FactorEngine
from backtest import BacktestEngine, PortfolioBuilder
from evaluation import PerformanceMetrics

# 加载配置
config = load_config('config/config.yaml')

# 数据获取
downloader = DataDownloader(config)
stock_data = downloader.get_stock_data()

# 数据处理
processor = DataProcessor(config)
processed_data = processor.process(stock_data)

# 因子计算
factor_engine = FactorEngine(config)
factors = factor_engine.calculate_all_factors(processed_data)

# 回测
portfolio_builder = PortfolioBuilder(config)
backtest_engine = BacktestEngine(config, portfolio_builder)
results = backtest_engine.run(factors, processed_data)

# 绩效评估
metrics = PerformanceMetrics(results, config)
perf = metrics.calculate()

print(f"年化收益: {perf['annual_return']:.2%}")
print(f"夏普比率: {perf['sharpe_ratio']:.2f}")
print(f"最大回撤: {perf['max_drawdown']:.2%}")
```

## 扩展开发

1. **添加新因子**: 在 `factors/` 目录下创建新的因子类
2. **修改回测逻辑**: 编辑 `backtest/engine.py`
3. **新增绩效指标**: 在 `evaluation/metrics.py` 中添加

## 免责声明

本系统仅供学习研究使用，不构成任何投资建议。投资有风险，入市需谨慎。
