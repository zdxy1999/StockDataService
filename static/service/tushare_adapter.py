import tushare as ts
import akshare as ak


token = "15bb21f848e2844fee6046746341f03079d4911b96fc80f1a48ee8da"

if __name__ == '__main__':

    # ts.set_token(token)
    # pro = ts.pro_api()
    #
    # # 提取沪深300指数2018年9月成分和权重
    # df = pro.index_weight(index_code='399300.SZ', start_date='20250801', end_date='20250831')
    # print(df)

    index_stock_cons_df = ak.index_stock_cons(symbol="000001")
    print(index_stock_cons_df)