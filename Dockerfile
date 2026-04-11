# 使用官方 Python 运行时作为基础镜像
# FROM docker.m.daocloud.io/python:3.12-slim
#FROM docker.m.daocloud.io/python:3.12-slim
#FROM docker.xuanyuan.me/python:3.12-slim
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.12-slim

# 设置时区为上海（python:3.12-slim 已内置 zoneinfo，无需安装 tzdata）
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo Asia/Shanghai > /etc/timezone

# 设置工作目录
WORKDIR /app

# 将 requirements.txt 复制到容器中
COPY requirements.txt .

# 安装项目依赖
RUN pip install --no-cache-dir -r requirements.txt

# 将 StockDataService 代码复制到 /app
# 先复制 VERSION 文件，这样可以用于构建时的版本标记
COPY VERSION /app/VERSION
COPY . .

# 确保启动脚本有可执行权限，并创建统一数据目录（可通过 -v 挂载覆盖）
RUN chmod +x start_servers.sh && \
    mkdir -p /app/data/cache /app/data/selector_output /app/data/invest_output /app/data/logs && \
    cp -r /app/invest/invest_plan/plans /app/_builtin_plans && \
    cp -r /app/invest/tushare_selector/strategies /app/_builtin_strategies

# 暴露端口
EXPOSE 9090 7070

# 环境变量默认值
# DATA_ROOT: 统一数据目录（缓存、选股CSV、调仓JSON、日志）
ENV DATA_ROOT=/app/data
# DAILY_CRON: 每日选股定时 cron 表达式（分 时 日 月 周），默认周一至周五 19:30
ENV DAILY_CRON="30 19 * * 1-5"

# 启动所有服务（HTTP Server + MCP Server + Scheduler）
CMD ["./start_servers.sh"]
