#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
DISPATCHER_SRC="${ROOT_DIR}/scripts/cc-hooks/pre-write-dispatcher.sh"
LIB_SRC="${ROOT_DIR}/scripts/lib/review_gate_common.sh"
COMMON_SRC="${ROOT_DIR}/scripts/lib/common.sh"
VALIDATION_SRC="${ROOT_DIR}/scripts/lib/validation.sh"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

need_cmd git
need_cmd jq

tmp_dir=$(mktemp -d)
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT

cd "$tmp_dir"
git init -q
git config user.email "test@example.com"
git config user.name "test"

mkdir -p scripts/cc-hooks scripts/lib docs/v1.0 src
cp "$DISPATCHER_SRC" scripts/cc-hooks/pre-write-dispatcher.sh
cp "$LIB_SRC" scripts/lib/review_gate_common.sh
cp "$COMMON_SRC" scripts/lib/common.sh
cp "$VALIDATION_SRC" scripts/lib/validation.sh
chmod +x scripts/cc-hooks/pre-write-dispatcher.sh

cat > aicoding.config.yaml <<'EOF_CFG'
entry_gate_mode: block
enable_hotfix: true
hotfix_max_diff_files: 2
EOF_CFG

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: abcdef0
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: hotfix
_review_round: 0
_phase: Implementation
---
EOF_STATUS

git add -A
git commit -q -m "base"

run_dispatcher() {
  local file_path="$1" content="$2"
  local input
  input=$(jq -n --arg tool_name "Write" --arg file_path "$file_path" --arg content "$content" \
    '{tool_name:$tool_name, tool_input:{file_path:$file_path, content:$content}}')
  echo "$input" | CLAUDE_PROJECT_DIR="$tmp_dir" bash scripts/cc-hooks/pre-write-dispatcher.sh 2>&1 || true
}

assert_block_contains() {
  local output="$1" pattern="$2"
  echo "$output" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"' \
    || fail "expected dispatcher to block, got: $output"
  echo "$output" | grep -q "$pattern" \
    || fail "expected block message to contain [$pattern], got: $output"
}

output=$(run_dispatcher "db/migrations/001_add_users.sql" "CREATE TABLE users(id bigint);")
assert_block_contains "$output" "hotfix"

mkdir -p docs/v1.0
output=$(run_dispatcher "docs/v1.0/requirements.md" $'#### REQ-C001：禁止暴露内部字段\n- [ ] GWT-REQ-C001-01: Given ...')
assert_block_contains "$output" "REQ-C"

# 暂存文件以触发 hotfix 边界检查（现在基于暂存区计数）
echo "console.log('a');" > src/a.js
echo "console.log('b');" > src/b.js
git add src/a.js src/b.js
output=$(run_dispatcher "src/c.js" "console.log('c');")
assert_block_contains "$output" "文件数"

echo "ok"
