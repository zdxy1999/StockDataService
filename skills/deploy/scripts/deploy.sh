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
ssh ${SSH_KEY} ${SERVER} << EOF
set -e
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
  ${IMAGE_NAME}

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
