#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

tmp_dir=$(mktemp -d)
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT

mkdir -p "$tmp_dir/docs/v1.0"

run_warning() {
  local script_path="$1"
  bash -c 'source "$1/scripts/lib/common.sh"; STATUS_FILE="$2"; AICODING_STATUS_FILE="$2"; VERSION_DIR="$3"; warn(){ echo "WARN:$*"; }; source "$4"' _ "$ROOT_DIR" "$tmp_dir/docs/v1.0/status.md" "$tmp_dir/docs/v1.0/" "$script_path"
}

cat > "$tmp_dir/docs/v1.0/status.md" <<'EOF_STATUS'
---
_phase: Deployment
_change_level: minor
_run_status: wait_confirm
_change_status: in_progress
---

<!-- TEST-RESULT-BEGIN -->
TEST_RESULT: pass
<!-- TEST-RESULT-END -->
EOF_STATUS

out=$(run_warning "$ROOT_DIR/scripts/git-hooks/warnings/w08-artifact-exists.sh")
[ -z "$out" ] || fail "expected W8 to respect minor status inline test evidence, got: $out"

cat > "$tmp_dir/docs/v1.0/status.md" <<'EOF_STATUS'
---
_phase: Testing
_change_level: minor
_run_status: wait_confirm
_change_status: in_progress
_current: abcdef1
---
EOF_STATUS

cat > "$tmp_dir/docs/v1.0/review_minor.md" <<'EOF_REVIEW'
REVIEW-SUMMARY-BEGIN
REVIEW_RESULT: pass
CODE_BASELINE: main
REQ_BASELINE_HASH: abc
REVIEW-SUMMARY-END

| GWT-ID | RESULT | EVIDENCE_TYPE | EVIDENCE |
|---|---|---|---|
| GWT-REQ-001-01 | PASS |  |  |
EOF_REVIEW

out=$(run_warning "$ROOT_DIR/scripts/git-hooks/warnings/w20-moving-ref.sh")
echo "$out" | grep -q "review_minor.md" || fail "expected W20 to cover review_minor.md, got: $out"

out=$(run_warning "$ROOT_DIR/scripts/git-hooks/warnings/w22-review-evidence.sh")
echo "$out" | grep -q "review_minor.md" || fail "expected W22 to cover review_minor.md, got: $out"

# W27 should NOT fire for minor reviews (minor is lightweight, no adversarial self-check required)
out=$(run_warning "$ROOT_DIR/scripts/git-hooks/warnings/w27-adversarial-selfcheck.sh")
[ -z "$out" ] || fail "expected W27 to skip minor review, got: $out"

echo "ok"
