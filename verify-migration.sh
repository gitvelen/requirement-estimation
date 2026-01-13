#!/bin/bash
# 迁移验证脚本
# 用于验证 pyproject.toml + uv.lock 迁移是否成功

set -e

echo "========================================="
echo "依赖管理迁移验证"
echo "========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 计数器
PASS=0
FAIL=0
WARN=0

# 检查函数
check_pass() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASS++))
}

check_fail() {
    echo -e "${RED}❌ $1${NC}"
    ((FAIL++))
}

check_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARN++))
}

# 1. 检查文件是否存在
echo "[检查 1/9] 验证文件完整性..."
echo ""

if [ -f "pyproject.toml" ]; then
    check_pass "pyproject.toml 存在"
else
    check_fail "pyproject.toml 不存在"
    exit 1
fi

if [ -f "uv.lock" ]; then
    check_pass "uv.lock 存在"
else
    check_fail "uv.lock 不存在"
    exit 1
fi

if [ -f "requirements.txt" ]; then
    check_pass "requirements.txt 保留（兼容性）"
else
    check_warn "requirements.txt 不存在（建议保留）"
fi

echo ""

# 2. 检查 pyproject.toml 内容
echo "[检查 2/9] 验证 pyproject.toml 内容..."
echo ""

if grep -q "name = \"requirement-estimation-system\"" pyproject.toml; then
    check_pass "项目名称正确"
else
    check_fail "项目名称缺失或错误"
fi

if grep -q "dependencies = \[" pyproject.toml; then
    check_pass "依赖声明存在"
else
    check_fail "依赖声明缺失"
fi

if grep -q "\[project.optional-dependencies\]" pyproject.toml; then
    check_pass "可选依赖配置存在"
else
    check_warn "可选依赖配置不存在（可选）"
fi

if grep -q "\[dependency-groups\]" pyproject.toml; then
    check_pass "依赖分组配置存在（新格式）"
else
    check_warn "依赖分组配置不存在（可选）"
fi

echo ""

# 3. 检查 uv.lock 内容
echo "[检查 3/9] 验证 uv.lock 内容..."
echo ""

PACKAGE_COUNT=$(grep -c "^\\[\\[package\\]\\]" uv.lock || echo "0")
if [ "$PACKAGE_COUNT" -ge 80 ]; then
    check_pass "uv.lock 包含 $PACKAGE_COUNT 个包（预期 80+）"
else
    check_fail "uv.lock 包含 $PACKAGE_COUNT 个包（预期 80+）"
fi

if grep -q "version = 1" uv.lock; then
    check_pass "uv.lock 版本正确"
else
    check_warn "uv.lock 版本可能不匹配"
fi

if grep -q "requires-python" uv.lock; then
    check_pass "Python 版本要求存在"
else
    check_fail "Python 版本要求缺失"
fi

echo ""

# 4. 检查 Dockerfile
echo "[检查 4/9] 验证 Dockerfile 配置..."
echo ""

if grep -q "COPY.*pyproject.toml uv.lock" Dockerfile; then
    check_pass "Dockerfile 复制 pyproject.toml 和 uv.lock"
else
    check_fail "Dockerfile 未复制新的依赖文件"
fi

if grep -q "uv sync --frozen" Dockerfile; then
    check_pass "Dockerfile 使用 uv sync --frozen"
else
    check_fail "Dockerfile 未使用 uv sync --frozen"
fi

if grep -q "--no-dev" Dockerfile; then
    check_pass "Dockerfile 不安装开发依赖"
else
    check_warn "Dockerfile 可能安装开发依赖（建议添加 --no-dev）"
fi

echo ""

# 5. 检查 .dockerignore
echo "[检查 5/9] 验证 .dockerignore 配置..."
echo ""

if grep -q "^\\.uv/$" .dockerignore; then
    check_pass ".dockerignore 忽略 .uv/ 缓存目录"
else
    check_warn ".dockerignore 未忽略 .uv/ 缓存目录"
fi

if grep -q "^uv\\.lock$" .dockerignore; then
    check_fail ".dockerignore 忽略了 uv.lock（错误！）"
else
    check_pass ".dockerignore 不忽略 uv.lock（正确）"
fi

echo ""

# 6. 检查 uv 工具
echo "[检查 6/9] 检查 uv 工具..."
echo ""

if command -v uv &> /dev/null; then
    check_pass "uv 工具已安装"

    UV_VERSION=$(uv --version 2>/dev/null || echo "unknown")
    echo "   版本: $UV_VERSION"
else
    check_warn "uv 工具未安装（推荐安装：pip install uv）"
fi

echo ""

# 7. 验证依赖安装
echo "[检查 7/9] 验证依赖安装..."
echo ""

if command -v uv &> /dev/null; then
    echo "   尝试安装依赖（可能需要几分钟）..."
    if uv sync --no-dev > /tmp/uv-sync.log 2>&1; then
        check_pass "依赖安装成功"
    else
        check_fail "依赖安装失败，查看 /tmp/uv-sync.log"
        echo "   错误信息："
        tail -5 /tmp/uv-sync.log | sed 's/^/   /'
    fi
else
    check_warn "跳过依赖安装测试（uv 未安装）"
fi

echo ""

# 8. 验证应用导入
echo "[检查 8/9] 验证应用导入..."
echo ""

if [ -d ".venv" ]; then
    check_pass "虚拟环境 .venv 存在"

    echo "   测试导入应用模块..."
    if .venv/bin/python -c "import sys; sys.path.insert(0, '.'); import backend.app" 2>/dev/null; then
        check_pass "应用模块导入成功"
    else
        check_fail "应用模块导入失败"
    fi
else
    check_warn "虚拟环境 .venv 不存在"
fi

echo ""

# 9. 对比 requirements.txt
echo "[检查 9/9] 对比旧版本 requirements.txt..."
echo ""

if [ -f "requirements.txt" ]; then
    DEPS_IN_TXT=$(grep -v "^#" requirements.txt | grep -v "^$" | wc -l)
    check_pass "requirements.txt 包含 $DEPS_IN_TXT 个依赖（保留用于兼容）"
    echo "   提示：requirements.txt 已弃用，建议使用 pyproject.toml + uv.lock"
fi

echo ""

# 总结
echo "========================================="
echo "验证结果"
echo "========================================="
echo ""
echo -e "${GREEN}✅ 通过: $PASS${NC}"
echo -e "${YELLOW}⚠️  警告: $WARN${NC}"
echo -e "${RED}❌ 失败: $FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}🎉 迁移验证通过！${NC}"
    echo ""
    echo "下一步："
    echo "1. 测试运行应用："
    echo "   uv run python backend/app.py"
    echo ""
    echo "2. 验证 Docker 构建："
    echo "   docker build -t requirement-backend ."
    echo ""
    echo "3. 提交代码："
    echo "   git add pyproject.toml uv.lock .dockerignore Dockerfile"
    echo "   git commit -m '迁移到 pyproject.toml + uv.lock'"
    echo ""
    exit 0
else
    echo -e "${RED}❌ 迁移验证失败！${NC}"
    echo ""
    echo "请修复上述错误后重试。"
    echo ""
    echo "常见问题："
    echo "1. uv.lock 不存在：运行 'uv lock' 生成"
    echo "2. uv 未安装：运行 'pip install uv'"
    echo "3. Dockerfile 错误：参考 MIGRATION_TO_UV_LOCK.md"
    echo ""
    exit 1
fi
