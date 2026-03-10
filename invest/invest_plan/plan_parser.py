"""
投资计划解析模块
解析 YAML 格式的投资计划配置
"""

import yaml
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class InvestPlan:
    """投资计划"""
    plan_name: str
    strategy_path: str   # 策略 yaml 的绝对路径
    first_plan_day: str  # YYYYMMDD
    interval: int        # 调仓间隔（交易日数量，0=每日调仓）
    top: int             # 取选股结果前 N 名
    yaml_path: str       # 计划 yaml 文件的绝对路径


class PlanParser:
    """投资计划解析器"""

    @staticmethod
    def _resolve_strategy_path(strategy_raw: str, yaml_abs: str) -> str:
        """
        解析策略文件绝对路径，支持两种写法：
        1. 相对于 plan yaml 文件的相对路径（原有方式）
        2. 仅文件名：在 STRATEGIES_DIR 环境变量指定目录下查找（挂载场景）

        Args:
            strategy_raw: yaml 中 strategy 字段的原始值
            yaml_abs:     plan yaml 文件的绝对路径

        Returns:
            策略文件绝对路径

        Raises:
            FileNotFoundError: 策略文件不存在
        """
        # 优先尝试相对于 yaml 文件目录解析
        strategy_abs = os.path.abspath(
            os.path.join(os.path.dirname(yaml_abs), strategy_raw)
        )
        if os.path.exists(strategy_abs):
            return strategy_abs

        # 降级：在 STRATEGIES_DIR 环境变量目录下按文件名查找
        strategies_dir = os.environ.get('STRATEGIES_DIR', '')
        if strategies_dir:
            fname = os.path.basename(strategy_raw)
            candidate = os.path.join(strategies_dir, fname)
            if os.path.exists(candidate):
                return candidate

        raise FileNotFoundError(
            f"策略文件不存在：{strategy_abs}"
            + (f"，也未在 STRATEGIES_DIR={strategies_dir} 中找到 {os.path.basename(strategy_raw)}" if strategies_dir else "")
        )

    @staticmethod
    def parse_from_file(yaml_file: str) -> InvestPlan:
        """
        从 YAML 文件解析投资计划

        Args:
            yaml_file: YAML 文件路径（绝对路径或相对路径）

        Returns:
            InvestPlan 数据类实例
        """
        yaml_abs = os.path.abspath(yaml_file)

        with open(yaml_abs, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        plan_name = config.get('plan_name')
        if not plan_name:
            raise ValueError(f"投资计划缺少 plan_name 字段：{yaml_abs}")

        strategy_raw = config.get('strategy')
        if not strategy_raw:
            raise ValueError(f"投资计划缺少 strategy 字段：{yaml_abs}")

        strategy_abs = PlanParser._resolve_strategy_path(strategy_raw, yaml_abs)

        first_plan_day = str(config.get('first_plan_day', ''))
        if not first_plan_day or len(first_plan_day) != 8:
            raise ValueError(f"first_plan_day 格式错误（需 YYYYMMDD）：{first_plan_day}")

        interval = int(config.get('interval', 5))
        if interval < 0:
            raise ValueError(f"interval 不能为负数：{interval}")

        top = int(config.get('top', 10))
        if top <= 0:
            raise ValueError(f"top 必须大于 0：{top}")

        return InvestPlan(
            plan_name=plan_name,
            strategy_path=strategy_abs,
            first_plan_day=first_plan_day,
            interval=interval,
            top=top,
            yaml_path=yaml_abs,
        )

    @staticmethod
    def load_all_from_dir(plans_dir: str) -> list:
        """
        加载目录下所有 yaml 投资计划

        Args:
            plans_dir: 投资计划 yaml 目录

        Returns:
            List[InvestPlan]
        """
        plans = []
        plans_dir = os.path.abspath(plans_dir)
        if not os.path.isdir(plans_dir):
            raise FileNotFoundError(f"投资计划目录不存在：{plans_dir}")

        for fname in sorted(os.listdir(plans_dir)):
            if fname.endswith('.yaml') or fname.endswith('.yml'):
                fpath = os.path.join(plans_dir, fname)
                try:
                    plan = PlanParser.parse_from_file(fpath)
                    plans.append(plan)
                except Exception as e:
                    print(f"  警告：跳过 {fname}，解析失败：{e}")

        return plans
