#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 5: 产出物结构校验（PostToolUse）
# 检查 Write 写入的文档是否包含必填章节
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // empty')
[ -z "$FILE_PATH" ] && exit 0
[ ! -f "$FILE_PATH" ] && exit 0

BASENAME=$(basename "$FILE_PATH")
MISSING=""

check_section() {
  grep -q "$1" "$FILE_PATH" || MISSING="${MISSING}\n  - $1"
}

case "$BASENAME" in
  proposal.md)
    check_section "## 一句话总结"
    check_section "## 背景与现状"
    check_section "## 目标与成功指标"
    check_section "## 目标用户"
    check_section "## 方案概述"
    check_section "## 范围界定"
    check_section "## 风险与依赖"
    check_section "## 变更记录"
    ;;
  requirements.md)
    check_section "## 1\."   # 概述
    check_section "## 2\."   # 业务场景
    check_section "## 3\."   # 功能性需求
    check_section "## 4\."   # 非功能需求
    check_section "## 7\."   # 变更记录
    # 额外：是否有 GWT 格式验收标准
    if ! grep -qE 'Given .+ When .+ Then ' "$FILE_PATH"; then
      MISSING="${MISSING}\n  - GWT 格式验收标准（Given...When...Then...）"
    fi
    ;;
  CR-*.md)
    check_section "## 1\. 变更意图"
    check_section "## 2\. 变更点"
    check_section "## 3\. 影响面"
    check_section "## 6\. 验收与验证"
    # 额外：影响面是否有勾选（兼容 [✓] 和 [x]/[X] 两种勾选风格）
    if ! grep -qE '\[(✓|x|X)\](是|否)' "$FILE_PATH"; then
      MISSING="${MISSING}\n  - §3 影响面未勾选（所有行仍为模板默认状态）"
    fi
    # 额外：GWT
    if ! grep -qE 'Given .+ When .+ Then ' "$FILE_PATH"; then
      MISSING="${MISSING}\n  - §6 缺少 GWT 验收标准"
    fi
    ;;
  *) exit 0 ;;
esac

if [ -n "$MISSING" ]; then
  ESCAPED=$(echo -e "$MISSING" | sed 's/"/\\"/g' | tr '\n' ' ')
  cat <<EOF
{
  "decision": "block",
  "reason": "${BASENAME} 缺少以下必要内容：${ESCAPED}请补充完整。"
}
EOF
fi

exit 0
