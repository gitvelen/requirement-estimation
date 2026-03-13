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
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: major
_review_round: 0
_phase: Implementation
---
EOF_STATUS

git add -A
git commit -q -m "base"

cat > docs/v1.0/spotcheck_implementation_main.md <<'EOF_SPOT'
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

cat > docs/v1.0/implementation_checklist.md <<'EOF_CHECK'
# implementation checklist
- [x] self check done
EOF_CHECK

git add docs/v1.0/spotcheck_implementation_main.md docs/v1.0/implementation_checklist.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected doc-scope gate to allow spotcheck_ and implementation_checklist.md in Implementation phase"
fi

git commit -q -m "implementation docs"

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: major
_review_round: 0
_phase: Testing
---
EOF_STATUS

git add docs/v1.0/status.md
git commit -q -m "move to testing baseline"

cat > docs/v1.0/plan.md <<'EOF_PLAN'
# plan
- task status refreshed in testing phase
EOF_PLAN

git add docs/v1.0/plan.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected doc-scope gate to allow plan.md updates in Testing phase"
fi

echo "ok"
