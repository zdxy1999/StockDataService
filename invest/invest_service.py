"""
投资计划核心服务模块

将 guoren/invest_plan/main.py 的命令行逻辑重构为可被 HTTP/MCP Server 调用的 Service 层。
路径通过 config.py 统一管理，不再依赖 guoren 内部的硬编码路径。
"""

import json
import os
import sys
from datetime import datetime
from typing import Optional

from invest.config import SELECTOR_OUTPUT_DIR, INVEST_OUTPUT_DIR, ensure_dirs
from invest.path_setup import ensure_paths, PLANS_DIR, SELECTOR_MAIN, SELECTOR_DIR

# 注入 guoren 模块路径
ensure_paths()

# 延迟导入（路径注入后才能正确解析）
from plan_parser import PlanParser, InvestPlan
from trade_calendar import calc_rebalance_dates, find_prev_rebalance_date, get_trade_dates
from stock_picker_runner import ensure_stock_pick, read_top_n_stocks, get_csv_path, _lock_path
from strategy_parser import StrategyParser

# 数据更新完成时间（18:30）
_DATA_READY_HOUR = 18
_DATA_READY_MINUTE = 30


# ---------------------------------------------------------------------------
# 返回值数据类型定义
# ---------------------------------------------------------------------------

class InvestPlanResult:
    """单个投资计划调仓结果"""

    def __init__(self, status: str, plan_name: str = None, date: str = None,
                 prev_date: str = None, buy: list = None, sell: list = None,
                 hold: list = None, message: str = None):
        self.status = status          # "ok" | "computing" | "error"
        self.plan_name = plan_name
        self.date = date
        self.prev_date = prev_date
        self.buy = buy or []
        self.sell = sell or []
        self.hold = hold or []
        self.message = message        # 错误或提示信息

    def to_dict(self) -> dict:
        d = {"status": self.status}
        if self.plan_name:
            d["plan_name"] = self.plan_name
        if self.date:
            d["date"] = self.date
        if self.prev_date:
            d["prev_date"] = self.prev_date
        if self.buy is not None:
            d["buy"] = self.buy
        if self.sell is not None:
            d["sell"] = self.sell
        if self.hold is not None:
            d["hold"] = self.hold
        if self.message:
            d["message"] = self.message
        return d


# ---------------------------------------------------------------------------
# 内部工具函数
# ---------------------------------------------------------------------------

def _is_trade_day(date_yyyymmdd: str) -> bool:
    """判断某日期是否为交易日"""
    dates = get_trade_dates(date_yyyymmdd, date_yyyymmdd)
    return len(dates) > 0 and dates[0] == date_yyyymmdd


def _resolve_target_date(plan: InvestPlan, date_arg: Optional[str]) -> str:
    """
    确定本次查询的调仓日。

    - 若 date_arg 指定了日期，直接返回（不做交易日校验，由调用方校验）
    - 若未指定，自动取"最新调仓日"（当天 < 18:30 则退回上一个）

    Raises:
        ValueError: 无法确定调仓日
    """
    now = datetime.now()
    today = now.strftime('%Y%m%d')

    if date_arg:
        return date_arg

    rebalance_dates = calc_rebalance_dates(plan.first_plan_day, plan.interval, today)
    if not rebalance_dates:
        raise ValueError(f"从 {plan.first_plan_day} 到今天没有调仓日，请检查计划配置。")

    data_ready = now.replace(
        hour=_DATA_READY_HOUR, minute=_DATA_READY_MINUTE, second=0, microsecond=0
    )
    if now < data_ready and rebalance_dates[-1] == today:
        if len(rebalance_dates) < 2:
            raise ValueError(
                f"今日（{today}）是第一个调仓日，且当前时间 {now.strftime('%H:%M')} "
                f"早于 18:30，数据尚未更新，无法获取结果。"
            )
        return rebalance_dates[-2]

    return rebalance_dates[-1]


