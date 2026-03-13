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

mkdir -p "$tmp_dir/scripts/cc-hooks" "$tmp_dir/scripts/lib" "$tmp_dir/docs/v1.0"
cp "$DISPATCHER_SRC" "$tmp_dir/scripts/cc-hooks/pre-write-dispatcher.sh"
cp "$LIB_SRC" "$tmp_dir/scripts/lib/review_gate_common.sh"
cp "$COMMON_SRC" "$tmp_dir/scripts/lib/common.sh"
cp "$VALIDATION_SRC" "$tmp_dir/scripts/lib/validation.sh"
chmod +x "$tmp_dir/scripts/cc-hooks/pre-write-dispatcher.sh"

cat > "$tmp_dir/docs/v1.0/status.md" <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: minor
_review_round: 0
_phase: Testing
---

<!-- TEST-RESULT-BEGIN -->
TEST_AT: 2026-02-26
TEST_SCOPE: smoke
TEST_RESULT: pass
TEST_COMMANDS: echo ok
<!-- TEST-RESULT-END -->
EOF_STATUS

cat > "$tmp_dir/docs/v1.0/requirements.md" <<'EOF_REQ'
## 3. 功能性需求
#### REQ-001：示例需求
- [ ] GWT-REQ-001-01: Given 条件，When 触发，Then 结果
EOF_REQ

cat > "$tmp_dir/docs/v1.0/review_minor.md" <<'EOF_REVIEW'
<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_RESULT: pass
REQ_BASELINE_HASH: abcdef
REVIEWER: AI
REVIEW_AT: 2026-02-26
<!-- REVIEW-SUMMARY-END -->

| GWT-ID | RESULT | EVIDENCE_TYPE | EVIDENCE |
|--------|--------|---------------|----------|
| GWT-REQ-001-01 | PASS | RUN_OUTPUT | pytest -q |

## 证据清单

EVIDENCE_TYPE: RUN_OUTPUT
EVIDENCE: pytest -q test_example.py
EOF_REVIEW

new_status_content=$(cat <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000001
_workflow_mode: semi-auto
_run_status: running
_change_status: in_progress
_change_level: minor
_review_round: 0
_phase: Deployment
---

<!-- TEST-RESULT-BEGIN -->
TEST_AT: 2026-02-26
TEST_SCOPE: smoke
TEST_RESULT: pass
TEST_COMMANDS: echo ok
<!-- TEST-RESULT-END -->
EOF_STATUS
)

input=$(jq -n --arg tool_name "Write" --arg file_path "docs/v1.0/status.md" --arg content "$new_status_content" \
  '{tool_name:$tool_name, tool_input:{file_path:$file_path, content:$content}}')

output=$(echo "$input" | CLAUDE_PROJECT_DIR="$tmp_dir" bash "$tmp_dir/scripts/cc-hooks/pre-write-dispatcher.sh" 2>&1 || true)
echo "$output" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"' \
  || fail "expected dispatcher to block when MINOR-TESTING-ROUND is missing"
# 现在先检查证据清单完整性，所以错误消息会是 "review_minor.md 不完整"
echo "$output" | grep -qE "(MINOR-TESTING-ROUND|review_minor\.md 不完整)" \
  || fail "expected missing minor testing round or incomplete review reason, got: $output"

cat >> "$tmp_dir/docs/v1.0/review_minor.md" <<'EOF_REVIEW_APPEND'

<!-- MINOR-TESTING-ROUND-BEGIN -->
ROUND_PHASE: testing
ROUND_RESULT: pass
ROUND_AT: 2026-02-26
<!-- MINOR-TESTING-ROUND-END -->
EOF_REVIEW_APPEND

output=$(echo "$input" | CLAUDE_PROJECT_DIR="$tmp_dir" bash "$tmp_dir/scripts/cc-hooks/pre-write-dispatcher.sh" 2>&1 || true)
echo "$output" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"' \
  && fail "expected dispatcher to pass when MINOR-TESTING-ROUND exists, got: $output"

echo "ok"
