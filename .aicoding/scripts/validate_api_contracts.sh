#!/bin/bash
# API 契约一致性验证脚本（参考实现，项目可定制）
# 用途：扫描前端 API 调用与后端路由定义，检查契约一致性

set -e

echo "=== API 契约一致性验证 ==="
echo ""

# 临时文件
FRONTEND_APIS="/tmp/frontend_apis.txt"
BACKEND_ROUTES="/tmp/backend_routes.txt"

# 清空临时文件
> "$FRONTEND_APIS"
> "$BACKEND_ROUTES"

# 1. 提取前端 API 调用
echo "1. 提取前端 API 调用..."
if [ -d "frontend/src" ] || [ -d "src" ]; then
  # 支持多种前端调用方式
  # axios.get/post/put/delete
  grep -rh "axios\.\(get\|post\|put\|delete\).*['\"]\/api" frontend/src src 2>/dev/null | \
    sed "s/.*['\"]\\(\/api[^'\"]*\\)['\"].*/\\1/" | \
    sed 's/\${[^}]*}/:param/g' | \
    sort -u >> "$FRONTEND_APIS" || true

  # fetch('/api/...')
  grep -rh "fetch.*['\"]\/api" frontend/src src 2>/dev/null | \
    sed "s/.*['\"]\\(\/api[^'\"]*\\)['\"].*/\\1/" | \
    sed 's/\${[^}]*}/:param/g' | \
    sort -u >> "$FRONTEND_APIS" || true

  # action: '/api/...' (Ant Design Form)
  grep -rh "action:.*['\"]\/api" frontend/src src 2>/dev/null | \
    sed "s/.*['\"]\\(\/api[^'\"]*\\)['\"].*/\\1/" | \
    sed 's/\${[^}]*}/:param/g' | \
    sort -u >> "$FRONTEND_APIS" || true

  # 去重
  sort -u "$FRONTEND_APIS" -o "$FRONTEND_APIS"
fi

# 2. 提取后端路由定义
echo "2. 提取后端路由定义..."
if [ -d "backend" ] || [ -d "server" ] || [ -d "api" ]; then
  # Python FastAPI/Flask
  grep -rh "@router\.\(get\|post\|put\|delete\)\|@app\.route" backend server api 2>/dev/null | \
    sed 's/.*["\x27]\\(\/api[^"\x27]*\\)["\x27].*/\\1/' | \
    sed 's/{[^}]*}/:param/g' | \
    sort -u >> "$BACKEND_ROUTES" || true

  # Node.js Express
  grep -rh "router\.\(get\|post\|put\|delete\)\|app\.\(get\|post\|put\|delete\)" backend server api 2>/dev/null | \
    sed "s/.*['\"]\\(\/api[^'\"]*\\)['\"].*/\\1/" | \
    sed 's/:[a-zA-Z_][a-zA-Z0-9_]*/:param/g' | \
    sort -u >> "$BACKEND_ROUTES" || true

  # 去重
  sort -u "$BACKEND_ROUTES" -o "$BACKEND_ROUTES"
fi

# 3. 检查是否提取到数据
if [ ! -s "$FRONTEND_APIS" ] && [ ! -s "$BACKEND_ROUTES" ]; then
  echo "⚠️  未检测到前后端 API 定义，跳过契约检查"
  echo "   提示：请确认项目目录结构或自定义此脚本的扫描规则"
  exit 0
fi

if [ ! -s "$FRONTEND_APIS" ]; then
  echo "⚠️  未检测到前端 API 调用"
fi

if [ ! -s "$BACKEND_ROUTES" ]; then
  echo "⚠️  未检测到后端路由定义"
fi

# 4. 对比差异
echo ""
echo "=== 对比结果 ==="
echo ""

MISMATCH=0

if [ -s "$FRONTEND_APIS" ] && [ -s "$BACKEND_ROUTES" ]; then
  # 前端调用但后端不存在
  FRONTEND_ONLY=$(comm -23 "$FRONTEND_APIS" "$BACKEND_ROUTES")
  if [ -n "$FRONTEND_ONLY" ]; then
    echo "❌ 前端调用但后端不存在的 API："
    echo "$FRONTEND_ONLY" | sed 's/^/   /'
    echo ""
    MISMATCH=1
  fi

  # 后端定义但前端未使用（仅提示，不阻断）
  BACKEND_ONLY=$(comm -13 "$FRONTEND_APIS" "$BACKEND_ROUTES")
  if [ -n "$BACKEND_ONLY" ]; then
    echo "ℹ️  后端定义但前端未使用的 API（仅提示）："
    echo "$BACKEND_ONLY" | sed 's/^/   /'
    echo ""
  fi

  if [ $MISMATCH -eq 0 ]; then
    echo "✅ API 契约一致性检查通过"
  fi
fi

# 5. 清理临时文件
rm -f "$FRONTEND_APIS" "$BACKEND_ROUTES"

# 6. 返回结果
if [ $MISMATCH -eq 1 ]; then
  echo ""
  echo "💡 修复建议："
  echo "   1. 检查前端 API 调用路径是否正确"
  echo "   2. 检查后端路由是否已定义"
  echo "   3. 检查 design.md 的 5.4 节 API 契约定义"
  exit 1
fi

exit 0
