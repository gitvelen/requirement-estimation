#!/bin/bash

# ========================================
# 需求估算系统 - 后端部署脚本
# ========================================
# 用途：自动部署后端服务到指定服务器
# 使用方法：./deploy-backend.sh [后端服务器IP]
# 示例：./deploy-backend.sh 8.153.194.178
# ========================================

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查参数
if [ $# -eq 0 ]; then
    print_error "请提供后端服务器IP地址"
    echo "使用方法: $0 <后端服务器IP>"
    echo "示例: $0 8.153.194.178"
    exit 1
fi

BACKEND_SERVER=$1
PROJECT_NAME="requirement-estimation-system"
REMOTE_DIR="/root/${PROJECT_NAME}"

print_info "========== 开始部署后端服务 =========="
print_info "后端服务器: ${BACKEND_SERVER}"

# 1. 测试SSH连接
print_info "步骤 1/7: 测试SSH连接到后端服务器"
if ! ssh -o ConnectTimeout=5 root@${BACKEND_SERVER} "echo 'SSH连接成功'" > /dev/null 2>&1; then
    print_error "无法SSH连接到 ${BACKEND_SERVER}"
    print_info "请检查："
    echo "  1. 服务器IP是否正确"
    echo "  2. SSH密钥是否配置"
    echo "  3. 网络是否连通"
    exit 1
fi
print_info "SSH连接测试成功"

# 2. 从GitHub克隆代码到后端服务器
print_info "步骤 2/7: 从GitHub克隆master分支到后端服务器"
ssh root@${BACKEND_SERVER} << 'EOF'
# 如果目录已存在，先备份
if [ -d "/root/requirement-estimation-system" ]; then
    echo "备份现有目录..."
    mv /root/requirement-estimation-system /root/requirement-estimation-system.backup.$(date +%Y%m%d_%H%M%S)
fi

# 克隆master分支
echo "从GitHub克隆master分支..."
git clone -b master https://github.com/gitvelen/requirement-estimation-system.git /root/requirement-estimation-system

echo "代码克隆完成"
EOF

# 3. 检查环境变量配置
print_info "步骤 3/7: 检查环境变量配置"
ssh root@${BACKEND_SERVER} << EOF
cd ${REMOTE_DIR}

# 检查 .env.backend 是否存在
if [ ! -f .env.backend ]; then
    echo "未找到 .env.backend 文件，从示例文件复制..."
    cp .env.backend.example .env.backend

    echo ""
    echo "=========================================="
    echo "请配置以下环境变量（重要！）："
    echo "=========================================="
    echo "1. DASHSCOPE_API_KEY - 阿里云API密钥（必填）"
    echo "2. JWT_SECRET - JWT密钥（建议修改）"
    echo "3. ADMIN_API_KEY - 管理接口密钥（建议修改）"
    echo "4. ALLOWED_ORIGINS - 前端服务器地址"
    echo ""
    echo "配置命令: vi ${REMOTE_DIR}/.env.backend"
    echo "=========================================="
    echo ""
    echo "按回车继续（请确保已配置环境变量）..."
    read
fi

# 显示关键配置（隐藏敏感信息）
echo ""
echo "环境变量配置："
grep -E "^(KNOWLEDGE_|DEBUG|PORT|HOST|ALLOWED_)" .env.backend || true
echo "DASHSCOPE_API_KEY=$(grep DASHSCOPE_API_KEY .env.backend | cut -d= -f1 | cut -c1-20)..."
EOF

print_warning "请确认已在后端服务器上正确配置 .env.backend 文件"
read -p "是否继续部署？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "部署已取消"
    exit 0
fi

# 4. 停止旧容器
print_info "步骤 4/7: 停止旧的后端容器"
ssh root@${BACKEND_SERVER} << EOF
cd ${REMOTE_DIR}
docker-compose -f docker-compose.backend.yml down 2>/dev/null || true
EOF

# 5. 构建并启动新容器
print_info "步骤 5/7: 构建并启动后端容器（可能需要几分钟）"
ssh root@${BACKEND_SERVER} << EOF
cd ${REMOTE_DIR}
if ! docker-compose -f docker-compose.backend.yml up -d --build; then
    echo "BuildKit 构建失败，回退到经典构建模式（DOCKER_BUILDKIT=0）..."
    DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 docker-compose -f docker-compose.backend.yml up -d --build
fi
EOF

# 6. 验证部署
print_info "步骤 6/7: 验证后端服务"
sleep 10  # 等待容器启动

ssh root@${BACKEND_SERVER} << EOF
cd ${REMOTE_DIR}

# 检查容器状态
echo ""
echo "容器状态："
docker-compose -f docker-compose.backend.yml ps

# 测试健康检查
echo ""
echo "测试健康检查接口..."
sleep 5
if curl -k -s https://localhost:443/api/v1/health | grep -q "healthy"; then
    echo ""
    echo "=========================================="
    echo "✅ 后端服务部署成功！"
    echo "=========================================="
    echo "后端地址: https://${BACKEND_SERVER}:443"
    echo "健康检查: https://${BACKEND_SERVER}:443/api/v1/health"
    echo ""
    echo "查看日志命令:"
    echo "  ssh root@${BACKEND_SERVER}"
    echo "  cd ${REMOTE_DIR}"
    echo "  docker-compose -f docker-compose.backend.yml logs -f backend"
    echo "=========================================="
else
    echo ""
    echo "⚠️  健康检查失败，请查看日志："
    echo "  docker-compose -f docker-compose.backend.yml logs backend"
    exit 1
fi
EOF

print_info "========== 后端部署完成 =========="
