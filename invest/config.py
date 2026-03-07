"""
数据目录配置模块

所有需要持久化的文件统一存放在 DATA_ROOT 下，
该目录在 Docker 部署时通过 -v 挂载到宿主机。

目录结构：
/app/data/
├── cache/           # Tushare API 缓存
├── selector_output/ # 每日选股 CSV
│   └── {策略名}/{策略名}_{日期}.csv
├── invest_output/   # 投资计划调仓 JSON
│   └── {计划名}/{计划名}_{日期}.json
└── logs/            # 后台选股任务日志
    └── {策略名}/{策略名}_{日期}.log
"""

import os

# 数据根目录：优先使用环境变量 DATA_ROOT，默认 /app/data
# 本地开发时可通过 export DATA_ROOT=/tmp/stock_data 覆盖
DATA_ROOT = os.environ.get('DATA_ROOT', '/app/data')

# 各子目录
CACHE_DIR = os.path.join(DATA_ROOT, 'cache')
SELECTOR_OUTPUT_DIR = os.path.join(DATA_ROOT, 'selector_output')
INVEST_OUTPUT_DIR = os.path.join(DATA_ROOT, 'invest_output')
LOGS_DIR = os.path.join(DATA_ROOT, 'logs')


def ensure_dirs():
    """创建所有必要的数据目录（幂等）"""
    for d in (CACHE_DIR, SELECTOR_OUTPUT_DIR, INVEST_OUTPUT_DIR, LOGS_DIR):
        os.makedirs(d, exist_ok=True)
