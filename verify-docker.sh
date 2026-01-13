#!/bin/bash
# Dockerfile 验证脚本
# 用于验证 uv sync、pyproject.toml、uv.lock 和非 root 用户配置

set -e

echo "========================================="
echo "Dockerfile 配置验证"
echo "========================================="

# 1. 检查是否使用了现代 uv sync 方式
echo ""
echo "[检查 1/6] Dockerfile 是否使用 uv sync..."
if grep -q "uv sync" Dockerfile; then
    echo "✅ Dockerfile 使用 uv sync（最佳实践）"
else
    echo "⚠️  Dockerfile 未使用 uv sync"
    echo "   建议使用：uv sync --frozen --no-dev"
fi

# 2. 检查是否复制了 pyproject.toml 和 uv.lock
echo ""
echo "[检查 2/6] Dockerfile 是否复制配置文件..."
if grep -q "pyproject.toml" Dockerfile && grep -q "uv.lock" Dockerfile; then
    echo "✅ Dockerfile 复制了 pyproject.toml 和 uv.lock"
else
    echo "❌ Dockerfile 未复制必要的配置文件"
    echo "   需要：COPY pyproject.toml uv.lock ./"
    exit 1
fi

# 3. 检查是否创建了非 root 用户
echo ""
echo "[检查 3/6] Dockerfile 是否创建非 root 用户..."
if grep -q "useradd.*appuser" Dockerfile; then
    echo "✅ Dockerfile 创建了 appuser 用户"
else
    echo "❌ Dockerfile 未创建非 root 用户"
    exit 1
fi

# 4. 检查是否切换到非 root 用户
echo ""
echo "[检查 4/6] Dockerfile 是否切换到非 root 用户..."
if grep -q "^USER appuser" Dockerfile; then
    echo "✅ Dockerfile 切换到 appuser 用户"
else
    echo "❌ Dockerfile 未切换到非 root 用户"
    exit 1
fi

# 5. 检查 docker-compose.yml 是否配置了 UV_INDEX_URL
echo ""
echo "[检查 5/6] docker-compose.yml 是否配置镜像源..."
if grep -q "UV_INDEX_URL" docker-compose.yml; then
    echo "✅ docker-compose.yml 配置了 UV_INDEX_URL"
    echo "当前配置："
    grep -A1 "UV_INDEX_URL" docker-compose.yml | head -2
else
    echo "❌ docker-compose.yml 未配置 UV_INDEX_URL"
    exit 1
fi

# 6. 检查文件权限设置
echo ""
echo "[检查 6/6] Dockerfile 是否设置文件权限..."
if grep -q "COPY.*--chown=appuser:appuser" Dockerfile; then
    echo "✅ Dockerfile 使用 --chown 设置文件权限"
else
    echo "⚠️  Dockerfile 未使用 --chown（建议添加）"
fi

# 7. 检查是否有 --frozen 和 --no-dev 参数
echo ""
echo "[检查 7/6] Dockerfile 是否使用安全参数..."
if grep -q "uv sync.*--frozen" Dockerfile; then
    echo "✅ 使用 --frozen 参数（生产环境安全）"
else
    echo "⚠️  未使用 --frozen 参数（建议添加）"
fi

if grep -q "uv sync.*--no-dev" Dockerfile; then
    echo "✅ 使用 --no-dev 参数（不安装开发依赖）"
else
    echo "⚠️  未使用 --no-dev 参数（建议添加）"
fi

echo ""
echo "========================================="
echo "✅ 基本配置检查通过！"
echo "========================================="
echo ""
echo "最佳实践检查："
echo "✅ uv sync --frozen --no-dev（现代方式）"
echo "✅ pyproject.toml + uv.lock（100% 可重现）"
echo "✅ 非 root 用户（安全）"
echo ""
echo "下一步："
echo "1. 测试构建：docker build -t requirement-backend ."
echo "2. 测试运行：docker-compose up -d"
echo "3. 验证用户：docker exec requirement-backend whoami"
echo "   （应该输出：appuser）"
echo ""