def _process_single_plan(plan: InvestPlan, target_date: str) -> InvestPlanResult:
    """
    处理单个投资计划，返回 InvestPlanResult。

    若选股 CSV 不存在，则在后台触发计算并立即返回 computing 状态。
    """
    plan_name = plan.plan_name
    safe_plan_name = plan_name.replace(' ', '_').replace('/', '_')

    # 1. 验证目标日期不早于计划开始日
    if target_date < plan.first_plan_day:
        return InvestPlanResult(
            status="error",
            plan_name=plan_name,
            date=target_date,
            message=f"指定日期 {target_date} 早于计划第一个调仓日 {plan.first_plan_day}。",
        )

    # 2. 计算调仓日列表
    rebalance_dates = calc_rebalance_dates(plan.first_plan_day, plan.interval, target_date)
    if not rebalance_dates:
        return InvestPlanResult(
            status="error",
            plan_name=plan_name,
            date=target_date,
            message=f"无法计算 {plan.first_plan_day} 到 {target_date} 的调仓日列表。",
        )

    # 3. 验证 target_date 是合法调仓日
    if target_date not in rebalance_dates:
        candidates = [d for d in rebalance_dates if d <= target_date]
        hint = f"最近的调仓日为 {candidates[-1]}" if candidates else "该计划尚无调仓日"
        return InvestPlanResult(
            status="error",
            plan_name=plan_name,
            date=target_date,
            message=f"{target_date} 不是计划「{plan_name}」的调仓日。{hint}。",
        )

    # 4. 找上一个调仓日
    prev_date = find_prev_rebalance_date(rebalance_dates, target_date)
    if prev_date is None:
        return InvestPlanResult(
            status="error",
            plan_name=plan_name,
            date=target_date,
            message=f"{target_date} 是计划「{plan_name}」的第一个调仓日，没有上期数据，无法计算买卖。",
        )

    # 5. 解析策略名
    strategy = StrategyParser.parse_from_file(plan.strategy_path)
    strategy_name = strategy.strategy_name

    # 6. 检查/触发两期 CSV
    curr_exists, curr_csv, curr_spawned = ensure_stock_pick(
        plan.strategy_path, strategy_name, target_date, output_root=SELECTOR_OUTPUT_DIR
    )
    prev_exists, prev_csv, prev_spawned = ensure_stock_pick(
        plan.strategy_path, strategy_name, prev_date, output_root=SELECTOR_OUTPUT_DIR
    )

    if not curr_exists or not prev_exists:
        missing = []
        if not curr_exists:
            missing.append(target_date)
        if not prev_exists:
            missing.append(prev_date)
        return InvestPlanResult(
            status="computing",
            plan_name=plan_name,
            date=target_date,
            prev_date=prev_date,
            message=f"以下日期的选股数据正在后台计算中，请稍后重试：{missing}",
        )

    # 7. 读取两期 top N 股票
    curr_stocks = read_top_n_stocks(curr_csv, plan.top)
    prev_stocks = read_top_n_stocks(prev_csv, plan.top)

    curr_map = {s["code"]: s["name"] for s in curr_stocks}
    prev_map = {s["code"]: s["name"] for s in prev_stocks}
    curr_codes = set(curr_map.keys())
    prev_codes = set(prev_map.keys())

    def _to_list(codes, name_map):
        return sorted(
            [{"code": c, "name": name_map[c]} for c in codes],
            key=lambda x: x["code"]
        )

    buy = _to_list(curr_codes - prev_codes, curr_map)
    sell = _to_list(prev_codes - curr_codes, prev_map)
    hold = _to_list(curr_codes & prev_codes, curr_map)

    result_data = {
        "plan": plan_name,
        "date": target_date,
        "prev_date": prev_date,
        "buy": buy,
        "sell": sell,
        "hold": hold,
    }

    # 8. 持久化 JSON
    out_dir = os.path.join(INVEST_OUTPUT_DIR, safe_plan_name)
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, f"{safe_plan_name}_{target_date}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    return InvestPlanResult(
        status="ok",
        plan_name=plan_name,
        date=target_date,
        prev_date=prev_date,
        buy=buy,
        sell=sell,
        hold=hold,
    )


# ---------------------------------------------------------------------------
# 对外暴露的 Service 函数
# ---------------------------------------------------------------------------

