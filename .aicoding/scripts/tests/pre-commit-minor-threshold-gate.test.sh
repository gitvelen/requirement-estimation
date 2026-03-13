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

mkdir -p scripts/git-hooks scripts/lib docs/v1.0 src
cp "$PRE_COMMIT_SRC" scripts/git-hooks/pre-commit
cp "$LIB_SRC" scripts/lib/review_gate_common.sh
cp "$COMMON_SRC" scripts/lib/common.sh
cp "$VALIDATION_SRC" scripts/lib/validation.sh
chmod +x scripts/git-hooks/pre-commit

cat > aicoding.config.yaml <<'EOF_CFG'
minor_max_diff_files: 2
minor_max_new_gwts: 1
EOF_CFG

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: minor
_review_round: 0
_phase: Implementation
---
EOF_STATUS

cat > docs/v1.0/requirements.md <<'EOF_REQ'
## 3. 功能性需求

#### REQ-001：示例需求
- [ ] GWT-REQ-001-01: Given 用户已登录，When 打开首页，Then 显示欢迎语
EOF_REQ

git add -A
git commit -q -m "base"

# Case 1: changed file count exceeds minor_max_diff_files
echo "touch" > src/a.txt
echo "touch" > src/b.txt
cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: minor
_review_round: 0
_phase: Implementation
---

## 变更摘要
- minor threshold case1
EOF_STATUS

git add docs/v1.0/status.md src/a.txt src/b.txt
if bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to block minor when staged file count exceeds threshold"
fi

git reset --hard -q HEAD

# Case 2: new GWT count exceeds minor_max_new_gwts
cat >> docs/v1.0/requirements.md <<'EOF_REQ_APPEND'
- [ ] GWT-REQ-001-02: Given 用户已登录，When 打开详情，Then 显示详情
- [ ] GWT-REQ-001-03: Given 用户已登录，When 点击刷新，Then 刷新数据
EOF_REQ_APPEND

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: minor
_review_round: 0
_phase: Implementation
---

## 变更摘要
- minor threshold case2
EOF_STATUS

git add docs/v1.0/status.md docs/v1.0/requirements.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to block minor when added GWT count exceeds threshold"
fi

git reset --hard -q HEAD

# Case 3: within threshold should pass
cat >> docs/v1.0/requirements.md <<'EOF_REQ_APPEND'
- [ ] GWT-REQ-001-02: Given 用户已登录，When 打开详情，Then 显示详情
EOF_REQ_APPEND

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: minor
_review_round: 0
_phase: Implementation
---

## 变更摘要
- minor threshold case3
EOF_STATUS

git add docs/v1.0/status.md docs/v1.0/requirements.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to allow minor changes within thresholds"
fi

echo "ok"
