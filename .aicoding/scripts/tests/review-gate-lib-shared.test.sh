#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

LIB="${ROOT_DIR}/scripts/lib/review_gate_common.sh"
COMMON="${ROOT_DIR}/scripts/lib/common.sh"
PRE_COMMIT="${ROOT_DIR}/scripts/git-hooks/pre-commit"
DISPATCHER="${ROOT_DIR}/scripts/cc-hooks/pre-write-dispatcher.sh"

[ -f "$LIB" ] || fail "missing shared lib: $LIB"
[ -f "$COMMON" ] || fail "missing common lib: $COMMON"

# pre-commit sources both libs
grep -q "review_gate_common.sh" "$PRE_COMMIT" || fail "pre-commit does not source review_gate_common.sh"
grep -q "common.sh" "$PRE_COMMIT" || fail "pre-commit does not source common.sh"
grep -q "review_gate_validate_review_summary_and_coverage" "$PRE_COMMIT" || fail "pre-commit does not call shared validator"

# dispatcher sources both libs
grep -q "review_gate_common.sh" "$DISPATCHER" || fail "dispatcher does not source review_gate_common.sh"
grep -q "common.sh" "$DISPATCHER" || fail "dispatcher does not source common.sh"
grep -q "review_gate_validate_design_trace_coverage" "$DISPATCHER" || fail "dispatcher missing design trace validator"

echo "ok"
