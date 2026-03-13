#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
PRE_COMMIT_SRC="${ROOT_DIR}/scripts/git-hooks/pre-commit"
LIB_SRC="${ROOT_DIR}/scripts/lib/review_gate_common.sh"
COMMON_SRC="${ROOT_DIR}/scripts/lib/common.sh"
VALIDATION_SRC="${ROOT_DIR}/scripts/lib/validation.sh"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

tmp_dir=$(mktemp -d)
cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

cd "$tmp_dir"
git init -q
git config user.email "test@example.com"
git config user.name "test"

mkdir -p scripts/git-hooks scripts/lib docs/v1.0
cp "$PRE_COMMIT_SRC" scripts/git-hooks/pre-commit
cp "$LIB_SRC" scripts/lib/review_gate_common.sh
cp "$COMMON_SRC" scripts/lib/common.sh
cp "$VALIDATION_SRC" scripts/lib/validation.sh
chmod +x scripts/git-hooks/pre-commit

cat > aicoding.config.yaml <<'EOF'
result_gate_test_command: false
result_gate_build_command: ""
result_gate_typecheck_command: ""
EOF

cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: minor
_phase: Implementation
---
EOF

cat > docs/v1.0/review_minor.md <<'EOF'
## review minor

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_RESULT: pass
REQ_BASELINE_HASH: base
<!-- REVIEW-SUMMARY-END -->

| GWT-ID | REQ-ID | 判定 | 证据类型 | 证据（可复现） | 备注 |
|---|---|---|---|---|---|
| GWT-REQ-001-01 | REQ-001 | ✅ | RUN_OUTPUT | pytest -k smoke | smoke |
EOF

git add -A
git commit -q -m "base"

# phase transition commit: Implementation -> Testing
# should trigger result_gate_test_command (false) and be blocked.
cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: 1111111
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: minor
_phase: Testing
---

TEST-RESULT-BEGIN
PASS
TEST-RESULT-END
EOF
git add docs/v1.0/status.md docs/v1.0/review_minor.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected result gate to block phase transition commit when configured command fails"
fi

# non-phase-change commit in same phase should not execute result gate command.
git reset --hard -q HEAD
cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: 2222222
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: minor
_phase: Implementation
---
EOF
git add docs/v1.0/status.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected non-phase-change commit to skip result gate command"
fi

echo "ok"
