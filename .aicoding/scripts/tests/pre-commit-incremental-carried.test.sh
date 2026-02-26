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
// 6
// 7
// 8
// 9
// 10
EOF_SRC

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

cat > docs/v1.0/requirements.md <<'EOF'
## 1. 概述

#### REQ-001: 示例需求
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-001-01: Given 条件，When 触发，Then 结果
- [ ] GWT-REQ-001-02: Given 条件，When 触发，Then 结果
- [ ] GWT-REQ-001-03: Given 条件，When 触发，Then 结果

#### REQ-C001: 示例禁止项
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-C001-01: Given 条件，When 触发，Then 不出现某文案
EOF

git add -A
git commit -q -m "base"

BASE_SHA=$(git rev-parse HEAD)
REQ_HASH=$(grep -oE 'GWT-REQ-C?[0-9]+-[0-9]+:.*' docs/v1.0/requirements.md | LC_ALL=C sort | git hash-object --stdin)

cat > docs/v1.0/review_implementation.md <<EOF
## 2026-02-14 第1轮（全量）

| GWT-ID | REQ-ID | 判定 | 证据类型 | 证据（可复现） | 备注 |
|---|---|---|---|---|---|
| GWT-REQ-001-01 | REQ-001 | ✅ | CODE_REF | \`src/example.ts:1\` | 风险：需关注边界输入 |
| GWT-REQ-001-02 | REQ-001 | ✅ | CODE_REF | \`src/example.ts:2\` |  |
| GWT-REQ-001-03 | REQ-001 | ✅ | CODE_REF | \`src/example.ts:3\` |  |
| GWT-REQ-C001-01 | REQ-C001 | ✅ | UI_PROOF | 截图链接 |  |

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: implementation
REVIEW_SCOPE: full
REVIEW_MODES: TECH,REQ
CODE_BASELINE: ${BASE_SHA}
REQ_BASELINE_HASH: ${REQ_HASH}
GWT_TOTAL: 4
GWT_CHECKED: 4
GWT_CARRIED: 0
CARRIED_FROM_COMMIT: N/A
CARRIED_GWTS: N/A
GWT_DEFERRED: 0
GWT_FAIL: 0
GWT_WARN: 0
SPOT_CHECK_GWTS: GWT-REQ-001-01
VERIFICATION_COMMANDS: echo incremental-carried
REVIEW_RESULT: pass
<!-- REVIEW-SUMMARY-END -->
EOF

git add docs/v1.0/review_implementation.md
git commit -q -m "review full"

PREV_REVIEW_SHA=$(git rev-parse HEAD)

cat > docs/v1.0/review_implementation.md <<EOF
## 2026-02-14 第2轮（增量）

| GWT-ID | REQ-ID | 判定 | 证据类型 | 证据（可复现） | 备注 |
|---|---|---|---|---|---|
| GWT-REQ-001-01 | REQ-001 | ✅ | CODE_REF | \`src/example.ts:1\` | 风险：增量覆盖可能漏边界 |
| GWT-REQ-001-02 | REQ-001 | CARRIED | CODE_REF | 沿用上次结论 |  |
| GWT-REQ-001-03 | REQ-001 | CARRIED | CODE_REF | 沿用上次结论 |  |
| GWT-REQ-C001-01 | REQ-C001 | ✅ | UI_PROOF | 截图链接 |  |

### 影响分析
| 变更文件 | 关联 REQ | 关联 GWT | 本次重判 |
|---------|---------|---------|---------|
| src/example.ts | REQ-001 | GWT-REQ-001-01 | ✅ |

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: implementation
REVIEW_SCOPE: incremental
REVIEW_MODES: TECH,REQ
CODE_BASELINE: ${BASE_SHA}
REQ_BASELINE_HASH: ${REQ_HASH}
GWT_TOTAL: 4
GWT_CHECKED: 2
GWT_CARRIED: 2
CARRIED_FROM_COMMIT: ${PREV_REVIEW_SHA}
CARRIED_GWTS: GWT-REQ-001-02,GWT-REQ-001-03
GWT_DEFERRED: 0
GWT_FAIL: 0
GWT_WARN: 0
SPOT_CHECK_GWTS: GWT-REQ-001-01
VERIFICATION_COMMANDS: echo incremental-carried
REVIEW_RESULT: pass
<!-- REVIEW-SUMMARY-END -->
EOF

cat > docs/v1.0/status.md <<EOF
---
_baseline: v0.9
_current: ${BASE_SHA}
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_phase: Testing
---
EOF

git add docs/v1.0/status.md docs/v1.0/review_implementation.md

if ! bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to accept incremental reviews with CARRIED markers and CARRIED_GWTS"
fi

echo "ok"
