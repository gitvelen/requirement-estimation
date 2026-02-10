#!/bin/bash
###############################################################################
# 内网环境后端一键部署脚本
#
# 服务器：10.62.22.121:443
# 工作目录：/home/admin/requirement-estimation
# 功能：自动构建并启动后端服务
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
    echo_info "内网后端一键部署脚本"
    echo_info "========================================"

    # 检查是否为 root 用户
    if [ "$EUID" -ne 0 ]; then
        echo_warn "建议使用 root 用户执行此脚本"
        read -p "是否继续？(y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

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
# 停止旧服务
###############################################################################

stop_old_service() {
    echo_info "停止旧服务..."

    cd /home/admin/requirement-estimation

    # 停止并删除旧容器
    if docker ps -a | grep -q requirement-backend; then
        docker-compose -f docker-compose.backend.internal.yml down 2>/dev/null || \
        docker stop requirement-backend 2>/dev/null || true
        docker rm requirement-backend 2>/dev/null || true
    fi

    echo_info "旧服务已停止"
}

###############################################################################
# 配置环境变量
###############################################################################

configure_env() {
    echo_info "配置环境变量..."

    cd /home/admin/requirement-estimation

    # 如果环境变量文件不存在，从示例复制
    if [ ! -f .env.backend ]; then
        if [ -f .env.backend.internal ]; then
            cp .env.backend.internal .env.backend
            echo_info "已从 .env.backend.internal 创建 .env.backend"
        else
            echo_error ".env.backend.internal 文件不存在"
            exit 1
        fi
    else
        echo_info ".env.backend 已存在，跳过配置"
    fi
}

###############################################################################
# 构建镜像
###############################################################################

build_image() {
    echo_info "开始构建后端镜像..."
    echo_info "这可能需要几分钟时间，请耐心等待..."

    cd /home/admin/requirement-estimation

    # 删除旧镜像
    if docker images | grep -q requirement-backend; then
        echo_info "删除旧镜像..."
        docker rmi requirement-backend:latest 2>/dev/null || true
    fi

    # 构建新镜像
    if ! docker-compose -f docker-compose.backend.internal.yml build --no-cache; then
        echo_warn "BuildKit 构建失败，回退到经典构建模式（DOCKER_BUILDKIT=0）..."
        DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 docker-compose -f docker-compose.backend.internal.yml build --no-cache
    fi

    if [ $? -eq 0 ]; then
        echo_info "镜像构建成功"
    else
        echo_error "镜像构建失败"
        exit 1
    fi
}

###############################################################################
# 启动服务
###############################################################################

start_service() {
    echo_info "启动后端服务..."

    cd /home/admin/requirement-estimation

    # 创建必要的目录
    mkdir -p data logs uploads backend/config

    # 启动服务
    docker-compose -f docker-compose.backend.internal.yml up -d

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
    sleep 10

    echo_info "检查容器状态..."
    if docker ps | grep -q requirement-backend; then
        echo_info "容器正在运行"
    else
        echo_error "容器未运行，请查看日志"
        docker logs requirement-backend
        exit 1
    fi

    echo_info "检查服务健康状态..."
    sleep 5

    if curl -f http://localhost:443/api/v1/health &> /dev/null; then
        echo_info "后端服务验证成功"
    else
        echo_warn "健康检查失败，但服务可能仍在启动中"
        echo_info "请稍后手动验证：curl http://localhost:443/api/v1/health"
    fi
}

###############################################################################
# 显示部署结果
###############################################################################

show_result() {
    echo_info "========================================"
    echo_info "部署完成！"
    echo_info "========================================"
    echo_info "后端服务地址：http://10.62.22.121:443"
    echo_info "健康检查：curl http://10.62.22.121:443/api/v1/health"
    echo_info ""
    echo_info "常用命令："
    echo_info "  查看日志：docker logs -f requirement-backend"
    echo_info "  重启服务：docker-compose -f docker-compose.backend.internal.yml restart"
    echo_info "  停止服务：docker-compose -f docker-compose.backend.internal.yml down"
    echo_info "========================================"
}

###############################################################################
# 主函数
###############################################################################

main() {
    check_prerequisites
    stop_old_service
    configure_env
    build_image
    start_service
    verify_service
    show_result
}

# 执行主函数
main
