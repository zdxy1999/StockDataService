# 使用官方 Python 运行时作为基础镜像
# FROM docker.m.daocloud.io/python:3.12-slim
FROM python:3.12-slim


# 设置工作目录
WORKDIR /app

# 将 requirements.txt 复制到容器中
COPY requirements.txt .

# 安装项目依赖
RUN pip install --no-cache-dir -r requirements.txt

# 将项目代码复制到容器中
COPY . .

# 暴露 Flask 应用的端口
EXPOSE 5000

# 设置环境变量
ENV FLASK_APP=app.py

# 启动 Flask 应用
CMD ["./start_servers.sh"]