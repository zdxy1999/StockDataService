"""
因子计算模块
计算各种选股因子
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple


class FactorCalculator:
    """因子计算器"""

    @staticmethod
    def calculate_price_amplitude(df_daily: pd.DataFrame) -> float:
        """
        计算股价振幅 = (最高价 - 最低价) / 昨收价

        Args:
            df_daily: 日行情数据（至少包含high, low, close列）

        Returns:
            float: 股价振幅
        """
        if df_daily.empty or len(df_daily) < 2:
            return np.nan

        latest = df_daily.iloc[0]
        prev = df_daily.iloc[1]

        amplitude = (latest['high'] - latest['low']) / prev['close']
        return amplitude

    @staticmethod
    def calculate_daily_return(df_daily: pd.DataFrame) -> float:
        """
        计算1日涨幅 = (今收 - 昨收) / 昨收

        Args:
            df_daily: 日行情数据（至少包含close列）

        Returns:
            float: 1日涨幅
        """
        if df_daily.empty or len(df_daily) < 2:
            return np.nan

        latest = df_daily.iloc[0]
        prev = df_daily.iloc[1]

        daily_return = (latest['close'] - prev['close']) / prev['close']
        return daily_return

    @staticmethod
    def calculate_net_assets_per_share(df_balance: pd.DataFrame, total_share: float) -> float:
        """
        计算每股净资产 = 净资产 / 总股本

        Args:
            df_balance: 资产负债表数据
            total_share: 总股本

        Returns:
            float: 每股净资产
        """
        if df_balance.empty or total_share == 0:
            return np.nan

        latest = df_balance.iloc[0]
        # total_hldr_eqy_exc_min_int 是股东权益合计（不含少数股东权益），即净资产
        net_assets = latest.get('total_hldr_eqy_exc_min_int', np.nan)

        if pd.isna(net_assets) or net_assets == 0:
            return np.nan

        # total_share 单位是万股，需要转换成股数（除以10000）得到每股净资产
        return net_assets / total_share

    @staticmethod
    def calculate_future_20day_new_share_ratio(df_daily_basic_future: pd.DataFrame,
                                                current_circ_share: float) -> float:
        """
        计算未来20日新增流通股占比
        使用历史流通股本数据，计算未来20个交易日内的最大流通股本增量

        Args:
            df_daily_basic_future: 未来一段时间的每日基本面数据（包含流通股本）
            current_circ_share: 当前流通股本（单位：万股）

        Returns:
            float: 未来20日新增流通股占比

        Note: 这个方法使用的是 daily_basic 数据，包含未来数据，不适合历史回测。
        请使用 calculate_future_20day_new_share_ratio_from_share_float 进行历史回测。
        """
        if current_circ_share == 0:
            return np.nan

        if df_daily_basic_future.empty:
            return 0.0

        # 获取未来20个交易日的流通股本
        # df_daily_basic_future 的 float_share 单位是万股
        future_float_shares = df_daily_basic_future['float_share'].tolist()

        # 计算未来20个交易日的最大流通股本
        max_future_float = max(future_float_shares) if future_float_shares else 0

        # 计算增量
        increase = max_future_float - current_circ_share

        # 计算占比
        ratio = increase / current_circ_share if increase > 0 else 0.0

        return ratio

    @staticmethod
    def calculate_future_20day_new_share_ratio_from_share_float(df_share_float: pd.DataFrame,
                                                                current_circ_share: float,
                                                                trade_date: str) -> float:
        """
        计算未来20日新增流通股占比（基于 share_float 数据）
        使用 share_float 数据中公告日 <= 选股日期的解禁信息

        Args:
            df_share_float: 解禁数据（share_float API 返回的数据，已按 ann_date 过滤）
                           float_share 单位是股（shares）
            current_circ_share: 当前流通股本（单位：万股）
            trade_date: 选股日期（YYYYMMDD）

        Returns:
            float: 未来20日新增流通股占比

        Note: 这个方法使用的是 share_float 数据，包含 ann_date，适合历史回测。
        只会计算在选股日之前已公告的解禁信息。
        """
        if current_circ_share == 0:
            return np.nan

        if df_share_float.empty:
            return 0.0

        # 只计算公告日 <= 选股日期的解禁（过滤掉未来公告的解禁）
        df_share_float_filtered = df_share_float[df_share_float['ann_date'] <= trade_date].copy()

        if df_share_float_filtered.empty:
            return 0.0

        # 去重：同一个股东的解禁只计算一次（按holder_name去重）
        # 注意：Tushare返回的数据可能有重复，同一股东在不同日期有相同解禁记录
        df_share_float_filtered = df_share_float_filtered.drop_duplicates(
            subset=['holder_name']
        )

        # share_float.float_share 单位是股（shares），需要转换为万股
        # 汇总所有解禁股数
        total_unlock_shares = df_share_float_filtered['float_share'].sum()

        # 转换为万股
        total_unlock_shares_wan = total_unlock_shares / 10000

        # 计算占比
        ratio = total_unlock_shares_wan / current_circ_share

        return ratio

    @staticmethod
    def get_close_price(df_daily: pd.DataFrame) -> float:
        """
        获取收盘价

        Args:
            df_daily: 日行情数据

        Returns:
            float: 收盘价
        """
        if df_daily.empty:
            return np.nan

        # df_daily是按trade_date降序排列的，所以iloc[0]是最新的（trade_date当天）
        return df_daily.iloc[0]['close']

    @staticmethod
    def get_volume(df_daily: pd.DataFrame) -> float:
        """
        获取成交量（万股）

        Args:
            df_daily: 日行情数据

        Returns:
            float: 成交量（万股）
        """
        if df_daily.empty:
            return np.nan

        # Tushare的vol单位是手，1手=100股，转换为万股需要除以100
        # df_daily是按trade_date降序排列的，所以iloc[0]是最新的（trade_date当天）
        return df_daily.iloc[0]['vol'] / 100

    @staticmethod
    def calculate_roe(df_income: pd.DataFrame, df_equity: pd.DataFrame, trade_date: str) -> float:
        """
        计算TTM净资产收益率(ROE)，与果仁网口径一致：
        ROE = TTM(净利润) / AvgQ(所有者权益合计, 4, 1)
        即：过去12个月归母净利润 / 一季度前起过去5个季度的平均归母所有者权益

        Args:
            df_income: 利润表数据（income接口返回，含 ann_date, end_date, n_income_attr_p）
            df_equity: 资产负债表数据（balancesheet接口返回，含 ann_date, end_date, total_hldr_eqy_exc_min_int）
            trade_date: 选股日期（YYYYMMDD），只使用 ann_date <= trade_date 的数据

        Returns:
            float: 净资产收益率（小数形式，如0.15表示15%）
        """
        if df_income.empty or df_equity.empty:
            return np.nan

        # 只使用选股日期前已公告的数据
        income_valid = df_income[df_income['ann_date'] <= trade_date].drop_duplicates('end_date')
        equity_valid = df_equity[df_equity['ann_date'] <= trade_date].drop_duplicates('end_date')

        if income_valid.empty or equity_valid.empty:
            return np.nan

        # ---- 第一步：计算TTM净利润 ----
        # TTM净利润 = 最新季报累计净利润 + 上年年报净利润 - 上年同期季报累计净利润
        latest_income = income_valid.iloc[0]
        latest_end = latest_income['end_date']          # 如 20230930
        latest_net = latest_income['n_income_attr_p']

        latest_month = int(latest_end[4:6])

        if latest_month == 12:
            # 最新就是年报，TTM净利润直接用年报
            ttm_net_profit = latest_net
        else:
            # 找上年年报：end_date = (latest_year-1)1231
            prev_year = str(int(latest_end[:4]) - 1)
            prev_annual_end = prev_year + '1231'
            prev_annual = income_valid[income_valid['end_date'] == prev_annual_end]

            # 找上年同期季报：end_date = (latest_year-1) + latest_month
            prev_same_end = prev_year + latest_end[4:]
            prev_same = income_valid[income_valid['end_date'] == prev_same_end]

            if prev_annual.empty:
                return np.nan

            prev_annual_net = prev_annual.iloc[0]['n_income_attr_p']

            if prev_same.empty:
                # 降级策略：上年同期季报缺失时，尝试用更早年份数据
                # 若上年年报存在但同期季报缺失（数据源问题），
                # 回退到直接用上年年报作为TTM近似值（准确性下降但优于N/A）
                ttm_net_profit = prev_annual_net
            else:
                prev_same_net = prev_same.iloc[0]['n_income_attr_p']
                # TTM = 最新季报 + 上年年报 - 上年同期
                ttm_net_profit = latest_net + prev_annual_net - prev_same_net

        if pd.isna(ttm_net_profit):
            return np.nan

        # ---- 第二步：计算平均所有者权益 ----
        # AvgQ(权益, 4, 1) = 从"一季度前"起往前数4个季度的平均值
        # 即：取 latest_end 往前推1季度 至 往前推4季度（共4个季度端点）的均值
        def prev_quarter_end(end_date: str, n: int) -> str:
            """往前推n个季度的季末日期"""
            year = int(end_date[:4])
            month = int(end_date[4:6])
            # 季度映射：3->12(prev year), 6->3, 9->6, 12->9
            quarter_months = [3, 6, 9, 12]
            idx = quarter_months.index(month)
            for _ in range(n):
                idx -= 1
                if idx < 0:
                    idx = 3
                    year -= 1
            return f"{year}{quarter_months[idx]:02d}{'31' if quarter_months[idx] == 12 else ('30' if quarter_months[idx] in [6, 9] else '31')}"

        # 修正：月份对应的正确季末日期
        def get_quarter_end(year: int, month: int) -> str:
            last_days = {3: '31', 6: '30', 9: '30', 12: '31'}
            return f"{year}{month:02d}{last_days[month]}"

        def prev_n_quarter(end_date: str, n: int) -> str:
            year = int(end_date[:4])
            month = int(end_date[4:6])
            quarter_months = [3, 6, 9, 12]
            idx = quarter_months.index(month)
            for _ in range(n):
                idx -= 1
                if idx < 0:
                    idx = 3
                    year -= 1
            return get_quarter_end(year, quarter_months[idx])

        # 取从 T-1季度 到 T-4季度 共4个季末的权益值（AvgQ第二个参数=4，第三个=1表示滞后1季度）
        equity_values = []
        for lag in range(1, 6):  # lag=1,2,3,4,5 共5个端点，取均值（4个区间的均值通常用5个端点）
            qend = prev_n_quarter(latest_end, lag)
            row = equity_valid[equity_valid['end_date'] == qend]
            if not row.empty:
                val = row.iloc[0]['total_hldr_eqy_exc_min_int']
                if pd.notna(val):
                    equity_values.append(val)

        if len(equity_values) < 2:
            return np.nan

        avg_equity = np.mean(equity_values)

        if avg_equity <= 0:
            return np.nan

        # ROE = TTM净利润 / 平均净资产
        roe = ttm_net_profit / avg_equity

        return roe


class BasicDataExtractor:
    """基础数据提取器"""

    @staticmethod
    def get_circulation_market_cap(df_daily_basic: pd.DataFrame) -> float:
        """
        获取流通市值（亿元）

        Args:
            df_daily_basic: 每日基本面数据

        Returns:
            float: 流通市值（亿元）
        """
        if df_daily_basic.empty:
            return np.nan

        # Tushare的circ_mv单位是万元，需要转换为亿元
        # df_daily_basic是按trade_date降序排列的，取第一行最新数据
        return round(df_daily_basic.iloc[0].get('circ_mv', np.nan) / 10000, 2)

    @staticmethod
    def get_total_market_cap(df_daily_basic: pd.DataFrame) -> float:
        """
        获取总市值（亿元）

        Args:
            df_daily_basic: 每日基本面数据

        Returns:
            float: 总市值（亿元）
        """
        if df_daily_basic.empty:
            return np.nan

        # Tushare的total_mv单位是万元，转换为亿元
        # df_daily_basic是按trade_date降序排列的，所以iloc[0]是最新的（trade_date当天）
        return round(df_daily_basic.iloc[0].get('total_mv', np.nan) / 10000, 2)

    @staticmethod
    def check_is_st(stock_name: str) -> bool:
        """
        检查是否为ST股票

        Args:
            stock_name: 股票名称

        Returns:
            bool: 是否为ST股票
        """
        if pd.isna(stock_name):
            return False
        return 'ST' in str(stock_name)

    @staticmethod
    def get_industry_classification(stock_info: dict, level: int = 1) -> str:
        """
        获取行业分类

        Args:
            stock_info: 股票信息
            level: 行业级别 1-一级, 2-二级

        Returns:
            str: 行业分类名称
        """
        if level == 2:
            return stock_info.get('industry', '')
        return stock_info.get('industry_sw_l1', '')

    @staticmethod
    def get_total_share(df_balance: pd.DataFrame) -> float:
        """
        获取总股本

        Args:
            df_balance: 资产负债表数据

        Returns:
            float: 总股本
        """
        if df_balance.empty:
            return np.nan

        return df_balance.iloc[0].get('total_share', np.nan)

    @staticmethod
    def get_current_circ_share(df_daily_basic: pd.DataFrame) -> float:
        """
        获取当前流通股本

        Args:
            df_daily_basic: 每日基本面数据

        Returns:
            float: 流通股本（万股）
        """
        if df_daily_basic.empty:
            return np.nan

        # Tushare的float_share单位是万股
        # df_daily_basic是按trade_date降序排列的，所以iloc[0]是最新的（trade_date当天）
        return df_daily_basic.iloc[0].get('float_share', np.nan)
