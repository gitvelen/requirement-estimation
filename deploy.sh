#!/bin/bash
# 部署脚本 - 一键部署到Docker环境

set -e

echo "========================================="
echo "需求评估系统 - Docker部署脚本"
echo "========================================="

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 1. 构建前端
echo ""
echo "[步骤 1/4] 构建前端..."
cd frontend
npm install
npm run build
cd ..

# 2. 构建Docker镜像
echo ""
echo "[步骤 2/4] 构建Docker镜像..."
docker build -t requirement-backend .

# 3. 启动服务
echo ""
echo "[步骤 3/4] 启动服务..."
docker-compose up -d

# 4. 检查服务状态
echo ""
echo "[步骤 4/4] 检查服务状态..."
sleep 5
docker-compose ps

echo ""
echo "========================================="
echo "部署完成！"
echo "========================================="
echo "访问地址: http://localhost"
echo ""
echo "查看日志:"
echo "  后端: docker-compose logs -f backend"
echo "  前端: docker-compose logs -f frontend"
echo ""
echo "停止服务:"
echo "  docker-compose down"
echo "========================================="
