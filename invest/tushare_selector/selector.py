"""
选股引擎模块
负责执行选股逻辑：数据获取、因子计算、筛选、排名
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os
from functools import partial
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from data_source import StockDataSource
from factor_calculator import FactorCalculator, BasicDataExtractor
from strategy_parser import Strategy, FilterCondition, RankingRule


class StockSelector:
    """选股引擎"""

    # 缓存股票的行业信息，避免重复调用
    _industry_cache: Dict[str, dict] = {}

    def __init__(self, data_source: Optional[StockDataSource] = None):
        self.data_source = data_source if data_source else StockDataSource()
        self.factor_calc = FactorCalculator()
        self.basic_extractor = BasicDataExtractor()

    def select_stocks(self,
                     strategy: Strategy,
                     trade_date: str,
                     lookback_days: int = 250,
                     max_workers: int = 5) -> pd.DataFrame:
        """
        执行选股（串行版）

        Args:
            strategy: 选股策略
            trade_date: 选股日期 YYYYMMDD
            lookback_days: 历史数据回看天数
            max_workers: 并发线程数

        Returns:
            DataFrame: 选股结果
        """
        print(f"\n{'='*60}")
        print(f"策略: {strategy.strategy_name}")
        print(f"选股日期: {trade_date}")

        print(f"{'='*60}\n")

        # 步骤1: 获取股票列表
        print("【步骤1】获取股票列表...")
        # 排除北交所和科创板股票（果仁网不包含北交所和科创板）
        # 注意：不排除ST股票，因为需要在筛选阶段基于选股日的ST状态来判断
        stock_list_df = self.data_source.get_stock_list(list_status='L', exclude_bse=True, exclude_star=True, exclude_st=False)

        if stock_list_df.empty:
            print("❌ 无法获取股票列表")
            return pd.DataFrame()

        print(f"✅ 获取到 {len(stock_list_df)} 只股票")

        # 计算日期范围
        end_date_obj = datetime.strptime(trade_date, '%Y%m%d')
        start_date_obj = end_date_obj - timedelta(days=lookback_days)
        start_date = start_date_obj.strftime('%Y%m%d')

        # 步骤2: 计算所有股票的因子（使用线程池并发处理）
        print(f"\n【步骤2】计算股票因子 (历史回看 {lookback_days} 天)...")

        # 批量获取所有股票的行业信息
        ts_codes = stock_list_df['ts_code'].tolist()
        print("  批量获取行业信息...")
        industry_dict = self.data_source.batch_get_industry_info(ts_codes)
        print(f"  ✅ 获取到 {len(industry_dict)} 只股票的行业信息")

        # 使用线程池并发处理每只股票
        results = []
        failed_count = 0
        completed_count = 0
        total_stocks = len(stock_list_df)

        # 线程安全的计数器
        lock = threading.Lock()

        # 工作函数
        def process_stock(stock):
            nonlocal failed_count, completed_count
            ts_code = stock['ts_code']
            name = stock['name']
            try:
                stock_data = self._calculate_stock_factors_with_industry(ts_code, name, trade_date, start_date, industry_dict)
                with lock:
                    completed_count += 1
                    # 显示进度
                    if completed_count % 50 == 0 and completed_count > 0:
                        print(f"  已处理 {completed_count}/{total_stocks} 只股票...")
                return stock_data
            except Exception as e:
                with lock:
                    failed_count += 1
                    # 只打印前几个错误
                    if failed_count <= 5:
                        print(f"  ❌ {ts_code} {name}: {str(e)}")
                return None

        # 使用线程池并发处理
        # 限制并发数以避免API频率限制
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_stock, row): idx for idx, row in stock_list_df.iterrows()}

            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

        print(f"✅ 成功计算 {len(results)} 只股票的因子")
        print(f"   失败/跳过: {failed_count} 只股票\n")

        if not results:
            print("❌ 没有有效的股票数据")
            return pd.DataFrame()

        # 步骤3: 应用筛选条件
        print("【步骤3】应用筛选条件...")
        for i, filter_cond in enumerate(strategy.filters, 1):
            field_name = filter_cond.field
            operator = filter_cond.operator.value
            value = filter_cond.value
            print(f"  {i}. {field_name} {operator} {value}")

        # 转换为DataFrame以便筛选
        all_stocks_df = pd.DataFrame(results)

        # 应用每个筛选条件
        for filter_cond in strategy.filters:
            all_stocks_df = self._apply_filter_condition(all_stocks_df, filter_cond)

        print(f"✅ 筛选后剩余 {len(all_stocks_df)} 只股票\n")

        if all_stocks_df.empty:
            print("❌ 筛选后没有股票")
            return pd.DataFrame()

        # 步骤4: 排名
        print("【步骤4】应用排名规则...")
        for i, ranking_rule in enumerate(strategy.ranking, 1):
            field_name = ranking_rule.field
            order = "升序" if ranking_rule.order == "asc" else "降序"
            weight = ranking_rule.weight
            print(f"  {i}. {field_name} ({order}), 权重: {weight}")

        # 应用排名规则
        ranked_df = self._apply_ranking_rules(all_stocks_df, strategy.ranking)

        # 计算排名分
        ranked_df = self._calculate_rank_score(ranked_df, strategy.ranking)

        print(f"✅ 排名完成\n")

        return ranked_df

    def _calculate_stock_factors(self, ts_code: str, name: str,
                                  trade_date: str, start_date: str) -> Optional[Dict]:
        """计算单只股票的所有因子"""
        # 获取数据
        df_daily = self.data_source.get_daily_data(ts_code, start_date, trade_date)
        df_basic = self.data_source.get_daily_basic(ts_code, start_date, trade_date)

        if df_daily.empty or df_basic.empty:
            return None

        # 获取ROE所需数据（利润表 + 资产负债表）
        # 获取全量历史数据（不限start_date），确保TTM计算时上年同期季报齐全
        # 在factor_calculator中按ann_date <= trade_date过滤
        df_income = self.data_source.get_income_for_roe(ts_code)
        df_equity = self.data_source.get_equity_for_roe(ts_code)

        # 获取解禁数据（用于计算未来20日新增流通股占比）
        # 只获取在选股当天或之前已公布的解禁信息
        # 未来20个交易日：使用交易日历计算
        # 注意：不传入 ann_date 参数，让 Tushare 返回所有数据，然后在 factor_calculator 中过滤
        future_date = self.data_source.get_nth_trading_day(trade_date, n=20)
        start_date_for_share = trade_date
        df_share_float = self.data_source.get_new_share_data(
            ts_code, start_date_for_share, future_date
        )

        # 提取基础数据
        # df_basic是按trade_date降序排列的，使用iloc[0]获取最新数据
        circulation_market_cap = self.basic_extractor.get_circulation_market_cap(df_basic)
        current_circ_share = self.basic_extractor.get_current_circ_share(df_basic)

        # 计算因子
        price_amplitude = self.factor_calc.calculate_price_amplitude(df_daily)
        close_price = self.factor_calc.get_close_price(df_daily)

        # 使用 pb 计算每股净资产（避免调用财报接口）
        # pb = 市值 / 净资产，所以：每股净资产 = 股价 / pb
        pb = df_basic.iloc[0].get('pb', None)
        if pd.notna(pb) and pb > 0:
            net_assets_per_share = close_price / pb
        else:
            net_assets_per_share = np.nan

        future_20day_new_share_ratio = self.factor_calc.calculate_future_20day_new_share_ratio_from_share_float(
            df_share_float, current_circ_share, trade_date
        )
        volume = self.factor_calc.get_volume(df_daily)
        daily_return = self.factor_calc.calculate_daily_return(df_daily)

        # 计算ROE（净资产收益率）- TTM ROE = TTM净利润 / 平均净资产
        roe = self.factor_calc.calculate_roe(df_income, df_equity, trade_date)

        # 获取行业信息
        industry_info = self.data_source.get_industry_info(ts_code)

        # 获取选股日时的ST状态（使用历史名称）
        is_st_on_trade_date = False
        try:
            df_stock_basic = self.data_source.api.call_with_retry(
                self.data_source.api.pro.stock_basic,
                api_name="stock_basic",
                ts_code=ts_code
            )
            if df_stock_basic is not None and not df_stock_basic.empty:
                current_name = df_stock_basic.iloc[0]['name']
                # 获取名称变化历史
                df_namechange = self.data_source.get_stock_name_history(ts_code)
                if not df_namechange.empty:
                    # 找出在trade_date时有效的名称
                    trade_date_obj = pd.to_datetime(trade_date, format='%Y%m%d')
                    df_namechange['start_date'] = pd.to_datetime(df_namechange['start_date'])
                    if 'end_date' in df_namechange.columns:
                        df_namechange['end_date'] = pd.to_datetime(df_namechange['end_date'], errors='coerce')
                    valid_records = df_namechange[
                        (df_namechange['start_date'] <= trade_date_obj) &
                        (df_namechange['end_date'].isna() | (df_namechange['end_date'] > trade_date_obj))
                    ]
                    if not valid_records.empty:
                        # 取start_date最晚的记录
                        latest_record = valid_records.sort_values('start_date').iloc[-1]
                        stock_name_at_date = latest_record['name']
                        is_st_on_trade_date = 'ST' in stock_name_at_date or 'st' in stock_name_at_date
        except Exception as e:
            pass  # 静默处理错误，保持默认值False

        return {
            'ts_code': ts_code,
            'name': name,
            'industry': industry_info.get('industry', ''),
            'industry_l2': industry_info.get('industry_sw_l1', ''),
            'close': close_price,
            'volume': volume,
            'daily_return': daily_return,
            'price_amplitude': price_amplitude,
            'future_20day_new_share_ratio': future_20day_new_share_ratio,
            'net_assets_per_share': net_assets_per_share,
            'circulation_market_cap': circulation_market_cap,
            'total_market_cap': self.basic_extractor.get_total_market_cap(df_basic),
            'is_st_on_trade_date': is_st_on_trade_date,
            'roe': roe,  # 净资产收益率
        }

    def _calculate_stock_factors_with_industry(self, ts_code: str, name: str,
                                              trade_date: str, start_date: str,
                                              industry_dict: Dict[str, dict]) -> Optional[Dict]:
        """计算单只股票的所有因子（带行业信息，避免重复API调用）"""
        # 打印进度日志
        print(f'  正在获取 {ts_code} ({name}) 的数据...')
        # 获取数据
        df_daily = self.data_source.get_daily_data(ts_code, start_date, trade_date)
        df_basic = self.data_source.get_daily_basic(ts_code, start_date, trade_date)

        if df_daily.empty or df_basic.empty:
            return None

        # 获取ROE所需数据（利润表 + 资产负债表）
        # 获取全量历史数据（不限start_date），确保TTM计算时上年同期季报齐全
        # 在factor_calculator中按ann_date <= trade_date过滤
        df_income = self.data_source.get_income_for_roe(ts_code)
        df_equity = self.data_source.get_equity_for_roe(ts_code)

        # 获取解禁数据（用于计算未来20日新增流通股占比）
        # 使用 share_float API，获取未来20日内的所有解禁信息
        # 注意：不传入 ann_date 参数，让 Tushare 返回所有数据
        # 然后在 factor_calculator 中按 ann_date <= trade_date 过滤
        future_date = self.data_source.get_nth_trading_day(trade_date, n=20)
        start_date_for_share = trade_date

        df_share_float = self.data_source.get_new_share_data(
            ts_code, start_date_for_share, future_date
        )

        # 提取基础数据
        # df_basic是按trade_date降序排列的，使用iloc[0]获取最新数据
        circulation_market_cap = self.basic_extractor.get_circulation_market_cap(df_basic)
        current_circ_share = self.basic_extractor.get_current_circ_share(df_basic)

        # 计算因子
        price_amplitude = self.factor_calc.calculate_price_amplitude(df_daily)
        close_price = self.factor_calc.get_close_price(df_daily)
        # 使用 pb 计算每股净资产（避免调用财报接口）
        # pb = 市值 / 净资产，所以：每股净资产 = 股价 / pb
        pb = df_basic.iloc[0].get('pb', None)
        if pd.notna(pb) and pb > 0:
            net_assets_per_share = close_price / pb
        else:
            net_assets_per_share = np.nan

        future_20day_new_share_ratio = self.factor_calc.calculate_future_20day_new_share_ratio_from_share_float(
            df_share_float, current_circ_share, trade_date
        )
        volume = self.factor_calc.get_volume(df_daily)
        daily_return = self.factor_calc.calculate_daily_return(df_daily)

        # 计算ROE（净资产收益率）- TTM ROE = TTM净利润 / 平均净资产
        roe = self.factor_calc.calculate_roe(df_income, df_equity, trade_date)

        # 获取行业信息
        industry_info = industry_dict.get(ts_code, {})

        # 获取选股日时的ST状态（使用历史名称）
        # 直接在此处实现ST状态判断，避免API调用问题
        is_st_on_trade_date = False
        try:
            df_stock_basic = self.data_source.api.call_with_retry(
                self.data_source.api.pro.stock_basic,
                api_name="stock_basic",
                ts_code=ts_code
            )
            if df_stock_basic is not None and not df_stock_basic.empty:
                current_name = df_stock_basic.iloc[0]['name']
                # 获取名称变化历史
                df_namechange = self.data_source.get_stock_name_history(ts_code)
                if not df_namechange.empty:
                    # 找出在trade_date时有效的名称
                    trade_date_obj = pd.to_datetime(trade_date, format='%Y%m%d')
                    df_namechange['start_date'] = pd.to_datetime(df_namechange['start_date'])
                    if 'end_date' in df_namechange.columns:
                        df_namechange['end_date'] = pd.to_datetime(df_namechange['end_date'], errors='coerce')
                    valid_records = df_namechange[
                        (df_namechange['start_date'] <= trade_date_obj) &
                        (df_namechange['end_date'].isna() | (df_namechange['end_date'] > trade_date_obj))
                    ]
                    if not valid_records.empty:
                        # 取start_date最晚的记录
                        latest_record = valid_records.sort_values('start_date').iloc[-1]
                        stock_name_at_date = latest_record['name']
                        is_st_on_trade_date = 'ST' in stock_name_at_date or 'st' in stock_name_at_date
        except Exception as e:
            print(f"  检查ST状态时出错 ({ts_code}): {e}")

        return {
            'ts_code': ts_code,
            'name': name,
            'industry': industry_info.get('industry', ''),
            'industry_l2': industry_info.get('industry_sw_l1', ''),
            'close': close_price,
            'volume': volume,
            'daily_return': daily_return,
            'price_amplitude': price_amplitude,
            'future_20day_new_share_ratio': future_20day_new_share_ratio,
            'net_assets_per_share': net_assets_per_share,
            'circulation_market_cap': circulation_market_cap,
            'total_market_cap': self.basic_extractor.get_total_market_cap(df_basic),
            'is_st_on_trade_date': is_st_on_trade_date,  # 添加选股日时的ST状态
            'roe': roe,  # 净资产收益率
        }

    def _apply_filter_condition(self, df: pd.DataFrame,
                                 filter_cond: FilterCondition) -> pd.DataFrame:
        """应用单个筛选条件"""
        field = filter_cond.field
        operator = filter_cond.operator.value
        value = filter_cond.value

        original_count = len(df)

        # 特殊处理 exclude_st 字段
        if field == "exclude_st":
            if value is True:
                # 排除ST股票 - 使用选股日时的历史ST状态
                df = df[~df['is_st_on_trade_date']]
                filtered_count = len(df)
                if filtered_count < original_count:
                    print(f"     -> 筛选 '排除ST股票（选股日历史状态）': {original_count} -> {filtered_count}")
            return df

        if field not in df.columns:
            print(f"  ⚠️  警告: 字段 '{field}' 不存在，跳过此筛选条件")
            return df

        if operator == "gt":
            df = df[df[field] > value]
        elif operator == "gte":
            df = df[df[field] >= value]
        elif operator == "lt":
            df = df[df[field] < value]
        elif operator == "lte":
            df = df[df[field] <= value]
        elif operator == "eq":
            df = df[df[field] == value]
        elif operator == "ne":
            df = df[df[field] != value]
        elif operator == "contains":
            df = df[df[field].astype(str).str.contains(str(value), na=False)]
        elif operator == "not_contains":
            df = df[~df[field].astype(str).str.contains(str(value), na=False)]

        filtered_count = len(df)
        if filtered_count < original_count:
            print(f"     -> 筛选 '{field} {operator} {value}': {original_count} -> {filtered_count}")

        return df

    def _apply_ranking_rules(self, df: pd.DataFrame,
                              ranking_rules: List[RankingRule]) -> pd.DataFrame:
        """应用排名规则进行排序"""
        # 构建排序参数
        sort_columns = []
        ascending = []

        for rule in ranking_rules:
            if rule.field in df.columns:
                sort_columns.append(rule.field)
                ascending.append(rule.order == "asc")
            else:
                print(f"  ⚠️  警告: 排名字段 '{rule.field}' 不存在")

        if not sort_columns:
            print("  ⚠️  没有有效的排名字段")
            return df

        # 排序
        df = df.sort_values(by=sort_columns, ascending=ascending).reset_index(drop=True)

        return df

    def _calculate_rank_score(self, df: pd.DataFrame,
                              ranking_rules: List[RankingRule]) -> pd.DataFrame:
        """计算综合排名分"""
        if not ranking_rules:
            return df

        # 使用第一个排名规则计算排名分（简化实现）
        # 实际应用中可以根据权重综合多个排名
        rule = ranking_rules[0]
        field = rule.field

        if field not in df.columns:
            return df

        # 根据排名顺序计算百分位排名
        values = df[field]
        min_val = values.min()
        max_val = values.max()

        if max_val == min_val:
            df['rank_score'] = 100.0
        else:
            if rule.order == "asc":
                # 升序：值越小排名分越高
                df['rank_score'] = 100 * (max_val - values) / (max_val - min_val)
            else:
                # 降序：值越大排名分越高
                df['rank_score'] = 100 * (values - min_val) / (max_val - min_val)

        df['rank_score'] = df['rank_score'].round(2)

        return df

    def get_top_n(self, df: pd.DataFrame, n: int) -> pd.DataFrame:
        """获取排名前N的股票"""
        if df.empty:
            return df

        if n >= len(df):
            return df

        return df.head(n)

    def save_to_csv(self, df: pd.DataFrame, output_dir: str,
                    trade_date: str, strategy_name: str) -> str:
        """保存结果到CSV文件。
        
        每个策略使用独立子目录，同一选股日期只保留一个文件（直接覆盖）。
        文件名格式：{策略名}_{选股日期}.csv
        """
        os.makedirs(output_dir, exist_ok=True)

        # 生成文件名（不含时间戳，同一日期直接覆盖）
        safe_name = strategy_name.replace(' ', '_').replace('/', '_')
        filename = f"{safe_name}_{trade_date}.csv"
        filepath = os.path.join(output_dir, filename)

        # 重命名列以匹配测试用例
        column_mapping = {
            'ts_code': '股票代码',
            'name': '股票名',
            'industry': '行业分类',
            'industry_l2': '二级行业',
            'close': '收盘价',
            'volume': '当日成交量(万)',
            'daily_return': '1日涨幅',
            'price_amplitude': '股价振幅',
            'future_20day_new_share_ratio': '未来20日新增流通股占比',
            'net_assets_per_share': '每股净资产',
            'circulation_market_cap': '流通市值(亿)',
            'rank_score': '总排名分',
            'roe': '净资产收益率',
        }

        df_to_save = df.rename(columns=column_mapping)

        # 按列顺序保存
        columns_to_save = [
            '股票代码', '股票名', '行业分类', '二级行业', '收盘价', '当日成交量(万)',
            '1日涨幅', '股价振幅', '未来20日新增流通股占比', '每股净资产',
            '流通市值(亿)', '净资产收益率', '总排名分'
        ]

        df_to_save = df_to_save[[col for col in columns_to_save if col in df_to_save.columns]]

        df_to_save.to_csv(filepath, index=False, encoding='utf-8-sig')

        return filepath
