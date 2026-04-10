"""
定时任务调度器
使用 APScheduler 实现定时更新
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, date
import pandas as pd
from a_stock_db.config import TRADING_HOURS
from .fetchers import (
    fetch_all_stocks_daily_incremental,
    fetch_all_stocks_minute,
    cleanup_old_minute_data,
)


def is_trading_day(today: date = None) -> bool:
    """
    判断今天是否是交易日
    :param today: 日期，默认今天
    :return: 是否交易日
    """
    if today is None:
        today = date.today()

    # 简单判断：周末不是交易日
    if today.weekday() >= 5:  # 周六=5, 周日=6
        return False

    try:
        import akshare as ak
        # 获取近期交易日历
        trade_dates = ak.tool_trade_date_hist_sina()
        trade_dates['trade_date'] = pd.to_datetime(trade_dates['trade_date']).dt.date
        return today in trade_dates['trade_date'].values
    except Exception as e:
        print(f"  获取交易日历失败，使用简单判断: {e}")
        # 降级：简单判断周末
        return today.weekday() < 5


def job_update_daily():
    """每日收盘后增量更新日线数据"""
    today = date.today()
    if not is_trading_day(today):
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 今日({today})非交易日，跳过日线更新")
        return

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 今日({today})为交易日，开始增量更新日线数据...")
    fetch_all_stocks_daily_incremental()


def job_update_minute():
    """交易时段更新分时数据"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始更新分时数据...")
    fetch_all_stocks_minute()


def job_cleanup_minute():
    """每日清理过期分时数据"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始清理过期分时数据...")
    cleanup_old_minute_data()


# 全局 scheduler 实例
_scheduler = None

# 状态文件路径
STATUS_FILE = '/Users/jschen/Desktop/person/claude-study/scheduler_status.json'


def save_status():
    """保存调度器状态到文件"""
    import json
    from datetime import datetime

    if _scheduler is None:
        return

    jobs = []
    for job in _scheduler.get_jobs():
        nrt = getattr(job, 'next_run_time', None)
        next_run = nrt.strftime('%Y-%m-%d %H:%M:%S') if nrt else 'N/A'
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': next_run
        })

    status = {
        'running': _scheduler.running,
        'job_count': len(jobs),
        'jobs': jobs,
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f, indent=2, ensure_ascii=False)


def get_scheduler():
    """获取当前的调度器实例"""
    return _scheduler


def start_scheduler():
    """启动定时任务调度器"""
    global _scheduler
    _scheduler = BackgroundScheduler()

    # 每个交易日 16:00 增量更新日线数据（收盘后1小时）
    _scheduler.add_job(
        job_update_daily,
        trigger=CronTrigger(
            day_of_week='mon-fri',
            hour=16,
            minute=0
        ),
        id='update_daily',
        name='增量更新日线数据'
    )

    # 交易时段每5分钟更新分时数据
    _scheduler.add_job(
        job_update_minute,
        trigger=CronTrigger(
            day_of_week='mon-fri',
            hour='9-11,13-15',
            minute='*/5'
        ),
        id='update_minute',
        name='更新分时数据'
    )

    # 每日 17:00 清理过期分时数据
    _scheduler.add_job(
        job_cleanup_minute,
        trigger=CronTrigger(
            day_of_week='mon-fri',
            hour=17,
            minute=0
        ),
        id='cleanup_minute',
        name='清理过期分时数据'
    )

    print("=" * 60)
    print("定时任务调度器已启动")
    print("=" * 60)
    print("任务列表:")
    print("  1. 日线数据增量更新 - 每个交易日 16:00")
    print("  2. 分时数据更新     - 交易时段每5分钟")
    print("  3. 过期数据清理     - 每个交易日 17:00")
    print("=" * 60)
    print("按 Ctrl+C 停止...")
    print()

    return _scheduler


def run_scheduler():
    """运行调度器（阻塞模式）"""
    scheduler = start_scheduler()
    scheduler.start()
    save_status()

    try:
        import time
        while True:
            time.sleep(60)  # 每分钟更新一次状态
            save_status()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("调度器已停止")


if __name__ == '__main__':
    run_scheduler()
