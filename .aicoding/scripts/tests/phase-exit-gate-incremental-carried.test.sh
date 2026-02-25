#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
PHASE_EXIT_SRC="${ROOT_DIR}/scripts/cc-hooks/phase-exit-gate.sh"

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
need_cmd jq

tmp_dir=$(mktemp -d)
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT

cd "$tmp_dir"
git init -q
git config user.email "test@example.com"
git config user.name "test"

mkdir -p docs/v1.0

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
VERIFICATION_COMMANDS: echo phase-exit-incremental-carried
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
VERIFICATION_COMMANDS: echo phase-exit-incremental-carried
REVIEW_RESULT: pass
<!-- REVIEW-SUMMARY-END -->
EOF

NEW_STATUS_CONTENT=$(cat <<EOF
---
_baseline: v0.9
_current: ${BASE_SHA}
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_phase: Testing
---
EOF
)

INPUT=$(jq -n --arg tool_name "Write" --arg file_path "docs/v1.0/status.md" --arg content "$NEW_STATUS_CONTENT" \
  '{tool_name:$tool_name, tool_input:{file_path:$file_path, content:$content}}')

if ! echo "$INPUT" | CLAUDE_PROJECT_DIR="$tmp_dir" bash "$PHASE_EXIT_SRC"; then
  fail "expected phase-exit-gate to accept incremental reviews with CARRIED markers and CARRIED_GWTS"
fi

echo "ok"
