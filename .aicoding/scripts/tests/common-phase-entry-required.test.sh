#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
PASS=0
FAIL_COUNT=0

fail() {
  echo "FAIL: $*" >&2
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

pass() {
  echo "  ok: $1"
  PASS=$((PASS + 1))
}

tmp_dir=$(mktemp -d)
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT

cd "$tmp_dir"
git init -q
mkdir -p docs/v1.0

cat > aicoding.config.yaml <<'EOF_CFG'
phase_skip_proposal: true
EOF_CFG

source "$ROOT_DIR/scripts/lib/common.sh"
aicoding_load_config

design_required=$(aicoding_phase_entry_required "Design" "docs/v1.0/")
echo "$design_required" | grep -q "templates/review_design_template.md" \
  && pass "Design entry requires review template" \
  || fail "Design entry should require templates/review_design_template.md"

planning_required=$(aicoding_phase_entry_required "Planning" "docs/v1.0/")
echo "$planning_required" | grep -q "templates/review_planning_template.md" \
  && pass "Planning entry requires review template" \
  || fail "Planning entry should require templates/review_planning_template.md"

implementation_required=$(aicoding_phase_entry_required "Implementation" "docs/v1.0/")
echo "$implementation_required" | grep -q "templates/review_implementation_template.md" \
  && pass "Implementation entry requires review template" \
  || fail "Implementation entry should require templates/review_implementation_template.md"

testing_required=$(aicoding_phase_entry_required "Testing" "docs/v1.0/")
echo "$testing_required" | grep -q "templates/review_testing_template.md" \
  && pass "Testing entry requires review template" \
  || fail "Testing entry should require templates/review_testing_template.md"

hotfix_required=$(aicoding_phase_entry_required "Hotfix" "docs/v1.0/")
echo "$hotfix_required" | grep -q "phases/08-hotfix.md" \
  && pass "Hotfix entry requires phase definition" \
  || fail "Hotfix entry should require phases/08-hotfix.md"
echo "$hotfix_required" | grep -q "templates/status_template.md" \
  && pass "Hotfix entry requires status template" \
  || fail "Hotfix entry should require templates/status_template.md"

hotfix_exit_required=$(aicoding_phase_exit_required "Hotfix" "hotfix")
echo "$hotfix_exit_required" | grep -qx "status.md" \
  && pass "Hotfix exit requires status.md" \
  || fail "Hotfix exit should require status.md"

requirements_required=$(aicoding_phase_entry_required "Requirements" "docs/v1.0/")
if echo "$requirements_required" | grep -q "docs/v1.0/proposal.md"; then
  pass "Requirements entry always requires proposal.md (phase_skip_proposal is deprecated)"
else
  fail "Requirements entry should always require proposal.md"
fi

cat > aicoding.config.yaml <<'EOF_CFG_NEW'
requirements_entry_skip_proposal: true
phase_skip_proposal: false
quality_debt_max_total: 12
quality_debt_high_risk_max: 2
tech_debt_max_total: 18
EOF_CFG_NEW
aicoding_load_config

requirements_required_new=$(aicoding_phase_entry_required "Requirements" "docs/v1.0/")
if echo "$requirements_required_new" | grep -q "docs/v1.0/proposal.md"; then
  pass "Requirements entry always requires proposal.md (requirements_entry_skip_proposal is deprecated)"
else
  fail "Requirements entry should always require proposal.md"
fi

[ "${AICODING_QUALITY_DEBT_MAX_TOTAL:-}" = "12" ] \
  && pass "quality debt total threshold loaded" \
  || fail "expected AICODING_QUALITY_DEBT_MAX_TOTAL=12, got: ${AICODING_QUALITY_DEBT_MAX_TOTAL:-<empty>}"

[ "${AICODING_QUALITY_DEBT_HIGH_RISK_MAX:-}" = "2" ] \
  && pass "quality debt high-risk threshold loaded" \
  || fail "expected AICODING_QUALITY_DEBT_HIGH_RISK_MAX=2, got: ${AICODING_QUALITY_DEBT_HIGH_RISK_MAX:-<empty>}"

[ "${AICODING_TECH_DEBT_MAX_TOTAL:-}" = "18" ] \
  && pass "tech debt total threshold loaded" \
  || fail "expected AICODING_TECH_DEBT_MAX_TOTAL=18, got: ${AICODING_TECH_DEBT_MAX_TOTAL:-<empty>}"

echo ""
echo "=== Results: $PASS passed, $FAIL_COUNT failed ==="
[ "$FAIL_COUNT" -eq 0 ] || exit 1
