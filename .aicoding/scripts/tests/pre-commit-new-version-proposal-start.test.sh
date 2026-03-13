#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
PRE_COMMIT_SRC="${ROOT_DIR}/scripts/git-hooks/pre-commit"
CHECK_DEBT_SRC="${ROOT_DIR}/scripts/check_quality_debt.sh"
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

mkdir -p scripts/git-hooks scripts/lib docs/v1.0 docs/v1.1 .aicoding
cp "$PRE_COMMIT_SRC" scripts/git-hooks/pre-commit
cp "$CHECK_DEBT_SRC" scripts/check_quality_debt.sh
cp "$LIB_SRC" scripts/lib/review_gate_common.sh
cp "$COMMON_SRC" scripts/lib/common.sh
cp "$VALIDATION_SRC" scripts/lib/validation.sh
chmod +x scripts/git-hooks/pre-commit scripts/check_quality_debt.sh

cat > .aicoding/aicoding.config.yaml <<'EOF_CFG'
quality_debt_max_total: 10
quality_debt_high_risk_max: 5
tech_debt_max_total: 15
EOF_CFG

cat > docs/v1.0/status.md <<'EOF_BASELINE'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: semi-auto
_run_status: completed
_change_status: done
_change_level: major
_review_round: 0
_phase: Deployment
---

## 质量债务登记
| 债务 ID | 类型 | 描述 | 风险等级 | 计划偿还版本 | 状态 |
|--------|------|------|---------|-------------|------|
EOF_BASELINE

git add -A
git commit -q -m "base"

# Test 1: new version startup may create status.md directly at Proposal when no Active CR exists.
cat > docs/v1.1/status.md <<'EOF_STATUS'
---
_baseline: v1.0
_current: HEAD
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: major
_review_round: 0
_phase: Proposal
---
EOF_STATUS

git add docs/v1.1/status.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected new-version Proposal startup without Active CR to pass"
fi

git reset -q HEAD -- docs/v1.1/status.md
rm -f docs/v1.1/status.md

# Test 2: new status.md still cannot jump beyond Proposal.
cat > docs/v1.1/status.md <<'EOF_STATUS'
---
_baseline: v1.0
_current: HEAD
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: major
_review_round: 0
_phase: Requirements
---
EOF_STATUS

git add docs/v1.1/status.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected new status.md at Requirements to be blocked"
fi

git reset -q HEAD -- docs/v1.1/status.md
rm -f docs/v1.1/status.md

# Test 3: Proposal + Active CR is not a new-version startup and must still start from ChangeManagement.
cat > docs/v1.1/status.md <<'EOF_STATUS'
---
_baseline: v1.0
_current: HEAD
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: major
_review_round: 0
_phase: Proposal
---

## Active CR 列表（🔴 MUST，CR场景）
| CR-ID | 状态 | 标题 | 影响面（文档/模块/ID） | 链接 |
|---|---|---|---|---|
| CR-20260306-001 | Accepted | same-version change | requirements / REQ-001 | `cr/CR-20260306-001.md` |
EOF_STATUS

git add docs/v1.1/status.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected Proposal + Active CR on new status.md to be blocked"
fi

echo "ok"
