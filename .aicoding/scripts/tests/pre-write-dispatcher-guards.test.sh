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
need_cmd grep

tmp_dir=$(mktemp -d)
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT

cd "$tmp_dir"
git init -q
git config user.email "test@example.com"
git config user.name "test"

mkdir -p scripts/cc-hooks scripts/lib docs/v1.0
cp "$DISPATCHER_SRC" scripts/cc-hooks/pre-write-dispatcher.sh
cp "$LIB_SRC" scripts/lib/review_gate_common.sh
cp "$COMMON_SRC" scripts/lib/common.sh
cp "$VALIDATION_SRC" scripts/lib/validation.sh
chmod +x scripts/cc-hooks/pre-write-dispatcher.sh

cat > docs/v1.0/requirements.md <<'EOF_REQ'
## 3. 功能性需求

#### REQ-001：示例需求
- [ ] GWT-REQ-001-01: Given 用户已登录，When 打开首页，Then 显示欢迎语
EOF_REQ

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: minor
_phase: Implementation
---
EOF_STATUS

cat > docs/v1.0/review_minor.md <<'EOF_REVIEW'
<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_RESULT: pass
REQ_BASELINE_HASH: abcdef
<!-- REVIEW-SUMMARY-END -->
EOF_REVIEW

cat > docs/v1.0/test_report.md <<'EOF_REPORT'
## 测试结论
- 整体结论：通过
EOF_REPORT

NEW_STATUS_CONTENT=$(cat <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: semi-auto
_run_status: running
_change_status: in_progress
_change_level: minor
_phase: Deployment
---
EOF_STATUS
)

INPUT=$(jq -n --arg tool_name "Write" --arg file_path "docs/v1.0/status.md" --arg content "$NEW_STATUS_CONTENT" \
  '{tool_name:$tool_name, tool_input:{file_path:$file_path, content:$content}}')

OUTPUT=$(echo "$INPUT" | CLAUDE_PROJECT_DIR="$tmp_dir" bash scripts/cc-hooks/pre-write-dispatcher.sh 2>&1)
echo "$OUTPUT" | jq -e '.decision=="block"' >/dev/null 2>&1 \
  || fail "expected dispatcher to block forward jump Implementation->Deployment, got: $OUTPUT"
echo "$OUTPUT" | grep -q "阶段跳跃" || fail "expected 阶段跳跃 message, got: $OUTPUT"

SPOTCHECK_CONTENT=$(cat <<'EOF_SPOT'
<!-- HUMAN-SPOTCHECK-BEGIN -->
SPOTCHECK_FILE: docs/v1.0/spotcheck_implementation_main.md
SPOTCHECK_REVIEWER: human
SPOTCHECK_AT: 2026-02-16
SPOTCHECK_SCOPE: REQ-C:all + SPOT_CHECK_GWTS
SPOTCHECK_BASELINE: 0000000
REQ_BASELINE_HASH: abcdef
| GWT-ID | RESULT | METHOD | NOTE |
|--------|--------|--------|------|
| GWT-REQ-001-01 | PASS | RUN_CMD | smoke |
SPOTCHECK_RESULT: pass
<!-- HUMAN-SPOTCHECK-END -->
EOF_SPOT
)

INPUT=$(jq -n --arg tool_name "Write" --arg file_path "docs/v1.0/spotcheck_implementation_main.md" --arg content "$SPOTCHECK_CONTENT" \
  '{tool_name:$tool_name, tool_input:{file_path:$file_path, content:$content}}')

if ! echo "$INPUT" | CLAUDE_PROJECT_DIR="$tmp_dir" bash scripts/cc-hooks/pre-write-dispatcher.sh >/dev/null 2>&1; then
  fail "expected dispatcher to allow spotcheck_ files in Implementation phase"
fi

CHECKLIST_CONTENT=$(cat <<'EOF_CHECK'
# implementation checklist
- [x] self check done
EOF_CHECK
)

INPUT=$(jq -n --arg tool_name "Write" --arg file_path "docs/v1.0/implementation_checklist.md" --arg content "$CHECKLIST_CONTENT" \
  '{tool_name:$tool_name, tool_input:{file_path:$file_path, content:$content}}')

if ! echo "$INPUT" | CLAUDE_PROJECT_DIR="$tmp_dir" bash scripts/cc-hooks/pre-write-dispatcher.sh >/dev/null 2>&1; then
  fail "expected dispatcher to allow implementation_checklist.md in Implementation phase"
fi

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: minor
_phase: Testing
---
EOF_STATUS

PLAN_CONTENT=$(cat <<'EOF_PLAN'
# plan
- task status refreshed in testing phase
EOF_PLAN
)

INPUT=$(jq -n --arg tool_name "Write" --arg file_path "docs/v1.0/plan.md" --arg content "$PLAN_CONTENT" \
  '{tool_name:$tool_name, tool_input:{file_path:$file_path, content:$content}}')

if ! echo "$INPUT" | CLAUDE_PROJECT_DIR="$tmp_dir" bash scripts/cc-hooks/pre-write-dispatcher.sh >/dev/null 2>&1; then
  fail "expected dispatcher to allow plan.md in Testing phase"
fi

echo "ok"
