#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

COMMON="${ROOT_DIR}/scripts/lib/common.sh"
ENTRY="${ROOT_DIR}/scripts/cc-hooks/phase-entry-gate.sh"
INJECT="${ROOT_DIR}/scripts/cc-hooks/inject-phase-context.sh"
EXIT_GATE="${ROOT_DIR}/scripts/cc-hooks/phase-exit-gate.sh"
PRE_COMMIT="${ROOT_DIR}/scripts/git-hooks/pre-commit"

grep -q "aicoding_phase_entry_required()" "$COMMON" || fail "missing aicoding_phase_entry_required in common.sh"
grep -q "aicoding_phase_exit_required()" "$COMMON" || fail "missing aicoding_phase_exit_required in common.sh"

grep -q "aicoding_phase_entry_required" "$ENTRY" || fail "phase-entry-gate.sh does not use common phase-entry single source"
grep -q "aicoding_phase_entry_required" "$INJECT" || fail "inject-phase-context.sh does not use common phase-entry single source"
grep -q 'aicoding_detect_version_dir ""' "$INJECT" && fail "inject-phase-context.sh should not rely on legacy find fallback"
grep -q "aicoding_phase_exit_required" "$EXIT_GATE" || fail "phase-exit-gate.sh does not use common phase-exit single source"
grep -q "aicoding_phase_exit_required" "$PRE_COMMIT" || fail "pre-commit does not use common phase-exit single source"

echo "ok"
