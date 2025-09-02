from datetime import datetime, timedelta

import pandas as pd
import tushare as ts

token = "15bb21f848e2844fee6046746341f03079d4911b96fc80f1a48ee8da"

class DfWithColumnDesc:
    df : pd.DataFrame
    desc : str
    column_desc : list[dict]

    def __init__(self, df: pd.DataFrame, desc: str, column_desc: list[dict]):
        self.df = df
        self.desc = desc
        self.column_desc = column_desc

    def get_dict(self):
        return {
            "df": self.df.to_dict(orient='records'),
            "desc": self.desc,
            "column_desc": self.column_desc
        }
def adapt_date_str(date_str: str) -> str:
    return date_str.replace("-", "")
def get_pro():
    ts.set_token(token)
    pro = ts.pro_api()
    return pro

def parse_column_desc_to_dict(input_string) -> list[dict]:
    # 分割字符串为行
    lines = input_string.strip().split('\n')

    # 使用列表推导式处理每一行
    result = [
        {
            "字段名称": parts[0],
            "字段类型": parts[1],
            "是否默认显示": parts[2],
            "字段描述": ' '.join(parts[3:])
        }
        for line in lines
        if (parts := line.split()) and len(parts) >= 4
    ]

    return result

##================== basic =================
# 查询所有个股的信息



##================== 当日特殊个股动态 =================
def get_ipo_stocks_of_a_day(date_str: str = datetime.now().strftime("%Y%m%d")) -> DfWithColumnDesc:
    """
    获取某一日 ipo 的新股数据
    """
    pro = get_pro()
    df = pro.new_share(start_date=adapt_date_str(date_str), end_date=adapt_date_str(date_str))
    desc = "当日ipo新股数据"
    column_desc = """
    ts_code	str	Y	TS股票代码
    sub_code	str	Y	申购代码
    name	str	Y	名称
    ipo_date	str	Y	上网发行日期
    issue_date	str	Y	上市日期
    amount	float	Y	发行总量（万股）
    market_amount	float	Y	上网发行总量（万股）
    price	float	Y	发行价格
    pe	float	Y	市盈率
    limit_amount	float	Y	个人申购上限（万股）
    funds	float	Y	募集资金（亿元）
    ballot	float	Y	中签率
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))

#
def get_suspend_stocks_of_a_day(date_str: str = datetime.now().strftime("%Y%m%d")) -> DfWithColumnDesc:
    """
    获取某一日 往后七日内的停牌股票
    """
    date_str = adapt_date_str(date_str)
    date_after_7_days = (datetime.strptime(date_str, "%Y%m%d") + timedelta(days=7)).strftime("%Y%m%d")
    pro = get_pro()
    df = pro.suspend_d(suspend_type='S', start_date=date_str, end_date=date_after_7_days)
    desc = "当日内与往后七日内的停牌股票"
    column_desc = """
    ts_code	str	Y	TS代码
    trade_date	str	Y	停复牌日期
    suspend_timing	str	Y	日内停牌时间段
    suspend_type	str	Y	停复牌类型：S-停牌，R-复牌
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))

