#!/bin/bash
###############################################################################
# 内网环境 GitHub zip 一键部署脚本
#
# 用法：
#   bash deploy-internal-from-github-zip.sh /home/admin/requirement-estimation-main.zip
#
# 默认：
#   ZIP_PATH=/home/admin/requirement-estimation-main.zip
#   PROJECT_DIR=/home/admin/requirement-estimation
#
# 说明：
#   - 安全解压 GitHub 下载的 requirement-estimation-main.zip
#   - 原地更新代码，保留 data/uploads/logs/.deploy-backups 和本机 env 配置
#   - 后端必部署；前端在检测到构建产物时自动部署
###############################################################################

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ZIP_PATH="${1:-/home/admin/requirement-estimation-main.zip}"
PROJECT_DIR="${PROJECT_DIR:-/home/admin/requirement-estimation}"
DEPLOY_BACKEND="${DEPLOY_BACKEND:-1}"
DEPLOY_FRONTEND="${DEPLOY_FRONTEND:-auto}"
BACKUP_DIR="$PROJECT_DIR/.deploy-backups"
EXTRACT_DIR=""
RELEASE_DIR=""

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

cleanup() {
    if [ -n "$EXTRACT_DIR" ] && [ -d "$EXTRACT_DIR" ]; then
        rm -rf "$EXTRACT_DIR"
    fi
}

trap cleanup EXIT

dir_has_data() {
    local target_dir="$1"
    [ -d "$target_dir" ] && [ -n "$(find "$target_dir" -mindepth 1 -print -quit)" ]
}

runtime_has_data() {
    dir_has_data "$PROJECT_DIR/data" \
        || dir_has_data "$PROJECT_DIR/uploads" \
        || dir_has_data "$PROJECT_DIR/logs"
}

backup_runtime_dirs() {
    local backup_file="$BACKUP_DIR/runtime_$(date +%Y%m%d_%H%M%S).tar.gz"
    mkdir -p "$BACKUP_DIR"
    tar czf "$backup_file" -C "$PROJECT_DIR" data uploads logs
    echo_info "已备份运行数据：$backup_file"
}

prepare_runtime_dirs() {
    mkdir -p "$PROJECT_DIR/data" "$PROJECT_DIR/uploads" "$PROJECT_DIR/logs" "$BACKUP_DIR"
    if runtime_has_data; then
        backup_runtime_dirs
    else
        echo_info "首次部署或运行数据目录为空，创建 data/uploads/logs"
    fi
}

check_prerequisites() {
    if ! command -v unzip >/dev/null 2>&1; then
        echo_error "未找到 unzip，请先安装 unzip"
        exit 1
    fi

    if [ ! -f "$ZIP_PATH" ]; then
        echo_error "未找到安装包：$ZIP_PATH"
        exit 1
    fi
}

resolve_zip_path() {
    local zip_dir
    local zip_name
    zip_dir="$(cd "$(dirname "$ZIP_PATH")" && pwd)"
    zip_name="$(basename "$ZIP_PATH")"
    ZIP_PATH="$zip_dir/$zip_name"
}

extract_release() {
    EXTRACT_DIR="$(mktemp -d /tmp/requirement-estimation-zip.XXXXXX)"
    echo_info "解压安装包：$ZIP_PATH"
    unzip -q "$ZIP_PATH" -d "$EXTRACT_DIR"

    if [ -f "$EXTRACT_DIR/deploy-backend-internal.sh" ]; then
        RELEASE_DIR="$EXTRACT_DIR"
    else
        RELEASE_DIR="$(find "$EXTRACT_DIR" -mindepth 1 -maxdepth 3 -type f -name deploy-backend-internal.sh -printf '%h\n' | head -n 1 || true)"
    fi

    if [ -z "$RELEASE_DIR" ] || [ ! -f "$RELEASE_DIR/deploy-backend-internal.sh" ]; then
        echo_error "安装包结构不正确，未找到 deploy-backend-internal.sh"
        exit 1
    fi

    echo_info "识别安装包目录：$RELEASE_DIR"
}

