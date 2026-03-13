#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
PASS=0; FAIL_COUNT=0

fail() { echo "FAIL: $*" >&2; FAIL_COUNT=$((FAIL_COUNT + 1)); }
pass() { echo "  ok: $1"; PASS=$((PASS + 1)); }

tmp_dir=$(mktemp -d)
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT

# 模拟 CLAUDE_PROJECT_DIR
export CLAUDE_PROJECT_DIR="$tmp_dir"
mkdir -p "$tmp_dir/docs/v1.0/cr"

# 创建测试用 status.md
cat > "$tmp_dir/docs/v1.0/status.md" <<'EOF'
---
_baseline: v0.9
_current: abc1234
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_phase: Implementation
---
EOF

# 加载 common.sh
source "$ROOT_DIR/scripts/lib/common.sh"

# ============================================================
# Test: aicoding_yaml_value
# ============================================================
echo "--- aicoding_yaml_value ---"

AICODING_STATUS_FILE="$tmp_dir/docs/v1.0/status.md"

val=$(aicoding_yaml_value "_phase")
[ "$val" = "Implementation" ] && pass "_phase = Implementation" || fail "_phase expected Implementation, got: $val"

val=$(aicoding_yaml_value "_current")
[ "$val" = "abc1234" ] && pass "_current = abc1234" || fail "_current expected abc1234, got: $val"

val=$(aicoding_yaml_value "_baseline")
[ "$val" = "v0.9" ] && pass "_baseline = v0.9" || fail "_baseline expected v0.9, got: $val"

val=$(aicoding_yaml_value "_nonexistent")
[ -z "$val" ] && pass "_nonexistent = empty" || fail "_nonexistent expected empty, got: $val"

# 测试指定文件参数
val=$(aicoding_yaml_value "_phase" "$tmp_dir/docs/v1.0/status.md")
[ "$val" = "Implementation" ] && pass "_phase with explicit file" || fail "_phase with explicit file failed"

# ============================================================
# Test: aicoding_phase_rank
# ============================================================
echo "--- aicoding_phase_rank ---"

r=$(aicoding_phase_rank "ChangeManagement")
[ "$r" -eq 0 ] && pass "ChangeManagement = 0" || fail "ChangeManagement expected 0, got: $r"

r=$(aicoding_phase_rank "Implementation")
[ "$r" -eq 5 ] && pass "Implementation = 5" || fail "Implementation expected 5, got: $r"

r=$(aicoding_phase_rank "Deployment")
[ "$r" -eq 7 ] && pass "Deployment = 7" || fail "Deployment expected 7, got: $r"

r=$(aicoding_phase_rank "Unknown")
[ "$r" -eq 999 ] && pass "Unknown = 999" || fail "Unknown expected 999, got: $r"

# ============================================================
# Test: aicoding_normalize_phase
# ============================================================
echo "--- aicoding_normalize_phase ---"

norm=$(aicoding_normalize_phase "Change Management")
[ "$norm" = "ChangeManagement" ] && pass "Change Management normalized to ChangeManagement" || fail "normalize failed, got: $norm"

norm=$(aicoding_normalize_phase "Implementation")
[ "$norm" = "Implementation" ] && pass "Implementation unchanged" || fail "normalize should keep Implementation, got: $norm"

# ============================================================
# Test: aicoding_is_commit_sha
# ============================================================
echo "--- aicoding_is_commit_sha ---"

aicoding_is_commit_sha "abc1234" && pass "abc1234 is SHA" || fail "abc1234 should be SHA"
aicoding_is_commit_sha "abc1234def5678" && pass "14-char hex is SHA" || fail "14-char hex should be SHA"
aicoding_is_commit_sha "HEAD" && fail "HEAD should not be SHA" || pass "HEAD is not SHA"
aicoding_is_commit_sha "v1.0" && fail "v1.0 should not be SHA" || pass "v1.0 is not SHA"
aicoding_is_commit_sha "" && fail "empty should not be SHA" || pass "empty is not SHA"

# ============================================================
# Test: aicoding_is_manual_phase
# ============================================================
echo "--- aicoding_is_manual_phase ---"

AICODING_PHASE="Proposal"
aicoding_is_manual_phase && pass "Proposal is manual" || fail "Proposal should be manual"

AICODING_PHASE="Requirements"
aicoding_is_manual_phase && pass "Requirements is manual" || fail "Requirements should be manual"

