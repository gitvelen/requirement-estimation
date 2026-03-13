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

mkdir -p "$tmp_dir/scripts/cc-hooks" "$tmp_dir/scripts/lib" "$tmp_dir/docs/v1.0" "$tmp_dir/src"
cp "$DISPATCHER_SRC" "$tmp_dir/scripts/cc-hooks/pre-write-dispatcher.sh"
cp "$LIB_SRC" "$tmp_dir/scripts/lib/review_gate_common.sh"
cp "$COMMON_SRC" "$tmp_dir/scripts/lib/common.sh"
cp "$VALIDATION_SRC" "$tmp_dir/scripts/lib/validation.sh"
chmod +x "$tmp_dir/scripts/cc-hooks/pre-write-dispatcher.sh"

cat > "$tmp_dir/aicoding.config.yaml" <<'EOF_CFG'
entry_gate_mode: block
enable_hotfix: true
EOF_CFG

cat > "$tmp_dir/docs/v1.0/status.md" <<'EOF_STATUS'
---
_baseline: v0.9
_current: abcdef0
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: hotfix
_review_round: 0
_phase: Hotfix
---
EOF_STATUS

git add -A
git commit -q -m "base"

input=$(jq -n --arg tool_name "Write" --arg file_path "src/a.js" --arg content "console.log('hotfix');" \
  '{tool_name:$tool_name, tool_input:{file_path:$file_path, content:$content}}')

output=$(echo "$input" | CLAUDE_PROJECT_DIR="$tmp_dir" bash "$tmp_dir/scripts/cc-hooks/pre-write-dispatcher.sh" 2>&1 || true)
echo "$output" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"' \
  && fail "expected hotfix writes to avoid read-tracking blocks, got: $output"
echo "$output" | grep -q "阶段入口门禁" \
  && fail "expected hotfix writes to avoid entry-gate warnings, got: $output"

status_update_no_evidence=$(jq -n \
  --arg tool_name "Write" \
  --arg file_path "docs/v1.0/status.md" \
  --arg content $'---\n_baseline: v0.9\n_current: abcdef0\n_workflow_mode: auto\n_run_status: running\n_change_status: in_progress\n_change_level: hotfix\n_review_round: 0\n_phase: Implementation\n---\n' \
  '{tool_name:$tool_name, tool_input:{file_path:$file_path, content:$content}}')
output=$(echo "$status_update_no_evidence" | CLAUDE_PROJECT_DIR="$tmp_dir" bash "$tmp_dir/scripts/cc-hooks/pre-write-dispatcher.sh" 2>&1 || true)
echo "$output" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"' \
  || fail "expected leaving Hotfix without TEST-RESULT to be blocked, got: $output"
echo "$output" | grep -q "TEST-RESULT" \
  || fail "expected hotfix exit gate to mention TEST-RESULT, got: $output"

status_update_with_evidence=$(jq -n \
  --arg tool_name "Write" \
  --arg file_path "docs/v1.0/status.md" \
  --arg content $'---\n_baseline: v0.9\n_current: abcdef0\n_workflow_mode: auto\n_run_status: running\n_change_status: in_progress\n_change_level: hotfix\n_review_round: 0\n_phase: Implementation\n---\n\n<!-- TEST-RESULT-BEGIN -->\nTEST_AT: 2026-03-12\nTEST_SCOPE: hotfix-smoke\nTEST_RESULT: pass\nTEST_COMMANDS: echo hotfix-smoke\n<!-- TEST-RESULT-END -->\n' \
  '{tool_name:$tool_name, tool_input:{file_path:$file_path, content:$content}}')
output=$(echo "$status_update_with_evidence" | CLAUDE_PROJECT_DIR="$tmp_dir" bash "$tmp_dir/scripts/cc-hooks/pre-write-dispatcher.sh" 2>&1 || true)
echo "$output" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"' \
  && fail "expected leaving Hotfix with TEST-RESULT evidence to pass, got: $output"

echo "ok"
