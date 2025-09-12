from dataclasses import fields
from datetime import datetime, timedelta, timezone

import pandas as pd
import tushare as ts

token = "15bb21f848e2844fee6046746341f03079d4911b96fc80f1a48ee8da"


class DfWithColumnDesc:
    df: pd.DataFrame
    desc: str
    column_desc: list[dict]

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


##================= 缓存相关 =================
cache = {}


class DataCache:
    key: str  # 缓存的 key, 用于标记一种数据的类型
    version: str  # 用于标记一种数据的版本
    data: DfWithColumnDesc  # 缓存的数据

    def __init__(self, key: str, version: str, data: DfWithColumnDesc):
        self.key = key
        self.version = version
        self.data = data


def get_data_cache(key: str, version: str) -> DfWithColumnDesc | None:
    if key in cache and cache[key].version == version:
        print("get data cache: {} {}".format(key, version))
        return cache[key].data
    return None


def set_data_cache(key: str, version: str, data: DfWithColumnDesc):
    cache[key] = DataCache(key, version, data)


def adapt_date_str(date_str: str) -> str:
    return date_str.replace("-", "")


def get_pro():
    ts.set_token(token)
    pro = ts.pro_api()
    return pro


def parse_column_desc_to_dict(input_string) -> list[dict]:
    # 分割字符串为行
    lines = input_string.strip().split('\n')

    part_number = len(lines[0].split())

    if part_number == 4:
        result = [
            {
                "字段名称": parts[0],
                "字段类型": parts[1],
                "是否默认显示": parts[2],
                "字段描述": ' '.join(parts[3:])
            }
            for line in lines
            if (parts := line.split()) and len(parts) == 4
        ]
    elif part_number == 3:
        result = [
            {
                "字段名称": parts[0],
                "字段类型": parts[1],
                "字段描述": ' '.join(parts[2:])
            }
            for line in lines
            if (parts := line.split()) and len(parts) == 3
        ]
    else:
        raise Exception("column desc number error")

    return result


##================== basic =================
# 查询所有个股的信息


##================== 当日特殊个股动态 =================
def get_ipo_stocks_of_a_day(date_str: str = datetime.now().strftime("%Y%m%d")) -> DfWithColumnDesc:
    """
    获取某一日 ipo 的新股数据
    """
    date_str = adapt_date_str(date_str)
    pro = get_pro()
    df = pro.new_share(start_date=adapt_date_str(date_str), end_date=adapt_date_str(date_str))
    desc = "{}当日ipo新股数据".format(date_str)
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
    desc = "{}当日内与往后七日内的停牌股票".format(date_str)
    column_desc = """
    ts_code	str	Y	TS代码
    trade_date	str	Y	停复牌日期
    suspend_timing	str	Y	日内停牌时间段
    suspend_type	str	Y	停复牌类型：S-停牌，R-复牌
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))


def get_resume_stocks_of_a_day(date_str: str = datetime.now().strftime("%Y%m%d")) -> DfWithColumnDesc | None:
    """
    获取某一日 的复牌股票
    """
    date_str = adapt_date_str(date_str)
    pro = get_pro()
    try:
        df = pro.suspend_d(suspend_type='R', trade_date=date_str)
    except:
        return None
    desc = "{}当日复牌股票".format(date_str)
    column_desc = """
    ts_code	str	Y	TS代码
    trade_date	str	Y	停复牌日期
    suspend_timing	str	Y	日内停牌时间段
    suspend_type	str	Y	停复牌类型：S-停牌，R-复牌
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))


