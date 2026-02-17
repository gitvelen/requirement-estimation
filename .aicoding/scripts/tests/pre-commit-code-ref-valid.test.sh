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
EOF_REQ

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: major
_phase: Implementation
---
EOF_STATUS

git add -A
git commit -q -m "base"

BASE_SHA=$(git rev-parse HEAD)
REQ_HASH=$(grep -oE 'GWT-REQ-C?[0-9]+-[0-9]+:.*' docs/v1.0/requirements.md | LC_ALL=C sort | git hash-object --stdin)

cat > docs/v1.0/review_implementation.md <<EOF_REVIEW
| GWT-ID | REQ-ID | 判定 | 证据类型 | 证据（可复现） | 备注 |
|---|---|---|---|---|---|
| GWT-REQ-001-01 | REQ-001 | ✅ | CODE_REF | src/not-exist.ts:88 | 风险说明 |

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
CARRIED_GWTS: N/A
GWT_DEFERRED: 0
GWT_FAIL: 0
GWT_WARN: 0
SPOT_CHECK_GWTS: GWT-REQ-001-01
REVIEW_RESULT: pass
<!-- REVIEW-SUMMARY-END -->
EOF_REVIEW

cat > docs/v1.0/status.md <<EOF_STATUS
---
_baseline: v0.9
_current: ${BASE_SHA}
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: major
_phase: Testing
---
EOF_STATUS

git add docs/v1.0/status.md docs/v1.0/review_implementation.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to reject invalid CODE_REF evidence"
fi

cat > docs/v1.0/review_implementation.md <<EOF_REVIEW
| GWT-ID | REQ-ID | 判定 | 证据类型 | 证据（可复现） | 备注 |
|---|---|---|---|---|---|
| GWT-REQ-001-01 | REQ-001 | ✅ | CODE_REF | docs/v1.0/requirements.md:4 | 风险说明 |

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
CARRIED_GWTS: N/A
GWT_DEFERRED: 0
GWT_FAIL: 0
GWT_WARN: 0
SPOT_CHECK_GWTS: GWT-REQ-001-01
REVIEW_RESULT: pass
<!-- REVIEW-SUMMARY-END -->
EOF_REVIEW

git add docs/v1.0/review_implementation.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to allow valid CODE_REF evidence"
fi

echo "ok"
