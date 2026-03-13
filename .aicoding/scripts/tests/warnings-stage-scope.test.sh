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
cat > "$tmp_dir/docs/v1.0/status.md" <<'EOF_STATUS'
---
_phase: Proposal
_run_status: wait_confirm
_change_status: in_progress
_current: main
---
EOF_STATUS

cat > "$tmp_dir/docs/v1.0/plan.md" <<'EOF_PLAN'
### T1 示例任务
- 描述：x
- 验证方式：
EOF_PLAN

cat > "$tmp_dir/docs/v1.0/review_testing.md" <<'EOF_REVIEW'
REVIEW-SUMMARY-BEGIN
REVIEW_RESULT: pass
CODE_BASELINE: main
REVIEW-SUMMARY-END

| GWT-ID | REQ-ID | 判定 | 备注 | 证据类型 | 证据 |
|---|---|---|---|---|---|
| GWT-REQ-001-01 | REQ-001 | PASS | - | CODE_REF | src/a.ts:1 |
EOF_REVIEW

run_warning() {
  local script_path="$1"
  bash -c 'source "$1/scripts/lib/common.sh"; STATUS_FILE="$2"; AICODING_STATUS_FILE="$2"; VERSION_DIR="$3"; warn(){ echo "WARN:$*"; }; source "$4"' _ "$ROOT_DIR" "$tmp_dir/docs/v1.0/status.md" "$tmp_dir/docs/v1.0/" "$script_path"
}

out=$(run_warning "$ROOT_DIR/scripts/git-hooks/warnings/w17-plan-verify-cmd.sh")
[ -z "$out" ] || fail "expected W17 to stay quiet outside Testing/Deployment, got: $out"

out=$(run_warning "$ROOT_DIR/scripts/git-hooks/warnings/w20-moving-ref.sh")
[ -z "$out" ] || fail "expected W20 to stay quiet outside Testing/Deployment, got: $out"

out=$(run_warning "$ROOT_DIR/scripts/git-hooks/warnings/w22-review-evidence.sh")
[ -z "$out" ] || fail "expected W22 to stay quiet outside Testing/Deployment, got: $out"

echo "ok"
