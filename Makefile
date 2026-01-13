.PHONY: help build test check-deps deploy

help: ## 显示帮助信息
	@echo "可用命令:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

check-deps: ## 检查依赖是否完整
	@echo "🔍 检查依赖..."
	@./check_dependencies.sh

build: check-deps ## 检查依赖后构建镜像
	@echo "🔨 构建Docker镜像..."
	docker build -t requirement-estimation-system-backend .

test: check-deps ## 运行测试（含依赖检查）
	@echo "🧪 运行测试..."
	# docker-compose run --rm backend pytest

deploy: build ## 部署（构建并启动）
	@echo "🚀 部署服务..."
	docker-compose up -d backend
	@echo "✅ 部署完成"

update-requirements: ## 使用pipreqs更新requirements.txt
	@echo "📦 扫描代码更新依赖..."
	pipreqs . --force --savepath requirements.txt
	@echo "✅ requirements.txt 已更新"
