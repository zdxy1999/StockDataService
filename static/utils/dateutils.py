from datetime import datetime, timedelta

def parse_date(date_str, format="%Y-%m-%d"):
    """将字符串日期转换为 datetime 对象"""
    return datetime.strptime(date_str, format)

def is_same_year(date_str1, date_str2, date_format="%Y-%m-%d"):
    """判断两个日期是否在同一年"""
    date1 = parse_date(date_str1, date_format)
    date2 = parse_date(date_str2, date_format)
    return date1.year == date2.year

def is_same_month(date_str1, date_str2, date_format="%Y-%m-%d"):
    """判断两个日期是否在同一年同一月"""
    date1 = parse_date(date_str1, date_format)
    date2 = parse_date(date_str2, date_format)
    return date1.year == date2.year and date1.month == date2.month

def is_same_week(date_str1, date_str2, date_format="%Y-%m-%d"):
    """判断两个日期是否在同一周（周一开始）"""
    date1 = parse_date(date_str1, date_format)
    date2 = parse_date(date_str2, date_format)

    # 计算每个日期所在周的周一
    monday1 = date1 - timedelta(days=date1.weekday())
    monday2 = date2 - timedelta(days=date2.weekday())

    return monday1 == monday2