def get_invest_plan(plan_name: Optional[str] = None, date: Optional[str] = None) -> dict:
    """
    查询投资计划调仓结果。

    Args:
        plan_name: 投资计划名称（plan_name 字段值）；不指定则返回所有计划
        date:      调仓日期 YYYYMMDD；不指定则自动推断最新调仓日

    Returns:
        dict，结构如下：
        {
            "status": "ok" | "error" | "partial",
            "results": [ InvestPlanResult.to_dict(), ... ],
            "message": "..."   # 仅有错误时存在
        }
    """
    ensure_dirs()

    # 校验日期格式
    if date:
        try:
            datetime.strptime(date, '%Y%m%d')
        except ValueError:
            return {
                "status": "error",
                "message": f"日期格式不正确，请使用 YYYYMMDD 格式：{date}",
            }
        # 校验是否为交易日（仅显式传入时检查）
        if not _is_trade_day(date):
            return {
                "status": "error",
                "message": f"{date} 不是交易日，请传入有效交易日期。",
            }

    # 加载投资计划
    try:
        all_plans = PlanParser.load_all_from_dir(PLANS_DIR)
    except Exception as e:
        return {"status": "error", "message": f"加载投资计划失败：{e}"}

    if not all_plans:
        return {"status": "error", "message": f"未找到任何投资计划（目录：{PLANS_DIR}）"}

    # 按 plan_name 过滤
    if plan_name:
        plans = [p for p in all_plans if p.plan_name == plan_name]
        if not plans:
            available = [p.plan_name for p in all_plans]
            return {
                "status": "error",
                "message": f"未找到投资计划「{plan_name}」，可用计划：{available}",
            }
    else:
        plans = all_plans

    results = []
    for plan in plans:
        try:
            target_date = _resolve_target_date(plan, date)
        except ValueError as e:
            results.append(InvestPlanResult(
                status="error",
                plan_name=plan.plan_name,
                message=str(e),
            ).to_dict())
            continue

        outcome = _process_single_plan(plan, target_date)
        results.append(outcome.to_dict())

    # 汇总状态
    statuses = {r["status"] for r in results}
    if statuses == {"ok"}:
        overall = "ok"
    elif "error" in statuses and len(statuses) == 1:
        overall = "error"
    else:
        overall = "partial"

    return {"status": overall, "results": results}


# ---------------------------------------------------------------------------
# 定时任务专用：批量触发当天选股
# ---------------------------------------------------------------------------

def trigger_daily_stock_pick(date: str) -> list:
    """
    遍历所有 plans/ 下的计划，对指定交易日触发选股（幂等：CSV 已存在则跳过）。

    仅触发后台子进程，不等待结果。

    Args:
        date: 选股日期 YYYYMMDD（调用方需保证是交易日）

    Returns:
        list of dict: 每项包含 strategy_name, date, status("skipped"|"spawned"|"running")
    """
    ensure_dirs()

    try:
        plans = PlanParser.load_all_from_dir(PLANS_DIR)
    except Exception as e:
        print(f"[scheduler] 加载投资计划失败：{e}")
        return []

    report = []
    seen_strategies = set()

    for plan in plans:
        strategy = StrategyParser.parse_from_file(plan.strategy_path)
        strategy_name = strategy.strategy_name

        if strategy_name in seen_strategies:
            continue
        seen_strategies.add(strategy_name)

        csv_path = get_csv_path(strategy_name, date, output_root=SELECTOR_OUTPUT_DIR)
        if os.path.exists(csv_path):
            report.append({"strategy": strategy_name, "date": date, "status": "skipped"})
            print(f"[scheduler] 已存在，跳过：{strategy_name} @ {date}")
            continue

        exists, _, spawned = ensure_stock_pick(
            plan.strategy_path, strategy_name, date, output_root=SELECTOR_OUTPUT_DIR
        )
        if exists:
            status = "skipped"
        elif spawned:
            status = "spawned"
            print(f"[scheduler] 已触发后台计算：{strategy_name} @ {date}")
        else:
            status = "running"
            print(f"[scheduler] 后台任务已在运行中：{strategy_name} @ {date}")

        report.append({"strategy": strategy_name, "date": date, "status": status})

    return report
