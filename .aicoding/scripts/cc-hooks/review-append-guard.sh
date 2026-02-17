#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 6: review 文件追加保护（PreToolUse）
# 阻止 AI 用 Write 覆盖已有的 review 审查记录
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // empty')
[ -z "$FILE_PATH" ] && exit 0

# 只关心 review_*.md 文件
echo "$FILE_PATH" | grep -qE 'review_[a-z_]+\.md$' || exit 0

# 文件不存在（首次创建），放行
[ ! -f "$FILE_PATH" ] && exit 0

# 统计已有的审查轮次记录
EXISTING_ROUNDS=$(grep -c '## [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}.*第.*轮' "$FILE_PATH" 2>/dev/null || echo 0)
[ "$EXISTING_ROUNDS" -eq 0 ] && exit 0

# 有已有轮次，检查新内容是否保留了它们
NEW_CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // empty')
NEW_ROUNDS=$(echo "$NEW_CONTENT" | grep -c '## [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}.*第.*轮' 2>/dev/null || echo 0)

if [ "$NEW_ROUNDS" -lt "$EXISTING_ROUNDS" ]; then
  echo "❌ review 文件已有 ${EXISTING_ROUNDS} 轮审查记录，新内容只有 ${NEW_ROUNDS} 轮。" >&2
  echo "   审查记录必须追加，不得覆盖。请使用 Edit 工具在文件末尾追加新一轮审查。" >&2
  exit 2
fi

exit 0
