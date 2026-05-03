# Stock Data Service 完整部署指南

本文档提供详细的部署步骤和故障排除指南。

## 服务器信息

- **服务器地址**: 47.99.207.160
- **用户**: root
- **SSH密钥**: ~/.ssh/zdxy-ali.pem
- **连接命令**: `ssh -i ~/.ssh/zdxy-ali.pem root@47.99.207.160`

## 服务端口

- **HTTP服务**: 9090端口 (Flask REST API)
- **MCP服务**: 7070端口 (FastMCP服务)

## 数据持久化

- **数据卷**: /data/stock-data-service
- **容器挂载点**: /app/data
- **包含内容**:
  - cache/: 缓存数据
  - selector_output/: 选股结果
  - invest_output/: 投资计划输出
  - logs/: 日志文件

## 环境变量

| 变量 | 值 | 说明 |
|------|-----|------|
| DATA_ROOT | /app/data | 统一数据目录根路径 |
| DAILY_CRON | "30 19 * * 1-5" | 定时任务cron表达式（工作日19:30） |
| TZ | Asia/Shanghai | 时区设置 |

## 详细部署步骤

### 1. 准备工作

确认版本号已更新：
```bash
cat VERSION
```

确认代码已提交：
```bash
git status
git diff
```

### 2. 构建镜像

使用Docker构建amd64架构镜像：
```bash
VERSION=$(cat VERSION)
docker build --platform linux/amd64 \
  -t stock-data-service:${VERSION}-amd64 \
  .
```

**构建注意事项**:
- 确保Docker守护进程正在运行
- 构建过程需要网络连接下载依赖
- 构建时间约2-5分钟

### 3. 保存镜像

将Docker镜像保存为tar文件：
```bash
mkdir -p dist
docker save stock-data-service:${VERSION}-amd64 \
  -o dist/stock-data-service_amd64_${VERSION}.tar
```

**文件大小**: 约400-450MB

### 4. 上传镜像

使用scp上传到服务器：
```bash
scp -i ~/.ssh/zdxy-ali.pem \
  dist/stock-data-service_amd64_${VERSION}.tar \
  root@47.99.207.160:/root/
```

**上传时间**: 取决于网络速度，通常2-10分钟

### 5. 服务器部署

#### 5.1 连接服务器
```bash
ssh -i ~/.ssh/zdxy-ali.pem root@47.99.207.160
```

#### 5.2 加载新镜像
```bash
docker load -i /root/stock-data-service_amd64_${VERSION}.tar
```

#### 5.3 停止旧容器
```bash
docker stop stock-data-service
docker rm stock-data-service
```

**注意**: 这会短暂中断服务（通常<10秒）

#### 5.4 启动新容器
```bash
docker run -d \
  --name stock-data-service \
  -p 9090:9090 \
  -p 7070:7070 \
  -v /data/stock-data-service:/app/data \
  -e DATA_ROOT=/app/data \
  -e DAILY_CRON="30 19 * * 1-5" \
  --restart=always \
  stock-data-service:${VERSION}-amd64
```

### 6. 验证部署

#### 6.1 检查容器状态
```bash
docker ps | grep stock-data-service
```

应该看到容器状态为 "Up"

#### 6.2 查看启动日志
```bash
docker logs --tail 20 stock-data-service
```

应该看到：
- Scheduler启动信息
- Flask服务运行在9090端口
- Uvicorn服务运行在7070端口

#### 6.3 测试HTTP接口
```bash
# 基础接口
curl http://localhost:9090/

# 交易日接口
curl http://localhost:9090/tradeDayBasic

# 资金流向接口
curl http://localhost:9090/lastDayMoneyFlow
```

#### 6.4 测试MCP接口
```bash
curl http://localhost:7070/
```

## 常见问题排查

### 容器无法启动

**症状**: `docker ps` 看不到容器

**排查步骤**:
1. 检查容器状态: `docker ps -a | grep stock-data-service`
2. 查看容器日志: `docker logs stock-data-service`
3. 检查镜像是否加载成功: `docker images | grep stock-data-service`

### 端口被占用

**症状**: 启动容器时提示端口已被使用

**解决方案**:
```bash
# 查看占用端口的进程
netstat -tlnp | grep 9090
netstat -tlnp | grep 7070

# 停止占用端口的容器
docker stop <container-name>
```

### 数据卷权限问题

**症状**: 容器启动但无法写入数据

**解决方案**:
```bash
# 检查数据卷权限
ls -la /data/stock-data-service

# 修正权限
chown -R root:root /data/stock-data-service
chmod -R 755 /data/stock-data-service
```

### 内存不足

**症状**: 容器频繁重启

**解决方案**:
```bash
# 查看服务器内存使用
free -h

# 清理未使用的镜像和容器
docker system prune -a
```

## 回滚操作

如果新版本出现问题，可以快速回滚：

### 1. 查看可用镜像版本
```bash
docker images | grep stock-data-service
```

### 2. 停止当前容器
```bash
docker stop stock-data-service
docker rm stock-data-service
```

### 3. 启动旧版本
```bash
docker run -d \
  --name stock-data-service \
  -p 9090:9090 \
  -p 7070:7070 \
  -v /data/stock-data-service:/app/data \
  -e DATA_ROOT=/app/data \
  -e DAILY_CRON="30 19 * * 1-5" \
  --restart=always \
  stock-data-service:<old-version>-amd64
```

## 监控建议

### 定期检查

```bash
# 容器健康状态
docker ps

# 服务日志
docker logs --tail 100 -f stock-data-service

# 磁盘使用
df -h

# 内存使用
free -h
```

### 日志管理

日志文件位于 `/data/stock-data-service/logs/`，定期清理旧日志：
```bash
find /data/stock-data-service/logs/ -name "*.log" -mtime +30 -delete
```

## 性能优化

### 镜像清理

定期清理未使用的Docker镜像和容器：
```bash
docker system prune -a --volumes
```

### 网络优化

如果上传速度慢，可以考虑：
1. 使用更快的网络连接
2. 压缩镜像（会牺牲一些加载速度）
3. 使用私有镜像仓库
