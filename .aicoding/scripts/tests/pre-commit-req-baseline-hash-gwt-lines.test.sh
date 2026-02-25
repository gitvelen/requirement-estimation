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

mkdir -p src
cat > src/example.ts <<'EOF_SRC'
// 1
// 2
// 3
// 4
// 5
EOF_SRC

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

cat > docs/v1.0/requirements.md <<'EOF'
## 1. 概述

这里是一段说明文字（不包含 GWT- 前缀），允许后续修订而不触发全量重审。

#### REQ-001: 示例需求
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-001-01: Given 条件，When 触发，Then 结果
EOF

git add -A
git commit -q -m "base"

BASE_SHA=$(git rev-parse HEAD)
REQ_HASH=$(grep -oE 'GWT-REQ-C?[0-9]+-[0-9]+:.*' docs/v1.0/requirements.md | LC_ALL=C sort | git hash-object --stdin)

cat > docs/v1.0/review_implementation.md <<EOF
## 2026-02-14 第1轮

| GWT-ID | REQ-ID | 判定 | 证据类型 | 证据（可复现） | 备注 |
|---|---|---|---|---|---|
| GWT-REQ-001-01 | REQ-001 | ✅ | CODE_REF | \`src/example.ts:1\` | 风险：示例 |

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: implementation
REVIEW_SCOPE: full
REVIEW_MODES: TECH,REQ
CODE_BASELINE: ${BASE_SHA}
REQ_BASELINE_HASH: ${REQ_HASH}
GWT_TOTAL: 1
GWT_CHECKED: 1
GWT_CARRIED: 0
CARRIED_FROM_COMMIT: N/A
GWT_FAIL: 0
GWT_WARN: 0
SPOT_CHECK_GWTS: GWT-REQ-001-01
VERIFICATION_COMMANDS: echo req-hash-gwt-lines
REVIEW_RESULT: pass
<!-- REVIEW-SUMMARY-END -->
EOF

# 仅修改 requirements.md 的非 GWT 说明文字（不改变任何 GWT 行）
printf "\n补充说明：这是一段新增背景（仍不包含 GWT-）。\n" >> docs/v1.0/requirements.md

# 推进阶段：Implementation → Testing（应允许“仅非 GWT 文本变更”不触发 REQ_BASELINE_HASH 失效）
cat > docs/v1.0/status.md <<EOF
---
_baseline: v0.9
_current: ${BASE_SHA}
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_phase: Testing
---
EOF

git add docs/v1.0/status.md docs/v1.0/requirements.md docs/v1.0/review_implementation.md

if ! bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to accept REQ_BASELINE_HASH based on GWT lines only"
fi

echo "ok"
