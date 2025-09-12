import concurrent.futures

from static.repo.tushare_adapter import get_main_index_pe_from_beginning, get_main_index_pb_from_beginning
from static.utils.cal_utils import cal_percentile

def get_main_index_pe_position(code:str):
    df = get_main_index_pe_from_beginning(code)
    return cal_percentile(df, 'pe')

def get_main_index_pb_position(code:str):
    df = get_main_index_pb_from_beginning(code)
    return cal_percentile(df, 'pb')


def get_all_main_index_pe_pb_position():
    codes = ['000001.SH', '000300.SH', '000905.SH', '399001.SZ', '399005.SZ', '399006.SZ', '399016.SZ']
    names = ['上证指数', '沪深300指数', '中证500指数', '深证成指', '中小100指数', '创业板指数', '深证创新指数']
    positions = []

    # 并发处理各个指数的查询与处理
    def process_index(code, name):
        print(f'processing {code} {name} position data')
        pe_position = float(get_main_index_pe_position(code))
        pb_position = float(get_main_index_pb_position(code))
        return {
            'code': code,
            'name': name,
            'pe_percentile_position': pe_position,
            'pb_percentile_position': pb_position
        }

    # 使用线程池并发处理
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # 提交所有任务
        future_to_index = {
            executor.submit(process_index, code, name): (code, name)
            for code, name in zip(codes, names)
        }

        # 收集结果
        for future in concurrent.futures.as_completed(future_to_index):
            try:
                result = future.result()
                positions.append(result)
            except Exception as e:
                code, name = future_to_index[future]
                print(f'Error processing {code} {name}: {e}')

    return positions

# todo: 大盘指数当前点位

if __name__ == '__main__':
    print(get_all_main_index_pe_pb_position())