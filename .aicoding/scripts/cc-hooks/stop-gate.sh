#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 2: Stop 门禁（Stop）
# 阻止 AI 在人工介入期未设 wait_confirm 或未经审查就停止
INPUT=$(cat)

# 检查是否已经在 stop hook 中（防止无限循环）
IS_STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
[ "$IS_STOP_ACTIVE" = "true" ] && exit 0

STATUS_FILE=$(find "$CLAUDE_PROJECT_DIR/docs" -name "status.md" -path "*/v*/status.md" \
  -exec ls -t {} + 2>/dev/null | head -1)
[ -z "$STATUS_FILE" ] || [ ! -f "$STATUS_FILE" ] && exit 0

PHASE=$(grep '^_phase:' "$STATUS_FILE" | awk '{print $2}')
[ -z "$PHASE" ] && PHASE=$(awk -F'|' '/\| 当前阶段/ {gsub(/^[ \t]+|[ \t]+$/,"",$3); print $3; exit}' "$STATUS_FILE")
VERSION_DIR=$(dirname "$STATUS_FILE")/

case "$PHASE" in
  Proposal|Requirements|"Change Management"|ChangeManagement) ;;
  *) exit 0 ;;
esac

REASONS=""

# 检查 1：运行状态是否已设为 wait_confirm（从 YAML front matter 读取）
RUN_STATUS=$(grep '^_run_status:' "$STATUS_FILE" | awk '{print $2}')
if [ "$RUN_STATUS" != "wait_confirm" ]; then
  REASONS="status.md 的 _run_status 未设为 wait_confirm（当前值: ${RUN_STATUS:-空}）。"
fi

# 检查 2：当前阶段的 review 文件是否存在（统一使用 review_<stage>.md）
case "$PHASE" in
  "Change Management"|ChangeManagement) REVIEW_FILE="review_change_management.md" ;;
  Proposal) REVIEW_FILE="review_proposal.md" ;;
  Requirements) REVIEW_FILE="review_requirements.md" ;;
esac
if [ -n "$REVIEW_FILE" ] && [ ! -f "${VERSION_DIR}${REVIEW_FILE}" ]; then
  REASONS="${REASONS} ${REVIEW_FILE} 不存在，尚未执行审查。"
fi

if [ -n "$REASONS" ]; then
  cat <<EOF
{
  "decision": "block",
  "reason": "当前处于人工介入期（${PHASE}），结束前需满足：1) YAML front matter 的 _run_status 设为 wait_confirm；2) 审查文件 ${REVIEW_FILE} 存在。未满足项：${REASONS}"
}
EOF
fi

exit 0
