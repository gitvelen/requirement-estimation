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

# 1) 重复 GWT-ID（应被硬拦截）
cat > docs/v1.0/requirements.md <<'EOF'
## 1. 概述

#### REQ-001: 示例需求
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-001-01: Given 条件，When 触发，Then 结果A
- [ ] GWT-REQ-001-01: Given 条件，When 触发，Then 结果B（重复）
EOF

git add docs/v1.0/requirements.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to block when requirements.md contains duplicate GWT-ID"
fi

# 2) 外键归属：GWT 前缀引用未定义 REQ（应被硬拦截）
cat > docs/v1.0/requirements.md <<'EOF'
## 1. 概述

#### REQ-001: 示例需求
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-001-01: Given 条件，When 触发，Then 结果
- [ ] GWT-REQ-999-01: Given 条件，When 触发，Then 结果（缺少 REQ-999 定义）
EOF

git add docs/v1.0/requirements.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to block when requirements.md contains GWT referencing undefined REQ-ID"
fi

# 3) 修复后应放行
cat > docs/v1.0/requirements.md <<'EOF'
## 1. 概述

#### REQ-001: 示例需求
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-001-01: Given 条件，When 触发，Then 结果

#### REQ-999: 补齐定义
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-999-01: Given 条件，When 触发，Then 结果
EOF

git add docs/v1.0/requirements.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to allow requirements.md when IDs are unique and prefixes are defined"
fi

echo "ok"

