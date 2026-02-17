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
cp "$ROOT_DIR/scripts/git-hooks/pre-commit" scripts/git-hooks/pre-commit
cp "$ROOT_DIR/scripts/git-hooks/commit-msg" scripts/git-hooks/commit-msg
cp "$ROOT_DIR/scripts/git-hooks/post-commit" scripts/git-hooks/post-commit
cp "$ROOT_DIR/scripts/lib/common.sh" scripts/lib/common.sh
cp "$ROOT_DIR/scripts/lib/review_gate_common.sh" scripts/lib/review_gate_common.sh
for w in "$ROOT_DIR"/scripts/git-hooks/warnings/w*.sh; do
  [ -f "$w" ] && cp "$w" scripts/git-hooks/warnings/
done
chmod +x scripts/git-hooks/pre-commit scripts/git-hooks/commit-msg scripts/git-hooks/post-commit

cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: major
_phase: Implementation
---
EOF

cat > docs/v1.0/requirements.md <<'EOF'
#### REQ-001：示例需求
- [ ] GWT-REQ-001-01: Given 条件，When 操作，Then 结果
EOF

git add -A
git commit -q -m "feat: base"

# major 流程提交（不推进阶段）：pre-commit -> commit-msg -> post-commit
cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: 1111111
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: major
_phase: Implementation
---
EOF

git add docs/v1.0/status.md

bash scripts/git-hooks/pre-commit >/tmp/aicoding-e2e-precommit.log 2>&1 || fail "pre-commit failed in e2e major flow"

msg_file=$(mktemp)
echo "feat: e2e major flow" > "$msg_file"
bash scripts/git-hooks/commit-msg "$msg_file" >/tmp/aicoding-e2e-commitmsg.log 2>&1 || fail "commit-msg failed in e2e major flow"
rm -f "$msg_file"

git commit -q -m "feat: e2e major flow"

post_output=$(bash scripts/git-hooks/post-commit 2>&1 || true)
echo "$post_output" | grep -q "W24" && fail "unexpected W24 in e2e major flow (pre-commit evidence should exist)"

echo "ok"