def get_resume_stocks_of_a_day(date_str: str = datetime.now().strftime("%Y%m%d")) -> DfWithColumnDesc:
    """
    获取某一日 的复牌股票
    """
    date_str = adapt_date_str(date_str)
    pro = get_pro()
    df = pro.suspend_d(suspend_type='R', trade_date=date_str)
    desc = "当日复牌股票"
    column_desc = """
    ts_code	str	Y	TS代码
    trade_date	str	Y	停复牌日期
    suspend_timing	str	Y	日内停牌时间段
    suspend_type	str	Y	停复牌类型：S-停牌，R-复牌
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))


##================== 资金流向 =================
def get_money_flow_hsgt(date_str: str = datetime.now().strftime("%Y%m%d")) -> DfWithColumnDesc:
    """
    获取某一日 及其之前7天的 沪深港通资金流向
    """
    date_str  = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=-1)).strftime("%Y-%m-%d")
    date_before_7_days = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=-7)).strftime("%Y-%m-%d")
    pro = get_pro()
    df = pro.moneyflow_hsgt(start_date=adapt_date_str(date_before_7_days), end_date=adapt_date_str(date_str))
    desc = "沪深港通资金流向"
    column_desc = """
    trade_date	str	交易日期
    ggt_ss	float	港股通（上海）
    ggt_sz	float	港股通（深圳）
    hgt	float	沪股通（百万元）
    sgt	float	深股通（百万元）
    north_money	float	北向资金（百万元）
    south_money	float	南向资金（百万元）
    """
    return DfWithColumnDesc(df,desc, parse_column_desc_to_dict(column_desc))

def get_money_flow(date_str: str = datetime.now().strftime("%Y%m%d")):
    date_str = adapt_date_str(date_str)
    pro = get_pro()
    df = pro.moneyflow(trade_date=date_str)
    desc = "个股资金流向"
    column_desc = """
    ts_code	str	Y	TS代码
    trade_date	str	Y	交易日期
    buy_sm_vol	int	Y	小单买入量（手）
    buy_sm_amount	float	Y	小单买入金额（万元）
    sell_sm_vol	int	Y	小单卖出量（手）
    sell_sm_amount	float	Y	小单卖出金额（万元）
    buy_md_vol	int	Y	中单买入量（手）
    buy_md_amount	float	Y	中单买入金额（万元）
    sell_md_vol	int	Y	中单卖出量（手）
    sell_md_amount	float	Y	中单卖出金额（万元）
    buy_lg_vol	int	Y	大单买入量（手）
    buy_lg_amount	float	Y	大单买入金额（万元）
    sell_lg_vol	int	Y	大单卖出量（手）
    sell_lg_amount	float	Y	大单卖出金额（万元）
    buy_elg_vol	int	Y	特大单买入量（手）
    buy_elg_amount	float	Y	特大单买入金额（万元）
    sell_elg_vol	int	Y	特大单卖出量（手）
    sell_elg_amount	float	Y	特大单卖出金额（万元）
    net_mf_vol	int	Y	净流入量（手）
    net_mf_amount	float	Y	净流入额（万元）
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))

def get_ind_money_flow(date_str: str = datetime.now().strftime("%Y%m%d")) -> DfWithColumnDesc | None:
    """
    获取某一日的行业资金流向
    """
    date_str = adapt_date_str(date_str)
    pro = get_pro()
    df = ''
    try :
        df = pro.moneyflow_ind(trade_date=date_str)
    except:
        print("get_ind_money_flow error")
        return None
    desc = "行业资金流向"
    column_desc = """
    trade_date	str	Y	交易日期
    ts_code	str	Y	板块代码
    industry	str	Y	板块名称
    lead_stock	str	Y	领涨股票名称
    close	float	Y	收盘指数
    pct_change	float	Y	指数涨跌幅
    company_num	int	Y	公司数量
    pct_change_stock	float	Y	领涨股涨跌幅
    close_price	float	Y	领涨股最新价
    net_buy_amount	float	Y	流入资金(亿元)
    net_sell_amount	float	Y	流出资金(亿元)
    net_amount	float	Y	净额(元)
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))

def get_mkt_dc_money_flow(date_str: str = datetime.now().strftime("%Y%m%d")) -> DfWithColumnDesc | None:
    """
    获取某一日 大盘资金流向
    """
    date_str = adapt_date_str(date_str)
    pro = get_pro()
    df = ''
    try :
        df = pro.moneyflow_mkt_dc(start_date=date_str, end_date=date_str)
    except:
        print("get_mkt_dc_money_flow error")
        return None
    desc = "大盘资金流向"
    column_desc = """
    trade_date	str	Y	交易日期
    close_sh	float	Y	上证收盘价（点）
    pct_change_sh	float	Y	上证涨跌幅(%)
    close_sz	float	Y	深证收盘价（点）
    pct_change_sz	float	Y	深证涨跌幅(%)
    net_amount	float	Y	今日主力净流入 净额（元）
    net_amount_rate	float	Y	今日主力净流入净占比%
    buy_elg_amount	float	Y	今日超大单净流入 净额（元）
    buy_elg_amount_rate	float	Y	今日超大单净流入 净占比%
    buy_lg_amount	float	Y	今日大单净流入 净额（元）
    buy_lg_amount_rate	float	Y	今日大单净流入 净占比%
    buy_md_amount	float	Y	今日中单净流入 净额（元）
    buy_md_amount_rate	float	Y	今日中单净流入 净占比%
    buy_sm_amount	float	Y	今日小单净流入 净额（元）
    buy_sm_amount_rate	float	Y	今日小单净流入 净占比%
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))


