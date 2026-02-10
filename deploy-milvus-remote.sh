#!/bin/bash

# Milvus远程部署脚本
# 用于在远程服务器上部署Milvus向量数据库

set -e

echo "======================================"
echo "  Milvus 远程部署脚本"
echo "======================================"
echo ""

# 配置变量
REMOTE_HOST="124.223.38.219"
REMOTE_USER="root"
REMOTE_PORT="22"
DATA_DIR="/home/admin/milvus/data"
COMPOSE_FILE="docker-compose.milvus.remote.yml"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查本地是否有docker-compose文件
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}错误: 找不到 $COMPOSE_FILE 文件${NC}"
    exit 1
fi

echo -e "${YELLOW}部署信息:${NC}"
echo "  远程主机: $REMOTE_HOST:$REMOTE_PORT"
echo "  远程用户: $REMOTE_USER"
echo "  数据目录: $DATA_DIR"
echo ""

# 确认部署
read -p "是否继续部署? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "部署已取消"
    exit 0
fi

echo ""
echo -e "${GREEN}1. 在远程服务器上创建数据目录...${NC}"
ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST "mkdir -p $DATA_DIR/{etcd,minio,milvus} && chmod -R 755 $DATA_DIR && ls -la $DATA_DIR"

echo ""
echo -e "${GREEN}2. 上传docker-compose配置文件...${NC}"
scp -P $REMOTE_PORT $COMPOSE_FILE $REMOTE_USER@$REMOTE_HOST:/home/admin/milvus/docker-compose.yml

echo ""
echo -e "${GREEN}3. 在远程服务器上停止旧服务（如果存在）...${NC}"
ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST "cd /home/admin/milvus && docker-compose down 2>/dev/null || true"

echo ""
echo -e "${GREEN}4. 在远程服务器上启动Milvus服务...${NC}"
ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST "cd /home/admin/milvus && docker-compose up -d"

echo ""
echo -e "${GREEN}5. 等待服务启动...${NC}"
sleep 15

echo ""
echo -e "${GREEN}6. 检查服务状态...${NC}"
ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST "cd /home/admin/milvus && docker-compose ps"

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  Milvus部署完成！${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "服务地址："
echo "  - Milvus gRPC: $REMOTE_HOST:19530"
echo "  - MinIO Console: http://$REMOTE_HOST:9001"
echo "    (用户名: minioadmin, 密码: minioadmin)"
echo ""
echo -e "${YELLOW}防火墙配置提示:${NC}"
echo "  需要开放以下端口:"
echo "    - 19530/tcp  (Milvus gRPC)"
echo "    - 9001/tcp   (MinIO Console，可选)"
echo ""
echo "查看日志："
echo "  ssh $REMOTE_USER@$REMOTE_HOST -p $REMOTE_PORT \"cd /home/admin/milvus && docker-compose logs -f milvus\""
echo ""
echo "停止服务："
echo "  ssh $REMOTE_USER@$REMOTE_HOST -p $REMOTE_PORT \"cd /home/admin/milvus && docker-compose down\""
echo ""
echo "重启服务："
echo "  ssh $REMOTE_USER@$REMOTE_HOST -p $REMOTE_PORT \"cd /home/admin/milvus && docker-compose restart\""
echo ""
