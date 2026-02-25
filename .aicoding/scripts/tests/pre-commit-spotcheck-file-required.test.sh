#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
PRE_COMMIT_SRC="${ROOT_DIR}/scripts/git-hooks/pre-commit"
LIB_SRC="${ROOT_DIR}/scripts/lib/review_gate_common.sh"
COMMON_SRC="${ROOT_DIR}/scripts/lib/common.sh"

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

mkdir -p scripts/git-hooks scripts/lib docs/v1.0
cp "$PRE_COMMIT_SRC" scripts/git-hooks/pre-commit
cp "$LIB_SRC" scripts/lib/review_gate_common.sh
cp "$COMMON_SRC" scripts/lib/common.sh
chmod +x scripts/git-hooks/pre-commit

cat > docs/v1.0/requirements.md <<'EOF_REQ'
## 3. 功能性需求

#### REQ-001：示例需求
- [ ] GWT-REQ-001-01: Given 用户已登录，When 打开首页，Then 显示欢迎语

## 4A. 约束与禁止项

#### REQ-C001：禁止项
- [ ] GWT-REQ-C001-01: Given 任意用户，When 打开首页，Then 页面不出现内部字段
EOF_REQ

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: major
_phase: Testing
---
EOF_STATUS

git add -A
git commit -q -m "base"

BASE_SHA=$(git rev-parse HEAD)
REQ_HASH=$(grep -oE 'GWT-REQ-C?[0-9]+-[0-9]+:.*' docs/v1.0/requirements.md | LC_ALL=C sort | git hash-object --stdin)

cat > docs/v1.0/review_testing.md <<EOF_REVIEW
| GWT-ID | REQ-ID | 判定 | 证据类型 | 证据（可复现） | 备注 |
|---|---|---|---|---|---|
| GWT-REQ-001-01 | REQ-001 | ✅ | RUN_OUTPUT | tests ok | 风险边界说明 |
| GWT-REQ-C001-01 | REQ-C001 | ✅ | UI_PROOF | screenshot.png | |

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: testing
REVIEW_SCOPE: full
REVIEW_MODES: TECH,REQ,TRACE
CODE_BASELINE: ${BASE_SHA}
REQ_BASELINE_HASH: ${REQ_HASH}
GWT_TOTAL: 2
GWT_CHECKED: 2
GWT_CARRIED: 0
CARRIED_FROM_COMMIT: N/A
CARRIED_GWTS: N/A
GWT_DEFERRED: 0
GWT_FAIL: 0
GWT_WARN: 0
SPOT_CHECK_GWTS: GWT-REQ-001-01
SPOTCHECK_FILE: docs/v1.0/spotcheck_testing_main.md
VERIFICATION_COMMANDS: echo spotcheck-file-required
REVIEW_RESULT: pass
<!-- REVIEW-SUMMARY-END -->
EOF_REVIEW

cat > docs/v1.0/test_report.md <<'EOF_REPORT'
## 需求覆盖矩阵（GWT 粒度追溯）

| GWT-ID | REQ-ID | 需求摘要 | 对应测试(TEST-ID) | 证据类型 | 证据 | 结果 |
|--------|--------|---------|-------------------|---------|------|------|
| GWT-REQ-001-01 | REQ-001 | 示例需求 | TEST-001 | RUN_OUTPUT | pytest ok | ✅ |
| GWT-REQ-C001-01 | REQ-C001 | 禁止项 | TEST-010 | UI_PROOF | screenshot.png | ✅ |

## 测试结论
- 整体结论：通过
EOF_REPORT

cat > docs/v1.0/status.md <<EOF_STATUS
---
_baseline: v0.9
_current: ${BASE_SHA}
_workflow_mode: auto
_run_status: wait_confirm
_change_status: done
_change_level: major
_phase: Testing
---
EOF_STATUS

git add docs/v1.0/status.md docs/v1.0/review_testing.md docs/v1.0/test_report.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to reject major delivery without spotcheck file"
fi

cat > docs/v1.0/spotcheck_testing_main.md <<EOF_SPOT
<!-- HUMAN-SPOTCHECK-BEGIN -->
SPOTCHECK_FILE: docs/v1.0/spotcheck_testing_main.md
SPOTCHECK_REVIEWER: human
SPOTCHECK_AT: 2026-02-16
SPOTCHECK_SCOPE: REQ-C:all + SPOT_CHECK_GWTS
SPOTCHECK_BASELINE: ${BASE_SHA}
REQ_BASELINE_HASH: ${REQ_HASH}
| GWT-ID | RESULT | METHOD | NOTE |
|--------|--------|--------|------|
| GWT-REQ-C001-01 | PASS | UI_VISUAL | 禁止项验证通过 |
| GWT-REQ-001-01 | PASS | RUN_CMD | spot check |
SPOTCHECK_RESULT: pass
<!-- HUMAN-SPOTCHECK-END -->
EOF_SPOT

git add docs/v1.0/spotcheck_testing_main.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to allow major delivery with valid spotcheck"
fi

echo "ok"
