# 自动化部署脚本说明

本文档描述 `scripts/deploy.sh` 自动化部署脚本的使用方法。

## 快速使用

```bash
./scripts/deploy.sh
```

脚本会自动执行完整的部署流程，无需手动干预。

## 脚本功能

自动化脚本完成以下操作：

1. ✅ 读取当前版本号
2. ✅ 构建Docker镜像（amd64）
3. ✅ 保存镜像为tar文件
4. ✅ 上传到远程服务器
5. ✅ 在服务器上加载镜像
6. ✅ 停止并删除旧容器
7. ✅ 启动新容器
8. ✅ 验证服务状态

## 脚本特性

### 错误处理
- 使用 `set -e` 确保任何步骤失败时立即停止
- 每个步骤都有明确的进度提示
- 失败时会显示清晰的错误信息

### 进度显示
每个步骤都有emoji标识：
- 🚀 开始部署
- 📦 构建镜像
- 💾 保存镜像
- 📤 上传镜像
- 🔧 部署服务
- 🧪 验证服务
- ✅ 部署完成

### 自动验证
部署完成后自动测试：
- HTTP服务响应
- 交易日接口功能
- 容器运行状态

## 使用场景

### 日常部署
```bash
# 更新版本号
echo "1.1.6" > VERSION

# 提交代码
git add .
git commit -m "Bump version to 1.1.6"

# 一键部署
./scripts/deploy.sh
```

### 紧急修复
```bash
# 快速修复bug
vim server_http.py

# 直接部署（跳过版本号更新）
./scripts/deploy.sh
```

## 脚本内容

```bash
#!/bin/bash
# Stock Data Service 远程部署脚本
# 使用方法: ./scripts/deploy.sh

set -e  # 遇到错误立即退出

# 读取版本号
VERSION=$(cat VERSION 2>/dev/null || echo "latest")
IMAGE_NAME="stock-data-service:${VERSION}-amd64"
TAR_FILE="dist/stock-data-service_amd64_${VERSION}.tar"
SERVER="root@47.99.207.160"
SSH_KEY="-i ~/.ssh/zdxy-ali.pem"

echo "🚀 开始部署 Stock Data Service v${VERSION}"

# 1. 构建 Docker 镜像
echo "📦 构建 Docker 镜像..."
docker build --platform linux/amd64 -t "${IMAGE_NAME}" .

# 2. 保存镜像
echo "💾 保存镜像到 ${TAR_FILE}..."
mkdir -p dist
docker save "${IMAGE_NAME}" -o "${TAR_FILE}"

# 3. 上传到服务器
echo "📤 上传镜像到服务器..."
scp ${SSH_KEY} "${TAR_FILE}" "${SERVER}:/root/"

# 4. 在服务器上部署
echo "🔧 在服务器上部署..."
ssh ${SSH_KEY} ${SERVER} << 'EOF'
set -e
VERSION=$(cat /tmp/VERSION 2>/dev/null || echo "latest")
echo "加载新镜像..."
docker load -i /root/stock-data-service_amd64_${VERSION}.tar

echo "停止旧容器..."
docker stop stock-data-service 2>/dev/null || true
docker rm stock-data-service 2>/dev/null || true

echo "启动新容器..."
docker run -d \
  --name stock-data-service \
  -p 9090:9090 \
  -p 7070:7070 \
  -v /data/stock-data-service:/app/data \
  -e DATA_ROOT=/app/data \
  -e DAILY_CRON="30 19 * * 1-5" \
  --restart=always \
  stock-data-service:${VERSION}-amd64

echo "验证服务状态..."
sleep 3
docker ps | grep stock-data-service
docker logs --tail 5 stock-data-service
EOF

# 5. 验证部署
echo "🧪 验证服务..."
sleep 2
echo "测试 HTTP 服务:"
curl -s http://47.99.207.160:9090/ | head -1
echo ""
echo "测试交易日接口:"
curl -s http://47.99.207.160:9090/tradeDayBasic | grep -o '"is_trade_day":[^,]*' || echo "接口测试失败"

echo ""
echo "✅ 部署完成！"
echo "🌐 HTTP 服务: http://47.99.207.160:9090"
echo "🔌 MCP 服务: http://47.99.207.160:7070"
```

## 自定义配置

如果需要修改服务器地址或其他配置，编辑脚本中的变量：

```bash
VERSION=$(cat VERSION 2>/dev/null || echo "latest")
IMAGE_NAME="stock-data-service:${VERSION}-amd64"
TAR_FILE="dist/stock-data-service_amd64_${VERSION}.tar"
SERVER="root@47.99.207.160"      # 修改服务器地址
SSH_KEY="-i ~/.ssh/zdxy-ali.pem"  # 修改SSH密钥路径
```

## 故障排查

### 脚本执行失败

1. 检查SSH密钥权限：
   ```bash
   chmod 400 ~/.ssh/zdxy-ali.pem
   ```

2. 手动测试服务器连接：
   ```bash
   ssh -i ~/.ssh/zdxy-ali.pem root@47.99.207.160
   ```

3. 检查Docker是否运行：
   ```bash
   docker ps
   ```

### 部署后验证失败

手动验证服务状态：
```bash
# 检查容器
ssh -i ~/.ssh/zdxy-ali.pem root@47.99.207.160 "docker ps"

# 查看日志
ssh -i ~/.ssh/zdxy-ali.pem root@47.99.207.160 "docker logs stock-data-service"

# 测试接口
curl http://47.99.207.160:9090/
```

## 最佳实践

1. **部署前测试**: 在本地测试所有修改
2. **版本管理**: 每次部署更新VERSION文件
3. **代码提交**: 部署前提交所有代码修改
4. **监控日志**: 部署后查看服务日志确保正常
5. **保留回滚**: 保留旧版本镜像以便回滚

## 时间估算

- 构建: 2-5分钟
- 保存: 1-2分钟
- 上传: 2-10分钟（取决于网络）
- 部署: 5-10秒
- 验证: 5-10秒

**总计**: 约5-20分钟
