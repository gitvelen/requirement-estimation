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

requirements_required=$(aicoding_phase_entry_required "Requirements" "docs/v1.0/")
if echo "$requirements_required" | grep -q "docs/v1.0/proposal.md"; then
  fail "Requirements entry should skip proposal.md when phase_skip_proposal=true"
else
  pass "Requirements entry respects phase_skip_proposal=true"
fi

cat > aicoding.config.yaml <<'EOF_CFG_NEW'
requirements_entry_skip_proposal: true
phase_skip_proposal: false
EOF_CFG_NEW
aicoding_load_config

requirements_required_new=$(aicoding_phase_entry_required "Requirements" "docs/v1.0/")
if echo "$requirements_required_new" | grep -q "docs/v1.0/proposal.md"; then
  fail "Requirements entry should skip proposal.md when requirements_entry_skip_proposal=true"
else
  pass "Requirements entry respects requirements_entry_skip_proposal=true"
fi

echo ""
echo "=== Results: $PASS passed, $FAIL_COUNT failed ==="
[ "$FAIL_COUNT" -eq 0 ] || exit 1
