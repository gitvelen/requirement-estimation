#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
PRE_COMMIT_SRC="${ROOT_DIR}/scripts/git-hooks/pre-commit"
LIB_SRC="${ROOT_DIR}/scripts/lib/review_gate_common.sh"
COMMON_SRC="${ROOT_DIR}/scripts/lib/common.sh"

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
chmod +x scripts/git-hooks/pre-commit

cat > aicoding.config.yaml <<'EOF_CFG'
enable_hotfix: true
hotfix_max_diff_files: 5
EOF_CFG

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: hotfix
_review_round: 0
_phase: ChangeManagement
---
EOF_STATUS

git add -A
git commit -q -m "base"

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: manual
_run_status: completed
_change_status: done
_change_level: hotfix
_review_round: 0
_phase: ChangeManagement
---
EOF_STATUS

git add docs/v1.0/status.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected hotfix done/completed to require TEST-RESULT evidence"
fi

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: manual
_run_status: completed
_change_status: done
_change_level: hotfix
_review_round: 0
_phase: ChangeManagement
---

<!-- TEST-RESULT-BEGIN -->
TEST_AT: 2026-02-26
TEST_SCOPE: hotfix-smoke
TEST_RESULT: pass
TEST_COMMANDS: echo hotfix-smoke
<!-- TEST-RESULT-END -->
EOF_STATUS

git add docs/v1.0/status.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected hotfix done/completed to pass with TEST-RESULT evidence"
fi

echo "ok"
