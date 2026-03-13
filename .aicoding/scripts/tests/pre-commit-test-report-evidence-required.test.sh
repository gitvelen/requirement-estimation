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
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: major
_phase: Testing
---
EOF

cat > docs/v1.0/requirements.md <<'EOF'
## 1. 概述

#### REQ-C001: 示例禁止项
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-C001-01: Given 条件，When 触发，Then 不出现某文案

#### REQ-002: 示例需求
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-002-01: Given 条件，When 触发，Then 结果
EOF

git add -A
git commit -q -m "base"

BASE_SHA=$(git rev-parse HEAD)
REQ_HASH=$(grep -oE 'GWT-REQ-C?[0-9]+-[0-9]+:.*' docs/v1.0/requirements.md | LC_ALL=C sort | git hash-object --stdin)

cat > docs/v1.0/review_testing.md <<EOF
## 2026-02-14 第1轮

| GWT-ID | REQ-ID | 判定 | 证据类型 | 证据（可复现） | 备注 |
|---|---|---|---|---|---|
| GWT-REQ-C001-01 | REQ-C001 | ✅ | UI_PROOF | 截图链接 | 风险：示例 |
| GWT-REQ-002-01 | REQ-002 | ✅ | RUN_OUTPUT | ok |  |

## 证据清单

### 1. 测试执行

EVIDENCE_TYPE: RUN_OUTPUT
EVIDENCE: All tests passed (2/2)

**命令：**
\`\`\`bash
pytest -q tests/
\`\`\`

**输出：**
\`\`\`
..
2 passed in 0.05s
\`\`\`

**定位：**
- tests/test_example.py:10-30

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: testing
REVIEW_SCOPE: full
REVIEW_MODES: REQ,TRACE
CODE_BASELINE: ${BASE_SHA}
REQ_BASELINE_HASH: ${REQ_HASH}
GWT_TOTAL: 2
GWT_CHECKED: 2
GWT_CARRIED: 0
CARRIED_FROM_COMMIT: N/A
GWT_DEFERRED: 0
GWT_FAIL: 0
GWT_WARN: 0
SPOT_CHECK_GWTS: GWT-REQ-C001-01
SPOTCHECK_FILE: docs/v1.0/spotcheck_testing_main.md
VERIFICATION_COMMANDS: echo test-report-evidence-required
REVIEW_RESULT: pass
<!-- REVIEW-SUMMARY-END -->
EOF

cat > docs/v1.0/spotcheck_testing_main.md <<EOF
<!-- HUMAN-SPOTCHECK-BEGIN -->
SPOTCHECK_FILE: docs/v1.0/spotcheck_testing_main.md
SPOTCHECK_REVIEWER: human
SPOTCHECK_AT: 2026-02-16
SPOTCHECK_SCOPE: REQ-C:all + SPOT_CHECK_GWTS
SPOTCHECK_BASELINE: ${BASE_SHA}
REQ_BASELINE_HASH: ${REQ_HASH}
| GWT-ID | RESULT | METHOD | NOTE |
|--------|--------|--------|------|
| GWT-REQ-C001-01 | PASS | UI_VISUAL | 抽检通过 |
SPOTCHECK_RESULT: pass
<!-- HUMAN-SPOTCHECK-END -->
EOF

cat > docs/v1.0/test_report.md <<'EOF'
# 测试报告

## 需求覆盖矩阵（GWT 粒度追溯）

| GWT-ID | REQ-ID | 需求摘要 | 对应测试(TEST-ID) | 证据类型 | 证据 | 结果 |
|--------|--------|---------|-------------------|---------|------|------|
| GWT-REQ-C001-01 | REQ-C001 | 示例 | TEST-001 | UI_PROOF | ... | ✅ |
| GWT-REQ-002-01 | REQ-002 | 示例 | TEST-002 | RUN_OUTPUT | ok | ✅ |

## 测试结论
- 整体结论：通过
EOF

git add docs/v1.0/review_testing.md docs/v1.0/spotcheck_testing_main.md
git commit -q -m "test: add review and spotcheck"

# 推进阶段：Testing → Deployment（覆盖矩阵证据列占位应被拦截）
cat > docs/v1.0/status.md <<EOF
---
_baseline: v0.9
_current: ${BASE_SHA}
_workflow_mode: semi-auto
_run_status: running
_change_status: in_progress
_change_level: major
_phase: Deployment
---
EOF

git add docs/v1.0/status.md docs/v1.0/test_report.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to block when test_report coverage matrix has placeholder evidence"
fi

# 修复证据后应放行
sed -i 's/| GWT-REQ-C001-01 | REQ-C001 | 示例 | TEST-001 | UI_PROOF | ... | ✅ |/| GWT-REQ-C001-01 | REQ-C001 | 示例 | TEST-001 | UI_PROOF | 截图链接 | ✅ |/' docs/v1.0/test_report.md
git add docs/v1.0/test_report.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to allow when test_report evidence fields are non-empty"
fi

echo "ok"