##================== 宏观数据（非日频） =================
def get_cpi_in_this_year(year_str: str = datetime.now().strftime("%Y")) -> DfWithColumnDesc:
    """
    年内 cpi 数据
    """
    pro = get_pro()
    df = pro.cn_cpi(start_m=year_str+"01", end_m=year_str+"12")
    desc = "年内 cpi 数据"
    column_desc = """
    month	str	Y	月份YYYYMM
    nt_val	float	Y	全国当月值
    nt_yoy	float	Y	全国同比（%）
    nt_mom	float	Y	全国环比（%）
    nt_accu	float	Y	全国累计值
    town_val	float	Y	城市当月值
    town_yoy	float	Y	城市同比（%）
    town_mom	float	Y	城市环比（%）
    town_accu	float	Y	城市累计值
    cnt_val	float	Y	农村当月值
    cnt_yoy	float	Y	农村同比（%）
    cnt_mom	float	Y	农村环比（%）
    cnt_accu	float	Y	农村累计值
    """

    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))

def get_ppi_in_this_year(year_str: str = datetime.now().strftime("%Y")) -> DfWithColumnDesc:
    """
    获取年内 cpi 数据
    """
    pro = get_pro()
    df = pro.cn_ppi(start_m=year_str+"01", end_m=year_str+"12")
    desc = "年内 ppi 数据"
    column_desc = """
    month	str	Y	月份YYYYMM
    ppi_yoy	float	Y	PPI：全部工业品：当月同比
    ppi_mp_yoy	float	Y	PPI：生产资料：当月同比
    ppi_mp_qm_yoy	float	Y	PPI：生产资料：采掘业：当月同比
    ppi_mp_rm_yoy	float	Y	PPI：生产资料：原料业：当月同比
    ppi_mp_p_yoy	float	Y	PPI：生产资料：加工业：当月同比
    ppi_cg_yoy	float	Y	PPI：生活资料：当月同比
    ppi_cg_f_yoy	float	Y	PPI：生活资料：食品类：当月同比
    ppi_cg_c_yoy	float	Y	PPI：生活资料：衣着类：当月同比
    ppi_cg_adu_yoy	float	Y	PPI：生活资料：一般日用品类：当月同比
    ppi_cg_dcg_yoy	float	Y	PPI：生活资料：耐用消费品类：当月同比
    ppi_mom	float	Y	PPI：全部工业品：环比
    ppi_mp_mom	float	Y	PPI：生产资料：环比
    ppi_mp_qm_mom	float	Y	PPI：生产资料：采掘业：环比
    ppi_mp_rm_mom	float	Y	PPI：生产资料：原料业：环比
    ppi_mp_p_mom	float	Y	PPI：生产资料：加工业：环比
    ppi_cg_mom	float	Y	PPI：生活资料：环比
    ppi_cg_f_mom	float	Y	PPI：生活资料：食品类：环比
    ppi_cg_c_mom	float	Y	PPI：生活资料：衣着类：环比
    ppi_cg_adu_mom	float	Y	PPI：生活资料：一般日用品类：环比
    ppi_cg_dcg_mom	float	Y	PPI：生活资料：耐用消费品类：环比
    ppi_accu	float	Y	PPI：全部工业品：累计同比
    ppi_mp_accu	float	Y	PPI：生产资料：累计同比
    ppi_mp_qm_accu	float	Y	PPI：生产资料：采掘业：累计同比
    ppi_mp_rm_accu	float	Y	PPI：生产资料：原料业：累计同比
    ppi_mp_p_accu	float	Y	PPI：生产资料：加工业：累计同比
    ppi_cg_accu	float	Y	PPI：生活资料：累计同比
    ppi_cg_f_accu	float	Y	PPI：生活资料：食品类：累计同比
    ppi_cg_c_accu	float	Y	PPI：生活资料：衣着类：累计同比
    ppi_cg_adu_accu	float	Y	PPI：生活资料：一般日用品类：累计同比
    ppi_cg_dcg_accu	float	Y	PPI：生活资料：耐用消费品类：累计同比
    """

    return DfWithColumnDesc(df, column_desc)

