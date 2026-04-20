"""
CLI 入口
"""
import sys
from a_stock_db import db
from a_stock_fetcher import (
    fetch_stock_basic,
    fetch_all_stocks_daily,
    fetch_all_stocks_daily_incremental,
    fetch_all_stocks_minute,
    cleanup_old_minute_data,
    fetch_stock_financial,
    fetch_all_boards,
    fetch_stock_daily_full_history,
    run_scheduler,
    get_scheduler,
    is_enabled,
    clean_daily_data,
)


HELP_TEXT = """
用法: cd /Users/jschen/Desktop/person/claude-study && python3 -m a_stock_fetcher.cli [命令] [参数]

命令:
  init                    - 初始化数据库（创建表 + 股票基本信息 + 板块）
  daily [N]             - 全量获取日线数据，可指定N限制数量
  daily-update [N]       - 增量更新日线数据（全量或限制N只）
  daily-update --codes 600519,000001 - 增量更新指定股票
  daily-full <CODE>       - 获取指定股票所有历史日线数据
  daily-full-all         - 获取所有股票所有历史日线数据
  minute [N]             - 更新1分钟分时数据，可指定N限制数量
  financial [N]          - 更新财务数据，默认100条
  boards                 - 更新概念/行业板块
  cleanup                - 清理过期分时数据
  clean-daily [N]       - 清洗日线数据：补全涨跌幅/涨跌额/振幅
  rules/rules2/rules3   - 查看配置规则
  scheduler              - 启动定时任务调度器
  status                 - 查看调度器状态

示例:
  python3 -m a_stock_fetcher.cli daily-update                    # 增量更新全部
  python3 -m a_stock_fetcher.cli daily-update 100                  # 增量更新前100只
  python3 -m a_stock_fetcher.cli daily-update --codes 600519,000001 # 增量更新指定股票
  python3 -m a_stock_fetcher.cli daily-full 600519                # 获取贵州茅台所有历史数据
  python3 -m a_stock_fetcher.cli daily-full-all                   # 获取所有股票所有历史数据
  python3 -m a_stock_fetcher.cli scheduler                        # 启动定时任务
  python3 -m a_stock_fetcher.cli status                            # 查看状态
"""


def parse_codes_arg(args: list) -> list:
    """解析 --codes 参数，返回股票代码列表"""
    codes = []
    i = 0
    while i < len(args):
        if args[i] == '--codes':
            # 下一个参数是逗号分隔的股票代码
            if i + 1 < len(args):
                codes = [c.strip() for c in args[i + 1].split(',')]
                break
        i += 1
    return codes


