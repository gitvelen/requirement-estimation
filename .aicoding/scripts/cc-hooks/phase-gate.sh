#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 1: 阶段推进拦截（PreToolUse）
# 阻止 AI 在人工介入期（Phase 00-02）自行推进 status.md 的"当前阶段"字段

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/../lib/common.sh"

aicoding_parse_cc_input

# 只关心 status.md
echo "$CC_FILE_PATH" | grep -q 'status\.md$' || exit 0

aicoding_detect_version_dir "$CC_FILE_PATH" || exit 0
aicoding_get_phase || exit 0

# 非人工介入期，放行
aicoding_is_manual_phase || exit 0

# wait_confirm 状态下放行：说明 AI 已暂停等待过用户确认，此时代为更新 _phase 是合法的
CURRENT_RUN_STATUS=$(aicoding_yaml_value "_run_status")
if [ "$CURRENT_RUN_STATUS" != "wait_confirm" ]; then
  NEW_PHASE_IN_CONTENT=$(echo "$CC_CONTENT" | grep -oE '^_phase:[[:space:]]*(ChangeManagement|Proposal|Requirements|Design|Planning|Implementation|Testing|Deployment)' \
    | sed 's/^_phase:[[:space:]]*//' | head -1)
  if [ -n "$NEW_PHASE_IN_CONTENT" ] && [ "$NEW_PHASE_IN_CONTENT" != "$AICODING_PHASE" ]; then
    aicoding_block "当前处于人工介入期（$AICODING_PHASE），禁止 AI 自行推进阶段至 ${NEW_PHASE_IN_CONTENT}。请先设置 _run_status: wait_confirm 并等待用户明确确认后再更新。"
  fi

  TABLE_PHASE=$(echo "$CC_CONTENT" | grep -oE '当前阶段.*\|[[:space:]]*[A-Za-z]+' | grep -oE '[A-Za-z]+$' | head -1)
  if [ -n "$TABLE_PHASE" ] && [ "$TABLE_PHASE" != "$AICODING_PHASE" ]; then
    aicoding_block "当前处于人工介入期（$AICODING_PHASE），禁止 AI 自行推进阶段至 ${TABLE_PHASE}。请先设置 _run_status: wait_confirm 并等待用户明确确认后再更新。"
  fi
fi

exit 0
