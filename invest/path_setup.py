"""
invest 模块内部路径配置工具

统一维护 invest_plan 和 tushare_selector 的路径常量与 sys.path 注入，
确保所有内部子模块的 import 在任何工作目录下都能正确解析。
"""

import os
import sys

# invest/ 目录自身（即本文件所在目录）
_INVEST_DIR = os.path.dirname(os.path.abspath(__file__))

# invest_plan 目录
INVEST_PLAN_DIR = os.path.join(_INVEST_DIR, 'invest_plan')

# tushare_selector 目录
SELECTOR_DIR = os.path.join(_INVEST_DIR, 'tushare_selector')

# invest_plan/plans 目录（内置计划所在位置）
PLANS_DIR = os.path.join(INVEST_PLAN_DIR, 'plans')

# tushare_selector/main.py 路径（用于后台子进程调用）
SELECTOR_MAIN = os.path.join(SELECTOR_DIR, 'main.py')


def ensure_paths():
    """
    将 invest_plan 和 tushare_selector 加入 sys.path（幂等）。
    在任何 import 内部子模块之前调用本函数。
    """
    for path in (INVEST_PLAN_DIR, SELECTOR_DIR):
        if path not in sys.path:
            sys.path.insert(0, path)
