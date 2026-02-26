#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
DISPATCHER_SRC="${ROOT_DIR}/scripts/cc-hooks/pre-write-dispatcher.sh"
LIB_SRC="${ROOT_DIR}/scripts/lib/review_gate_common.sh"
COMMON_SRC="${ROOT_DIR}/scripts/lib/common.sh"

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
_phase: Implementation
---
EOF_STATUS

input=$(jq -n --arg tool_name "Write" --arg file_path "src/a.js" --arg content "console.log('hotfix');" \
  '{tool_name:$tool_name, tool_input:{file_path:$file_path, content:$content}}')

rm -f /tmp/aicoding-reads-test-hotfix-entry.log /tmp/aicoding-entry-passed-*test-hotfix-entry* 2>/dev/null || true
output=$(echo "$input" | CLAUDE_PROJECT_DIR="$tmp_dir" CLAUDE_SESSION_ID="test-hotfix-entry" bash "$tmp_dir/scripts/cc-hooks/pre-write-dispatcher.sh" 2>&1 || true)
echo "$output" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"' \
  && fail "expected hotfix to skip entry gate even in block mode, got: $output"

echo "ok"
