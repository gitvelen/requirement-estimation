#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
RELEASE_GATE_SRC="${ROOT_DIR}/scripts/check_release_gate.sh"
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

mkdir -p scripts/lib docs/v1.0
cp "$COMMON_SRC" scripts/lib/common.sh
cp "$VALIDATION_SRC" scripts/lib/validation.sh
[ -f "$RELEASE_GATE_SRC" ] || fail "missing scripts/check_release_gate.sh"
cp "$RELEASE_GATE_SRC" scripts/check_release_gate.sh
chmod +x scripts/check_release_gate.sh

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: abc1234
_workflow_mode: semi-auto
_run_status: running
_change_status: in_progress
_change_level: major
_review_round: 0
_phase: Deployment
---
EOF_STATUS

git add docs/v1.0/status.md
git commit -q -m "base"
git branch -M master
base_sha=$(git rev-parse HEAD)

git checkout -q -b feat/release

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: abc1234
_workflow_mode: semi-auto
_run_status: completed
_change_status: done
_change_level: major
_review_round: 0
_phase: Deployment
---
EOF_STATUS

git add docs/v1.0/status.md
git commit -q -m "feat: complete release"
head_sha=$(git rev-parse HEAD)

if ! pr_output=$(bash scripts/check_release_gate.sh ci pull_request master "$base_sha" "$head_sha" 2>&1); then
  fail "expected PR audit to warn but not block completed status before mainline release"
fi

printf '%s' "$pr_output" | grep -q "completed" \
  || fail "expected PR audit warning to mention completed release gate"
printf '%s' "$pr_output" | grep -q "合入后将由 push 事件的 release gate 校验基线完整性" \
  || fail "expected PR audit warning to explain follow-up push validation"

git checkout -q master
git merge --ff-only feat/release >/dev/null
push_head=$(git rev-parse HEAD)

if bash scripts/check_release_gate.sh ci push master "$base_sha" "$push_head"; then
  fail "expected main push audit to require matching tag"
fi

git tag -a v1.0 -m "Release v1.0"

if ! bash scripts/check_release_gate.sh ci push master "$base_sha" "$push_head"; then
  fail "expected main push audit to pass with matching tag"
fi

echo "ok"
