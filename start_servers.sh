#!/bin/bash

# 启动 MCP Server 在后台
python server_mcp.py &

# 启动 Flask 应用在前台
python server_mcp.py

# 等待所有后台进程
wait