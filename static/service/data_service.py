import json
from datetime import datetime
from enum import Enum
from typing import Any

from static.repo.baostock_adapter import get_trade_date
from static.repo.holidays_adapter import HolidayInfo, get_upcoming_holiday_info, is_reschedule_working_day
from static.repo.tushare_adapter import DfWithColumnDesc, get_ipo_stocks_of_a_day, get_suspend_stocks_of_a_day, \
    get_resume_stocks_of_a_day, get_mkt_dc_money_flow, get_ind_money_flow, get_money_flow_hsgt, \
    get_shibor_in_last_7_day, get_shibor_quota, get_short_news_in_2_days, get_cctv_news, get_fx_in_last_7_days
from static.utils.dateutils import is_same_year, is_same_month, is_same_week


class SpecialTradeDay(Enum):
    WEEK_LAST = 1
    WEEK_FIRST = 2
    MONTH_LAST = 3
    MONTH_FIRST = 4
    YEAR_LAST = 5
    YEAR_FIRST = 6


class TradeDayInfo:
    today_str: str
    is_trade_day: bool
    is_rescheduled_working_day: bool
    last_trade_date: str
    next_trade_date: str

    special_trade_day_tag: list[str]
    upcoming_holiday: HolidayInfo

    mkt_data: list[dict]

    def __init__(self) -> None:
        self.mkt_data = []


class DataObj:
    data: Any

    def __init__(self, data) -> None:
        self.data = data


# 存储上一个交易日，防止过多的接口调用
# key 为日期a，value为日期a的上一个交易日
last_trade_day_cache: dict[str, str] = {}


def get_last_trade_day_in_cache(date_str: str) -> str | None:
    if date_str in last_trade_day_cache:
        return last_trade_day_cache[date_str]
    else:
        return None


def set_last_trade_day_in_cache(date_str: str, last_trade_day: str) -> None:
    last_trade_day_cache.clear()
    last_trade_day_cache[date_str] = last_trade_day


def get_last_trade_day(date_str: str) -> str:
    if date_str in last_trade_day_cache:
        return last_trade_day_cache[date_str]
    else:
        last_trade_day = get_next_and_last_trade_date(date_str)['last']
        set_last_trade_day_in_cache(date_str, last_trade_day)
        return last_trade_day


def is_date_trade_day(date_str: str = datetime.now().strftime("%Y-%m-%d")) -> bool:
    next_trade_day_list = get_trade_date(date_str=date_str, length=1)['next']
    if next_trade_day_list is not None and len(next_trade_day_list) > 0:
        return next_trade_day_list[0] == date_str
    else:
        raise RuntimeError("latest 1 trade date should not be none")


def get_next_and_last_trade_date(date_str: str = datetime.now().strftime("%Y-%m-%d")) -> dict[str, str]:
    trade_day_dict = get_trade_date(date_str=date_str, length=2)
    last_trade_day_list = trade_day_dict['last']
    next_trade_day_list = trade_day_dict['next']

    return {
        'next': next_trade_day_list[1] if next_trade_day_list[0] == date_str else next_trade_day_list[0],
        'last': last_trade_day_list[-2] if last_trade_day_list[-1] == date_str else last_trade_day_list[-1]
    }


def tag_special_trade_day_without_next_or_last(date_str: str = datetime.now().strftime("%Y-%m-%d")) -> list[str]:
    next_last_trade_dict = get_next_and_last_trade_date(date_str=date_str)
    last_trade_day = next_last_trade_dict['last']
    next_trade_day = next_last_trade_dict['next']
    return tag_special_trade_day_with_next_and_last(date_str, next_trade_day, last_trade_day)


def tag_special_trade_day_with_next_and_last(date_str, next_trade_day, last_trade_day) -> list[str]:
    res: list[str] = []

    if not is_same_year(last_trade_day, date_str):
        res.append(SpecialTradeDay.YEAR_FIRST.name)

    if not is_same_year(date_str, next_trade_day):
        res.append(SpecialTradeDay.YEAR_LAST.name)

    if not is_same_month(last_trade_day, date_str):
        res.append(SpecialTradeDay.MONTH_FIRST.name)

    if not is_same_month(date_str, next_trade_day):
        res.append(SpecialTradeDay.MONTH_LAST.name)

    if not is_same_week(last_trade_day, date_str):
        res.append(SpecialTradeDay.WEEK_FIRST.name)

    if not is_same_week(date_str, next_trade_day):
        res.append(SpecialTradeDay.WEEK_LAST.name)

    return res


def get_trade_day_info(date_str: str = datetime.now().strftime("%Y-%m-%d")) -> TradeDayInfo:
    res = TradeDayInfo()

    # 获取交易日信息
    res.today_str = date_str
    res.is_trade_day = is_date_trade_day(date_str)
    res.is_rescheduled_working_day = is_reschedule_working_day(date_str)
    trade_date_last_next = get_next_and_last_trade_date(date_str)
    last_trade_day = trade_date_last_next['last']
    next_trade_day = trade_date_last_next['next']
    res.last_trade_date, res.next_trade_date = last_trade_day, next_trade_day

    # 获取特殊交易日标签
    if res.is_trade_day:
        res.special_trade_day_tag = tag_special_trade_day_with_next_and_last(date_str, res.next_trade_date,
                                                                             res.last_trade_date)

    # 获取即将到来的节假日
    res.upcoming_holiday = get_upcoming_holiday_info(date_str)
    return res


def get_special_stocks_of_a_day(date_str: str = datetime.now().strftime("%Y-%m-%d")) -> DataObj:
    res = []
    data = get_ipo_stocks_of_a_day(date_str)
    res.append(data.get_dict() if data is not None else None)
    data = get_suspend_stocks_of_a_day(date_str)
    res.append(data.get_dict() if data is not None else None)
    data = get_resume_stocks_of_a_day(date_str)
    res.append(data.get_dict() if data is not None else None)

    return DataObj(res)


def get_last_trade_day_money_flow(date_str: str = datetime.now().strftime("%Y-%m-%d")) -> DataObj:
    last_trade_day = get_last_trade_day(date_str)
    data = get_mkt_dc_money_flow(last_trade_day)

    res = []
    res.append(data.get_dict() if data is not None else None)
    data = get_ind_money_flow(last_trade_day)
    res.append(data.get_dict() if data is not None else None)
    data = get_money_flow_hsgt(last_trade_day)
    res.append(data.get_dict() if data is not None else None)

    return DataObj(res)


def get_shibor_in_last_7_days(date_str: str = datetime.now().strftime("%Y-%m-%d")) -> dict:
    return get_shibor_in_last_7_day(date_str).get_dict()


def get_news_for_today(date_str: str = datetime.now().strftime("%Y-%m-%d")) -> DataObj:
    res = []
    data = get_short_news_in_2_days(date_str)
    res.append(data.get_dict() if data is not None else None)

    data = get_cctv_news(get_last_trade_day(date_str))
    res.append(data.get_dict() if data is not None else None)
    return DataObj(res)


def get_global_data_for_today(date_str: str) -> DataObj:
    res = []
    data = get_fx_in_last_7_days(date_str)
    res.append(data.get_dict() if data is not None else None)
    return DataObj(res)


if __name__ == '__main__':
    print(json.dumps(get_special_stocks_of_a_day("2025-09-11").__dict__, indent=2, ensure_ascii=False))
