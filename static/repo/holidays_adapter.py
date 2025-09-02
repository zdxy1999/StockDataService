from datetime import datetime, timedelta

import requests

class HolidayInfo:
    name: str
    date: str
    isOffDay: bool

# 缓存
holiday_info_list_cache: list[HolidayInfo] = []

def get_holiday_info_list(year:str) -> list[HolidayInfo]:
    if year in holiday_info_list_cache:
        return holiday_info_list_cache

    url = "https://holiday.cyi.me/api/holidays?year={}".format(year)
    response = requests.get(url)
    holiday_info_list = response.json()["days"]
    holiday_info_list_cache.append(holiday_info_list)
    return holiday_info_list

def get_holiday_info(date_str: str) -> HolidayInfo:
    holiday_info_list = get_holiday_info_list(date_str[:4])
    return next(filter(lambda x: x["date"] == date_str, holiday_info_list), None)

def get_upcoming_holiday_info(date_str: str = datetime.now().strftime("%Y-%m-%d")) -> HolidayInfo:
    """
    获取七日内的节假日
    """
    date_after_7_days = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")
    holiday_info_list = get_holiday_info_list(date_str[:4])
    return next(filter(lambda x: date_str < x["date"] <= date_after_7_days and x["isOffDay"], holiday_info_list), None)

def is_reschedule_working_day(date_str: str) -> bool:
    """
    是否是调休工作日
    """
    holiday_info = get_holiday_info(date_str)
    return holiday_info is not None and not holiday_info["isOffDay"]

if __name__ == '__main__':
    print(get_holiday_info("2025-09-27"))
    print(get_upcoming_holiday_info("2025-09-27"))