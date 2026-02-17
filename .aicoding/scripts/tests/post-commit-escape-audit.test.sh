#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)

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

mkdir -p scripts/git-hooks/warnings scripts/lib docs/v1.0
cp "$ROOT_DIR/scripts/git-hooks/post-commit" scripts/git-hooks/post-commit
cp "$ROOT_DIR/scripts/lib/common.sh" scripts/lib/common.sh
for w in "$ROOT_DIR"/scripts/git-hooks/warnings/w*.sh; do
  [ -f "$w" ] && cp "$w" scripts/git-hooks/warnings/
done
chmod +x scripts/git-hooks/post-commit

cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_phase: Implementation
---
EOF

git add -A
git commit -q -m "base"

# simulate a commit created with --no-verify:
# no pre-commit pass evidence in gate-pass.log for this HEAD.
cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: 1111111
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_phase: Implementation
---
EOF

git add docs/v1.0/status.md
git commit -q -m "fix: bypass example"

output=$(bash scripts/git-hooks/post-commit 2>&1 || true)
echo "$output" | grep -q "W24" || fail "expected W24 escape-audit warning when pre-commit evidence is missing"
[ -f .git/aicoding/gate-warnings.log ] || fail "expected gate warning log"
grep -q "W24" .git/aicoding/gate-warnings.log || fail "expected W24 persisted in gate-warnings.log"

echo "ok"
