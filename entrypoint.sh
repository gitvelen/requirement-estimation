#!/bin/bash
###############################################################################
# 容器启动脚本
#
# 作用：
#   1. 容器启动时的预处理操作
#   2. 等待依赖服务（如数据库）
#   3. 执行初始化任务（如数据迁移）
#   4. 启动主应用
#
# 使用方式：
#   在 Dockerfile 中通过 ENTRYPOINT 或 CMD 调用
###############################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
# 环境变量验证
###############################################################################

validate_env_vars() {
    echo_info "验证环境变量..."

    # 检查必需的环境变量
    required_vars=("DASHSCOPE_API_KEY")
    missing_vars=()

    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -ne 0 ]; then
        echo_error "缺少必需的环境变量: ${missing_vars[*]}"
        echo_error "请在 .env 文件中配置这些变量"
        exit 1
    fi

    echo_info "环境变量验证通过"
}

###############################################################################
# 创建必要的目录
###############################################################################

create_directories() {
    echo_info "创建必要的目录..."

    mkdir -p /app/logs /app/data /app/uploads /app/backend/config

    # 确保日志目录可写（以 root 身份运行此脚本时）
    if [ "$(id -u)" = "0" ]; then
        chown -R appuser:appuser /app/logs /app/data /app/uploads
    fi

    echo_info "目录创建完成"
}

###############################################################################
# 等待依赖服务（如果有数据库）
###############################################################################

wait_for_dependencies() {
    # 本项目不依赖外部数据库，此函数保留供扩展使用
    # 如果将来添加 PostgreSQL、MySQL、Redis 等，可以在这里等待

    # 示例：等待 PostgreSQL
    # if [ -n "$DATABASE_URL" ]; then
    #     echo_info "等待 PostgreSQL 启动..."
    #     until pg_isready -h $DB_HOST -U $DB_USER; do
    #         echo_warn "PostgreSQL 尚未就绪，等待中..."
    #         sleep 2
    #     done
    #     echo_info "PostgreSQL 已就绪"
    # fi

    # 示例：等待 Redis
    # if [ -n "$REDIS_URL" ]; then
    #     echo_info "等待 Redis 启动..."
    #     until redis-cli -h $REDIS_HOST ping; do
    #         echo_warn "Redis 尚未就绪，等待中..."
    #         sleep 2
    #     done
    #     echo_info "Redis 已就绪"
    # fi

    echo_info "依赖服务检查完成"
}

###############################################################################
# 执行数据库迁移（如果需要）
###############################################################################

run_migrations() {
    # 本项目不使用数据库，此函数保留供扩展使用
    # 如果将来使用 Django、SQLAlchemy 等，可以在这里执行迁移

    # 示例：Django 迁移
    # if [ "$RUN_MIGRATIONS" = "true" ]; then
    #     echo_info "执行数据库迁移..."
    #     python manage.py migrate --noinput
    #     echo_info "数据库迁移完成"
    # fi

    # 示例：Alembic 迁移
    # if [ "$RUN_MIGRATIONS" = "true" ]; then
    #     echo_info "执行数据库迁移..."
    #     alembic upgrade head
    #     echo_info "数据库迁移完成"
    # fi

    echo_info "迁移检查完成"
}

###############################################################################
# 收集静态文件（如果需要）
###############################################################################

collect_static() {
    # 本项目不使用 Django，此函数保留供扩展使用

    # 示例：Django 静态文件收集
    # if [ "$COLLECT_STATIC" = "true" ]; then
    #     echo_info "收集静态文件..."
    #     python manage.py collectstatic --noinput
    #     echo_info "静态文件收集完成"
    # fi

    echo_info "静态文件检查完成"
}

###############################################################################
# 健康检查
###############################################################################

health_check() {
    echo_info "执行健康检查..."

    # 检查 Python 环境
    python3 --version || {
        echo_error "Python 不可用"
        exit 1
    }

    # 检查主应用文件
    if [ ! -f "/app/backend/app.py" ]; then
        echo_error "主应用文件不存在: /app/backend/app.py"
        exit 1
    fi

    # 尝试导入主应用
    python3 -c "import sys; sys.path.insert(0, '/app'); import backend.app" || {
        echo_error "应用导入失败，请检查依赖"
        exit 1
    }

    echo_info "健康检查通过"
}

###############################################################################
# 显示启动信息
###############################################################################

show_startup_info() {
    echo_info "========================================"
    echo_info "启动需求评估系统"
    echo_info "========================================"
    echo_info "项目名称: $(grep '^name = ' pyproject.toml | cut -d'"' -f2 | tr -d '"')"
    echo_info "Python 版本: $(python3 --version)"
    echo_info "工作目录: $(pwd)"
    echo_info "用户: $(whoami)"
    echo_info "端口: ${PORT:-443}"
    echo_info "调试模式: ${DEBUG:-false}"
    echo_info "========================================"
}

###############################################################################
# 主函数
###############################################################################

main() {
    echo_info "容器启动脚本开始执行..."

    # 1. 验证环境变量
    validate_env_vars

    # 2. 创建必要的目录
    create_directories

    # 3. 等待依赖服务（如果有）
    wait_for_dependencies

    # 4. 执行数据库迁移（如果有）
    run_migrations

    # 5. 收集静态文件（如果有）
    collect_static

    # 6. 健康检查
    health_check

    # 7. 显示启动信息
    show_startup_info

    # 8. 启动主应用
    echo_info "启动应用..."

    # 如果有传入参数，执行参数命令
    # 否则使用默认启动命令
    if [ $# -gt 0 ]; then
        echo_info "执行命令: $@"
        exec "$@"
    else
        # 默认启动命令 - 使用 uvicorn（PATH 中已包含虚拟环境）
        # 根据 DEBUG 模式决定 workers 和 reload
        if [ "${DEBUG:-false}" = "true" ]; then
            echo_info "调试模式：单进程 + 热重载"
            exec uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-443} --reload --workers 1 --log-level info
        else
            echo_info "生产模式：多进程 (${WORKERS:-4}) + 无热重载"
            exec uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-443} --workers ${WORKERS:-4} --log-level info
        fi
    fi
}

###############################################################################
# 执行主函数
###############################################################################

# 传递所有参数给 main 函数
main "$@"
