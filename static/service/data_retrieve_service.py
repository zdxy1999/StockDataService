from datetime import datetime
from enum import Enum

from static.service.baostock_adapter import get_trade_date
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
    last_trade_date: str
    next_trade_date: str

    special_trade_day_tag: list[str]
    upcoming_events: list[str]




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
    # todo: 获取交易日信息
    return None
