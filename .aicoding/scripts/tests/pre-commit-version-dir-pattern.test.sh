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

mkdir -p .aicoding scripts/git-hooks scripts/lib docs/v1.0.0
cp "$PRE_COMMIT_SRC" scripts/git-hooks/pre-commit
cp "$LIB_SRC" scripts/lib/review_gate_common.sh
cp "$COMMON_SRC" scripts/lib/common.sh
cp "$VALIDATION_SRC" scripts/lib/validation.sh
chmod +x scripts/git-hooks/pre-commit

cat > .aicoding/aicoding.config.yaml <<'EOF_CFG'
version_dir_pattern: ^v([0-9]+\.[0-9]+\.[0-9]+)$
EOF_CFG

cat > docs/v1.0.0/status.md <<'STATUS'
---
_baseline: v0.9.0
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: major
_phase: Implementation
---
STATUS

git add -A
git commit -q -m "base"

cat > docs/v1.0.0/status.md <<'STATUS'
---
_baseline: v0.9.0
_current: 0000000
_workflow_mode: manul
_run_status: running
_change_status: in_progress
_change_level: major
_phase: Implementation
---
STATUS

git add docs/v1.0.0/status.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to reject invalid _workflow_mode for semver version dirs"
fi

grep -q "_workflow_mode 值非法" <(bash scripts/git-hooks/pre-commit 2>&1 || true) \
  || fail "expected invalid _workflow_mode message for semver version dirs"

echo "ok"
