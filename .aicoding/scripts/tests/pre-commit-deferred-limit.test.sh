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
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_phase: Implementation
---
EOF

cat > docs/v1.0/requirements.md <<'EOF'
## 1. 概述

#### REQ-001: 示例需求
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-001-01: Given 条件，When 触发，Then 结果
- [ ] GWT-REQ-001-02: Given 条件，When 触发，Then 结果
- [ ] GWT-REQ-001-03: Given 条件，When 触发，Then 结果
- [ ] GWT-REQ-001-04: Given 条件，When 触发，Then 结果
- [ ] GWT-REQ-001-05: Given 条件，When 触发，Then 结果
- [ ] GWT-REQ-001-06: Given 条件，When 触发，Then 结果
- [ ] GWT-REQ-001-07: Given 条件，When 触发，Then 结果
- [ ] GWT-REQ-001-08: Given 条件，When 触发，Then 结果
- [ ] GWT-REQ-001-09: Given 条件，When 触发，Then 结果
- [ ] GWT-REQ-001-10: Given 条件，When 触发，Then 结果
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
| GWT-REQ-001-02 | REQ-001 | ✅ | CODE_REF | \`src/example.ts:2\` |  |
| GWT-REQ-001-03 | REQ-001 | ✅ | CODE_REF | \`src/example.ts:3\` |  |
| GWT-REQ-001-04 | REQ-001 | ✅ | CODE_REF | \`src/example.ts:4\` |  |
| GWT-REQ-001-05 | REQ-001 | ✅ | CODE_REF | \`src/example.ts:5\` |  |
| GWT-REQ-001-06 | REQ-001 | ✅ | CODE_REF | \`src/example.ts:6\` |  |
| GWT-REQ-001-07 | REQ-001 | ✅ | CODE_REF | \`src/example.ts:7\` |  |
| GWT-REQ-001-08 | REQ-001 | ✅ | CODE_REF | \`src/example.ts:8\` |  |
| GWT-REQ-001-09 | REQ-001 | DEFERRED_TO_STAGING | RUN_OUTPUT | \`echo deferred\` |  |
| GWT-REQ-001-10 | REQ-001 | DEFERRED_TO_STAGING | RUN_OUTPUT | \`echo deferred\` |  |

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: implementation
REVIEW_SCOPE: full
REVIEW_MODES: TECH,REQ
CODE_BASELINE: ${BASE_SHA}
REQ_BASELINE_HASH: ${REQ_HASH}
GWT_TOTAL: 10
GWT_CHECKED: 10
GWT_CARRIED: 0
CARRIED_FROM_COMMIT: N/A
GWT_DEFERRED: 2
GWT_FAIL: 0
GWT_WARN: 0
SPOT_CHECK_GWTS: GWT-REQ-001-01
REVIEW_RESULT: pass
<!-- REVIEW-SUMMARY-END -->
EOF

# 推进阶段：Implementation → Testing（DEFERRED 超过 10% 应被拦截）
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

git add docs/v1.0/status.md docs/v1.0/review_implementation.md

if bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to block when DEFERRED_TO_STAGING exceeds 10% of GWT_TOTAL"
fi

echo "ok"
