#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 1: 阶段推进拦截（PreToolUse）
# 阻止 AI 在人工介入期（Phase 00-02）自行推进 status.md 的"当前阶段"字段
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // empty')

# 只关心 status.md
echo "$FILE_PATH" | grep -q 'status\.md$' || exit 0

# 从 file_path 反推版本目录的 status.md（优先同目录）
VERSION_DIR=$(echo "$FILE_PATH" | grep -oE 'docs/v[0-9]+\.[0-9]+/')
if [ -n "$VERSION_DIR" ]; then
  STATUS_FILE="${CLAUDE_PROJECT_DIR}/${VERSION_DIR}status.md"
else
  STATUS_FILE=$(find "$CLAUDE_PROJECT_DIR/docs" -name "status.md" -path "*/v*/status.md" \
    -exec ls -t {} + 2>/dev/null | head -1)
fi
[ -z "$STATUS_FILE" ] || [ ! -f "$STATUS_FILE" ] && exit 0

# 检查当前阶段是否在人工介入期
PHASE=$(grep '^_phase:' "$STATUS_FILE" | awk '{print $2}')
[ -z "$PHASE" ] && PHASE=$(awk -F'|' '/\| 当前阶段/ {gsub(/^[ \t]+|[ \t]+$/,"",$3); print $3; exit}' "$STATUS_FILE")
case "$PHASE" in
  Proposal|Requirements|"Change Management"|ChangeManagement) ;;
  *) exit 0 ;;  # 非人工介入期，放行
esac

# 检查写入内容是否试图修改"当前阶段"到下一阶段
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty')
if echo "$CONTENT" | grep -qE '^_phase:[[:space:]]*(Design|Planning|Implementation|Testing|Deployment)[[:space:]]*$' || \
   echo "$CONTENT" | grep -qE '当前阶段.*\| *(Design|Planning|Implementation|Testing|Deployment)'; then
  echo "❌ 当前处于人工介入期（$PHASE），禁止 AI 自行推进阶段。" >&2
    echo "   请等待用户明确确认后再更新「当前阶段」。" >&2
  exit 2
fi

exit 0
