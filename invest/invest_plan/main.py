"""
投资计划命令行入口

使用方法:
    python invest_plan/main.py                              # 处理所有计划，自动推断调仓日
    python invest_plan/main.py --plan invest_plans/xxx.yaml # 处理单个计划
    python invest_plan/main.py --date 20240408              # 指定调仓日
    python invest_plan/main.py --plan xxx.yaml --date 20240408
"""

import argparse
import json
import os
import sys
from datetime import datetime

# 将 invest_plan/ 自身加入路径
_INVEST_PLAN_DIR = os.path.dirname(os.path.abspath(__file__))
if _INVEST_PLAN_DIR not in sys.path:
    sys.path.insert(0, _INVEST_PLAN_DIR)

# 将 tushare_selector/ 加入路径（trade_calendar 内部也会加，但这里显式加更清晰）
_SELECTOR_DIR = os.path.abspath(os.path.join(_INVEST_PLAN_DIR, '..', 'tushare_selector'))
if _SELECTOR_DIR not in sys.path:
    sys.path.insert(0, _SELECTOR_DIR)

from plan_parser import PlanParser, InvestPlan
from trade_calendar import calc_rebalance_dates, find_prev_rebalance_date, get_trade_dates
from stock_picker_runner import ensure_stock_pick, read_top_n_stocks

# 项目根目录
_PROJECT_ROOT = os.path.abspath(os.path.join(_INVEST_PLAN_DIR, '..'))
# 投资计划默认目录
_PLANS_DIR = os.path.join(_INVEST_PLAN_DIR, 'plans')
# JSON 输出根目录
_OUTPUT_ROOT = os.path.join(_INVEST_PLAN_DIR, 'output')

# 数据更新完成时间（18:30）
_DATA_READY_HOUR = 18
_DATA_READY_MINUTE = 30


def _resolve_target_date(plan: InvestPlan, date_arg: str = None) -> str:
    """
    确定本次需要查询的调仓日。

    - 若 date_arg 指定了日期，直接使用
    - 若未指定，自动取"当前时间前最后一个调仓日"
      （若当前时间 < 18:30 则再往前退一个调仓日）

    Returns:
        str: 目标调仓日 YYYYMMDD

    Raises:
        SystemExit: 无法确定调仓日时退出
    """
    now = datetime.now()
    today = now.strftime('%Y%m%d')

    if date_arg:
        target = date_arg
    else:
        # 自动推断：取到今天（含）的调仓日列表，再根据时间决定用哪个
        rebalance_dates = calc_rebalance_dates(plan.first_plan_day, plan.interval, today)
        if not rebalance_dates:
            print(f"错误：从 {plan.first_plan_day} 到今天没有调仓日，请检查计划配置。")
            sys.exit(1)

        # 若当前时间 < 18:30，数据还未更新，最后一个调仓日不可用
        data_ready = now.replace(
            hour=_DATA_READY_HOUR, minute=_DATA_READY_MINUTE, second=0, microsecond=0
        )
        if now < data_ready and rebalance_dates[-1] == today:
            # 今日数据未就绪，退回上一个调仓日
            if len(rebalance_dates) < 2:
                print(
                    f"错误：今日（{today}）是第一个调仓日，且当前时间 {now.strftime('%H:%M')} "
                    f"早于 18:30，数据尚未更新，无法获取结果。"
                )
                sys.exit(1)
            print(
                f"提示：当前时间 {now.strftime('%H:%M')} 早于 18:30，今日数据尚未更新，"
                f"使用上一个调仓日 {rebalance_dates[-2]} 的结果。"
            )
            target = rebalance_dates[-2]
        else:
            target = rebalance_dates[-1]

    return target


