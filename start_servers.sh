#!/bin/bash

# 初始化：若挂载目录为空，从内置备份拷贝文件到挂载目录
PLANS_DIR="/app/invest/invest_plan/plans"
STRATEGIES_DIR="/app/invest/tushare_selector/strategies"

if [ -d "$PLANS_DIR" ] && [ -z "$(ls -A $PLANS_DIR 2>/dev/null)" ]; then
    echo "[init] plans 目录为空，拷贝内置计划到 $PLANS_DIR"
    cp -r /app/_builtin_plans/. "$PLANS_DIR"/
fi

if [ -d "$STRATEGIES_DIR" ] && [ -z "$(ls -A $STRATEGIES_DIR 2>/dev/null)" ]; then
    echo "[init] strategies 目录为空，拷贝内置策略到 $STRATEGIES_DIR"
    cp -r /app/_builtin_strategies/. "$STRATEGIES_DIR"/
fi

# 启动 Scheduler 在后台（每日选股定时任务）
python scheduler.py &

# 启动 MCP Server 在后台
python server_mcp.py &

# 启动 Flask 应用在前台
python server_http.py

# 等待所有后台进程
wait