AICODING_PHASE="Implementation"
aicoding_is_manual_phase && fail "Implementation should not be manual" || pass "Implementation is not manual"

AICODING_PHASE="Testing"
aicoding_is_manual_phase && fail "Testing should not be manual" || pass "Testing is not manual"

# ============================================================
# Test: aicoding_detect_version_dir
# ============================================================
echo "--- aicoding_detect_version_dir ---"

aicoding_detect_version_dir "docs/v1.0/design.md"
[ "$AICODING_VERSION_DIR" = "docs/v1.0/" ] && pass "version dir from path" || fail "expected docs/v1.0/, got: $AICODING_VERSION_DIR"

aicoding_detect_version_dir "src/main.py"
[ "$AICODING_VERSION_DIR" = "docs/v1.0/" ] && pass "version dir fallback find" || fail "fallback expected docs/v1.0/, got: $AICODING_VERSION_DIR"

OLD_CLAUDE_PROJECT_DIR=${CLAUDE_PROJECT_DIR:-}
OLD_PWD=$(pwd)
cd "$tmp_dir"
unset CLAUDE_PROJECT_DIR
aicoding_detect_version_dir "src/main.py"
[ "$AICODING_VERSION_DIR" = "docs/v1.0/" ] && pass "version dir fallback without CLAUDE_PROJECT_DIR" || fail "fallback without CLAUDE_PROJECT_DIR expected docs/v1.0/, got: $AICODING_VERSION_DIR"
export CLAUDE_PROJECT_DIR="$OLD_CLAUDE_PROJECT_DIR"
cd "$OLD_PWD"

# ============================================================
# Test: aicoding_summary_value_from_file
# ============================================================
echo "--- aicoding_summary_value_from_file ---"

cat > "$tmp_dir/review.md" <<'EOF'
## Review

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_RESULT: pass
GWT_TOTAL: 5
GWT_FAIL: 0
<!-- REVIEW-SUMMARY-END -->
EOF

val=$(aicoding_summary_value_from_file "$tmp_dir/review.md" "REVIEW_RESULT")
[ "$val" = "pass" ] && pass "REVIEW_RESULT = pass" || fail "REVIEW_RESULT expected pass, got: $val"

val=$(aicoding_summary_value_from_file "$tmp_dir/review.md" "GWT_TOTAL")
[ "$val" = "5" ] && pass "GWT_TOTAL = 5" || fail "GWT_TOTAL expected 5, got: $val"

val=$(aicoding_summary_value_from_file "$tmp_dir/review.md" "NONEXISTENT" || true)
[ -z "$val" ] && pass "NONEXISTENT = empty" || fail "NONEXISTENT expected empty, got: $val"

# ============================================================
# Test: aicoding_last_gwt_table_rows
# ============================================================
echo "--- aicoding_last_gwt_table_rows ---"

cat > "$tmp_dir/gwt.md" <<'EOF'
| GWT-ID | REQ-ID | 判定 |
|---|---|---|
| GWT-REQ-001-01 | REQ-001 | ✅ |
| GWT-REQ-001-02 | REQ-001 | ❌ |

Some text

| GWT-ID | REQ-ID | 判定 |
|---|---|---|
| GWT-REQ-002-01 | REQ-002 | ✅ |
EOF

rows=$(aicoding_last_gwt_table_rows < "$tmp_dir/gwt.md")
echo "$rows" | grep -q "GWT-REQ-002-01" && pass "last table has GWT-REQ-002-01" || fail "last table should have GWT-REQ-002-01"
echo "$rows" | grep -q "GWT-REQ-001-01" && fail "last table should not have first table rows" || pass "last table excludes first table"

# ============================================================
# Test: aicoding_active_crs
# ============================================================
echo "--- aicoding_active_crs ---"

cat > "$tmp_dir/docs/v1.0/status.md" <<'EOF'
---
_baseline: v0.9
_current: abc1234
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_phase: Implementation
---

## Active CRs
| CR-ID | 状态 |
|---|---|
| CR-20260306-001 | Accepted |
| CR-20260306-002 | Closed |
EOF

crs=$(aicoding_active_crs "$tmp_dir/docs/v1.0/status.md")
echo "$crs" | grep -q "CR-20260306-001" && pass "CR-20260306-001 is active" || fail "CR-20260306-001 should be active"

# ============================================================
# Summary
# ============================================================
echo ""
echo "=== Results: $PASS passed, $FAIL_COUNT failed ==="
[ "$FAIL_COUNT" -eq 0 ] || exit 1
