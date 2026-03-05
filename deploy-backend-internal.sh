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
PROJECT_DIR="/home/admin/requirement-estimation"
COMPOSE_FILE="docker-compose.backend.internal.yml"

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

strip_wrapping_quotes() {
    local value="$1"
    value="${value#\"}"
    value="${value%\"}"
    value="${value#\'}"
    value="${value%\'}"
    printf "%s" "$value"
}

read_env_value() {
    local key="$1"
    local env_file="$2"
    local raw_value

    raw_value="$(grep "^${key}=" "$env_file" | tail -n 1 | cut -d '=' -f2- | tr -d '\r')"
    strip_wrapping_quotes "$raw_value"
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

    cd "$PROJECT_DIR"

    # 停止并删除旧容器
    if docker ps -a | grep -q requirement-backend; then
        docker-compose -f "$COMPOSE_FILE" down 2>/dev/null || \
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

    cd "$PROJECT_DIR"

    if [ ! -f .env.backend.internal ]; then
        echo_error ".env.backend.internal 文件不存在"
        exit 1
    fi

    if [ -f .env.backend ]; then
        cp .env.backend ".env.backend.bak.$(date +%Y%m%d_%H%M%S)"
        echo_warn "检测到已有 .env.backend，已自动备份"
    fi

    cp .env.backend.internal .env.backend
    echo_info "已从 .env.backend.internal 同步 .env.backend"

    local ENV_FILE=".env.backend"
    local required_env_keys=("DASHSCOPE_API_KEY" "DASHSCOPE_API_BASE")
    local key
    for key in "${required_env_keys[@]}"; do
        if ! grep -q "^${key}=" "$ENV_FILE"; then
            echo_error "环境变量缺失: $key（文件: $ENV_FILE）"
            exit 1
        fi

        local normalized_value
        normalized_value="$(read_env_value "$key" "$ENV_FILE")"
        if [ -z "$normalized_value" ]; then
            echo_error "环境变量为空: $key（文件: $ENV_FILE）"
            exit 1
        fi
    done

    if ! docker-compose -f "$COMPOSE_FILE" config > /dev/null; then
        echo_error "docker-compose 配置解析失败，请检查 $COMPOSE_FILE 与 .env.backend"
        exit 1
    fi

    echo_info "环境变量文件检查通过"
}

###############################################################################
# 构建镜像
###############################################################################

build_image() {
    echo_info "开始构建后端镜像..."
    echo_info "这可能需要几分钟时间，请耐心等待..."

    cd "$PROJECT_DIR"

    # 删除旧镜像
    if docker images | grep -q requirement-backend; then
        echo_info "删除旧镜像..."
        docker rmi requirement-backend:latest 2>/dev/null || true
    fi

    # 构建新镜像
    if ! docker-compose -f "$COMPOSE_FILE" build --no-cache; then
        echo_warn "BuildKit 构建失败，回退到经典构建模式（DOCKER_BUILDKIT=0）..."
        DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 docker-compose -f "$COMPOSE_FILE" build --no-cache
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

    cd "$PROJECT_DIR"

    # 创建必要目录并对齐属主到项目目录 owner/group
    mkdir -p data logs uploads backend/config

    local ref_uid_gid
    local ref_owner
    local dir
    local target_dirs=(data logs uploads backend/config)
    if [ -e "$PROJECT_DIR/backend" ]; then
        ref_uid_gid="$(stat -c '%u:%g' "$PROJECT_DIR/backend")"
        ref_owner="$(stat -c '%U:%G' "$PROJECT_DIR/backend")"
    else
        ref_uid_gid="$(stat -c '%u:%g' "$PROJECT_DIR")"
        ref_owner="$(stat -c '%U:%G' "$PROJECT_DIR")"
    fi

    if [ "$EUID" -eq 0 ]; then
        chown -R "$ref_uid_gid" "${target_dirs[@]}" 2>/dev/null || \
            echo_warn "目录属主自动对齐失败，请手动执行: chown -R $ref_uid_gid data logs uploads backend/config"
    else
        local mismatch=0
        for dir in "${target_dirs[@]}"; do
            if [ "$(stat -c '%u:%g' "$dir")" != "$ref_uid_gid" ]; then
                mismatch=1
                break
            fi
        done
        if [ "$mismatch" -eq 1 ]; then
            echo_warn "当前非 root 且目录属主与项目目录不一致，可能影响容器写入权限"
        fi
    fi

    chmod -R u+rwX,g+rwX "${target_dirs[@]}" 2>/dev/null || \
        echo_warn "目录权限自动修复失败，请手动执行: chmod -R u+rwX,g+rwX data logs uploads backend/config"
    echo_info "目录属主参考：$ref_owner"

    # 初始化内网默认账号（用户名=密码，容器内执行，不依赖宿主机 python3）
    if ! docker-compose -f "$COMPOSE_FILE" run --rm --no-deps backend \
        python scripts/init_internal_users.py --data-dir /app/data; then
        echo_error "默认用户初始化失败"
        exit 1
    fi

    # 启动服务
    docker-compose -f "$COMPOSE_FILE" up -d

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

    echo_info "验证容器运行时环境变量..."
    local file_api_base
    local runtime_api_base
    file_api_base="$(read_env_value "DASHSCOPE_API_BASE" ".env.backend")"
    runtime_api_base="$(docker exec requirement-backend printenv DASHSCOPE_API_BASE 2>/dev/null | tr -d '\r')"
    runtime_api_base="$(strip_wrapping_quotes "$runtime_api_base")"

    if [ -z "$runtime_api_base" ]; then
        echo_error "容器内未加载 DASHSCOPE_API_BASE"
        exit 1
    fi

    if [ "$runtime_api_base" != "$file_api_base" ]; then
        echo_error "容器内 DASHSCOPE_API_BASE 与 .env.backend 不一致"
        echo_error "请检查 docker-compose 环境注入链路"
        exit 1
    fi
    echo_info "运行时环境变量验证通过"

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
    echo_info "  重启服务：docker-compose -f $COMPOSE_FILE restart"
    echo_info "  停止服务：docker-compose -f $COMPOSE_FILE down"
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