##================== 资金流向 =================
def get_money_flow_hsgt(date_str: str = datetime.now().strftime("%Y%m%d")) -> DfWithColumnDesc | None:
    """
    获取某一日 及其之前7天的 沪深港通资金流向
    """
    date_str = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=-1)).strftime("%Y-%m-%d")
    date_before_7_days = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=-7)).strftime("%Y-%m-%d")
    pro = get_pro()
    try:
        df = pro.moneyflow_hsgt(start_date=adapt_date_str(date_before_7_days), end_date=adapt_date_str(date_str))
    except:
        return None
    desc = "{}沪深港通资金流向".format(date_str)
    column_desc = """
    trade_date	str	交易日期
    ggt_ss	float	港股通（上海）
    ggt_sz	float	港股通（深圳）
    hgt	float	沪股通（百万元）
    sgt	float	深股通（百万元）
    north_money	float	北向资金（百万元）
    south_money	float	南向资金（百万元）
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))


def get_money_flow(date_str: str = datetime.now().strftime("%Y%m%d")):
    key = "money_flow"
    date_str = adapt_date_str(date_str)

    data_cache = get_data_cache(key, date_str)
    if data_cache is not None:
        return data_cache

    pro = get_pro()
    df = pro.moneyflow(trade_date=date_str)
    desc = "{}当日个股资金流向".format(date_str)
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
    res = DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))
    set_data_cache(key, date_str, res)
    return res


def get_ind_money_flow(date_str: str = datetime.now().strftime("%Y%m%d")) -> DfWithColumnDesc | None:
    """
    获取某一日的行业资金流向
    """
    key = "ind_money_flow"
    date_str = adapt_date_str(date_str)

    data_cache = get_data_cache(key, date_str)
    if data_cache is not None:
        return data_cache

    pro = get_pro()
    df = ''
    try:
        df = pro.moneyflow_ind(trade_date=date_str)
    except:
        print("get_ind_money_flow error")
        return None
    desc = "{}当日行业资金流向".format(date_str)
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
    res = DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))
    set_data_cache(key, date_str, res)
    return res


def get_mkt_dc_money_flow(date_str: str = datetime.now().strftime("%Y%m%d")) -> DfWithColumnDesc | None:
    """
    获取某一日 大盘资金流向
    """
    key = "mkt_dc_money_flow"
    date_str = adapt_date_str(date_str)

    data_cache = get_data_cache(key, date_str)
    if data_cache is not None:
        return data_cache

    pro = get_pro()
    df = ''
    try:
        df = pro.moneyflow_mkt_dc(start_date=date_str, end_date=date_str)
    except:
        print("get_mkt_dc_money_flow error")
        return None
    desc = "{}当日内大盘资金流向".format(date_str)
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
    res = DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))
    set_data_cache(key, date_str, res)
    return res


##================== 利率数据 =================
def get_lpr_in_last_7_day(date_str: str = datetime.now().strftime("%Y%m%d")) -> DfWithColumnDesc:
    """
    七日内lpr利率
    """
    date_str = adapt_date_str(date_str)
    date_before_7_days = (datetime.strptime(date_str, "%Y%m%d") + timedelta(days=-7)).strftime("%Y%m%d")
    pro = get_pro()
    df = pro.shibor_lpr(start_date=date_before_7_days, end_date=date_str)
    desc = " 以 {} 为开始日期，以 {} 为结束日期的LPR 利率数据".format(date_before_7_days, date_str)
    column_desc = """
    date	str	Y	日期
    1y	float	Y	1年贷款利率
    5y	float	Y	5年贷款利率
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))


