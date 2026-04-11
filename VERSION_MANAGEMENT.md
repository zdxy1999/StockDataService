# 版本管理说明

## 概述

本项目使用文件化的版本管理机制，通过 `VERSION` 文件统一管理版本号。

## 文件结构

```
StockDataService/
├── VERSION              # 版本号文件
├── CHANGELOG.md        # 版本变更日志
├── Makefile           # 自动读取 VERSION 文件
└── Dockerfile         # 构建时包含 VERSION 文件
```

## 使用方法

### 1. 查看当前版本

```bash
cat VERSION
```

### 2. 更新版本号

```bash
echo "1.1.5" > VERSION
```

### 3. 构建镜像

```bash
# Makefile 会自动读取 VERSION 文件中的版本号
make build-amd64

# 或者构建所有架构
make all
```

构建后的镜像：
- 名称：`stock-data-service:{VERSION}-amd64`
- 文件：`dist/stock-data-service_amd64_{VERSION}.tar`

### 4. 查看容器内的版本

```bash
docker run --rm stock-data-service:1.1.4-amd64 cat /app/VERSION
```

## 版本号规范

采用语义化版本号：`主版本.次版本.修订版本`

- **主版本**：重大架构变更或破坏性更新
- **次版本**：新增功能
- **修订版本**：Bug修复或小的改进

示例：
- `1.0.0` → 第一个稳定版本
- `1.1.0` → 新增功能
- `1.1.1` → Bug修复
- `2.0.0` → 重大架构变更

## 发布流程

1. 更新版本号：
   ```bash
   echo "1.1.5" > VERSION
   ```

2. 更新 CHANGELOG.md：
   ```markdown
   ## [1.1.5] - 2026-04-11

   ### Added
   - 新功能描述

   ### Fixed
   - 修复的问题
   ```

3. 提交代码：
   ```bash
   git add VERSION CHANGELOG.md
   git commit -m "bump version to 1.1.5"
   git tag v1.1.5
   ```

4. 构建镜像：
   ```bash
   make build-amd64
   ```

## 优势

- ✅ **集中管理**：版本号统一在一个文件中
- ✅ **自动化**：Makefile 自动读取版本号
- ✅ **可追溯**：镜像内包含版本文件
- ✅ **易维护**：修改一个文件即可更新版本
- ✅ **标准化**：遵循语义化版本规范

## 示例

```bash
# 查看当前版本
$ cat VERSION
1.1.4

# 构建镜像（自动使用 1.1.4 作为版本号）
$ make build-amd64
✅ amd64 镜像已保存至 dist/stock-data-service_amd64_1.1.4.tar

# 验证镜像版本
$ docker run --rm stock-data-service:1.1.4-amd64 cat /app/VERSION
1.1.4
```
