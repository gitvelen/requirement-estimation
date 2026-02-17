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

# 检查写入内容是否试图推进到 AI 自动期阶段
if echo "$CC_CONTENT" | grep -qE '^_phase:[[:space:]]*(Design|Planning|Implementation|Testing|Deployment)[[:space:]]*$' || \
   echo "$CC_CONTENT" | grep -qE '当前阶段.*\| *(Design|Planning|Implementation|Testing|Deployment)'; then
  aicoding_block "当前处于人工介入期（$AICODING_PHASE），禁止 AI 自行推进阶段。请等待用户明确确认后再更新「当前阶段」。"
fi

exit 0
