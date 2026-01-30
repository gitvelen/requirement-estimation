#!/bin/bash
# 一键部署脚本（本期：知识库使用本地向量库，无 Milvus/MinIO）

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
echo "1) 基础部署（禁用知识库，资源占用少）"
echo "2) 默认部署（启用知识库-本地向量库，推荐）"
echo ""
read -p "请输入选项 [1/2] (默认: 2): " mode

mode=${mode:-2}

if [ "$mode" = "1" ]; then
    echo ""
    echo "启动基础部署（禁用知识库）..."
    export KNOWLEDGE_ENABLED=false
    export KNOWLEDGE_VECTOR_STORE=local
    docker-compose up -d --build
elif [ "$mode" = "2" ]; then
    echo ""
    echo "启动默认部署（启用知识库-本地向量库）..."
    echo "提示：如需知识库导入/检索，请在 .env 中配置 DASHSCOPE_API_KEY。"
    export KNOWLEDGE_ENABLED=true
    export KNOWLEDGE_VECTOR_STORE=local
    docker-compose up -d --build
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
