#!/bin/bash

# ========================================
# 需求估算系统 - 远程服务器一键部署脚本
# ========================================
# 用途：一键部署到远程服务器（前后端分离）
# 使用方法：./deploy-remote-all.sh [前端服务器IP] [后端服务器IP]
# 示例：./deploy-remote-all.sh 124.223.38.219 8.153.194.178
# ========================================

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
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

echo ""
echo "=========================================="
echo "   需求估算系统 - 远程服务器一键部署"
echo "=========================================="
echo ""
echo "前端服务器: ${FRONTEND_SERVER}"
echo "后端服务器: ${BACKEND_SERVER}"
echo ""
echo "部署流程："
echo "  1. 部署后端服务"
echo "  2. 部署前端服务"
echo "  3. 验证部署结果"
echo ""
echo "=========================================="
echo ""

read -p "确认开始部署？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "部署已取消"
    exit 0
fi

# 1. 部署后端
print_step "第1步：部署后端服务"
echo ""
bash deploy-backend.sh ${BACKEND_SERVER}

if [ $? -ne 0 ]; then
    print_error "后端部署失败，终止部署流程"
    exit 1
fi

echo ""
echo ""

# 2. 部署前端
print_step "第2步：部署前端服务"
echo ""
bash deploy-frontend.sh ${FRONTEND_SERVER} ${BACKEND_SERVER}

if [ $? -ne 0 ]; then
    print_error "前端部署失败"
    exit 1
fi

echo ""
echo ""

# 3. 最终验证
print_step "第3步：验证部署结果"
echo ""

print_info "测试后端服务..."
if curl -k -s https://${BACKEND_SERVER}:443/api/v1/health 2>/dev/null | grep -q "healthy"; then
    echo "✅ 后端服务正常"
else
    echo "⚠️  后端服务异常（可能需要等待更长时间启动）"
fi

print_info "测试前端服务..."
if curl -s -o /dev/null -w "%{http_code}" http://${FRONTEND_SERVER} 2>/dev/null | grep -q "200"; then
    echo "✅ 前端服务正常"
else
    echo "⚠️  前端服务异常（可能需要等待更长时间启动）"
fi

echo ""
echo "=========================================="
echo "   🎉 部署完成！"
echo "=========================================="
echo ""
echo "访问地址："
echo "  前端: http://${FRONTEND_SERVER}"
echo "  后端: https://${BACKEND_SERVER}:443"
echo ""
echo "下一步操作："
echo "  1. 在浏览器中访问前端地址"
echo "  2. 在后端服务器创建管理员用户"
echo ""
echo "创建管理员用户命令："
cat << 'EOF'
  ssh root@后端服务器IP
  cd /root/requirement-estimation-system
  docker exec -it requirement-backend bash
  python -c "from backend.service.user_service import UserService; UserService().create_user(username='admin', password='admin123', role='admin')"
EOF
echo ""
echo "登录账号：admin / admin123"
echo ""
echo "=========================================="
