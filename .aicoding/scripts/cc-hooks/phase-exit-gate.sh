#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 8: 阶段出口门禁（PreToolUse）
# 当 AI 试图修改 status.md 的 _phase 推进到下一阶段时，
# 检查当前阶段的必要产出物是否存在。
# 覆盖 Requirements + AI 自动期（Phase 02-06）阶段推进写入门禁。

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=../lib/review_gate_common.sh
source "${SCRIPT_DIR}/../lib/review_gate_common.sh"
source "${SCRIPT_DIR}/../lib/common.sh"
source "${SCRIPT_DIR}/../lib/validation.sh"
aicoding_load_config

aicoding_parse_cc_input
[ -z "$CC_FILE_PATH" ] && exit 0

# 只关心 status.md
echo "$CC_FILE_PATH" | grep -q 'status\.md$' || exit 0

NEW_PHASE=$(echo "$CC_CONTENT" | grep -oE '_phase:[[:space:]]*(ChangeManagement|Proposal|Requirements|Design|Planning|Implementation|Testing|Deployment|Hotfix)' \
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

# 只在 Requirements + AI 自动期（Phase 02-06）和 Hotfix 做出口检查
case "$AICODING_PHASE" in
  Requirements|Design|Planning|Implementation|Testing|Hotfix) ;;
  *) exit 0 ;;
esac

# 相邻阶段校验：前进跨度 >1 硬拦截
OLD_RANK=$(aicoding_phase_rank "$AICODING_PHASE")
NEW_RANK=$(aicoding_phase_rank "$NEW_PHASE")
FORWARD_JUMP=$((NEW_RANK - OLD_RANK))
if [ "$FORWARD_JUMP" -gt 1 ]; then
  aicoding_block "阶段跳跃（${AICODING_PHASE} → ${NEW_PHASE}，跨度 ${FORWARD_JUMP}）：只允许推进到相邻的下一阶段，不允许跳跃。"
fi

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
validate_minor_testing_round_file() {
  local review_file="$1"
  local block phase result round_at phase_norm result_norm
  [ -f "$review_file" ] || return 1
  block=$(
    awk '
      /MINOR-TESTING-ROUND-BEGIN/ {in_block=1; buf=""; next}
      /MINOR-TESTING-ROUND-END/ {
        if (in_block) {last=buf}
        in_block=0
        next
      }
      in_block {buf = buf $0 "\n"}
      END {printf "%s", last}
    ' "$review_file"
  )
  [ -n "$block" ] || return 1

  phase=$(printf '%s\n' "$block" | sed -n 's/^ROUND_PHASE:[[:space:]]*//p' | tail -1)
  result=$(printf '%s\n' "$block" | sed -n 's/^ROUND_RESULT:[[:space:]]*//p' | tail -1)
  round_at=$(printf '%s\n' "$block" | sed -n 's/^ROUND_AT:[[:space:]]*//p' | tail -1)
  phase_norm=$(printf '%s' "$phase" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')
  result_norm=$(printf '%s' "$result" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')

  [ "$phase_norm" = "testing" ] || return 1
  [ "$result_norm" = "pass" ] || return 1
  echo "$round_at" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' || return 1
  return 0
}
validate_constraints_confirmation_file() {
  local review_label="$1" review_file="$2" req_label="$3" req_file="$4" proposal_label="$5" proposal_file="$6"
  review_gate_validate_constraints_confirmation \
    "$review_label" "$review_file" "$req_label" "$req_file" "$proposal_label" "$proposal_file"
}
validate_proposal_coverage_file() {
  local proposal_label="$1" proposal_file="$2" req_label="$3" req_file="$4"
  [ -f "$proposal_file" ] || return 0
  review_gate_validate_proposal_coverage "$proposal_label" "$proposal_file" "$req_label" "$req_file"
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
  Requirements)
    validate_constraints_confirmation_file \
      "${AICODING_VERSION_DIR}review_requirements.md" "${VERSION_PATH}review_requirements.md" \
      "$REQ_LABEL" "$REQ_FILE" \
      "${AICODING_VERSION_DIR}proposal.md" "${VERSION_PATH}proposal.md" || { aicoding_block "Requirements 禁止项确认校验失败"; }
    validate_proposal_coverage_file \
      "${AICODING_VERSION_DIR}proposal.md" "${VERSION_PATH}proposal.md" \
      "$REQ_LABEL" "$REQ_FILE" || { aicoding_block "Requirements Proposal 覆盖校验失败"; }
    ;;
  Design)
    review_gate_validate_design_trace_coverage "$REQ_LABEL" "$REQ_FILE" "${AICODING_VERSION_DIR}design.md" "${VERSION_PATH}design.md" || { aicoding_block "Design 追溯覆盖校验失败"; } ;;
  Planning)
    review_gate_validate_plan_reverse_coverage "$REQ_LABEL" "$REQ_FILE" "${AICODING_VERSION_DIR}plan.md" "${VERSION_PATH}plan.md" || { aicoding_block "Planning 覆盖校验失败"; } ;;
  Implementation)
    if [ "$CHANGE_LEVEL" = "minor" ]; then
      validate_minor_review_file "${VERSION_PATH}review_minor.md" || { aicoding_block "Implementation minor 审查校验失败（review_minor.md 不完整）"; }
    else
      review_gate_validate_review_summary_and_coverage "${AICODING_VERSION_DIR}review_implementation.md" "${VERSION_PATH}review_implementation.md" "$REQ_LABEL" "$REQ_FILE" "$STATUS_CURRENT_REF" "${AICODING_VERSION_DIR}review_implementation.md" || { aicoding_block "Implementation 审查摘要校验失败"; }
    fi
    ;;
  Testing)
    if [ "$CHANGE_LEVEL" = "minor" ]; then
      validate_minor_review_file "${VERSION_PATH}review_minor.md" || { aicoding_block "Testing minor 审查校验失败（review_minor.md 不完整）"; }
      has_minor_test_evidence "${VERSION_PATH}status.md" || { aicoding_block "Testing minor 缺少测试证据（test_report.md 或 status.md TEST-RESULT）"; }
      validate_minor_testing_round_file "${VERSION_PATH}review_minor.md" || { aicoding_block "Testing minor 缺少 Testing 轮次机器可读结论（MINOR-TESTING-ROUND）"; }
    else
      review_gate_validate_review_summary_and_coverage "${AICODING_VERSION_DIR}review_testing.md" "${VERSION_PATH}review_testing.md" "$REQ_LABEL" "$REQ_FILE" "$STATUS_CURRENT_REF" "${AICODING_VERSION_DIR}review_testing.md" || { aicoding_block "Testing 审查摘要校验失败"; }
      review_gate_validate_test_report_gwt_coverage "$REQ_LABEL" "$REQ_FILE" "${AICODING_VERSION_DIR}test_report.md" "${VERSION_PATH}test_report.md" || { aicoding_block "Testing GWT 覆盖校验失败"; }
    fi
    ;;
  Hotfix)
    has_test_result_block "$CC_CONTENT" || { aicoding_block "Hotfix 阶段退出前必须在 status.md 内联 TEST-RESULT 结果块"; }
    ;;
esac

exit 0