def main():
    if len(sys.argv) < 2:
        print(HELP_TEXT)
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    # 解析参数
    limit = None
    codes = parse_codes_arg(args)

    # 解析数字参数
    for arg in args:
        if arg != '--codes' and not codes:
            try:
                limit = int(arg)
            except ValueError:
                pass

    if cmd == "init":
        print("=" * 50)
        print("初始化数据库")
        print("=" * 50)
        db.create_all()
        fetch_stock_basic()
        fetch_all_boards()

    elif cmd == "daily":
        fetch_all_stocks_daily(limit=limit)

    elif cmd == "daily-update":
        fetch_all_stocks_daily_incremental(codes=codes if codes else None, limit=limit)

    elif cmd == "daily-full":
        if not args or args[0].startswith('--'):
            print("用法: python3 -m a_stock_fetcher.cli daily-full <股票代码>")
            print("示例: python3 -m a_stock_fetcher.cli daily-full 600519")
            return
        code = args[0].strip()
        print(f"=" * 50)
        print(f"获取 {code} 所有历史日线数据...")
        print(f"=" * 50)
        result = fetch_stock_daily_full_history(code)
        if result == "已有完整数据":
            print("已有完整数据，无需获取")
        else:
            print(f"结果: {result}")

    elif cmd == "daily-full-all":
        import time
        from a_stock_db.database import StockBasic

        session = db.get_session()
        all_stocks = session.query(StockBasic).all()
        session.close()

        # 按配置过滤市场
        stocks = [s for s in all_stocks if is_enabled(s.code)]
        market_skipped = len(all_stocks) - len(stocks)

        print(f"=" * 50)
        print(f"全量获取所有股票历史日线数据")
        print(f"=" * 50)
        print(f"股票总数: {len(stocks)}（已跳过 {market_skipped} 只北证/创业板/科创板）")

        completed = 0
        failed = []
        start_time = time.time()

        skipped_complete = 0
        for stock in stocks:
            t0 = time.time()
            result = fetch_stock_daily_full_history(stock.code)
            elapsed = time.time() - t0
            completed += 1
            pct = completed / len(stocks) * 100
            avg_time = (time.time() - start_time) / completed
            remaining = len(stocks) - completed
            eta = avg_time * remaining
            if result is True:
                status = "✓"
            elif result == "已有完整数据":
                status = "○ 已有完整"
                skipped_complete += 1
            else:
                status = f"✗ {result}"
                failed.append({'code': stock.code, 'name': stock.股票简称, 'reason': result})
            print(f"[{completed}/{len(stocks)} {pct:.1f}%] {stock.code} {stock.股票简称}... {status} ({elapsed:.1f}s) ETA:{eta/3600:.1f}h", flush=True)

        print(f"\n完成: 获取 {len(stocks) - skipped_complete - len(failed)}/{len(stocks)}, 已有完整 {skipped_complete}, 失败 {len(failed)}")
        if failed:
            print(f"\n失败列表:")
            for f in failed[:20]:
                print(f"  {f['code']} {f['name']}: {f['reason']}")
            if len(failed) > 20:
                print(f"  ... 还有 {len(failed) - 20} 只")

    elif cmd == "minute":
        fetch_all_stocks_minute(limit=limit)

    elif cmd == "financial":
        fetch_stock_financial(limit=limit if limit else 100)

    elif cmd == "boards":
        fetch_all_boards()

    elif cmd == "cleanup":
        cleanup_old_minute_data()

    elif cmd == "clean-daily":
        clean_daily_data(limit=limit)

    elif cmd == "scheduler":
        run_scheduler()

    elif cmd == "status":
        from a_stock_fetcher.scheduler import STATUS_FILE
        import json

        try:
            with open(STATUS_FILE, 'r') as f:
                status = json.load(f)
        except FileNotFoundError:
            print("调度器未运行（未找到状态文件）")
            return

        print("=" * 60)
        print("定时任务调度器状态")
        print("=" * 60)
        print(f"运行状态: {'运行中' if status.get('running') else '已停止'}")
        print(f"任务数量: {status.get('job_count', 0)}")
        print(f"更新时间: {status.get('updated_at', 'N/A')}")
        print()
        print("任务列表:")
        for job in status.get('jobs', []):
            print(f"  [{job['id']}] {job['name']} - 下次运行: {job['next_run']}")
        print("=" * 60)

    elif cmd in ("rules", "rules2", "rules3"):
        from a_stock_db.config import (
            REQUEST_DELAY, MINUTE_KEEP_DAYS, MINUTE_STOCK_LIMIT,
            DAILY_HISTORY_DAYS, ADJUST, TRADING_HOURS, ENABLED_EXCHANGES,
        )
        print("=" * 60)
        print("a_stock_fetcher 配置规则")
        print("=" * 60)
        print(f"请求间隔: {REQUEST_DELAY}s")
        print(f"分时保留: {MINUTE_KEEP_DAYS} 天")
        print(f"分时股票数限制: {MINUTE_STOCK_LIMIT if MINUTE_STOCK_LIMIT else '无限制'}")
        print(f"日线历史获取: {DAILY_HISTORY_DAYS} 天")
        print(f"复权类型: {ADJUST}")
        print(f"交易时段: {TRADING_HOURS['morning_start']}-{TRADING_HOURS['morning_end']} / "
              f"{TRADING_HOURS['afternoon_start']}-{TRADING_HOURS['afternoon_end']}")
        print(f"市场启用状态: {', '.join(f'{k}={v}' for k, v in ENABLED_EXCHANGES.items())}")
        print("=" * 60)

    else:
        print(f"未知命令: {cmd}")
        print(HELP_TEXT)


if __name__ == '__main__':
    main()
