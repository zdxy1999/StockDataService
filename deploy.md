# 环境说明

线上环境通过ssh连接

ssh  -i ~/.ssh/zdxy-ali.pem root@47.99.207.160

# 自动化部署

AI Agent 在构建部署时可以直接调用部署 skill：

## 方式一：自动化脚本（推荐）
```bash
./skills/deploy/scripts/deploy.sh
```

## 方式二：调用 Agent Skill
AI Agent 可以通过以下路径调用部署 skill：
```
skills/deploy/
```

该 skill 包含完整的打包、上传、部署流程，自动化执行以下操作：
1. 构建 Docker 镜像
2. 保存并上传到服务器
3. 在服务器上加载镜像并重启容器
4. 验证服务状态

**Skill 内容**：
- `SKILL.md` - 主要技能文档
- `scripts/deploy.sh` - 自动化部署脚本
- `references/full-guide.md` - 完整部署指南
- `references/automated-script.md` - 脚本使用说明

# 启动命令
```bash
docker run -d \
  --name stock-data-service \
  -p 9090:9090 \
  -p 7070:7070 \
  -v /data/stock-data-service:/app/data \
  -e DATA_ROOT=/app/data \
  -e DAILY_CRON="30 19 * * 1-5" \
  --restart=always \
  docker.io/library/stock-data-service:<tag>
```