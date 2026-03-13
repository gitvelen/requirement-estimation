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

run_case() {
  local baseline="$1"
  local should_pass="$2"
  local label="$3"
  local tmp_dir
  tmp_dir=$(mktemp -d)

  (
    trap 'rm -rf "$tmp_dir"' EXIT
    cd "$tmp_dir"
    git init -q
    git config user.email "test@example.com"
    git config user.name "test"

    mkdir -p scripts/git-hooks scripts/lib .aicoding docs/v1.1
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

    cat > docs/v1.1/status.md <<EOF_STATUS
---
_baseline: ${baseline}
_current: HEAD
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: major
_review_round: 0
_phase: ChangeManagement
---
EOF_STATUS

    git add docs/v1.1/status.md

    if [ "$should_pass" = "pass" ]; then
      if ! bash scripts/git-hooks/pre-commit; then
        fail "$label: expected pass for _baseline=${baseline}"
      fi
    else
      if bash scripts/git-hooks/pre-commit; then
        fail "$label: expected failure for _baseline=${baseline}"
      fi
    fi
  )
}

run_case "v1.0" pass "case 1"
run_case "main" fail "case 2"
run_case "abc1234" fail "case 3"
run_case "v1.0-baseline" fail "case 4"

echo "ok"
