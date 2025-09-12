import concurrent.futures

from static.repo.tushare_adapter import get_main_index_pe_from_beginning, get_main_index_pb_from_beginning, \
    get_stock_basic_info, get_stock_basic_index_in_30_days, get_share_float_in_30_days, \
    get_repurchase_data_in_last_and_after_1_year, get_stock_all_pe_pb, get_all_stocks_name_and_code
from static.utils.cal_utils import cal_percentile


def list_all_stock():
    return get_all_stocks_name_and_code()


def get_stock_real_time_info(date_str: str, code: str):
    stock_basic_info = get_stock_basic_info(code)
    stock_index_in_30_days = get_stock_basic_index_in_30_days(date_str, code)
    share_float_in_30_days = get_share_float_in_30_days(date_str, code)
    repurchase_data = get_repurchase_data_in_last_and_after_1_year(date_str, code)
    pepb_df = get_stock_all_pe_pb(code)

    pe_percentile = cal_percentile(pepb_df, 'pe')
    pb_percentile = cal_percentile(pepb_df, 'pb')

    return {
        '股票基本信息': stock_basic_info.get_dict(),
        '30日内基本指标数据': stock_index_in_30_days.get_dict(),
        '30日内限售股票解禁数据': share_float_in_30_days.get_dict(),
        '1年内回购数据': repurchase_data.get_dict(),
        'pe 百分位点': float(pe_percentile),
        'pb 百分位点': float(pb_percentile)
    }


if __name__ == '__main__':
    print(get_stock_real_time_info('2025-09-12', '000002.SZ'))