def get_shibor_in_last_7_day(date_str: str = datetime.now().strftime("%Y%m%d")) -> DfWithColumnDesc:
    date_str = adapt_date_str(date_str)
    date_before_7_days = (datetime.strptime(date_str, "%Y%m%d") + timedelta(days=-7)).strftime("%Y%m%d")
    pro = get_pro()
    df = pro.shibor(start_date=date_before_7_days, end_date=date_str)
    desc = " 以 {} 为开始日期，以 {} 为结束日期的SHIBOR 利率数据".format(date_before_7_days, date_str)
    column_desc = """
    date	str	Y	日期
    on	float	Y	隔夜
    1w	float	Y	1周
    2w	float	Y	2周
    1m	float	Y	1个月
    3m	float	Y	3个月
    6m	float	Y	6个月
    9m	float	Y	9个月
    1y	float	Y	1年
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))


def get_shibor_quota(date_str: str = datetime.now().strftime("%Y%m%d")) -> DfWithColumnDesc:
    date_str = adapt_date_str(date_str)
    pro = get_pro()
    df = pro.shibor_quote(start_date=date_str, end_date=date_str)
    desc = "{}当日的shibor报价数据".format(date_str)
    column_desc = """
    date	str	Y	日期
    bank	str	Y	报价银行
    on_b	float	Y	隔夜_Bid
    on_a	float	Y	隔夜_Ask
    1w_b	float	Y	1周_Bid
    1w_a	float	Y	1周_Ask
    2w_b	float	Y	2周_Bid
    2w_a	float	Y	2周_Ask
    1m_b	float	Y	1月_Bid
    1m_a	float	Y	1月_Ask
    3m_b	float	Y	3月_Bid
    3m_a	float	Y	3月_Ask
    6m_b	float	Y	6月_Bid
    6m_a	float	Y	6月_Ask
    9m_b	float	Y	9月_Bid
    9m_a	float	Y	9月_Ask
    1y_b	float	Y	1年_Bid
    1y_a	float	Y	1年_Ask
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))


##================== 新闻数据 =================


def get_short_news_in_2_days(date_str: str = datetime.now().strftime("%Y-%m-%d")) -> DfWithColumnDesc:
    pro = get_pro()
    yesterday = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=-1)).strftime("%Y-%m-%d")
    df = pro.news(src='sina', start_date='{} 20:00:00'.format(yesterday), end_date='{} 09:00:00'.format(date_str),
                  fields='content')
    desc = "{} 09:00:00 当日的新闻数据,新闻渠道包含：新浪财经".format(date_str)
    column_desc = """
    content	str	Y	内容
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))


def get_cctv_news(date_str: str = datetime.now().strftime("%Y%m%d"),
                  require_yesterday: bool = False) -> DfWithColumnDesc | None:
    key = "cctv_news"

    data_cache = get_data_cache(key, date_str)
    if data_cache is not None:
        return data_cache

    pro = get_pro()
    if require_yesterday:
        date_str = (datetime.strptime(date_str, "%Y%m%d") + timedelta(days=-1)).strftime("%Y%m%d")

    desc = "{} 当日的新闻联播数据".format(date_str)
    column_desc = """
    date	str	Y	日期
    title	str	Y	标题
    content	str	Y	内容
    """

    try:
        df = pro.cctv_news(date=date_str)
    except:
        return None

    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))


##================= 国际信息 =====================
def get_fx_in_last_7_days(date_str: str = datetime.now().strftime("%Y%m%d")) -> DfWithColumnDesc:
    date_str = adapt_date_str(date_str)
    key = "fx_in_last_7_days"
    data_cache = get_data_cache(key, date_str)
    if data_cache is not None:
        return data_cache

    pro = get_pro()
    start_date = (datetime.strptime(date_str, "%Y%m%d") + timedelta(days=-7)).strftime("%Y%m%d")
    df = pro.fx_daily(ts_code='USDCNH.FXCM', start_date=start_date, end_date=date_str)
    desc = "{} 七日内美元兑人民币汇率".format(date_str)
    column_desc = """
    ts_code	str	Y	外汇代码
    trade_date	str	Y	交易日期
    bid_open	float	Y	买入开盘价
    bid_close	float	Y	买入收盘价
    bid_high	float	Y	买入最高价
    bid_low	float	Y	买入最低价
    ask_open	float	Y	卖出开盘价
    ask_close	float	Y	卖出收盘价
    ask_high	float	Y	卖出最高价
    ask_low	float	Y	卖出最低价
    tick_qty	int	Y	报价笔数
    exchange	str	N	交易商
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))


