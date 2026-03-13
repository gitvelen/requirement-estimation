#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
RELEASE_HELPER_SRC="${ROOT_DIR}/scripts/release-complete.sh"
COMMON_SRC="${ROOT_DIR}/scripts/lib/common.sh"
VALIDATION_SRC="${ROOT_DIR}/scripts/lib/validation.sh"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

tmp_dir=$(mktemp -d)
remote_dir=$(mktemp -d)
cleanup() {
  rm -rf "$tmp_dir" "$remote_dir"
}
trap cleanup EXIT

git init --bare -q "$remote_dir/origin.git"

cd "$tmp_dir"
git init -q
git config user.email "test@example.com"
git config user.name "test"
git remote add origin "$remote_dir/origin.git"

mkdir -p scripts/lib docs/v1.0
cp "$COMMON_SRC" scripts/lib/common.sh
cp "$VALIDATION_SRC" scripts/lib/validation.sh
[ -f "$RELEASE_HELPER_SRC" ] || fail "missing scripts/release-complete.sh"
cp "$RELEASE_HELPER_SRC" scripts/release-complete.sh
chmod +x scripts/release-complete.sh

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
git commit -q -m "feat: release commit"
git branch -M master

if ! bash scripts/release-complete.sh v1.0 origin; then
  fail "expected release helper to create tag and push branch + tag"
fi

git --git-dir="$remote_dir/origin.git" rev-parse --verify refs/heads/master >/dev/null 2>&1 \
  || fail "expected remote master to be updated"
git --git-dir="$remote_dir/origin.git" rev-parse --verify refs/tags/v1.0 >/dev/null 2>&1 \
  || fail "expected remote tag v1.0 to exist"

echo "ok"
