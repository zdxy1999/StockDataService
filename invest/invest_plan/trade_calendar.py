"""
交易日历工具模块
提供交易日列表查询和调仓日计算
"""

import sys
import os
from typing import List, Optional
from datetime import datetime, timedelta
from functools import lru_cache

# 引用 tushare_selector 目录
_SELECTOR_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'tushare_selector')
)
if _SELECTOR_DIR not in sys.path:
    sys.path.insert(0, _SELECTOR_DIR)

from data_source import StockDataSource

# 模块级单例，避免重复初始化
_data_source: Optional[StockDataSource] = None


def _get_data_source() -> StockDataSource:
    global _data_source
    if _data_source is None:
        _data_source = StockDataSource()
    return _data_source


def get_trade_dates(start: str, end: str) -> List[str]:
    """
    获取 [start, end] 区间内的所有交易日列表（升序）

    Args:
        start: 开始日期 YYYYMMDD（含）
        end:   结束日期 YYYYMMDD（含）

    Returns:
        List[str]: 交易日列表，格式 YYYYMMDD，升序
    """
    ds = _get_data_source()
    df = ds.api.call_with_retry(
        ds.api.pro.trade_cal,
        api_name="trade_cal",
        exchange='',
        start_date=start,
        end_date=end,
    )
    if df is None or df.empty:
        return []

    dates = df[df['is_open'] == 1]['cal_date'].tolist()
    dates.sort()
    return dates


def get_first_trade_date_on_or_after(date: str) -> str:
    """
    返回 date 当天或之后的第一个交易日

    Args:
        date: 日期 YYYYMMDD

    Returns:
        str: 交易日 YYYYMMDD
    """
    # 往后查询最多 10 天
    d = datetime.strptime(date, '%Y%m%d')
    end = (d + timedelta(days=14)).strftime('%Y%m%d')
    dates = get_trade_dates(date, end)
    if not dates:
        return date
    return dates[0]


def calc_rebalance_dates(first_day: str, interval: int, up_to: str) -> List[str]:
    """
    从 first_day 起，按 interval 个交易日的间隔，推算到 up_to 为止的所有调仓日。

    Args:
        first_day: 第一个调仓日（YYYYMMDD，若非交易日则向后顺延）
        interval:  调仓间隔（交易日数量）；0 表示每个交易日都调仓
        up_to:     截止日期 YYYYMMDD（含）

    Returns:
        List[str]: 调仓日列表（升序），每个元素均为交易日
    """
    # 确保 first_day 是交易日
    actual_first = get_first_trade_date_on_or_after(first_day)

    # 获取 [actual_first, up_to] 的全量交易日
    all_dates = get_trade_dates(actual_first, up_to)
    if not all_dates:
        return []

    if interval == 0:
        # 每个交易日调仓
        return all_dates

    # 按间隔取样：索引 0, interval+1, 2*(interval+1), ...
    step = interval + 1
    rebalance = [all_dates[i] for i in range(0, len(all_dates), step)]
    return rebalance


def find_prev_rebalance_date(rebalance_dates: List[str], target: str) -> Optional[str]:
    """
    在调仓日列表中找到 target 的上一个调仓日

    Args:
        rebalance_dates: 升序调仓日列表
        target: 目标调仓日 YYYYMMDD

    Returns:
        str | None: 上一个调仓日，若 target 为第一个调仓日则返回 None
    """
    try:
        idx = rebalance_dates.index(target)
    except ValueError:
        return None

    if idx == 0:
        return None
    return rebalance_dates[idx - 1]
