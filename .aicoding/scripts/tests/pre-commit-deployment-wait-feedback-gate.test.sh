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
cleanup() { rm -rf "$tmp_dir"; }
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

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: semi-auto
_run_status: running
_change_status: in_progress
_change_level: minor
_review_round: 0
_phase: Deployment
---
EOF_STATUS

cat > docs/v1.0/review_minor.md <<'EOF_REVIEW'
<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_RESULT: pass
REQ_BASELINE_HASH: abcdef
<!-- REVIEW-SUMMARY-END -->

| GWT-ID | RESULT | EVIDENCE_TYPE | EVIDENCE |
|--------|--------|---------------|----------|
| GWT-REQ-001-01 | PASS | RUN_OUTPUT | echo ok |

## 证据清单

### 1. 测试执行
EVIDENCE_TYPE: RUN_OUTPUT
EVIDENCE: All tests passed (1/1)

<!-- MINOR-TESTING-ROUND-BEGIN -->
ROUND_PHASE: testing
ROUND_RESULT: pass
ROUND_AT: 2026-03-12
<!-- MINOR-TESTING-ROUND-END -->
EOF_REVIEW

git add -A
git commit -q -m "base"

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: semi-auto
_run_status: wait_feedback
_change_status: in_progress
_change_level: minor
_review_round: 0
_phase: Deployment
---

<!-- TEST-RESULT-BEGIN -->
TEST_AT: 2026-03-12
TEST_SCOPE: deployment-ready
TEST_RESULT: pass
TEST_COMMANDS: echo deployment-ready
<!-- TEST-RESULT-END -->
EOF_STATUS

git add docs/v1.0/status.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected Deployment wait_feedback to require deployment.md"
fi

cat > docs/v1.0/deployment.md <<'EOF_DEPLOY'
# deployment

## 文档元信息
| 项 | 值 |
|---|---|
| 目标环境 | STAGING |
EOF_DEPLOY

git add docs/v1.0/status.md docs/v1.0/deployment.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected Deployment wait_feedback to pass with deployment.md and without acceptance evidence"
fi

echo "ok"
