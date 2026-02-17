#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 2: Stop 门禁（Stop）
# 阻止 AI 在人工介入期未设 wait_confirm 或未经审查就停止

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/../lib/common.sh"

CC_RAW_INPUT=$(cat)

# 检查是否已经在 stop hook 中（防止无限循环）
IS_STOP_ACTIVE=$(echo "$CC_RAW_INPUT" | jq -r '.stop_hook_active // false')
[ "$IS_STOP_ACTIVE" = "true" ] && exit 0

aicoding_detect_version_dir "" || exit 0
aicoding_get_phase || exit 0

# 非人工介入期，放行
aicoding_is_manual_phase || exit 0

VERSION_DIR=$(dirname "$AICODING_STATUS_FILE")/
REASONS=""

# 检查 1：运行状态是否已设为 wait_confirm
RUN_STATUS=$(aicoding_yaml_value "_run_status")
if [ "$RUN_STATUS" != "wait_confirm" ]; then
  REASONS="status.md 的 _run_status 未设为 wait_confirm（当前值: ${RUN_STATUS:-空}）。"
fi

# 检查 2：当前阶段的 review 文件是否存在
case "$AICODING_PHASE" in
  "Change Management"|ChangeManagement) REVIEW_FILE="review_change_management.md" ;;
  Proposal) REVIEW_FILE="review_proposal.md" ;;
  Requirements) REVIEW_FILE="review_requirements.md" ;;
esac
if [ -n "$REVIEW_FILE" ] && [ ! -f "${VERSION_DIR}${REVIEW_FILE}" ]; then
  REASONS="${REASONS} ${REVIEW_FILE} 不存在，尚未执行审查。"
fi

if [ -n "$REASONS" ]; then
  aicoding_block "当前处于人工介入期（${AICODING_PHASE}），结束前需满足：1) YAML front matter 的 _run_status 设为 wait_confirm；2) 审查文件 ${REVIEW_FILE} 存在。未满足项：${REASONS}"
fi

exit 0
