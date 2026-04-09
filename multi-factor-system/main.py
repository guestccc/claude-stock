"""
多因子选股系统 - 主入口
"""
import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger
from config import load_config
from data import DataDownloader, DataProcessor, DataCache
from factors import FactorEngine
from analysis import ICAnalyzer, Neutralizer
from backtest import BacktestEngine, PortfolioBuilder
from evaluation import PerformanceMetrics, ReportGenerator


def setup_logger():
    """配置日志"""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        "logs/system_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="DEBUG"
    )


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="多因子选股系统")
    parser.add_argument("--mode", choices=["data", "factor", "backtest", "full"],
                        default="full", help="运行模式")
    parser.add_argument("--config", default="config/config.yaml", help="配置文件路径")
    parser.add_argument("--start-date", default=None, help="回测开始日期")
    parser.add_argument("--end-date", default=None, help="回测结束日期")

    args = parser.parse_args()

    setup_logger()
    logger.info("=" * 60)
    logger.info("多因子选股系统启动")
    logger.info(f"运行模式: {args.mode}")
    logger.info("=" * 60)

    # 加载配置
    config = load_config(args.config)

    if args.start_date:
        config._config["backtest"]["start_date"] = args.start_date
    if args.end_date:
        config._config["backtest"]["end_date"] = args.end_date

    try:
        if args.mode == "data":
            # 数据获取模式
            logger.info("模式: 数据获取")
            downloader = DataDownloader(config)
            data = downloader.get_stock_data()
            logger.info(f"数据获取完成，共 {len(data)} 条记录")

        elif args.mode == "factor":
            # 因子计算模式
            logger.info("模式: 因子计算")
            cache = DataCache(config)
            data = cache.load_data()
            engine = FactorEngine(config)
            factors = engine.calculate_all_factors(data)
            logger.info(f"因子计算完成，共 {len(factors.columns)} 个因子")

        elif args.mode == "backtest":
            # 回测模式
            logger.info("模式: 完整回测")
            # 完整流程在下方执行

        elif args.mode == "full":
            # 完整模式
            logger.info("模式: 完整流程")
            # 完整流程在下方执行

        # 执行完整流程（用于 backtest 和 full 模式）
        if args.mode in ["backtest", "full"]:
            # 1. 数据获取
            logger.info("\n[Step 1/6] 数据获取...")
            downloader = DataDownloader(config)
            stock_data = downloader.get_stock_data()

            # 2. 数据处理
            logger.info("\n[Step 2/6] 数据处理...")
            processor = DataProcessor(config)
            processed_data = processor.process(stock_data)

            # 3. 因子计算
            logger.info("\n[Step 3/6] 因子计算...")
            factor_engine = FactorEngine(config)
            factors = factor_engine.calculate_all_factors(processed_data)

            # 4. 因子分析
            logger.info("\n[Step 4/6] 因子分析...")
            neutralizer = Neutralizer(config)
            neutralized_factors = neutralizer.neutralize(factors)

            ic_analyzer = ICAnalyzer(config)
            ic_results = ic_analyzer.calculate_ic(neutralized_factors, processed_data)
            logger.info(f"因子IC分析完成，平均IC: {ic_results['mean_ic']:.4f}")

            # 5. 回测
            logger.info("\n[Step 5/6] 执行回测...")
            portfolio_builder = PortfolioBuilder(config)
            backtest_engine = BacktestEngine(config, portfolio_builder)
            results = backtest_engine.run(neutralized_factors, processed_data)

            # 6. 绩效评估
            logger.info("\n[Step 6/6] 绩效评估...")
            metrics = PerformanceMetrics(results, config)
            perf_metrics = metrics.calculate()

            # 生成报告
            report_gen = ReportGenerator(config)
            report_gen.generate(perf_metrics, results)

            logger.info("\n" + "=" * 60)
            logger.info("回测完成!")
            logger.info(f"年化收益率: {perf_metrics['annual_return']:.2%}")
            logger.info(f"夏普比率: {perf_metrics['sharpe_ratio']:.2f}")
            logger.info(f"最大回撤: {perf_metrics['max_drawdown']:.2%}")
            logger.info("=" * 60)

    except Exception as e:
        logger.error(f"执行出错: {e}")
        raise


if __name__ == "__main__":
    main()
