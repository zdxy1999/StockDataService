from static.repo.tushare_adapter import get_main_index_pe_from_beginning, get_main_index_pb_from_beginning
from static.utils.cal_utils import cal_percentile

def get_main_index_pe_position(code:str):
    df = get_main_index_pe_from_beginning(code)
    return cal_percentile(df, 'pe')

def get_main_index_pb_position(code:str):
    df = get_main_index_pb_from_beginning(code)
    return cal_percentile(df, 'pb')

def get_all_main_index_pe_pb_position():
    codes = ['000001.SH','000300.SH','000905.SH','399001.SZ','399005.SZ','399006.SZ','399016.SZ']
    names = ['上证指数','沪深300指数','中证500指数','深证成指','中小100指数','创业板指数','深证创新指数']
    positions = []
    for i in range(len(codes)):
        print('processing {} {} position data'.format(codes[i], names[i]))
        positions.append({
            'code': codes[i],
            'name': names[i],
            'pe_percentile_position': float(get_main_index_pe_position(codes[i])),
            'pb_percentile_position': float(get_main_index_pb_position(codes[i]))
        })
    return positions

if __name__ == '__main__':
    print(get_all_main_index_pe_pb_position())