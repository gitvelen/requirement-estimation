#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 3: 文档作用域控制（PreToolUse）
# 阻止 AI 在当前阶段创建/修改不属于该阶段的产出物
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // empty')
[ -z "$FILE_PATH" ] && exit 0

# 只关心 docs/vX.Y/ 下的文件
echo "$FILE_PATH" | grep -qE 'docs/v[0-9]+\.[0-9]+/' || exit 0

# 从 file_path 反推版本目录的 status.md（优先同目录）
VERSION_DIR=$(echo "$FILE_PATH" | grep -oE 'docs/v[0-9]+\.[0-9]+/')
if [ -n "$VERSION_DIR" ]; then
  STATUS_FILE="${CLAUDE_PROJECT_DIR}/${VERSION_DIR}status.md"
else
  STATUS_FILE=$(find "$CLAUDE_PROJECT_DIR/docs" -name "status.md" -path "*/v*/status.md" \
    -exec ls -t {} + 2>/dev/null | head -1)
fi
[ -z "$STATUS_FILE" ] || [ ! -f "$STATUS_FILE" ] && exit 0

PHASE=$(grep '^_phase:' "$STATUS_FILE" | awk '{print $2}')
[ -z "$PHASE" ] && PHASE=$(awk -F'|' '/\| 当前阶段/ {gsub(/^[ \t]+|[ \t]+$/,"",$3); print $3; exit}' "$STATUS_FILE")

# 各阶段允许的产出文件白名单
# review_*.md 在任何阶段都允许（审查可随时发起）
case "$PHASE" in
  "Change Management"|ChangeManagement)
    ALLOWED="status.md|review_|cr/" ;;
  Proposal)
    ALLOWED="status.md|proposal.md|review_|cr/" ;;
  Requirements)
    # 允许 proposal.md：覆盖性检查（R5）可能需要回写 Non-goals
    ALLOWED="status.md|requirements.md|proposal.md|review_|cr/" ;;
  *) exit 0 ;;
esac

MATCH=false
for pattern in $(echo "$ALLOWED" | tr '|' ' '); do
  echo "$FILE_PATH" | grep -q "$pattern" && { MATCH=true; break; }
done

if [ "$MATCH" = false ]; then
  BASENAME=$(basename "$FILE_PATH")
  echo "❌ 当前阶段 $PHASE，不允许创建/修改 $BASENAME" >&2
  echo "   本阶段允许的文件：${ALLOWED//|/, }" >&2
  exit 2
fi
exit 0
