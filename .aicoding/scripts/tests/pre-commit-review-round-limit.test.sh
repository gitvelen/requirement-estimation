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
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: major
_review_round: 2
_phase: Proposal
---
EOF_STATUS

git add -A
git commit -q -m "base"

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: major
_phase: Proposal
---
EOF_STATUS

git add docs/v1.0/status.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to warn but allow missing _review_round for compatibility"
fi

grep -q "_review_round 缺失" .git/aicoding/gate-warnings.log \
  || fail "expected warning log when _review_round is missing"

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: major
_review_round: 2
_phase: Requirements
---
EOF_STATUS

git add docs/v1.0/status.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to block phase transition when _review_round is not reset to 0"
fi

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: major
_review_round: 0
_phase: Requirements
---
EOF_STATUS

cat > docs/v1.0/review_proposal.md <<'EOF_REVIEW'
## review proposal
- ok
EOF_REVIEW

git add docs/v1.0/status.md docs/v1.0/review_proposal.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to allow phase transition when _review_round=0"
fi

git commit -q -m "move to requirements"

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: major
_review_round: 6
_phase: Requirements
---
EOF_STATUS

git add docs/v1.0/status.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to block when _review_round > 5 and run_status is not wait_confirm"
fi

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: manual
_run_status: wait_confirm
_change_status: in_progress
_change_level: major
_review_round: 6
_phase: Requirements
---
EOF_STATUS

git add docs/v1.0/status.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to allow _review_round > 5 when run_status=wait_confirm"
fi

echo "ok"
