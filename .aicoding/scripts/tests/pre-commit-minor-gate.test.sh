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

mkdir -p scripts/git-hooks scripts/lib docs/v1.0
cp "$PRE_COMMIT_SRC" scripts/git-hooks/pre-commit
cp "$LIB_SRC" scripts/lib/review_gate_common.sh
cp "$COMMON_SRC" scripts/lib/common.sh
cp "$VALIDATION_SRC" scripts/lib/validation.sh
chmod +x scripts/git-hooks/pre-commit

cat > docs/v1.0/requirements.md <<'EOF_REQ'
## 3. 功能性需求

#### REQ-001：示例需求
- [ ] GWT-REQ-001-01: Given 用户已登录，When 打开首页，Then 显示欢迎语
EOF_REQ

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: minor
_phase: Implementation
---

## 变更摘要
- 修复文案
EOF_STATUS

git add -A
git commit -q -m "base"

BASE_SHA=$(git rev-parse HEAD)

cat > docs/v1.0/review_minor.md <<'EOF_REVIEW'
<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_RESULT: pass
REQ_BASELINE_HASH: abcdef
REVIEWER: AI
REVIEW_AT: 2026-02-16
<!-- REVIEW-SUMMARY-END -->

## 变更验证

| GWT-ID | RESULT | EVIDENCE_TYPE | EVIDENCE |
|--------|--------|---------------|----------|
| GWT-REQ-001-01 | PASS | CODE_REF | docs/v1.0/requirements.md:4 |

## 证据清单

### 1. 测试执行
EVIDENCE_TYPE: RUN_OUTPUT
EVIDENCE: All tests passed (1/1)
EOF_REVIEW

cat > docs/v1.0/status.md <<EOF_STATUS
---
_baseline: v0.9
_current: ${BASE_SHA}
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: minor
_phase: Testing
---

## 变更摘要
- 修复文案
EOF_STATUS

git add docs/v1.0/status.md docs/v1.0/review_minor.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected Implementation->Testing (minor) to pass with review_minor only"
fi

git commit -q -m "move to testing"

cat > docs/v1.0/status.md <<EOF_STATUS
---
_baseline: v0.9
_current: ${BASE_SHA}
_workflow_mode: semi-auto
_run_status: running
_change_status: in_progress
_change_level: minor
_phase: Deployment
---

## 变更摘要
- 修复文案
EOF_STATUS

git add docs/v1.0/status.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected Testing->Deployment (minor) to require test evidence"
fi

cat > docs/v1.0/test_report.md <<'EOF_REPORT'
## 需求覆盖矩阵（GWT 粒度追溯）
| GWT-ID | REQ-ID | 需求摘要 | 对应测试(TEST-ID) | 证据类型 | 证据 | 结果 |
|--------|--------|---------|-------------------|---------|------|------|
| GWT-REQ-001-01 | REQ-001 | 示例需求 | TEST-001 | RUN_OUTPUT | ok | ✅ |

## 测试结论
- 整体结论：通过
EOF_REPORT

git add docs/v1.0/status.md docs/v1.0/test_report.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected Testing->Deployment (minor) to require fresh review_minor update for testing conclusion"
fi

cat >> docs/v1.0/review_minor.md <<'EOF_REVIEW_APPEND'

## 2026-02-26 第2轮（Testing）
- 测试阶段结论：test_report 已补充并通过
EOF_REVIEW_APPEND

git add docs/v1.0/status.md docs/v1.0/test_report.md docs/v1.0/review_minor.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected Testing->Deployment (minor) to require machine-readable testing round conclusion in review_minor"
fi

cat >> docs/v1.0/review_minor.md <<'EOF_REVIEW_APPEND'

<!-- MINOR-TESTING-ROUND-BEGIN -->
ROUND_PHASE: testing
ROUND_RESULT: pass
ROUND_AT: 2026-02-26
<!-- MINOR-TESTING-ROUND-END -->
EOF_REVIEW_APPEND

git add docs/v1.0/status.md docs/v1.0/test_report.md docs/v1.0/review_minor.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected Testing->Deployment (minor) to pass after testing round marker + test evidence"
fi

# minor 触碰 REQ-C：必须升级为 major，pre-commit 应拦截
cat >> docs/v1.0/requirements.md <<'EOF_REQC'

#### REQ-C001：禁止暴露内部字段
- [ ] GWT-REQ-C001-01: Given 用户打开页面，When 页面渲染，Then 不显示 internal_id
EOF_REQC

cat > docs/v1.0/status.md <<EOF_STATUS
---
_baseline: v0.9
_current: ${BASE_SHA}
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: minor
_phase: Testing
---

## 变更摘要
- 增补禁止项
EOF_STATUS

git add docs/v1.0/status.md docs/v1.0/requirements.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected minor change touching REQ-C to be blocked and require upgrade to major"
fi

echo "ok"
