"""
Tushare 多因子选股工具 - 命令行入口

使用方法:
    python main.py --strategy strategies/strategy1.yaml --date 20250228 --top 10 --output ./output
"""

import argparse
import sys
import os
from datetime import datetime
import pandas as pd

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from selector import StockSelector
from strategy_parser import StrategyParser


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Tushare 多因子选股工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py --strategy strategies/strategy1_min_circulation_market_cap.yaml --date 20250228
  python main.py --strategy strategies/strategy1_min_circulation_market_cap.yaml --date 20250228 --top 20
  python main.py -s strategies/strategy1.yaml -d 20250228 -t 10 -o ./output
        """
    )

    parser.add_argument(
        '-s', '--strategy',
        required=True,
        help='选股策略文件路径（YAML格式）'
    )

    parser.add_argument(
        '-d', '--date',
        required=True,
        help='选股日期（YYYYMMDD格式）'
    )

    parser.add_argument(
        '-t', '--top',
        type=int,
        default=10,
        help='输出前N只股票（默认：10）'
    )

    parser.add_argument(
        '-o', '--output',
        default=None,
        help='CSV文件输出目录（默认：根据策略名自动创建 ./output/{策略名} 子目录）'
    )

    parser.add_argument(
        '--lookback',
        type=int,
        default=250,
        help='历史数据回看天数（默认：250）'
    )

    args = parser.parse_args()

    # 验证日期格式
    try:
        datetime.strptime(args.date, '%Y%m%d')
    except ValueError:
        print(f"❌ 错误: 日期格式不正确，请使用 YYYYMMDD 格式")
        return 1

    # 验证策略文件存在
    if not os.path.exists(args.strategy):
        print(f"❌ 错误: 策略文件不存在: {args.strategy}")
        return 1

    # 解析策略
    print(f"\n{'='*60}")
    print("Tushare 多因子选股工具")
    print(f"{'='*60}")
    print(f"策略文件: {args.strategy}")
    print(f"选股日期: {args.date}")
    print(f"输出数量: {args.top}")
    print(f"回看天数: {args.lookback}")

    try:
        strategy = StrategyParser.parse_from_file(args.strategy)
        print(f"策略名称: {strategy.strategy_name}")
        print(f"筛选条件数: {len(strategy.filters)}")
        print(f"排名规则数: {len(strategy.ranking)}")
    except Exception as e:
        print(f"❌ 错误: 无法解析策略文件: {e}")
        return 1

    # 确定输出目录：未指定时按策略名自动创建子目录
    if args.output:
        output_dir = args.output
    else:
        safe_name = strategy.strategy_name.replace(' ', '_').replace('/', '_')
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', safe_name)
    print(f"输出目录: {output_dir}")

    # 执行选股
    selector = StockSelector()

    try:
        results_df = selector.select_stocks(
            strategy=strategy,
            trade_date=args.date,
            lookback_days=args.lookback
        )
    except Exception as e:
        print(f"❌ 选股失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    if results_df.empty:
        print("\n⚠️  没有符合条件的股票，生成空CSV文件")
        try:
            csv_path = selector.save_to_csv(
                results_df,
                output_dir,
                args.date,
                strategy.strategy_name
            )
            print(f"✅ 空结果文件已保存至: {csv_path}")
        except Exception as e:
            print(f"⚠️  保存CSV文件失败: {e}")
        return 0

    # 获取前N只股票
    top_n_df = selector.get_top_n(results_df, args.top)

    # 输出结果
    print(f"{'='*60}")
    print("选股结果（前{}只）".format(args.top))
    print(f"{'='*60}\n")

    # 打印表格
    print(f"{'排名':<4} {'股票代码':<12} {'股票名':<10} {'收盘价':<8} {'流通市值(亿)':<12} {'股价振幅':<10} {'总排名分':<10}")
    print("-" * 70)

    for idx, row in top_n_df.iterrows():
        rank = idx + 1
        ts_code = row['ts_code']
        name = row['name']
        close = f"{row['close']:.2f}" if pd.notna(row['close']) else "N/A"
        circ_cap = f"{row['circulation_market_cap']:.2f}" if pd.notna(row['circulation_market_cap']) else "N/A"
        amplitude = f"{row['price_amplitude']*100:.2f}%" if pd.notna(row['price_amplitude']) else "N/A"
        score = f"{row['rank_score']:.2f}"

        print(f"{rank:<4} {ts_code:<12} {name:<10} {close:<8} {circ_cap:<12} {amplitude:<10} {score:<10}")

    # 保存完整结果到CSV
    print(f"\n总计: 筛选出 {len(results_df)} 只股票")
    try:
        csv_path = selector.save_to_csv(
            results_df,
            output_dir,
            args.date,
            strategy.strategy_name
        )
        print(f"✅ 完整结果已保存至: {csv_path}")
    except Exception as e:
        print(f"⚠️  保存CSV文件失败: {e}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
