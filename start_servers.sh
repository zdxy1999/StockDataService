#!/bin/bash

# 启动 Scheduler 在后台（每日选股定时任务）
python scheduler.py &

# 启动 MCP Server 在后台
python server_mcp.py &

# 启动 Flask 应用在前台
python server_http.py

# 等待所有后台进程
wait