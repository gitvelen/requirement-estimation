#!/bin/bash

# ========================================
# 需求估算系统 - 前端部署脚本
# ========================================
# 用途：自动部署前端服务到指定服务器
# 使用方法：./deploy-frontend.sh [前端服务器IP] [后端服务器IP]
# 示例：./deploy-frontend.sh 124.223.38.219 8.153.194.178
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
if [ $# -lt 2 ]; then
    print_error "请提供前端服务器IP和后端服务器IP"
    echo "使用方法: $0 <前端服务器IP> <后端服务器IP>"
    echo "示例: $0 124.223.38.219 8.153.194.178"
    exit 1
fi

FRONTEND_SERVER=$1
BACKEND_SERVER=$2
PROJECT_NAME="requirement-estimation-system"
REMOTE_DIR="/root/${PROJECT_NAME}"

print_info "========== 开始部署前端服务 =========="
print_info "前端服务器: ${FRONTEND_SERVER}"
print_info "后端服务器: ${BACKEND_SERVER}"

# 1. 检查当前分支
# 1. 测试SSH连接
print_info "步骤 1/7: 测试SSH连接到前端服务器"
if ! ssh -o ConnectTimeout=5 root@${FRONTEND_SERVER} "echo 'SSH连接成功'" > /dev/null 2>&1; then
    print_error "无法SSH连接到 ${FRONTEND_SERVER}"
    print_info "请检查："
    echo "  1. 服务器IP是否正确"
    echo "  2. SSH密钥是否配置"
    echo "  3. 网络是否连通"
    exit 1
fi
print_info "SSH连接测试成功"

# 2. 从GitHub克隆代码到前端服务器
print_info "步骤 2/7: 从GitHub克隆master分支到前端服务器"
ssh root@${FRONTEND_SERVER} << 'EOF'
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

# 3. 修改nginx配置文件
print_info "步骤 3/7: 修改nginx配置文件"
ssh root@${FRONTEND_SERVER} << EOF
cd /root/requirement-estimation-system/frontend
sed "s/BACKEND_SERVER_PLACEHOLDER/${BACKEND_SERVER}/g" nginx-remote.conf > nginx-remote-deploy.conf
echo "nginx配置已更新为指向后端: ${BACKEND_SERVER}"
EOF

print_info "nginx配置已更新"

ssh root@${FRONTEND_SERVER} << EOF
cd /root/requirement-estimation-system

# 创建 .env.frontend 文件
cat > .env.frontend << ENVEOF
# 前端环境变量配置
REACT_APP_API_URL=https://${BACKEND_SERVER}
ENVEOF

echo "前端环境变量已配置："
cat .env.frontend
EOF

# 5. 替换nginx配置
ssh root@${FRONTEND_SERVER} << EOF
cd /root/requirement-estimation-system/frontend

# 备份原配置
cp nginx.conf nginx.conf.local.bak 2>/dev/null || true

# 使用部署版本配置
cp nginx-remote-deploy.conf nginx.conf

echo "nginx配置已更新，proxy_pass指向: https://${BACKEND_SERVER}:443"
EOF

# 6. 停止旧容器
ssh root@${FRONTEND_SERVER} << EOF
cd /root/requirement-estimation-system
docker-compose -f docker-compose.frontend.yml down 2>/dev/null || true
EOF

# 7. 构建并启动新容器
print_info "步骤 7/7: 构建并启动前端容器（可能需要几分钟）"
ssh root@${FRONTEND_SERVER} << EOF
cd ${REMOTE_DIR}
if ! docker-compose -f docker-compose.frontend.yml up -d --build; then
    echo "BuildKit 构建失败，回退到经典构建模式（DOCKER_BUILDKIT=0）..."
    DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 docker-compose -f docker-compose.frontend.yml up -d --build
fi
EOF

# 验证部署
print_info "验证前端服务"
sleep 15  # 等待容器启动

ssh root@${FRONTEND_SERVER} << EOF
cd ${REMOTE_DIR}

# 检查容器状态
echo ""
echo "容器状态："
docker-compose -f docker-compose.frontend.yml ps

# 测试前端页面
echo ""
echo "测试前端页面..."
sleep 5
if curl -s -o /dev/null -w "%{http_code}" http://localhost:80 | grep -q "200"; then
    echo ""
    echo "=========================================="
    echo "✅ 前端服务部署成功！"
    echo "=========================================="
    echo "前端地址: http://${FRONTEND_SERVER}"
    echo "后端地址: https://${BACKEND_SERVER}:443"
    echo ""
    echo "下一步操作："
    echo "1. 在浏览器中访问: http://${FRONTEND_SERVER}"
    echo "2. 在后端服务器创建管理员用户"
    echo "   ssh root@${BACKEND_SERVER}"
    echo "   cd ${REMOTE_DIR}"
    echo "   docker exec -it requirement-backend bash"
    echo "   python -c \"from backend.service.user_service import UserService; UserService().create_user(username='admin', password='admin123', role='admin')\""
    echo "3. 使用 admin/admin123 登录系统"
    echo ""
    echo "查看日志命令:"
    echo "  ssh root@${FRONTEND_SERVER}"
    echo "  cd ${REMOTE_DIR}"
    echo "  docker-compose -f docker-compose.frontend.yml logs -f frontend"
    echo "=========================================="
else
    echo ""
    echo "⚠️  前端页面访问失败，请查看日志："
    echo "  docker-compose -f docker-compose.frontend.yml logs frontend"
    exit 1
fi
EOF

print_info "========== 前端部署完成 =========="