##================== 宏观数据（非日频） =================
def get_cpi_in_this_year(year_str: str = datetime.now().strftime("%Y")) -> DfWithColumnDesc:
    """
    年内 cpi 数据
    """
    pro = get_pro()
    df = pro.cn_cpi(start_m=year_str + "01", end_m=year_str + "12")
    desc = "{} 年内 cpi 数据".format(year_str)
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
    df = pro.cn_ppi(start_m=year_str + "01", end_m=year_str + "12")
    desc = "{}年内 ppi 数据".format(year_str)
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

    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))


def get_pmi_in_this_year(year_str: str = datetime.now().strftime("%Y")) -> DfWithColumnDesc:
    """
    获取年内的pmi数据
    """
    pro = get_pro()
    df = pro.cn_pmi(start_m=year_str + "01", end_m=year_str + "12")
    desc = "{}年内 pmi 数据".format(year_str)
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
    df = pro.sf_month(start_m=year_str + "01", end_m=year_str + "12")
    desc = "{} 年内社融数据".format(year_str)
    column_desc = """
    month	str	Y	月度
    inc_month	float	Y	社融增量当月值（亿元）
    inc_cumval	float	Y	社融增量累计值（亿元）
    stk_endval	float	Y	社融存量期末值（万亿元）
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))


def get_currency_supply(year_str: str = datetime.now().strftime("%Y")) -> DfWithColumnDesc:
    """
    获取年内的货币供应
    """
    desc = "{}年内货币供应".format(year_str)
    pro = get_pro()
    df = pro.cn_m(start_m=year_str + '01', end_m=year_str + '12')
    column_desc = """
    month	str	Y	月份YYYYMM
    m0	float	Y	M0（亿元）
    m0_yoy	float	Y	M0同比（%）
    m0_mom	float	Y	M0环比（%）
    m1	float	Y	M1（亿元）
    m1_yoy	float	Y	M1同比（%）
    m1_mom	float	Y	M1环比（%）
    m2	float	Y	M2（亿元）
    m2_yoy	float	Y	M2同比（%）
    m2_mom	float	Y	M2环比（%）
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))


##================== 指数数据 =================
def get_index_info():
    pro = get_pro()
    df = pro.index_daily(ts_code='399300.SZ', start_date='20180101', end_date='20180102')


def get_main_index_pe_from_beginning(code: str):
    pro = get_pro()
    df = pro.index_dailybasic(ts_code=code, fields='ts_code,trade_date,pe')
    return df


def get_main_index_pb_from_beginning(code: str):
    pro = get_pro()
    df = pro.index_dailybasic(ts_code=code, fields='ts_code,trade_date,pb')
    return df


def get_index_daily_info(date_str: str, code: str):
    date_str = adapt_date_str(date_str)
    pro = get_pro()
    df = pro.index_basic(ts_code=code, fields='name,fullname')
    name = df['name'].values[0]
    fullname = df['fullname'].values[0]
    df = pro.index_daily(ts_code=code, trade_date=date_str)
    desc = '{} {}({}) 指数于 {} 交易日的行情'.format(code, name, fullname, date_str)
    column_desc = """
    ts_code	str	Y TS指数代码
    trade_date	str	Y 交易日
    close	float	Y 收盘点位
    open	float	Y 开盘点位
    high	float	Y 最高点位
    low	float	Y 最低点位
    pre_close	float	Y 昨日收盘点
    change	float	Y 涨跌点
    pct_chg	float	Y 涨跌幅（%）
    vol	float	Y 成交量（手）
    amount	float	Y 成交额（千元）
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))


# 个股信息
def get_all_stocks_name_and_code():
    pro = get_pro()
    df = pro.stock_basic(fields='ts_code,name')
    records = df[['ts_code', 'name']].to_dict('records')

    # 将每个字典拼接成一行字符串
    result_str = '\n'.join([f"{item['ts_code']} {item['name']}" for item in records])
    return result_str


def get_stock_basic_info(ts_code: str) -> DfWithColumnDesc:
    pro = get_pro()
    df = pro.stock_basic(ts_code=ts_code)
    name = df['name'][0]
    desc = '{} {} 股票的基本信息'.format(ts_code, name)
    column_desc = """
    ts_code	str	Y	TS代码
    symbol	str	Y	股票代码
    name	str	Y	股票名称
    area	str	Y	地域
    industry	str	Y	所属行业
    fullname	str	N	股票全称
    enname	str	N	英文全称
    cnspell	str	Y	拼音缩写
    market	str	Y	市场类型（主板/创业板/科创板/CDR）
    exchange	str	N	交易所代码
    curr_type	str	N	交易货币
    list_status	str	N	上市状态 L上市 D退市 P暂停上市
    list_date	str	Y	上市日期
    delist_date	str	N	退市日期
    is_hs	str	N	是否沪深港通标的，N否 H沪股通 S深股通
    act_name	str	Y	实控人名称
    act_ent_type	str	Y	实控人企业性质
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))


