#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
CHECKER="${ROOT_DIR}/scripts/cc-hooks/doc-structure-check.sh"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

need_cmd jq

tmp_dir=$(mktemp -d)
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT

file_path="${tmp_dir}/requirements.md"
cat > "$file_path" <<'EOF'
## 1. 概述

## 2. 业务场景

## 3. 功能性需求

## 4. 非功能需求

## 4A. 约束与禁止项

## 7. 变更记录

#### REQ-1000: 示例
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-1000-01: Given 用户已登录， When 打开首页， Then 显示欢迎语
EOF

input=$(jq -n --arg p "$file_path" '{tool_input:{file_path:$p}}')
output=$(echo "$input" | bash "$CHECKER" || true)

echo "$output" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"' && {
  echo "$output" >&2
  fail "expected doc-structure-check to accept variable-width GWT-ID like GWT-REQ-1000-01"
}

echo "ok"
