#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 4: 会话上下文注入（SessionStart）
# 在新会话开始时注入当前项目状态到 AI 上下文
STATUS_FILE=$(find "$CLAUDE_PROJECT_DIR/docs" -name "status.md" -path "*/v*/status.md" \
  -exec ls -t {} + 2>/dev/null | head -1)

if [ -z "$STATUS_FILE" ]; then
  echo '{"hookSpecificOutput":{"additionalContext":"[项目状态] 当前无活跃版本目录，无 status.md。"}}'
  exit 0
fi

PHASE=$(grep '^_phase:' "$STATUS_FILE" | awk '{print $2}')
[ -z "$PHASE" ] && PHASE=$(awk -F'|' '/\| 当前阶段/ {gsub(/^[ \t]+|[ \t]+$/,"",$3); print $3; exit}' "$STATUS_FILE")
RUN_STATUS=$(grep '^_run_status:' "$STATUS_FILE" | awk '{print $2}')
VERSION_DIR=$(echo "$STATUS_FILE" | sed 's/status\.md$//')

# 收集 Active CR
ACTIVE_CRS=$(awk -F'|' '{gsub(/[ \t]/,"",$2); gsub(/[ \t]/,"",$3)}
  $2 ~ /^CR-[0-9]{8}-[0-9]{3}$/ && ($3=="Accepted"||$3=="InProgress")
  {print $2}' "$STATUS_FILE" | tr '\n' ',' | sed 's/,$//')

CONTEXT="[项目状态] 版本目录: ${VERSION_DIR} | 当前阶段: ${PHASE} | 运行状态: ${RUN_STATUS}"
[ -n "$ACTIVE_CRS" ] && CONTEXT="${CONTEXT} | Active CRs: ${ACTIVE_CRS}"

case "$PHASE" in
  Proposal|Requirements|"Change Management"|ChangeManagement)
    CONTEXT="${CONTEXT} | 当前处于人工介入期，阶段推进需用户明确确认。" ;;
esac

echo "{\"hookSpecificOutput\":{\"additionalContext\":\"${CONTEXT}\"}}"
exit 0