stop_existing_services() {
    if [ ! -d "$PROJECT_DIR" ]; then
        return 0
    fi

    if command -v docker-compose >/dev/null 2>&1; then
        if frontend_requested && [ -f "$PROJECT_DIR/docker-compose.frontend.internal.yml" ]; then
            (cd "$PROJECT_DIR" && docker-compose -f docker-compose.frontend.internal.yml down 2>/dev/null || true)
        fi
        if backend_enabled && [ -f "$PROJECT_DIR/docker-compose.backend.internal.yml" ]; then
            (cd "$PROJECT_DIR" && docker-compose -f docker-compose.backend.internal.yml down 2>/dev/null || true)
        fi
    fi

    if command -v docker >/dev/null 2>&1; then
        if frontend_requested; then
            docker stop requirement-frontend 2>/dev/null || true
            docker rm requirement-frontend 2>/dev/null || true
        fi
        if backend_enabled; then
            docker stop requirement-backend 2>/dev/null || true
            docker rm requirement-backend 2>/dev/null || true
        fi
    fi
}

update_project_files() {
    mkdir -p "$PROJECT_DIR"
    prepare_runtime_dirs

    echo_info "停止旧服务..."
    stop_existing_services

    rm -rf "$RELEASE_DIR/data" "$RELEASE_DIR/uploads" "$RELEASE_DIR/logs" "$RELEASE_DIR/.deploy-backups"

    echo_info "原地更新代码，保留运行数据和环境配置..."
    cd "$PROJECT_DIR"
    find . -mindepth 1 -maxdepth 1 \
        ! -name data \
        ! -name uploads \
        ! -name logs \
        ! -name .deploy-backups \
        ! -name .env.backend \
        ! -name .env.backend.internal \
        ! -name .env.frontend \
        ! -name .env.frontend.internal \
        -exec rm -rf {} +

    cp -a "$RELEASE_DIR"/. "$PROJECT_DIR"/
    mkdir -p "$PROJECT_DIR/data" "$PROJECT_DIR/uploads" "$PROJECT_DIR/logs" "$BACKUP_DIR"
    chmod +x "$PROJECT_DIR/deploy-backend-internal.sh" "$PROJECT_DIR/deploy-frontend-internal.sh" 2>/dev/null || true
}

prepare_frontend_package() {
    if [ -f "$PROJECT_DIR/frontend/build/index.html" ] || [ -f /home/admin/frontend-build.tar.gz ]; then
        return 0
    fi

    if [ -f "$PROJECT_DIR/release/frontend-build.tar.gz" ]; then
        cp "$PROJECT_DIR/release/frontend-build.tar.gz" /home/admin/frontend-build.tar.gz
        echo_info "已准备前端构建包：/home/admin/frontend-build.tar.gz"
    fi
}

backend_enabled() {
    case "$DEPLOY_BACKEND" in
        0|false|False|no|NO)
            return 1
            ;;
        1|true|True|yes|YES)
            return 0
            ;;
        *)
            echo_error "DEPLOY_BACKEND 只能是 1/0，当前值：$DEPLOY_BACKEND"
            exit 1
            ;;
    esac
}

frontend_requested() {
    case "$DEPLOY_FRONTEND" in
        0|false|False|no|NO)
            return 1
            ;;
        auto|1|true|True|yes|YES)
            return 0
            ;;
        *)
            echo_error "DEPLOY_FRONTEND 只能是 auto/1/0，当前值：$DEPLOY_FRONTEND"
            exit 1
            ;;
    esac
}

should_deploy_frontend() {
    case "$DEPLOY_FRONTEND" in
        0|false|False|no|NO)
            return 1
            ;;
        1|true|True|yes|YES)
            return 0
            ;;
        auto)
            [ -f "$PROJECT_DIR/frontend/build/index.html" ] \
                || [ -f /home/admin/frontend-build.tar.gz ] \
                || [ -f "$PROJECT_DIR/release/frontend-build.tar.gz" ]
            return $?
            ;;
        *)
            echo_error "DEPLOY_FRONTEND 只能是 auto/1/0，当前值：$DEPLOY_FRONTEND"
            exit 1
            ;;
    esac
}

deploy_services() {
    cd "$PROJECT_DIR"

    if backend_enabled; then
        echo_info "部署后端..."
        bash deploy-backend-internal.sh
    else
        echo_warn "DEPLOY_BACKEND=0，已跳过后端部署"
    fi

    if should_deploy_frontend; then
        prepare_frontend_package
        echo_info "部署前端..."
        bash deploy-frontend-internal.sh
    else
        echo_warn "未检测到前端构建产物，已跳过前端部署"
        echo_warn "如需部署前端，请上传 /home/admin/frontend-build.tar.gz 后执行：bash deploy-frontend-internal.sh"
    fi
}

main() {
    echo_info "========================================"
    echo_info "GitHub zip 内网一键部署"
    echo_info "========================================"
    check_prerequisites
    resolve_zip_path
    extract_release
    update_project_files
    deploy_services
    echo_info "部署流程完成"
}

main
