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
PROJECT_DIR="${PROJECT_DIR:-/home/admin/requirement-estimation}"
COMPOSE_FILE="docker-compose.frontend.internal.yml"
NGINX_CONF_PATH="$PROJECT_DIR/frontend/nginx.internal.conf"
RUNTIME_NGINX_CONF="$PROJECT_DIR/frontend/nginx.internal.runtime.conf"
BUILD_DIR="$PROJECT_DIR/frontend/build"
BACKEND_UPSTREAM=""

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

normalize_upstream_value() {
    local raw="$1"
    local normalized
    normalized="$(strip_wrapping_quotes "$raw")"
    normalized="${normalized#http://}"
    normalized="${normalized#https://}"
    normalized="${normalized%/}"
    printf "%s" "$normalized"
}

read_env_file_value() {
    local file_path="$1"
    local key="$2"

    if [ ! -f "$file_path" ]; then
        return 0
    fi

    grep -E "^${key}=" "$file_path" 2>/dev/null | tail -n 1 | cut -d '=' -f2- | tr -d '\r'
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

normalize_build_layout() {
    local BUILD_DIR="$1"
    local NESTED_INDEX

    # Some tar packages include an extra directory level (e.g. build/index.html).
    NESTED_INDEX=$(find "$BUILD_DIR" -mindepth 2 -maxdepth 5 -type f -name index.html | head -n 1 || true)

    if [ -z "$NESTED_INDEX" ]; then
        return 1
    fi

    local NESTED_DIR
    local TMP_DIR
    NESTED_DIR=$(dirname "$NESTED_INDEX")
    TMP_DIR=$(mktemp -d)

    echo_warn "检测到嵌套构建目录：$NESTED_DIR，自动展开到 $BUILD_DIR"
    cp -a "$NESTED_DIR"/. "$TMP_DIR"/
    find "$BUILD_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    cp -a "$TMP_DIR"/. "$BUILD_DIR"/
    rm -rf "$TMP_DIR"
}

prepare_build_files() {
    echo_info "检查前端构建文件..."

    local BUILD_TAR="/home/admin/frontend-build.tar.gz"

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

    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"
    echo_info "解压前端构建文件..."
    tar xzf "$BUILD_TAR" -C "$BUILD_DIR"

    if [ ! -f "$BUILD_DIR/index.html" ]; then
        normalize_build_layout "$BUILD_DIR" || true
    fi

    if [ ! -f "$BUILD_DIR/index.html" ]; then
        echo_error "前端构建文件不完整（缺少 index.html）"
        echo_info "请检查压缩包目录，推荐结构：index.html 与 static/ 在压缩包根目录"
        exit 1
    fi

    echo_info "前端构建文件解压成功"
}

###############################################################################
# 渲染运行时 nginx 配置（支持前后端分离）
###############################################################################

resolve_backend_upstream() {
    local value="${FRONTEND_BACKEND_UPSTREAM:-}"

    if [ -z "$value" ]; then
        value="$(read_env_file_value "$PROJECT_DIR/.env.frontend" "FRONTEND_BACKEND_UPSTREAM")"
    fi

    if [ -z "$value" ]; then
        value="$(read_env_file_value "$PROJECT_DIR/.env.frontend.internal" "FRONTEND_BACKEND_UPSTREAM")"
    fi

    if [ -z "$value" ] && [ -f "$NGINX_CONF_PATH" ]; then
        value="$(grep -E 'proxy_pass[[:space:]]+http://[^;]+;' "$NGINX_CONF_PATH" | head -n 1 | sed -E 's/.*proxy_pass[[:space:]]+http:\/\/([^;]+);.*/\1/')"
    fi

    BACKEND_UPSTREAM="$(normalize_upstream_value "$value")"

    if [ -z "$BACKEND_UPSTREAM" ]; then
        echo_error "未解析到后端地址，请通过以下任一方式设置 FRONTEND_BACKEND_UPSTREAM："
        echo_error "1) 临时环境变量：FRONTEND_BACKEND_UPSTREAM=10.62.22.121:443 bash deploy-frontend-internal.sh"
        echo_error "2) 持久配置文件：$PROJECT_DIR/.env.frontend"
        echo_error "3) 兼容旧配置文件：$PROJECT_DIR/.env.frontend.internal"
        exit 1
    fi

    if [ "$BACKEND_UPSTREAM" = "requirement-backend:443" ] || [ "$BACKEND_UPSTREAM" = "requirement-backend" ]; then
        echo_error "当前后端地址为容器名 requirement-backend，前后端分离部署不可达"
        echo_error "请改为后端服务器可达地址，例如：10.62.22.121:443"
        echo_error "也可写入 $PROJECT_DIR/.env.frontend 后重试"
        exit 1
    fi

    if [[ "$BACKEND_UPSTREAM" =~ [[:space:]] ]]; then
        echo_error "FRONTEND_BACKEND_UPSTREAM 包含空格，格式非法: $BACKEND_UPSTREAM"
        exit 1
    fi

    echo_info "后端代理目标: $BACKEND_UPSTREAM"
}

render_runtime_nginx_config() {
    echo_info "渲染运行时 nginx 配置..."

    if [ ! -f "$NGINX_CONF_PATH" ]; then
        echo_error "nginx 内网配置文件不存在: frontend/nginx.internal.conf"
        exit 1
    fi

    resolve_backend_upstream

    sed -E "s#proxy_pass[[:space:]]+http://[^;]+;#proxy_pass http://${BACKEND_UPSTREAM};#g" \
        "$NGINX_CONF_PATH" > "$RUNTIME_NGINX_CONF"

    if ! grep -q "proxy_pass http://${BACKEND_UPSTREAM};" "$RUNTIME_NGINX_CONF"; then
        echo_error "运行时 nginx 配置渲染失败，未找到目标 proxy_pass"
        exit 1
    fi

    export FRONTEND_NGINX_CONF="./frontend/$(basename "$RUNTIME_NGINX_CONF")"
}

###############################################################################
# 检查 nginx 配置
###############################################################################

check_nginx_config() {
    echo_info "检查 nginx 配置..."

    if [ ! -f "$RUNTIME_NGINX_CONF" ]; then
        echo_error "运行时 nginx 配置不存在: $RUNTIME_NGINX_CONF"
        exit 1
    fi

    if ! grep -q "proxy_pass http://${BACKEND_UPSTREAM};" "$RUNTIME_NGINX_CONF"; then
        echo_error "运行时 nginx 配置缺少后端代理: proxy_pass http://${BACKEND_UPSTREAM};"
        exit 1
    fi

    # 使用离线 nginx 镜像进行语法预检，避免错误配置上线
    if ! docker run --rm \
        -v "$RUNTIME_NGINX_CONF:/etc/nginx/nginx.conf:ro" \
        -v "$BUILD_DIR:/usr/share/nginx/html:ro" \
        nginx:latest nginx -t; then
        echo_error "nginx 配置语法校验失败"
        exit 1
    fi

    echo_info "nginx 配置检查通过"
}

###############################################################################
# 停止旧服务
###############################################################################

stop_old_service() {
    echo_info "停止旧服务..."

    cd "$PROJECT_DIR"

    # 停止并删除旧容器
    if docker ps -a | grep -q requirement-frontend; then
        docker stop requirement-frontend 2>/dev/null || true
        docker rm requirement-frontend 2>/dev/null || true
    fi

    # 停止 docker-compose 启动的服务
    docker-compose -f "$COMPOSE_FILE" down 2>/dev/null || true

    echo_info "旧服务已停止"
}

###############################################################################
# 检查 nginx 镜像
###############################################################################

check_nginx_image() {
    echo_info "检查 nginx 镜像..."

    cd "$PROJECT_DIR"

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

    cd "$PROJECT_DIR"

    # 直接启动服务（不构建，使用已构建前端产物）
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
    sleep 5

    echo_info "检查容器状态..."
    if docker ps | grep -q requirement-frontend; then
        echo_info "容器正在运行"
    else
        echo_error "容器未运行，请查看日志"
        docker logs requirement-frontend
        exit 1
    fi

    echo_info "验证容器内 nginx 配置..."
    if ! docker exec requirement-frontend nginx -t; then
        echo_error "容器内 nginx 配置校验失败"
        docker logs requirement-frontend
        exit 1
    fi

    local runtime_upstream
    runtime_upstream="$(docker exec requirement-frontend sh -c "grep -E 'proxy_pass[[:space:]]+http://[^;]+;' /etc/nginx/nginx.conf | head -n 1 | sed -E 's/.*proxy_pass[[:space:]]+http:\/\/([^;]+);.*/\\1/'")"
    runtime_upstream="$(normalize_upstream_value "$runtime_upstream")"
    if [ "$runtime_upstream" != "$BACKEND_UPSTREAM" ]; then
        echo_error "容器内 proxy_pass 与目标后端不一致：$runtime_upstream != $BACKEND_UPSTREAM"
        exit 1
    fi

    echo_info "检查服务健康状态..."
    sleep 3

    if ! curl -f http://localhost:8000 &> /dev/null; then
        echo_error "HTTP 入口验证失败，查看日志..."
        docker logs requirement-frontend
        exit 1
    fi

    if ! curl -I http://localhost:8000 2>/dev/null | grep -qi 'Strict-Transport-Security: max-age=16070400'; then
        echo_error "HTTP 8000 入口缺少 HSTS 响应头"
        docker logs requirement-frontend
        exit 1
    fi

    echo_info "前端服务验证成功"
}

###############################################################################
# 显示部署结果
###############################################################################

show_result() {
    local display_ip="${FRONTEND_PUBLIC_IP:-10.62.16.251}"

    echo_info "========================================"
    echo_info "部署完成！"
    echo_info "========================================"
    echo_info "前端服务地址：http://${display_ip}:8000"
    echo_info "后端代理地址：http://$BACKEND_UPSTREAM"
    echo_info ""
    echo_info "常用命令："
    echo_info "  查看日志：docker logs -f requirement-frontend"
    echo_info "  重启服务：docker-compose -f $COMPOSE_FILE restart"
    echo_info "  停止服务：docker-compose -f $COMPOSE_FILE down"
    echo_info "========================================"
}

###############################################################################
# 主函数
###############################################################################

main() {
    check_prerequisites
    prepare_build_files
    check_nginx_image
    render_runtime_nginx_config
    check_nginx_config
    stop_old_service
    start_service
    verify_service
    show_result
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main
fi
