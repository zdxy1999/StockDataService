"""
Tushare 数据源模块
参考: /Users/dichang/code/personal-projects/stock/industry_pe_pb/industry_pe_pb_sw.py
"""

import tushare as ts
import pandas as pd
import time
from typing import Optional, List
from datetime import datetime, timedelta
from cache_manager import APICacheManager


# Tushare Token（用户需要替换为自己的token）
TOKEN = '15bb21f848e2844fee6046746341f03079d4911b96fc80f1a48ee8da'

# API频率限制配置
REQUEST_INTERVAL = 0.0  # 去掉调用间隔
RATE_LIMIT_WAIT = 0.5  # 触发上限等待0.5秒


class TushareAPI:
    """Tushare API封装类"""

    def __init__(self, token: str = TOKEN, enable_cache: bool = True, cache_ttl_days: int = 30):
        self.pro = ts.pro_api(token)
        self.last_request_time = 0
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0

        # 初始化缓存管理器
        self.enable_cache = enable_cache
        if enable_cache:
            self.cache = APICacheManager(cache_ttl_days=cache_ttl_days)
        else:
            self.cache = None

    def call_with_retry(self, api_func, api_name="未知API", max_retries=5, use_cache=True, **kwargs):
        """
        带重试机制和缓存的API调用

        Args:
            api_func: API函数
            api_name: API名称（用于缓存键）
            max_retries: 最大重试次数
            use_cache: 是否使用缓存
            **kwargs: API调用参数
        """
        # 尝试从缓存获取
        if self.enable_cache and use_cache and self.cache:
            cached_data = self.cache.get(api_name, **kwargs)
            if cached_data is not None:
                self.cache_hits += 1
                return cached_data
            self.cache_misses += 1

        # 对于频率限制错误，使用更大的重试次数
        rate_limit_max_retries = 1000
        normal_retries = 0
        rate_limit_retries = 0

        while True:
            try:
                elapsed = time.time() - self.last_request_time
                if elapsed < REQUEST_INTERVAL:
                    time.sleep(REQUEST_INTERVAL - elapsed)

                result = api_func(**kwargs)
                self.last_request_time = time.time()
                self.total_requests += 1

                # 保存到缓存
                if self.enable_cache and use_cache and self.cache and result is not None:
                    self.cache.set(api_name, result, **kwargs)

                return result

            except Exception as e:
                error_msg = str(e)

                # 检查是否是频率限制错误
                if "每分钟最多访问" in error_msg or "访问过于频繁" in error_msg:
                    rate_limit_retries += 1
                    if rate_limit_retries <= rate_limit_max_retries:
                        if rate_limit_retries % 10 == 1 or rate_limit_retries == 1:
                            print(f"⚠️  触发频率限制，等待中... ({rate_limit_retries}/{rate_limit_max_retries})")
                        time.sleep(RATE_LIMIT_WAIT)
                        continue
                    else:
                        print(f"❌ 频率限制重试次数超限 ({rate_limit_max_retries}次)")
                        return None

                # 其他错误，使用正常重试逻辑
                normal_retries += 1
                if normal_retries < max_retries:
                    print(f"❌ API调用失败 (尝试 {normal_retries}/{max_retries}): {error_msg}")
                    time.sleep(2)
                else:
                    print(f"❌ API调用失败，已达到最大重试次数")
                    return None

    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        if not self.enable_cache or not self.cache:
            return {"enabled": False}

        stats = self.cache.get_cache_stats()
        stats.update({
            "enabled": True,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": f"{self.cache_hits / (self.cache_hits + self.cache_misses) * 100:.1f}%" if (self.cache_hits + self.cache_misses) > 0 else "N/A"
        })
        return stats

    def clear_cache(self, expired_only: bool = True):
        """清理缓存"""
        if not self.enable_cache or not self.cache:
            print("缓存未启用")
            return

        if expired_only:
            return self.cache.clear_expired()
        else:
            return self.cache.clear_all()


