#!/bin/bash
# 一键部署脚本（包含知识库功能）

set -e

echo "========================================="
echo "  业务需求工作量评估系统 - 一键部署"
echo "========================================="
echo ""

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

echo "✓ Docker环境检查通过"
echo ""

# 选择部署模式
echo "请选择部署模式："
echo "1) 基础部署（不包含知识库功能，资源占用少）"
echo "2) 完整部署（包含知识库功能，推荐）"
echo ""
read -p "请输入选项 [1/2] (默认: 2): " mode

mode=${mode:-2}

if [ "$mode" = "1" ]; then
    echo ""
    echo "启动基础部署（不包含Milvus知识库）..."
    docker-compose up -d --build
elif [ "$mode" = "2" ]; then
    echo ""
    echo "启动完整部署（包含Milvus知识库）..."
    echo "这可能需要1-2分钟，请耐心等待..."
    docker-compose --profile milvus up -d --build

    echo ""
    echo "等待Milvus启动..."
    sleep 30

    # 等待Milvus健康
    echo "检查Milvus健康状态..."
    for i in {1..30}; do
        if curl -s http://localhost:9091/healthz > /dev/null 2>&1; then
            echo "✓ Milvus已就绪"
            break
        fi
        echo "等待Milvus启动... ($i/30)"
        sleep 2
    done
else
    echo "错误: 无效的选项"
    exit 1
fi

echo ""
echo "========================================="
echo "部署完成！"
echo "========================================="
echo ""
echo "服务状态："
docker-compose ps
echo ""
echo "访问地址："
echo "  - 主页: http://localhost"
echo "  - 知识库管理: http://localhost/knowledge"
echo ""
echo "查看日志："
echo "  docker-compose logs -f backend"
echo ""
echo "停止服务："
echo "  docker-compose down"
echo ""
