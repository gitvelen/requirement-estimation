#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
PRE_COMMIT_SRC="${ROOT_DIR}/scripts/git-hooks/pre-commit"
LIB_SRC="${ROOT_DIR}/scripts/lib/review_gate_common.sh"

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
cp "${ROOT_DIR}/scripts/lib/common.sh" scripts/lib/common.sh
chmod +x scripts/git-hooks/pre-commit

cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_phase: Planning
---
EOF

cat > docs/v1.0/requirements.md <<'EOF'
## 1. 概述

#### REQ-100: 示例需求（3位）
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-100-01: Given 条件，When 触发，Then 结果

#### REQ-1000: 示例需求（4位）
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-1000-01: Given 条件，When 触发，Then 结果
EOF

cat > docs/v1.0/plan.md <<'EOF'
# plan

### T001: 仅覆盖 REQ-100
**关联需求项**：REQ-100
EOF

cat > docs/v1.0/review_planning.md <<'EOF'
# Review Report：Planning / v1.0
EOF

git add -A
git commit -q -m "base"

# 推进阶段：Planning → Implementation（应因 REQ-1000 未覆盖而被拦截）
cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_phase: Implementation
---
EOF
git add docs/v1.0/status.md

if bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to block due to missing REQ-1000 coverage in plan.md"
fi

echo "ok"
