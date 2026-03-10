"""
invest 模块内部路径配置工具

统一维护 invest_plan 和 tushare_selector 的路径常量与 sys.path 注入，
确保所有内部子模块的 import 在任何工作目录下都能正确解析。

支持通过环境变量覆盖关键目录，便于 Docker 挂载外部 YAML 文件：
  PLANS_DIR       - 投资计划 YAML 目录
  STRATEGIES_DIR  - 选股策略 YAML 目录
"""

import os
import sys

# invest/ 目录自身（即本文件所在目录）
_INVEST_DIR = os.path.dirname(os.path.abspath(__file__))

# invest_plan 目录（代码目录，不可覆盖）
INVEST_PLAN_DIR = os.path.join(_INVEST_DIR, 'invest_plan')

# tushare_selector 目录（代码目录，不可覆盖）
SELECTOR_DIR = os.path.join(_INVEST_DIR, 'tushare_selector')

# invest_plan/plans 目录：优先读取环境变量 PLANS_DIR，支持挂载外部计划
PLANS_DIR = os.environ.get('PLANS_DIR', os.path.join(INVEST_PLAN_DIR, 'plans'))

# tushare_selector/strategies 目录：优先读取环境变量 STRATEGIES_DIR，支持挂载外部策略
STRATEGIES_DIR = os.environ.get('STRATEGIES_DIR', os.path.join(SELECTOR_DIR, 'strategies'))

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
