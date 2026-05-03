import functools
from typing import Any

import tushare as ts
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

# 使用tushare替代baostock，因为baostock API经常连接失败
token = "15bb21f848e2844fee6046746341f03079d4911b96fc80f1a48ee8da"


def get_trade_date_from_akshare(date_str: str, length: int = 7) -> dict[str, list[str]]:
    """
    使用akshare获取交易日历（备用方案，当tushare数据不可用时）

    :param date_str: 日期 YYYY-MM-DD
    :param length: 获取的交易日数量
    :return: {'last': [...], 'next': [...]}
    """
    result = {'last': [], 'next': []}

    try:
        # akshare的交易日历接口
        target_date = datetime.strptime(date_str, '%Y-%m-%d')

        # 获取目标日期前后的交易日历数据（获取更大范围以确保有足够数据）
        start_date = (target_date - timedelta(days=365)).strftime('%Y%m%d')
        end_date = (target_date + timedelta(days=365)).strftime('%Y%m%d')

        # 使用akshare获取沪深交易日历
        df = ak.tool_trade_date_hist_sina()

        if df is not None and not df.empty:
            # akshare返回的trade_date字段包含所有交易日
            all_trade_dates = df['trade_date'].tolist()

            # 转换为标准格式，处理可能的异常日期格式
            all_trade_dates_formatted = []
            for d in all_trade_dates:
                try:
                    # 处理可能的多种日期格式
                    d_clean = str(d).strip()
                    if len(d_clean) == 8:  # YYYYMMDD格式
                        formatted_date = datetime.strptime(d_clean, '%Y%m%d').strftime('%Y-%m-%d')
                    elif '-' in d_clean:  # YYYY-MM-DD格式
                        formatted_date = datetime.strptime(d_clean, '%Y-%m-%d').strftime('%Y-%m-%d')
                    else:
                        print(f"WARNING: Unknown date format: {d_clean}")
                        continue
                    all_trade_dates_formatted.append(formatted_date)
                except Exception as e:
                    print(f"WARNING: Failed to parse date {d}: {e}")
                    continue

            # 找到目标日期在交易日列表中的位置
            target_index = None
            for i, trade_date in enumerate(all_trade_dates_formatted):
                if trade_date >= date_str:
                    target_index = i
                    break

            if target_index is not None:
                # 获取之后的交易日
                result['next'] = all_trade_dates_formatted[target_index:target_index + length]

                # 获取之前的交易日
                start_index = max(0, target_index - length)
                result['last'] = all_trade_dates_formatted[start_index:target_index]

                print(f"DEBUG: akshare found {len(result['next'])} next dates, {len(result['last'])} last dates")
            else:
                print(f"WARNING: akshare could not find dates after {date_str}")

    except Exception as e:
        print(f"Error fetching trade dates from akshare: {e}")

    return result


def get_trade_date(date_str: str = datetime.now().strftime("%Y-%m-%d"), length: int = 7) -> dict[str, list[str]]:
    """
    获取从 start_date_str 开始/结束 的 length 个交易日，
    以 一个字典 返回
        其中
        'last' 是一个 '%Y-%m-%d' 形式的str数组，表示过去的 length个交易日 (若date_str是则包含)
        'next' 是一个 '%Y-%m-%d' 形式的str数组，表示过去的 length个交易日 (若date_str是则包含)

    :param date_str: 开始/结束 的日期，格式 YYYY-MM-DD
    :param length:  长度
    """
    max_length = 100

    if length <= 0:
        return {'last': [], 'next': []}
    if length > max_length:
        raise ValueError('length could not exceed max: {}, required: {}'.format(max_length, length))

    result: dict[str, list[str]] = {'last': [], 'next': []}

    # 初始化tushare API
    pro_api = ts.pro_api(token)

    # 转换日期格式 YYYY-MM-DD -> YYYYMMDD
    target_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y%m%d')

    # 查找之后的数据
    next_end_date = (datetime.strptime(date_str, '%Y-%m-%d') + timedelta(days=max_length)).strftime('%Y%m%d')
    tushare_success = True

    try:
        # 使用SSE（上交所）参数，避免空exchange导致的数据问题
        df_next = pro_api.trade_cal(exchange='SSE', start_date=target_date, end_date=next_end_date)
        print(f"DEBUG: df_next for {target_date} to {next_end_date}: {len(df_next)} rows")

        if df_next.empty:
            print(f"WARNING: tushare returned empty data for {target_date} to {next_end_date}")
            tushare_success = False
        else:
            # 筛选交易日并转换格式回 YYYY-MM-DD
            trade_dates_next = df_next[df_next['is_open'] == 1]['cal_date'].tolist()
            trade_dates_next_formatted = [datetime.strptime(d, '%Y%m%d').strftime('%Y-%m-%d') for d in trade_dates_next]
            result['next'] = trade_dates_next_formatted[:length]
            print(f"DEBUG: next trade dates from tushare: {result['next']}")

            # 检查返回的数据是否合理（如果没有返回预期的长度，可能是数据不完整）
            if len(result['next']) == 0 or (len(result['next']) < length and target_date not in trade_dates_next):
                print(f"WARNING: tushare data seems incomplete, only got {len(result['next'])} dates")
                tushare_success = False

            # 检查返回的日期是否合理（不应该出现跳跃巨大的情况）
            if len(result['next']) > 0:
                first_next_date = result['next'][0]
                try:
                    days_diff = (datetime.strptime(first_next_date, '%Y-%m-%d') -
                                 datetime.strptime(date_str, '%Y-%m-%d')).days
                    if abs(days_diff) > 10:  # 如果下一个交易日距离超过10天，可能数据有问题
                        print(f"WARNING: tushare returned suspicious next date: {first_next_date}, diff: {days_diff} days")
                        tushare_success = False
                except Exception as e:
                    print(f"ERROR: Failed to parse date: {e}")
                    tushare_success = False

    except Exception as e:
        print(f"Error fetching next trade dates from tushare: {e}")
        tushare_success = False

    # 查找之前的数据
    last_start_date = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=max_length)).strftime('%Y%m%d')
    try:
        # 使用SSE（上交所）参数，避免空exchange导致的数据问题
        df_last = pro_api.trade_cal(exchange='SSE', start_date=last_start_date, end_date=target_date)
        print(f"DEBUG: df_last for {last_start_date} to {target_date}: {len(df_last)} rows")

        if df_last.empty:
            print(f"WARNING: tushare returned empty data for {last_start_date} to {target_date}")
            tushare_success = False
        else:
            # 筛选交易日并转换格式回 YYYY-MM-DD
            trade_dates_last = df_last[df_last['is_open'] == 1]['cal_date'].tolist()
            trade_dates_last_formatted = [datetime.strptime(d, '%Y%m%d').strftime('%Y-%m-%d') for d in trade_dates_last]
            result['last'] = trade_dates_last_formatted[-length:]
            print(f"DEBUG: last trade dates from tushare: {result['last']}")

            # 检查返回的数据是否合理
            if len(result['last']) == 0:
                print(f"WARNING: tushare last data seems incomplete")
                tushare_success = False

    except Exception as e:
        print(f"Error fetching last trade dates from tushare: {e}")
        tushare_success = False

    # 如果tushare失败或数据不完整，使用akshare作为备用
    if not tushare_success or len(result['next']) == 0 or len(result['last']) == 0:
        print("INFO: tushare data unavailable or incomplete, trying akshare...")
        result = get_trade_date_from_akshare(date_str, length)

    return result


if __name__ == '__main__':
    print(get_trade_date())
