#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
PRE_COMMIT_SRC="${ROOT_DIR}/scripts/git-hooks/pre-commit"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

need_cmd git
need_cmd awk
need_cmd grep
need_cmd sed

tmp_dir=$(mktemp -d)
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT

cd "$tmp_dir"
git init -q
git config user.email "test@example.com"
git config user.name "test"

mkdir -p scripts/git-hooks scripts/lib docs/v1.0
cp "$PRE_COMMIT_SRC" scripts/git-hooks/pre-commit
cp "${ROOT_DIR}/scripts/lib/review_gate_common.sh" scripts/lib/review_gate_common.sh
cp "${ROOT_DIR}/scripts/lib/common.sh" scripts/lib/common.sh
cp "${ROOT_DIR}/scripts/lib/validation.sh" scripts/lib/validation.sh
chmod +x scripts/git-hooks/pre-commit

# Base status at Design phase
cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_phase: Design
---
EOF

cat > docs/v1.0/requirements.md <<'EOF'
## 1. 概述
#### REQ-001: 示例需求
- [ ] GWT-REQ-001-01: Given 条件，When 触发，Then 结果
EOF

git add -A
git commit -q -m "base"

# --- Test 1: Forward jump >1 should be blocked ---
# Try to jump from Design directly to Implementation (skip Planning)
cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_phase: Implementation
---
EOF

git add docs/v1.0/status.md

OUTPUT=$(scripts/git-hooks/pre-commit 2>&1) && {
  fail "Test 1: forward jump Design→Implementation should be blocked but pre-commit passed"
}
echo "$OUTPUT" | grep -q "阶段跳跃" || fail "Test 1: expected '阶段跳跃' in output, got: $OUTPUT"
echo "PASS: Test 1 — forward jump Design→Implementation blocked"

git reset -q HEAD -- docs/v1.0/status.md

# --- Test 2: Adjacent forward (Design→Planning) should NOT be blocked by jump check ---
# Note: it may still fail on exit gate (missing design.md/review_design.md), that's expected
# We just verify it does NOT fail with "阶段跳跃"
cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_phase: Planning
---
EOF

git add docs/v1.0/status.md

OUTPUT=$(scripts/git-hooks/pre-commit 2>&1) || true
if echo "$OUTPUT" | grep -q "阶段跳跃"; then
  fail "Test 2: adjacent Design→Planning should NOT trigger '阶段跳跃', got: $OUTPUT"
fi
echo "PASS: Test 2 — adjacent Design→Planning does not trigger jump block"

git reset -q HEAD -- docs/v1.0/status.md

# --- Test 3: Forward jump >2 (Design→Testing) should be blocked ---
cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_phase: Testing
---
EOF

git add docs/v1.0/status.md

OUTPUT=$(scripts/git-hooks/pre-commit 2>&1) && {
  fail "Test 3: forward jump Design→Testing should be blocked but pre-commit passed"
}
echo "$OUTPUT" | grep -q "阶段跳跃" || fail "Test 3: expected '阶段跳跃' in output, got: $OUTPUT"
echo "PASS: Test 3 — forward jump Design→Testing blocked"

echo ""
echo "All phase-forward-jump tests passed."