def get_pmi_in_this_year(year_str: str = datetime.now().strftime("%Y")) -> DfWithColumnDesc:
    """
    获取年内的pmi数据
    """
    pro = get_pro()
    df = pro.cn_pmi(start_m=year_str+"01", end_m=year_str+"12")
    desc = "年内 pmi 数据"
    column_desc = """
    month	str	N	月份YYYYMM
    pmi010000	float	N	制造业PMI
    pmi010100	float	N	制造业PMI:企业规模/大型企业
    pmi010200	float	N	制造业PMI:企业规模/中型企业
    pmi010300	float	N	制造业PMI:企业规模/小型企业
    pmi010400	float	N	制造业PMI:构成指数/生产指数
    pmi010401	float	N	制造业PMI:构成指数/生产指数:企业规模/大型企业
    pmi010402	float	N	制造业PMI:构成指数/生产指数:企业规模/中型企业
    pmi010403	float	N	制造业PMI:构成指数/生产指数:企业规模/小型企业
    pmi010500	float	N	制造业PMI:构成指数/新订单指数
    pmi010501	float	N	制造业PMI:构成指数/新订单指数:企业规模/大型企业
    pmi010502	float	N	制造业PMI:构成指数/新订单指数:企业规模/中型企业
    pmi010503	float	N	制造业PMI:构成指数/新订单指数:企业规模/小型企业
    pmi010600	float	N	制造业PMI:构成指数/供应商配送时间指数
    pmi010601	float	N	制造业PMI:构成指数/供应商配送时间指数:企业规模/大型企业
    pmi010602	float	N	制造业PMI:构成指数/供应商配送时间指数:企业规模/中型企业
    pmi010603	float	N	制造业PMI:构成指数/供应商配送时间指数:企业规模/小型企业
    pmi010700	float	N	制造业PMI:构成指数/原材料库存指数
    pmi010701	float	N	制造业PMI:构成指数/原材料库存指数:企业规模/大型企业
    pmi010702	float	N	制造业PMI:构成指数/原材料库存指数:企业规模/中型企业
    pmi010703	float	N	制造业PMI:构成指数/原材料库存指数:企业规模/小型企业
    pmi010800	float	N	制造业PMI:构成指数/从业人员指数
    pmi010801	float	N	制造业PMI:构成指数/从业人员指数:企业规模/大型企业
    pmi010802	float	N	制造业PMI:构成指数/从业人员指数:企业规模/中型企业
    pmi010803	float	N	制造业PMI:构成指数/从业人员指数:企业规模/小型企业
    pmi010900	float	N	制造业PMI:其他/新出口订单
    pmi011000	float	N	制造业PMI:其他/进口
    pmi011100	float	N	制造业PMI:其他/采购量
    pmi011200	float	N	制造业PMI:其他/主要原材料购进价格
    pmi011300	float	N	制造业PMI:其他/出厂价格
    pmi011400	float	N	制造业PMI:其他/产成品库存
    pmi011500	float	N	制造业PMI:其他/在手订单
    pmi011600	float	N	制造业PMI:其他/生产经营活动预期
    pmi011700	float	N	制造业PMI:分行业/装备制造业
    pmi011800	float	N	制造业PMI:分行业/高技术制造业
    pmi011900	float	N	制造业PMI:分行业/基础原材料制造业
    pmi012000	float	N	制造业PMI:分行业/消费品制造业
    pmi020100	float	N	非制造业PMI:商务活动
    pmi020101	float	N	非制造业PMI:商务活动:分行业/建筑业
    pmi020102	float	N	非制造业PMI:商务活动:分行业/服务业业
    pmi020200	float	N	非制造业PMI:新订单指数
    pmi020201	float	N	非制造业PMI:新订单指数:分行业/建筑业
    pmi020202	float	N	非制造业PMI:新订单指数:分行业/服务业
    pmi020300	float	N	非制造业PMI:投入品价格指数
    pmi020301	float	N	非制造业PMI:投入品价格指数:分行业/建筑业
    pmi020302	float	N	非制造业PMI:投入品价格指数:分行业/服务业
    pmi020400	float	N	非制造业PMI:销售价格指数
    pmi020401	float	N	非制造业PMI:销售价格指数:分行业/建筑业
    pmi020402	float	N	非制造业PMI:销售价格指数:分行业/服务业
    pmi020500	float	N	非制造业PMI:从业人员指数
    pmi020501	float	N	非制造业PMI:从业人员指数:分行业/建筑业
    pmi020502	float	N	非制造业PMI:从业人员指数:分行业/服务业
    pmi020600	float	N	非制造业PMI:业务活动预期指数
    pmi020601	float	N	非制造业PMI:业务活动预期指数:分行业/建筑业
    pmi020602	float	N	非制造业PMI:业务活动预期指数:分行业/服务业
    pmi020700	float	N	非制造业PMI:新出口订单
    pmi020800	float	N	非制造业PMI:在手订单
    pmi020900	float	N	非制造业PMI:存货
    pmi021000	float	N	非制造业PMI:供应商配送时间
    pmi030000	float	N	中国综合PMI:产出指数
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))

def get_sf_in_this_year(year_str: str = datetime.now().strftime("%Y")) -> DfWithColumnDesc:
    """
    获取年内的社融数据
    """
    pro = get_pro()
    df = pro.sf_month(start_m=year_str+"01", end_m=year_str+"12")
    desc = "年内 社融 数据"
    column_desc = """
    month	str	Y	月度
    inc_month	float	Y	社融增量当月值（亿元）
    inc_cumval	float	Y	社融增量累计值（亿元）
    stk_endval	float	Y	社融存量期末值（万亿元）
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))




if __name__ == '__main__':

    # 新股发售数据
    # df = get_ipo_stocks_of_a_day("2025-09-11")
    # print(df.df)


    # 宏观数据
    # df = get_cpi_in_this_year("2025")
    # print(df.df)

    # df = get_ppi_in_this_year("2025")
    # print(df.df)

    # df = get_pmi_in_this_year("2025")
    # print(df.df)

    # df = get_sf_in_this_year("2025")
    # print(df.df)


    # 资金流向数据
    # df = get_money_flow_hsgt("2024-09-11")
    # print(df.df)

    # df = get_money_flow("20250901")
    # print(df.df)

    # df = get_ind_money_flow("20250902")
    # print(df.df)

    # df = get_mkt_dc_money_flow("20250902")
    # print(df.df)

    # df = get_suspend_stocks_of_a_day("20250902")
    # print(df.df)

    df = get_resume_stocks_of_a_day("20250902")
    print(df.df)

    print(1)


