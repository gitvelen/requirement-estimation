#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
PRE_PUSH_SRC="${ROOT_DIR}/scripts/git-hooks/pre-push"
COMMON_SRC="${ROOT_DIR}/scripts/lib/common.sh"
VALIDATION_SRC="${ROOT_DIR}/scripts/lib/validation.sh"
RELEASE_GATE_SRC="${ROOT_DIR}/scripts/check_release_gate.sh"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

ZERO_SHA="0000000000000000000000000000000000000000"

tmp_dir=$(mktemp -d)
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT

cd "$tmp_dir"
git init -q
git config user.email "test@example.com"
git config user.name "test"

mkdir -p scripts/git-hooks scripts/lib docs/v1.0
cp "$PRE_PUSH_SRC" scripts/git-hooks/pre-push
cp "$COMMON_SRC" scripts/lib/common.sh
cp "$VALIDATION_SRC" scripts/lib/validation.sh
[ -f "$RELEASE_GATE_SRC" ] && cp "$RELEASE_GATE_SRC" scripts/check_release_gate.sh
chmod +x scripts/git-hooks/pre-push
[ -f scripts/check_release_gate.sh ] && chmod +x scripts/check_release_gate.sh

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

main_head=$(git rev-parse HEAD)
normal_push_output=$(bash scripts/git-hooks/pre-push origin git@example.com <<EOF_PUSH 2>&1 || true
refs/heads/master ${main_head} refs/heads/master ${ZERO_SHA}
EOF_PUSH
)
printf '%s' "$normal_push_output" | grep -q "禁止直接在 main/master 分支上开发并 push" \
  || fail "expected existing direct-push protection to remain for non-release pushes"

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

cat > docs/v1.0/deployment.md <<'EOF_DEPLOY'
# deployment

## 文档元信息
| 项 | 值 |
|---|---|
| 目标环境 | STAGING |

## 验收记录
- 验收时间：2026-03-12 10:00
- 验收人：用户
- 验收结论：通过
- 验收说明：ok
EOF_DEPLOY

git add docs/v1.0/status.md docs/v1.0/deployment.md
git commit -q -m "feat: mark deployment completed"

feature_head=$(git rev-parse HEAD)
if bash scripts/git-hooks/pre-push origin git@example.com <<EOF_PUSH
refs/heads/feat/release ${feature_head} refs/heads/feat/release ${ZERO_SHA}
EOF_PUSH
then
  fail "expected completed status push to non-main branch to be blocked"
fi

feature_push_output=$(bash scripts/git-hooks/pre-push origin git@example.com <<EOF_PUSH 2>&1 || true
refs/heads/feat/release ${feature_head} refs/heads/feat/release ${ZERO_SHA}
EOF_PUSH
)
printf '%s' "$feature_push_output" | grep -q "completed" \
  || fail "expected non-main completed push error to mention completed release gate"

git checkout -q master
git merge --ff-only feat/release >/dev/null

release_head=$(git rev-parse HEAD)
if bash scripts/git-hooks/pre-push origin git@example.com <<EOF_PUSH
refs/heads/master ${release_head} refs/heads/master ${ZERO_SHA}
EOF_PUSH
then
  fail "expected completed release push without tag to be blocked"
fi

missing_tag_output=$(bash scripts/git-hooks/pre-push origin git@example.com <<EOF_PUSH 2>&1 || true
refs/heads/master ${release_head} refs/heads/master ${ZERO_SHA}
EOF_PUSH
)
printf '%s' "$missing_tag_output" | grep -q "tag" \
  || fail "expected missing release tag error message"

git tag -a v1.0 -m "Release v1.0"
tag_object=$(git rev-parse refs/tags/v1.0)

if ! bash scripts/git-hooks/pre-push origin git@example.com <<EOF_PUSH
refs/heads/master ${release_head} refs/heads/master ${ZERO_SHA}
refs/tags/v1.0 ${tag_object} refs/tags/v1.0 ${ZERO_SHA}
EOF_PUSH
then
  fail "expected completed release push to main with matching tag to pass"
fi

echo "ok"
