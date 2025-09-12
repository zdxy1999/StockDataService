import json
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Flask, request

from static.service.data_service import get_trade_day_info, get_special_stocks_of_a_day, get_last_trade_day_money_flow, \
    get_shibor_in_last_7_days, get_news_for_today, get_global_data_for_today, get_main_index_info_for_last_day, \
    get_main_index_info_for_today
from static.service.evaluation_service import get_all_main_index_pe_pb_position
from static.service.single_stock_service import get_stock_real_time_info, list_all_stock

app = Flask(__name__)


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'


def get_date_related_data(handler_func):
    """处理日期参数的装饰器"""

    @wraps(handler_func)
    def wrapper(*args, **kwargs):
        date = request.args.get('date')
        date_str = ''
        if date is None or date == 'null' or date == 'None':
            date_str = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d")
        else:
            date_str = date

        # 调用原始处理函数，并传递处理后的日期
        result = handler_func(date_str, *args, **kwargs)
        return json.dumps(result.__dict__, indent=2, ensure_ascii=False)

    return wrapper


@app.route('/tradeDayBasic')
@get_date_related_data
def trade_day_basic_info(date_str):
    """获取某一天的交易日基本信息（包含是否是交易日、上一个、下一个交易日）等

    Args:
        date_str: 以 YYYY-MM-DD 格式表示的日期字符串
    """
    return get_trade_day_info(date_str)


@app.route('/specialStocks')
@get_date_related_data
def special_stocks_info(date_str):
    return get_special_stocks_of_a_day(date_str)


@app.route('/lastDayMoneyFlow')
@get_date_related_data
def last_day_money_flow(date_str):
    return get_last_trade_day_money_flow(date_str)


@app.route('/interests')
@get_date_related_data
def get_interest_data(date_str):
    return get_shibor_in_last_7_days(date_str)


@app.route('/news')
@get_date_related_data
def get_news_data(date_str):
    return get_news_for_today(date_str)


@app.route('/global')
@get_date_related_data
def get_global_data(date_str):
    return get_global_data_for_today(date_str)


@app.route('/mainIndexPosition')
def get_main_index_pe_pb_position():
    return get_all_main_index_pe_pb_position()


@app.route('/mainIndexInfo/lastDay')
@get_date_related_data
def get_main_index_info_of_last_day(date_str: str):
    return get_main_index_info_for_last_day(date_str)


@app.route('/mainIndexInfo/today')
@get_date_related_data
def get_main_index_info_of_today(date_str: str):
    return get_main_index_info_for_today(date_str)

@app.route('/stock/list')
def get_all_stock_name_and_code():
    return list_all_stock()

@app.route('/stock/info')
def get_stock_info():
    date = request.args.get('date')
    code = request.args.get('code')
    date_str = ''
    if date is None or date == 'null' or date == 'None':
        date_str = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d")
    else:
        date_str = date

    result = get_stock_real_time_info(date_str, code)
    return json.dumps(result.__dict__, indent=2, ensure_ascii=False)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9090)