class StockDataSource:
    """股票数据源"""

    def __init__(self, api: Optional[TushareAPI] = None):
        self.api = api if api else TushareAPI()

    def get_stock_list(self, list_status: str = 'L', exclude_bse: bool = True, exclude_star: bool = True, exclude_gem: bool = False, exclude_st: bool = True) -> pd.DataFrame:
        """
        获取股票列表

        Args:
            list_status: 上市状态 L-上市, D-退市, P-暂停上市
            exclude_bse: 是否排除北交所股票
            exclude_star: 是否排除科创板股票（688开头）
            exclude_gem: 是否排除创业板股票（000/001/002/003开头）
            exclude_st: 是否排除ST股票

        Returns:
            DataFrame: 股票列表
        """
        df = self.api.call_with_retry(
            self.api.pro.stock_basic,
            api_name="stock_basic",
            exchange='',
            list_status=list_status
        )

        # 检查返回结果
        if df is None or df.empty:
            return pd.DataFrame()

        # 排除北交所股票（如果指定）
        # 北交所股票代码以 .BJ 结尾
        if exclude_bse:
            df = df[~df['ts_code'].str.endswith('.BJ')]

        # 排除科创板股票（如果指定）
        # 科创板股票代码以 688 开头
        if exclude_star:
            df = df[~df['ts_code'].str.startswith('688')]

        # 排除创业板股票（如果指定）
        # 创业板股票代码以 300 开头
        if exclude_gem:
            # 创业板以 000/001/002/003 开头
            # 先排除所有 300 开头的
            df = df[~df['ts_code'].str.startswith('300')]

        # 排除ST股票（如果指定）
        if exclude_st:
            df = df[~df['name'].str.contains('ST|st', na=False)]

        return df

    def get_daily_data(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取日行情数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            DataFrame: 日行情数据
        """
        df = self.api.call_with_retry(
            self.api.pro.daily,
            api_name="daily",
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )
        return df if df is not None else pd.DataFrame()

    def get_daily_basic(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取每日基本面数据（PE、PB、市值等）

        Args:
            ts_code: 股票代码
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            DataFrame: 每日基本面数据
        """
        df = self.api.call_with_retry(
            self.api.pro.daily_basic,
            api_name="daily_basic",
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )
        return df if df is not None else pd.DataFrame()

    def get_income_statement(self, ts_code: str, period: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取利润表数据

        Args:
            ts_code: 股票代码
            period: 报告期 20241231
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            DataFrame: 利润表数据
        """
        df = self.api.call_with_retry(
            self.api.pro.income,
            api_name="income",
            ts_code=ts_code,
            period=period,
            start_date=start_date,
            end_date=end_date
        )
        return df if df is not None else pd.DataFrame()

    def get_balance_sheet(self, ts_code: str, period: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取资产负债表数据

        Args:
            ts_code: 股票代码
            period: 报告期 20241231
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            DataFrame: 资产负债表数据
        """
        df = self.api.call_with_retry(
            self.api.pro.balancesheet,
            api_name="balancesheet",
            ts_code=ts_code,
            period=period,
            start_date=start_date,
            end_date=end_date
        )
        return df if df is not None else pd.DataFrame()

    def get_new_share_data(self, ts_code: str, start_date: str, end_date: str, ann_date: str = None) -> pd.DataFrame:
        """
        获取新股发行/解禁数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            ann_date: 公告日期限制（可选），用于只获取在选股当天或之前已公布的解禁信息

        Returns:
            DataFrame: 新股发行/解禁数据
        """
        # 使用 share_float 接口获取解禁数据
        params = {
            'ts_code': ts_code,
            'start_date': start_date,
            'end_date': end_date
        }
        if ann_date is not None:
            params['ann_date'] = ann_date

        df = self.api.call_with_retry(
            self.api.pro.share_float,
            api_name="share_float",
            **params
        )

        return df if df is not None else pd.DataFrame()

    def get_industry_info(self, ts_code: str) -> dict:
        """
        获取股票行业信息

        Args:
            ts_code: 股票代码

        Returns:
            dict: 行业信息
        """
        df = self.get_stock_list()
        if df.empty:
            return {}

        stock_info = df[df['ts_code'] == ts_code]
        if stock_info.empty:
            return {}

        return {
            'industry': stock_info.iloc[0].get('industry', ''),
            'industry_sw_l1': stock_info.iloc[0].get('industry_sw_l1', ''),
        }

    def batch_get_industry_info(self, ts_codes):
        """
        批量获取股票行业信息

        Args:
            ts_codes: 股票代码列表

        Returns:
            dict: 股票代码 -> 行业信息的映射
        """
        if not ts_codes:
            return {}

        df = self.get_stock_list()
        if df.empty:
            return {}

        # 使用字典缓存结果
        industry_dict = {}
        for _, stock in df.iterrows():
            ts_code = stock['ts_code']
            industry = stock.get('industry', '')
            industry_l1 = stock.get('industry_sw_l1', '')
            if industry:  # 只缓存有行业的
                industry_dict[ts_code] = {
                    'industry': industry,
                    'industry_sw_l1': industry_l1
                }

        return industry_dict

    def get_nth_trading_day(self, start_date: str, n: int = 20) -> str:
        """
        获取从start_date之后的第n个交易日

        Args:
            start_date: 开始日期 YYYYMMDD
            n: 交易日天数（从start_date+1开始计算）

        Returns:
            str: 第n个交易日的日期 YYYYMMDD
        """
        # 获取交易日历（取足够长的时间范围）
        # 从start_date开始，往后取约n*2天的交易日历（考虑周末和节假日）
        from datetime import datetime, timedelta
        start_date_obj = datetime.strptime(start_date, '%Y%m%d')
        end_date_obj = start_date_obj + timedelta(days=n * 2)
        end_date = end_date_obj.strftime('%Y%m%d')

        df = self.api.call_with_retry(
            self.api.pro.trade_cal,
            api_name="trade_cal",
            exchange='',
            start_date=start_date,
            end_date=end_date
        )

        if df is None or df.empty:
            # 如果获取失败，回退到使用日历天数
            end_date_obj = start_date_obj + timedelta(days=n)
            return end_date_obj.strftime('%Y%m%d')

        # 筛选交易日（is_open=1），并排除start_date当天
        # Tushare返回的日期是降序排列，需要排序成升序
        trading_days = df[(df['is_open'] == 1) & (df['cal_date'] > start_date)]['cal_date'].tolist()
        trading_days.sort()  # 升序排列

        if len(trading_days) >= n:
            return trading_days[n - 1]
        else:
            # 如果交易日不足，返回最后一个交易日
            return trading_days[-1] if trading_days else start_date

    def get_stock_name_history(self, ts_code: str) -> pd.DataFrame:
        """
        获取股票历史名称变化记录

        Args:
            ts_code: 股票代码

        Returns:
            DataFrame: 股票名称变化记录
        """
        df = self.api.call_with_retry(
            self.api.pro.namechange,
            api_name="namechange",
            ts_code=ts_code
        )

        return df if df is not None else pd.DataFrame()

    def is_st_stock_on_date(self, ts_code: str, trade_date: str) -> bool:
        """
        判断指定日期时是否为ST股票

        Args:
            ts_code: 股票代码
            trade_date: 选股日期 YYYYMMDD

        Returns:
            bool: 是否为ST股票
        """
        try:
            # 获取当前股票名称
            df_stock_basic = self.api.call_with_retry(
                self.api.pro.stock_basic,
                api_name="stock_basic",
                ts_code=ts_code
            )

            if df_stock_basic is None or df_stock_basic.empty:
                return False

            current_name = df_stock_basic.iloc[0]['name']

            # 获取名称变化历史
            df_namechange = self.get_stock_name_history(ts_code)

            if df_namechange.empty:
                # 没有历史记录，直接根据当前名称判断
                return 'ST' in current_name or 'st' in current_name

            # 找出在trade_date时有效的名称
            # 规则：start_date <= trade_date AND (end_date IS NULL OR end_date > trade_date)
            trade_date_obj = pd.to_datetime(trade_date, format='%Y%m%d')

            df_namechange['start_date'] = pd.to_datetime(df_namechange['start_date'])
            if 'end_date' in df_namechange.columns:
                df_namechange['end_date'] = pd.to_datetime(df_namechange['end_date'], errors='coerce')

            valid_records = df_namechange[
                (df_namechange['start_date'] <= trade_date_obj) &
                (df_namechange['end_date'].isna() | (df_namechange['end_date'] > trade_date_obj))
            ]

            if valid_records.empty:
                # 没有有效记录，直接根据当前名称判断
                return 'ST' in current_name or 'st' in current_name

            # 取start_date最晚的记录
            latest_record = valid_records.sort_values('start_date').iloc[-1]
            stock_name_at_date = latest_record['name']

            return 'ST' in stock_name_at_date or 'st' in stock_name_at_date

        except Exception as e:
            print(f"  检查ST状态时出错 ({ts_code}): {e}")
            return False

    def get_income_for_roe(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取利润表中的归母净利润数据（用于计算TTM ROE）
        不传start_date/end_date时获取全量数据，确保历史季报齐全

        Args:
            ts_code: 股票代码
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）

        Returns:
            DataFrame: 利润表数据，包含 ann_date, end_date, n_income_attr_p
        """
        try:
            kwargs = dict(
                ts_code=ts_code,
                fields='ts_code,ann_date,end_date,n_income_attr_p'
            )
            if start_date:
                kwargs['start_date'] = start_date
            if end_date:
                kwargs['end_date'] = end_date
            df = self.api.call_with_retry(
                self.api.pro.income,
                api_name="income_for_roe",
                **kwargs
            )
            if df is None or df.empty:
                return pd.DataFrame()
            df = df.sort_values('end_date', ascending=False)
            return df
        except Exception as e:
            print(f"  获取利润表数据失败 ({ts_code}): {e}")
            return pd.DataFrame()

    def get_equity_for_roe(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取资产负债表中的归母所有者权益数据（用于计算TTM ROE）
        不传start_date/end_date时获取全量数据，确保历史季报齐全

        Args:
            ts_code: 股票代码
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）

        Returns:
            DataFrame: 资产负债表数据，包含 ann_date, end_date, total_hldr_eqy_exc_min_int
        """
        try:
            kwargs = dict(
                ts_code=ts_code,
                fields='ts_code,ann_date,end_date,total_hldr_eqy_exc_min_int'
            )
            if start_date:
                kwargs['start_date'] = start_date
            if end_date:
                kwargs['end_date'] = end_date
            df = self.api.call_with_retry(
                self.api.pro.balancesheet,
                api_name="balancesheet_for_roe",
                **kwargs
            )
            if df is None or df.empty:
                return pd.DataFrame()
            df = df.sort_values('end_date', ascending=False)
            return df
        except Exception as e:
            print(f"  获取资产负债表数据失败 ({ts_code}): {e}")
            return pd.DataFrame()

    def get_fina_indicator(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取财务指标数据（包含ROE等）

        Args:
            ts_code: 股票代码
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            DataFrame: 财务指标数据
        """
        try:
            df = self.api.call_with_retry(
                self.api.pro.fina_indicator,
                api_name="fina_indicator",
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                return pd.DataFrame()

            # 按报告期降序排列，最新的在前面
            df = df.sort_values('end_date', ascending=False)
            return df

        except Exception as e:
            print(f"  获取财务指标数据失败 ({ts_code}): {e}")
            return pd.DataFrame()
