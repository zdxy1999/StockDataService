"""
定时任务进程

功能：
- 每天在指定时间（默认 19:30，周一至周五）自动触发所有投资计划关联策略的选股计算
- 当天为非交易日则跳过
- 若当天 CSV 已存在则跳过（幂等）
- 通过环境变量 DAILY_CRON 自定义 cron 表达式

启动方式：
    python scheduler.py
"""

import os
import sys
import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# 确保 StockDataService 根目录在 sys.path
_SERVICE_ROOT = os.path.dirname(os.path.abspath(__file__))
if _SERVICE_ROOT not in sys.path:
    sys.path.insert(0, _SERVICE_ROOT)

from invest.config import LOGS_DIR, ensure_dirs
from invest.path_setup import ensure_paths

# 注入 guoren 路径
ensure_paths()

from trade_calendar import get_trade_dates
from invest.invest_service import trigger_daily_stock_pick

# ---------------------------------------------------------------------------
# 日志配置
# ---------------------------------------------------------------------------

ensure_dirs()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [scheduler] %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(LOGS_DIR, 'scheduler.log'), encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 调度任务
# ---------------------------------------------------------------------------

def _is_trade_day(date_yyyymmdd: str) -> bool:
    """判断指定日期是否为交易日"""
    dates = get_trade_dates(date_yyyymmdd, date_yyyymmdd)
    return len(dates) > 0 and dates[0] == date_yyyymmdd


def daily_job():
    """
    每日选股定时任务。

    1. 判断当天是否为交易日，非交易日直接跳过
    2. 对所有 invest_plan/plans/ 下关联策略触发选股（幂等）
    """
    today = datetime.now().strftime('%Y%m%d')
    logger.info(f"=== 定时任务触发 | 日期：{today} ===")

    if not _is_trade_day(today):
        logger.info(f"{today} 不是交易日，跳过本次选股。")
        return

    logger.info(f"{today} 是交易日，开始触发选股...")
    try:
        report = trigger_daily_stock_pick(today)
        for item in report:
            logger.info(
                f"  策略：{item['strategy']} | 日期：{item['date']} | 状态：{item['status']}"
            )
        logger.info(f"=== 定时任务完成，共处理 {len(report)} 个策略 ===")
    except Exception as e:
        logger.exception(f"定时任务执行异常：{e}")


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main():
    # 解析 DAILY_CRON 环境变量，格式：分 时 日 月 周
    # 默认：30 19 * * 1-5 （周一至周五 19:30）
    cron_expr = os.environ.get('DAILY_CRON', '30 19 * * 1-5')
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        logger.error(f"DAILY_CRON 格式不正确（需 5 字段），使用默认值 '30 19 * * 1-5'。当前值：{cron_expr}")
        parts = ['30', '19', '*', '*', '1-5']

    minute, hour, day, month, day_of_week = parts

    logger.info(
        f"Scheduler 启动，cron 表达式：{cron_expr} "
        f"（即每周 {day_of_week} {hour}:{minute} 触发）"
    )

    scheduler = BlockingScheduler(timezone='Asia/Shanghai')
    scheduler.add_job(
        daily_job,
        trigger=CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            timezone='Asia/Shanghai',
        ),
        id='daily_stock_pick',
        name='每日选股定时任务',
        replace_existing=True,
        misfire_grace_time=300,  # 允许 5 分钟内的延迟触发
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler 已停止。")


if __name__ == '__main__':
    main()