def _process_plan(plan: InvestPlan, target_date: str) -> dict:
    """
    处理单个投资计划，返回调仓结果 dict。

    Raises:
        SystemExit: 出现无法继续的错误时退出
    """
    print(f"\n{'='*60}")
    print(f"计划：{plan.plan_name}")
    print(f"策略：{plan.strategy_path}")
    print(f"调仓日：{target_date}")
    print(f"{'='*60}")

    # 1. 验证目标日期不早于计划开始日
    if target_date < plan.first_plan_day:
        print(
            f"错误：指定日期 {target_date} 早于计划第一个调仓日 {plan.first_plan_day}。"
        )
        return None

    # 2. 计算到目标日期为止的调仓日列表
    rebalance_dates = calc_rebalance_dates(plan.first_plan_day, plan.interval, target_date)
    if not rebalance_dates:
        print(f"错误：无法计算 {plan.first_plan_day} 到 {target_date} 的调仓日列表。")
        return None

    # 3. 验证 target_date 是合法调仓日
    if target_date not in rebalance_dates:
        # 找最近的调仓日提示
        candidates = [d for d in rebalance_dates if d <= target_date]
        hint = f"最近的调仓日为 {candidates[-1]}" if candidates else "该计划尚无调仓日"
        print(
            f"错误：{target_date} 不是计划「{plan.plan_name}」的调仓日。{hint}。"
        )
        return None

    # 4. 找上一个调仓日
    prev_date = find_prev_rebalance_date(rebalance_dates, target_date)
    if prev_date is None:
        print(
            f"错误：{target_date} 是计划「{plan.plan_name}」的第一个调仓日，"
            f"没有上期数据，无法计算买卖。"
        )
        return None

    print(f"上期调仓日：{prev_date}")

    # 5. 读取策略名（从策略 yaml）
    _selector_path = _SELECTOR_DIR
    if _selector_path not in sys.path:
        sys.path.insert(0, _selector_path)
    from strategy_parser import StrategyParser
    strategy = StrategyParser.parse_from_file(plan.strategy_path)
    strategy_name = strategy.strategy_name

    # 6. 检查两期 CSV 是否存在
    curr_exists, curr_csv, curr_spawned = ensure_stock_pick(plan.strategy_path, strategy_name, target_date)
    prev_exists, prev_csv, prev_spawned = ensure_stock_pick(plan.strategy_path, strategy_name, prev_date)

    newly_spawned = []
    already_running = []
    if not curr_exists:
        (newly_spawned if curr_spawned else already_running).append(target_date)
    if not prev_exists:
        (newly_spawned if prev_spawned else already_running).append(prev_date)

    if newly_spawned or already_running:
        if newly_spawned:
            print(
                f"\n提示：以下日期的选股数据不存在，已在后台启动计算，请稍后重新运行：\n"
                + '\n'.join(f"  - {d}" for d in newly_spawned)
            )
            # 打印日志文件路径，方便实时跟踪进度
            from stock_picker_runner import _lock_path, get_csv_path
            for d in newly_spawned:
                log = _lock_path(strategy_name, d).replace('.running', '.log')
                print(f"    进度日志：tail -f {log}")
        if already_running:
            print(
                f"\n提示：以下日期的选股正在后台计算中，请稍后重新运行：\n"
                + '\n'.join(f"  - {d}" for d in already_running)
            )
            from stock_picker_runner import _lock_path
            for d in already_running:
                log = _lock_path(strategy_name, d).replace('.running', '.log')
                print(f"    进度日志：tail -f {log}")
        return None

    # 7. 读取两期 top N 股票
    curr_stocks = read_top_n_stocks(curr_csv, plan.top)
    prev_stocks = read_top_n_stocks(prev_csv, plan.top)

    # 构建以 code 为 key 的 dict，方便做集合运算同时保留名称
    curr_map = {s["code"]: s["name"] for s in curr_stocks}
    prev_map = {s["code"]: s["name"] for s in prev_stocks}

    curr_codes = set(curr_map.keys())
    prev_codes = set(prev_map.keys())

    def _to_list(codes, name_map):
        return sorted([{"code": c, "name": name_map[c]} for c in codes], key=lambda x: x["code"])

    buy  = _to_list(curr_codes - prev_codes, curr_map)
    sell = _to_list(prev_codes - curr_codes, prev_map)
    hold = _to_list(curr_codes & prev_codes, curr_map)

    result = {
        "plan": plan.plan_name,
        "date": target_date,
        "prev_date": prev_date,
        "buy": buy,
        "sell": sell,
        "hold": hold,
    }

    # 8. 保存 JSON
    safe_plan_name = plan.plan_name.replace(' ', '_').replace('/', '_')
    out_dir = os.path.join(_OUTPUT_ROOT, safe_plan_name)
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, f"{safe_plan_name}_{target_date}.json")

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result, json_path


def _print_result(result: dict, json_path: str) -> None:
    """格式化打印调仓结果"""
    def _fmt(stocks):
        if not stocks:
            return "无"
        return ", ".join(f"{s['code']}({s['name']})" for s in stocks)

    print(f"\n{'='*60}")
    print(f"调仓结果：{result['plan']}  {result['date']}")
    print(f"（上期：{result['prev_date']}）")
    print(f"{'='*60}")
    print(f"买入（{len(result['buy'])} 只）：{_fmt(result['buy'])}")
    print(f"卖出（{len(result['sell'])} 只）：{_fmt(result['sell'])}")
    print(f"持有（{len(result['hold'])} 只）：{_fmt(result['hold'])}")
    print(f"\nJSON 已保存至：{json_path}")


def main():
    parser = argparse.ArgumentParser(
        description='投资计划调仓工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python invest_plan/main.py
  python invest_plan/main.py --plan invest_plans/example_plan.yaml
  python invest_plan/main.py --date 20240408
  python invest_plan/main.py --plan invest_plans/example_plan.yaml --date 20240408
        """,
    )
    parser.add_argument(
        '--plan', '-p',
        default=None,
        help='投资计划 YAML 文件路径；不指定则处理 invest_plans/ 下所有计划',
    )
    parser.add_argument(
        '--date', '-d',
        default=None,
        help='调仓日期 YYYYMMDD；不指定则自动推断最新调仓日',
    )
    args = parser.parse_args()

    # 验证日期格式
    if args.date:
        try:
            datetime.strptime(args.date, '%Y%m%d')
        except ValueError:
            print("错误：日期格式不正确，请使用 YYYYMMDD 格式。")
            sys.exit(1)

    # 加载投资计划
    if args.plan:
        plan_path = os.path.abspath(args.plan)
        if not os.path.exists(plan_path):
            print(f"错误：计划文件不存在：{plan_path}")
            sys.exit(1)
        try:
            plans = [PlanParser.parse_from_file(plan_path)]
        except Exception as e:
            print(f"错误：无法解析计划文件：{e}")
            sys.exit(1)
    else:
        try:
            plans = PlanParser.load_all_from_dir(_PLANS_DIR)
        except FileNotFoundError as e:
            print(f"错误：{e}")
            sys.exit(1)

    if not plans:
        print(f"错误：在 {_PLANS_DIR} 中未找到任何投资计划。")
        sys.exit(1)

    any_success = False
    for plan in plans:
        target_date = _resolve_target_date(plan, args.date)
        outcome = _process_plan(plan, target_date)
        if outcome is not None:
            result, json_path = outcome
            _print_result(result, json_path)
            any_success = True

    if not any_success:
        sys.exit(1)


if __name__ == '__main__':
    main()