def get_stock_basic_index_in_30_days(date_str: str, ts_code: str):
    date_str = adapt_date_str(date_str)
    pro = get_pro()
    start_date_str = (datetime.strptime(date_str, "%Y%m%d") + timedelta(days=-30)).strftime("%Y%m%d")
    df = pro.daily_basic(start_date=start_date_str, end_date=date_str, ts_code=ts_code)
    desc = '{} 股票前七日基本交易指标'.format(ts_code)
    column_desc = """
    ts_code	str	TS股票代码
    trade_date	str	交易日期
    close	float	当日收盘价
    turnover_rate	float	换手率（%）
    turnover_rate_f	float	换手率（自由流通股）
    volume_ratio	float	量比
    pe	float	市盈率（总市值/净利润， 亏损的PE为空）
    pe_ttm	float	市盈率（TTM，亏损的PE为空）
    pb	float	市净率（总市值/净资产）
    ps	float	市销率
    ps_ttm	float	市销率（TTM）
    dv_ratio	float	股息率 （%）
    dv_ttm	float	股息率（TTM）（%）
    total_share	float	总股本 （万股）
    float_share	float	流通股本 （万股）
    free_share	float	自由流通股本 （万）
    total_mv	float	总市值 （万元）
    circ_mv	float	流通市值（万元）
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))


def get_stock_daily_trade_data_in_7days(date_str: str, ts_code: str):
    date_str = adapt_date_str(date_str)
    pro = get_pro()
    start_date_str = (datetime.strptime(date_str, "%Y%m%d") + timedelta(days=-7)).strftime("%Y%m%d")
    df = pro.daily(start_date=start_date_str, end_date=date_str, ts_code=ts_code)
    desc = '{} 股票前七日盘内交易信息'.format(ts_code)
    column_desc = """
    ts_code	str	股票代码
    trade_date	str	交易日期
    open	float	开盘价
    high	float	最高价
    low	float	最低价
    close	float	收盘价
    pre_close	float	昨收价【除权价，前复权】
    change	float	涨跌额
    pct_chg	float	涨跌幅 【基于除权后的昨收计算的涨跌幅：（今收-除权昨收）/除权昨收 】
    vol	float	成交量 （手）
    amount	float	成交额 （千元）
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))


