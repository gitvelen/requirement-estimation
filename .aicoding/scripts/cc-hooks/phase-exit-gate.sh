#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 8: 阶段出口门禁（PreToolUse）
# 当 AI 试图修改 status.md 的 _phase 推进到下一阶段时，
# 检查当前阶段的必要产出物是否存在。
# 仅在 AI 自动期（Phase 03-06）生效。

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=../lib/review_gate_common.sh
source "${SCRIPT_DIR}/../lib/review_gate_common.sh"
source "${SCRIPT_DIR}/../lib/common.sh"
aicoding_load_config

aicoding_parse_cc_input
[ -z "$CC_FILE_PATH" ] && exit 0

# 只关心 status.md
echo "$CC_FILE_PATH" | grep -q 'status\.md$' || exit 0

NEW_PHASE=$(echo "$CC_CONTENT" | grep -oE '_phase:[[:space:]]*(ChangeManagement|Proposal|Requirements|Design|Planning|Implementation|Testing|Deployment)' \
  | sed 's/_phase:[[:space:]]*//' | head -1)
[ -z "$NEW_PHASE" ] && exit 0

aicoding_detect_version_dir "$CC_FILE_PATH" || exit 0
aicoding_get_phase || exit 0

NEW_CURRENT=$(echo "$CC_CONTENT" | awk '/^_current:/{sub(/^_current:[[:space:]]*/, "", $0); gsub(/[[:space:]]+$/, "", $0); print; exit}')
STATUS_CURRENT=$(aicoding_yaml_value "_current")
STATUS_CURRENT_REF="${NEW_CURRENT:-$STATUS_CURRENT}"
CHANGE_LEVEL=$(aicoding_yaml_value "_change_level")
[ -z "$CHANGE_LEVEL" ] && CHANGE_LEVEL="major"

# 如果新旧 _phase 相同，不是阶段推进，放行
[ "$AICODING_PHASE" = "$NEW_PHASE" ] && exit 0

# 只在 AI 自动期（Phase 03-06）做出口检查
case "$AICODING_PHASE" in
  Design|Planning|Implementation|Testing) ;;
  *) exit 0 ;;
esac

VERSION_PATH="${CLAUDE_PROJECT_DIR}/${AICODING_VERSION_DIR}"
MISSING=""

if [ -n "${CLAUDE_PROJECT_DIR:-}" ] && [ -d "$CLAUDE_PROJECT_DIR" ]; then
  cd "$CLAUDE_PROJECT_DIR" || exit 0
fi

check_file() {
  [ ! -f "${VERSION_PATH}$1" ] && MISSING="${MISSING}\n  - $1"
}

validate_minor_review_file() {
  local file="$1"
  [ -f "$file" ] || return 1
  grep -q 'REVIEW-SUMMARY-BEGIN' "$file" || return 1
  grep -q 'REVIEW_RESULT:[[:space:]]*pass' "$file" || return 1
  grep -q 'REQ_BASELINE_HASH:' "$file" || return 1
}

has_minor_test_evidence() {
  local status_file="$1"
  [ -f "${VERSION_PATH}test_report.md" ] && return 0
  grep -q 'TEST-RESULT-BEGIN' "$status_file" 2>/dev/null && return 0
  return 1
}

# 各阶段出口必须存在的产出物
while IFS= read -r required_doc; do
  [ -z "$required_doc" ] && continue
  check_file "$required_doc"
done < <(aicoding_phase_exit_required "$AICODING_PHASE" "$CHANGE_LEVEL")

if [ "$AICODING_PHASE" = "Testing" ] && [ "$CHANGE_LEVEL" = "minor" ]; then
  [ -f "${VERSION_PATH}test_report.md" ] || [ -n "$(grep -n 'TEST-RESULT-BEGIN' "${VERSION_PATH}status.md" 2>/dev/null || true)" ] || MISSING="${MISSING}\n  - test_report.md 或 status.md 内联 TEST-RESULT 块"
fi

if [ -n "$MISSING" ]; then
  ESCAPED=$(echo -e "$MISSING" | tr '\n' ' ')
  aicoding_block "阶段出口门禁（${AICODING_PHASE} → ${NEW_PHASE}）：以下必要产出物缺失：${ESCAPED}请补充完整后再推进阶段。（见 phases/ 中的「阶段出口门禁」）"
fi

# 内容级门禁（可验真）
REQ_FILE="${VERSION_PATH}requirements.md"
REQ_LABEL="${AICODING_VERSION_DIR}requirements.md"
case "$AICODING_PHASE" in
  Design)
    review_gate_validate_design_trace_coverage "$REQ_LABEL" "$REQ_FILE" "${AICODING_VERSION_DIR}design.md" "${VERSION_PATH}design.md" || { aicoding_block "Design 追溯覆盖校验失败"; } ;;
  Planning)
    review_gate_validate_plan_reverse_coverage "$REQ_LABEL" "$REQ_FILE" "${AICODING_VERSION_DIR}plan.md" "${VERSION_PATH}plan.md" || { aicoding_block "Planning 覆盖校验失败"; } ;;
  Implementation)
    if [ "$CHANGE_LEVEL" = "minor" ]; then
      validate_minor_review_file "${VERSION_PATH}review_minor.md" || { aicoding_block "Implementation minor 审查校验失败（review_minor.md 不完整）"; }
      has_minor_test_evidence "${VERSION_PATH}status.md" || { aicoding_block "Implementation minor 缺少测试证据（test_report.md 或 status.md TEST-RESULT）"; }
    else
      review_gate_validate_review_summary_and_coverage "${AICODING_VERSION_DIR}review_implementation.md" "${VERSION_PATH}review_implementation.md" "$REQ_LABEL" "$REQ_FILE" "$STATUS_CURRENT_REF" "${AICODING_VERSION_DIR}review_implementation.md" || { aicoding_block "Implementation 审查摘要校验失败"; }
    fi
    ;;
  Testing)
    if [ "$CHANGE_LEVEL" = "minor" ]; then
      validate_minor_review_file "${VERSION_PATH}review_minor.md" || { aicoding_block "Testing minor 审查校验失败（review_minor.md 不完整）"; }
      has_minor_test_evidence "${VERSION_PATH}status.md" || { aicoding_block "Testing minor 缺少测试证据（test_report.md 或 status.md TEST-RESULT）"; }
    else
      review_gate_validate_review_summary_and_coverage "${AICODING_VERSION_DIR}review_testing.md" "${VERSION_PATH}review_testing.md" "$REQ_LABEL" "$REQ_FILE" "$STATUS_CURRENT_REF" "${AICODING_VERSION_DIR}review_testing.md" || { aicoding_block "Testing 审查摘要校验失败"; }
      review_gate_validate_test_report_gwt_coverage "$REQ_LABEL" "$REQ_FILE" "${AICODING_VERSION_DIR}test_report.md" "${VERSION_PATH}test_report.md" || { aicoding_block "Testing GWT 覆盖校验失败"; }
    fi
    ;;
esac

exit 0
