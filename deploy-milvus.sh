#!/bin/bash

# Milvus部署脚本
# 用于快速启动Milvus向量数据库

set -e

echo "======================================"
echo "  Milvus 向量数据库部署脚本"
echo "======================================"
echo ""

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker未安装，请先安装Docker"
    echo "安装命令: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# 检查Docker Compose是否安装
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "错误: Docker Compose未安装，请先安装Docker Compose"
    echo "安装命令: sudo apt-get install docker-compose"
    exit 1
fi

# 停止并删除旧容器（如果存在）
echo "1. 清理旧容器..."
docker-compose -f docker-compose.milvus.yml down -v 2>/dev/null || true

# 启动Milvus服务
echo ""
echo "2. 启动Milvus服务..."
docker-compose -f docker-compose.milvus.yml up -d

# 等待服务启动
echo ""
echo "3. 等待服务启动..."
sleep 10

# 检查服务状态
echo ""
echo "4. 检查服务状态..."
docker-compose -f docker-compose.milvus.yml ps

echo ""
echo "======================================"
echo "  Milvus部署完成！"
echo "======================================"
echo ""
echo "服务地址："
echo "  - Milvus gRPC: localhost:19530"
echo "  - MinIO Console: http://localhost:9001"
echo "    (用户名: minioadmin, 密码: minioadmin)"
echo ""
echo "测试连接："
echo "  python -c \"from pymilvus import connections; connections.connect('default', host='localhost', port=19530); print('Milvus连接成功！')\""
echo ""
echo "查看日志："
echo "  docker-compose -f docker-compose.milvus.yml logs -f milvus"
echo ""
echo "停止服务："
echo "  docker-compose -f docker-compose.milvus.yml down"
echo ""
