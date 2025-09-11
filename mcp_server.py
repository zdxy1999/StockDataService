import json
from datetime import datetime, timedelta, timezone
from functools import wraps

from static.service.data_service import get_trade_day_info, get_special_stocks_of_a_day, get_last_trade_day_money_flow, \
    get_shibor_in_last_7_days, get_news_for_today, get_global_data_for_today
from mcp.server.fastmcp import FastMCP

from static.service.evaluation_service import get_all_main_index_pe_pb_position

mcp = FastMCP("stock-data", port=7070, host='0.0.0.0')


def json_serialize(func):
    """JSON 序列化装饰器"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        # 如果结果是对象且有 __dict__ 属性，则序列化
        if hasattr(result, '__dict__'):
            return json.dumps(result.__dict__, indent=2, ensure_ascii=False)
        # 如果已经是字符串或字典，直接返回或序列化
        elif isinstance(result, dict):
            return json.dumps(result, indent=2, ensure_ascii=False)
        elif isinstance(result, str):
            return result
        else:
            # 其他类型尝试直接序列化
            return json.dumps(result, indent=2, ensure_ascii=False)

    return wrapper


@mcp.tool()
@json_serialize
def trade_day_basic_info(date_str):
    """获取某一天的交易日基本信息（包含是否是交易日、上一个、下一个交易日）等

    Args:
        date_str: 以 YYYY-MM-DD 格式表示的日期字符串
    """
    return get_trade_day_info(date_str)


@mcp.tool()
@json_serialize
def special_stocks_info(date_str):
    """获取某一天的特殊个股，新ipo上市的、以及停牌复牌的个股（其中停牌个股是从今天开始7日内的）

    Args:
        date_str: 以 YYYY-MM-DD 格式表示的今天日期字符串
    """
    return get_special_stocks_of_a_day(date_str)


@mcp.tool()
@json_serialize
def last_day_money_flow(date_str):
    """获取某一天前一天的资金流动情况

    Args:
        date_str: 以 YYYY-MM-DD 格式表示的今天日期字符串
    """
    return get_last_trade_day_money_flow(date_str)


@mcp.tool()
@json_serialize
def get_interest_data(date_str):
    """获取某一天前7天的利率变化情况

    Args:
        date_str: 以 YYYY-MM-DD 格式表示的今天日期字符串
    """
    return get_shibor_in_last_7_days(date_str)


@mcp.tool()
@json_serialize
def get_news_data(date_str):
    """获取从昨晚到今早的新闻内容

    Args:
        date_str: 以 YYYY-MM-DD 格式表示的今天日期字符串
    """
    return get_news_for_today(date_str)


@mcp.tool()
@json_serialize
def get_global_data(date_str):
    """获取今天的全球数据（如汇率等）

    Args:
        date_str: 以 YYYY-MM-DD 格式表示的今天日期字符串
    """
    return get_global_data_for_today(date_str)

@mcp.tool()
def get_main_index_pe_pb_position():
    """获得大盘主要指数的pe（市盈率）、pb（市净率）百分位点 (2004年以来)
    包含八个指数：
    codes = ['000001.SH','000300.SH','000905.SH','399001.SZ','399005.SZ','399006.SZ','399016.SZ]
    names = ['上证指数','沪深300指数','中证500指数','深证成指','中小100指数','创业板指数','深证创新指数']
    """
    return get_all_main_index_pe_pb_position()


if __name__ == '__main__':
    mcp.run(transport="sse")
