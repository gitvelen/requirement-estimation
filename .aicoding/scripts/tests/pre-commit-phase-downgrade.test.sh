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
_phase: Testing
---
EOF_STATUS

git add -A
git commit -q -m "base"

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: major
_phase: Proposal
---
EOF_STATUS

git add docs/v1.0/status.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected large phase downgrade (Testing -> Proposal) to be blocked"
fi

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: major
_phase: ChangeManagement
---
EOF_STATUS

git add docs/v1.0/status.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected downgrade to ChangeManagement to be allowed for version-scope re-entry"
fi

grep -q "Testing -> ChangeManagement" .git/aicoding/gate-warnings.log \
  || fail "expected warning log for downgrade to ChangeManagement"

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: major
_phase: Implementation
---
EOF_STATUS

git add docs/v1.0/status.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected small phase downgrade (Testing -> Implementation) to be allowed with warning"
fi

[ -f .git/aicoding/gate-warnings.log ] || fail "expected warning log for small phase downgrade"
grep -q "阶段降级" .git/aicoding/gate-warnings.log || fail "expected phase downgrade warning entry"

echo "ok"
