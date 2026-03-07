IMAGE_NAME  := stock-data-service
VERSION     ?= latest
DIST_DIR    := dist

AMD64_TAR   := $(DIST_DIR)/$(IMAGE_NAME)_amd64_$(VERSION).tar
ARM64_TAR   := $(DIST_DIR)/$(IMAGE_NAME)_arm64_$(VERSION).tar

.PHONY: all build-amd64 build-arm64 clean help

## 默认目标：同时构建 amd64 和 arm64
all: build-amd64 build-arm64

## 构建 x86_64（amd64）镜像并保存为 tar 文件
build-amd64: $(DIST_DIR)
	docker buildx build \
		--platform linux/amd64 \
		--tag $(IMAGE_NAME):$(VERSION)-amd64 \
		--load \
		.
	docker save $(IMAGE_NAME):$(VERSION)-amd64 -o $(AMD64_TAR)
	@echo "✅ amd64 镜像已保存至 $(AMD64_TAR)"

## 构建 ARM64（arm64）镜像并保存为 tar 文件
build-arm64: $(DIST_DIR)
	docker buildx build \
		--platform linux/arm64 \
		--tag $(IMAGE_NAME):$(VERSION)-arm64 \
		--load \
		.
	docker save $(IMAGE_NAME):$(VERSION)-arm64 -o $(ARM64_TAR)
	@echo "✅ arm64 镜像已保存至 $(ARM64_TAR)"

## 创建输出目录
$(DIST_DIR):
	mkdir -p $(DIST_DIR)

## 清理 tar 文件和本地镜像
clean:
	rm -rf $(DIST_DIR)
	-docker rmi $(IMAGE_NAME):$(VERSION)-amd64 2>/dev/null
	-docker rmi $(IMAGE_NAME):$(VERSION)-arm64 2>/dev/null
	@echo "🧹 已清理"

help:
	@echo ""
	@echo "用法："
	@echo "  make build-amd64          # 构建 x86_64 镜像"
	@echo "  make build-arm64          # 构建 ARM64 镜像"
	@echo "  make all                  # 同时构建两个平台"
	@echo "  make all VERSION=1.0.0    # 指定版本号"
	@echo "  make clean                # 清理产物"
	@echo ""
	@echo "产物默认保存至 dist/ 目录："
	@echo "  $(AMD64_TAR)"
	@echo "  $(ARM64_TAR)"
	@echo ""
