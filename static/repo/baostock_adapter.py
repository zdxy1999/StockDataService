import functools
from typing import Any

import baostock as bs
import pandas as pd
from datetime import datetime, timedelta


class BaoStockApiCallDecorator:
    def __init__(self, func):
        self.func = func
        functools.update_wrapper(self, func)

    def __call__(self, *args, **kwargs) -> Any:
        print(f"decorator: running {self.func.__name__}")
        lg = bs.login()
        if lg.error_code != '0':
            print('baostock login error')
            print('login respond error_code:' + lg.error_code)
            print('login respond error_msg:' + lg.error_msg)
        else:
            print('baostock login success')

        res = self.func(*args, **kwargs)

        bs.logout()

        return res

    @staticmethod
    def __getdata__(resp):
        if resp.error_code and resp.error_code != '0':
            print("baostock api call error, error code {} error_msg".format(
                resp.error_code, resp.error_msg
            ))
        return resp.fields, resp.data


@BaoStockApiCallDecorator
def get_trade_date(date_str: str = datetime.now().strftime("%Y-%m-%d"), length: int = 7) -> dict[str,list[str]]:
    """
    获取从 start_date_str 开始/结束 的 length 个交易日，
    以 一个字典 返回
        其中
        'last' 是一个 '%Y-%m-%d' 形式的str数组，表示过去的 length个交易日 (若date_str是则包含)
        'next' 是一个 '%Y-%m-%d' 形式的str数组，表示过去的 length个交易日 (若date_str是则包含)

    :param date_str: 开始/结束 的日期
    :param length:  长度
    """
    max_length = 100

    if length <= 0:
        return list()
    if length > max_length:
        raise ValueError('length could not exceed max: {}, required: {}'.format(max_length, length))

    result: dict[str, list[str]] = dict()
    # 查找之后的数据
    next_start_date = datetime.strptime(date_str, '%Y-%m-%d')
    next_end_date = next_start_date + timedelta(days=max_length)
    resp = bs.query_trade_dates(start_date=date_str, end_date=next_end_date.strftime("%Y-%m-%d"))
    if resp.error_code != '0':
        print('baostock api call error:' + resp.error_msg)

    fields, data = BaoStockApiCallDecorator.__getdata__(resp)

    result['next'] = [item[0] for item in data if item[1] == '1'][:length]

    # 查找之前的数据
    last_end_date = datetime.strptime(date_str, '%Y-%m-%d')
    last_start_date = last_end_date + timedelta(days=-max_length)
    resp = bs.query_trade_dates(start_date=last_start_date, end_date=last_end_date.strftime("%Y-%m-%d"))
    fields, data = BaoStockApiCallDecorator.__getdata__(resp)
    result['last'] = [item[0] for item in data if item[1] == '1'][-length:]
    return result


if __name__ == '__main__':
    print(get_trade_date())