def get_share_float_in_30_days(date_str: str, ts_code: str):
    date_str = adapt_date_str(date_str)
    pro = get_pro()
    end_date_str = (datetime.strptime(date_str, "%Y%m%d") + timedelta(days=30)).strftime("%Y%m%d")
    df = pro.daily(start_date=date_str, end_date=end_date_str, ts_code=ts_code)
    desc = '{} 30天内限售股解禁信息'.format(ts_code)
    column_desc = """
    ts_code	str	Y	TS代码
    ann_date	str	Y	公告日期
    float_date	str	Y	解禁日期
    float_share	float	Y	流通股份(股)
    float_ratio	float	Y	流通股份占总股本比率
    holder_name	str	Y	股东名称
    share_type	str	Y	股份类型
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))


def get_repurchase_data_in_last_and_after_1_year(date_str: str, ts_code: str):
    date_str = adapt_date_str(date_str)
    pro = get_pro()
    start_date_str = (datetime.strptime(date_str, "%Y%m%d") + timedelta(days=-365)).strftime("%Y%m%d")
    end_date_str = (datetime.strptime(date_str, "%Y%m%d") + timedelta(days=365)).strftime("%Y%m%d")
    df = pro.daily(start_date=start_date_str, end_date=end_date_str, ts_code=ts_code)
    desc = '{} 前后一年回购信息'.format(ts_code)
    column_desc = """
    ts_code	str	Y	TS代码
    ann_date	str	Y	公告日期
    end_date	str	Y	截止日期
    proc	str	Y	进度
    exp_date	str	Y	过期日期
    vol	float	Y	回购数量
    amount	float	Y	回购金额
    high_limit	float	Y	回购最高价
    low_limit	float	Y	回购最低价
    """
    return DfWithColumnDesc(df, desc, parse_column_desc_to_dict(column_desc))

def get_stock_all_pe_pb(ts_code: str):
    pro = get_pro()
    df = pro.daily_basic(ts_code=ts_code, fields='trade_date,pe,pb')
    return df



if __name__ == '__main__':
    # ----------- 特殊个股信息 -----------------------
    # df = get_ipo_stocks_of_a_day("2025-09-11")
    # print(df.df)

    # df = get_suspend_stocks_of_a_day("20250902")
    # print(df.df)

    # df = get_resume_stocks_of_a_day("20250902")
    # print(df.df)

    # ----------- 资金流向数据 -----------------------
    # df = get_money_flow_hsgt("2024-09-11")
    # print(df.df)

    # df = get_money_flow("20250901")
    # print(df.df)

    # df = get_ind_money_flow("20250902")
    # print(df.df)

    # df = get_mkt_dc_money_flow("20250902")
    # print(df.df)

    # ----------- 利率信息 -----------------------
    # df = get_lpr_in_last_7_day("20240903")
    # print(df.df)
    #
    # df = get_shibor_in_last_7_day("20240903")
    # print(df.df)

    # df = get_shibor_quota("20240903")
    # print(df.df)

    # ----------- 实时新闻 -----------------------
    # df = get_short_news_in_2_days("2024-09-03")
    # print(df.df)

    # df = get_cctv_news("20240903")
    # print(df.df)

    # ----------- 宏观数据 ----------------------
    # df = get_cpi_in_this_year("2025")
    # print(df.df)

    # df = get_ppi_in_this_year("2025")
    # print(df.df)

    # df = get_pmi_in_this_year("2025")
    # print(df.df)

    # df = get_sf_in_this_year("2025")
    # print(df.df)

    # ----------- 国际数据 ----------------------
    # df = get_fx_in_last_7_days("20250906")
    # print(df.df)

    # 指数相关
    # df = get_index_daily_info('20250912', '000001.SH')
    # print(df.df)

    # 个股相关

    print(get_all_stocks_name_and_code())
    # df = get_stock_basic_info('000001.SZ')
    # print(df.df)

    # df = get_stock_basic_index_in_7_days('2025-09-12', '000001.SZ')
    # print(df.df)
    # print(df.column_desc)

    # df = get_stock_daily_trade_data_in_7days('2025-09-12', '000001.SZ')
    # print(df.df)
    # print(df.column_desc)

    # df = get_repurchase_data_in_last_and_after_1_year('2025-09-12', '000002.SZ')
    # print(df.df)
    # print(df.column_desc)

    # print(get_stock_all_pe_pb('000002.SZ'))

    print("")
