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

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

need_cmd git
need_cmd awk
need_cmd grep
need_cmd sed

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

cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_phase: Requirements
---
EOF

cat > docs/v1.0/proposal.md <<'EOF'
# Proposal

## Non-goals
- 不做：示例非目标
EOF

cat > docs/v1.0/requirements.md <<'EOF'
## 1. 概述

## 4A. 约束与禁止项（Constraints & Prohibitions）

#### REQ-C001：示例禁止项
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-C001-01: Given 任意用户，When 打开页面，Then 页面不出现「内部字段」
EOF

git add -A
git commit -q -m "base"

BASE_SHA=$(git rev-parse HEAD)

cat > docs/v1.0/review_requirements.md <<'EOF'
## 禁止项/不做项确认清单

（此处故意缺少 CONSTRAINTS-CHECKLIST 块）

## 证据清单
### 1. 验证命令
**命令：** echo "test"
**输出：** test

<!-- CONSTRAINTS-CONFIRMATION-BEGIN -->
CONSTRAINTS_CONFIRMED: yes
CONFIRMED_BY: human
CONFIRMED_AT: 2026-02-14
<!-- CONSTRAINTS-CONFIRMATION-END -->
EOF

# 推进阶段：Requirements → Design（缺少机器可读清单块应被拦截）
cat > docs/v1.0/status.md <<EOF
---
_baseline: v0.9
_current: ${BASE_SHA}
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_phase: Design
---
EOF

git add docs/v1.0/status.md docs/v1.0/review_requirements.md

if bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to block when review_requirements.md lacks CONSTRAINTS-CHECKLIST"
fi

cat > docs/v1.0/review_requirements.md <<'EOF'
## 禁止项/不做项确认清单

<!-- CONSTRAINTS-CHECKLIST-BEGIN -->
| ITEM | CLASS | TARGET | SOURCE |
|---|---|---|---|
| C-001 | A | REQ-C001 | requirements.md REQ-C001（来源：proposal.md §Non-goals） |
| C-002 | B | Non-goals | proposal.md §Non-goals（原因：不在本期范围） |
<!-- CONSTRAINTS-CHECKLIST-END -->

## 证据清单
### 1. 验证命令
**命令：** echo "test"
**输出：** test

<!-- CONSTRAINTS-CONFIRMATION-BEGIN -->
CONSTRAINTS_CONFIRMED: yes
CONFIRMED_BY: human
CONFIRMED_AT: 2026-02-14
<!-- CONSTRAINTS-CONFIRMATION-END -->
EOF

git add docs/v1.0/review_requirements.md

if ! bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to allow valid constraints checklist and confirmation"
fi

echo "ok"

