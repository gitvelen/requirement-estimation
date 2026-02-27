#!/bin/bash
###############################################################################
# 内网环境前端一键部署脚本
#
# 服务器：10.62.16.251:8000
# 工作目录：/home/admin/requirement-estimation
# 功能：使用已构建前端产物启动前端服务
###############################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

###############################################################################
# 检查前置条件
###############################################################################

check_prerequisites() {
    echo_info "========================================"
    echo_info "内网前端一键部署脚本"
    echo_info "========================================"

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        echo_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi

    echo_info "前置条件检查通过"
}

###############################################################################
# 准备前端构建文件（优先使用仓库内 frontend/build）
###############################################################################

prepare_build_files() {
    echo_info "检查前端构建文件..."

    local BUILD_TAR="/home/admin/frontend-build.tar.gz"
    local BUILD_DIR="/home/admin/requirement-estimation/frontend/build"

    # 优先使用项目内已存在的构建产物
    if [ -f "$BUILD_DIR/index.html" ]; then
        echo_info "检测到现成构建产物：$BUILD_DIR/index.html"
        return 0
    fi

    # 兜底：使用独立构建包
    if [ ! -f "$BUILD_TAR" ]; then
        echo_error "未找到可用构建产物："
        echo_error "1) $BUILD_DIR/index.html"
        echo_error "2) $BUILD_TAR"
        echo_info "请先同步 frontend/build 或上传 frontend-build.tar.gz"
        exit 1
    fi

    mkdir -p "$BUILD_DIR"
    echo_info "解压前端构建文件..."
    tar xzf "$BUILD_TAR" -C "$BUILD_DIR"

    if [ ! -f "$BUILD_DIR/index.html" ]; then
        echo_error "前端构建文件不完整（缺少 index.html）"
        exit 1
    fi

    echo_info "前端构建文件解压成功"
}

###############################################################################
# 检查 nginx 配置
###############################################################################

check_nginx_config() {
    echo_info "检查 nginx 配置..."

    if [ ! -f "/home/admin/requirement-estimation/frontend/nginx.internal.conf" ]; then
        echo_error "nginx 内网配置文件不存在: frontend/nginx.internal.conf"
        exit 1
    fi

    echo_info "nginx 配置文件检查通过"
}

###############################################################################
# 停止旧服务
###############################################################################

stop_old_service() {
    echo_info "停止旧服务..."

    cd /home/admin/requirement-estimation

    # 停止并删除旧容器
    if docker ps -a | grep -q requirement-frontend; then
        docker stop requirement-frontend 2>/dev/null || true
        docker rm requirement-frontend 2>/dev/null || true
    fi

    # 停止 docker-compose 启动的服务
    docker-compose -f docker-compose.frontend.internal.yml down 2>/dev/null || true

    echo_info "旧服务已停止"
}

###############################################################################
# 检查 nginx 镜像
###############################################################################

check_nginx_image() {
    echo_info "检查 nginx 镜像..."

    cd /home/admin/requirement-estimation

    if ! docker image inspect nginx:latest >/dev/null 2>&1; then
        echo_error "本地不存在 nginx:latest，请先离线导入镜像"
        echo_info "示例：docker load -i nginx_latest.tar"
        exit 1
    fi

    echo_info "nginx 镜像检查通过"
}

###############################################################################
# 启动服务
###############################################################################

start_service() {
    echo_info "启动前端服务..."

    cd /home/admin/requirement-estimation

    # 直接启动服务（不构建，使用已构建前端产物）
    docker-compose -f docker-compose.frontend.internal.yml up -d

    if [ $? -eq 0 ]; then
        echo_info "服务启动成功"
    else
        echo_error "服务启动失败"
        exit 1
    fi
}

###############################################################################
# 验证服务
###############################################################################

verify_service() {
    echo_info "等待服务启动..."
    sleep 5

    echo_info "检查容器状态..."
    if docker ps | grep -q requirement-frontend; then
        echo_info "容器正在运行"
    else
        echo_error "容器未运行，请查看日志"
        docker logs requirement-frontend
        exit 1
    fi

    echo_info "检查服务健康状态..."
    sleep 3

    if curl -f http://localhost:8000 &> /dev/null; then
        echo_info "前端服务验证成功"
    else
        echo_warn "健康检查失败，查看日志..."
        docker logs requirement-frontend
    fi
}

###############################################################################
# 显示部署结果
###############################################################################

show_result() {
    echo_info "========================================"
    echo_info "部署完成！"
    echo_info "========================================"
    echo_info "前端服务地址：http://10.62.16.251:8000"
    echo_info ""
    echo_info "常用命令："
    echo_info "  查看日志：docker logs -f requirement-frontend"
    echo_info "  重启服务：docker-compose -f docker-compose.frontend.internal.yml restart"
    echo_info "  停止服务：docker-compose -f docker-compose.frontend.internal.yml down"
    echo_info "========================================"
    echo_warn "请确保后端服务 (10.62.22.121:443) 已启动"
}

###############################################################################
# 主函数
###############################################################################

main() {
    check_prerequisites
    prepare_build_files
    check_nginx_config
    check_nginx_image
    stop_old_service
    start_service
    verify_service
    show_result
}

# 执行主函数
main
