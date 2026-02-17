#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 5: 产出物结构校验（PostToolUse）
# 检查 Write 写入的文档是否包含必填章节

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/../lib/common.sh"

aicoding_parse_cc_input
[ -z "$CC_FILE_PATH" ] && exit 0
[ ! -f "$CC_FILE_PATH" ] && exit 0

BASENAME=$(basename "$CC_FILE_PATH")
MISSING=""

check_section() {
  grep -qF "$1" "$CC_FILE_PATH" || MISSING="${MISSING}\n  - $1"
}

check_section_regex() {
  grep -qE "$1" "$CC_FILE_PATH" || MISSING="${MISSING}\n  - $2"
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
    check_section "## 1."
    check_section "## 2."
    check_section "## 3."
    check_section "## 4."
    check_section "## 4A."
    check_section "## 7."
    check_section_regex 'Given .+ When .+ Then ' "GWT 格式验收标准（Given...When...Then...）"
    check_section_regex 'GWT-REQ-C?[0-9]+-[0-9]+' "GWT-ID 格式验收标准（如 GWT-REQ-001-01）"
    ;;
  CR-*.md)
    check_section "## 1. 变更意图"
    check_section "## 2. 变更点"
    check_section "## 3. 影响面"
    check_section "## 6. 验收与验证"
    check_section_regex '\[(✓|x|X)\](是|否)' "§3 影响面未勾选（所有行仍为模板默认状态）"
    check_section_regex 'Given .+ When .+ Then ' "§6 缺少 GWT 验收标准"
    ;;
  *) exit 0 ;;
esac

if [ -n "$MISSING" ]; then
  ESCAPED=$(echo -e "$MISSING" | sed 's/"/\\"/g' | tr '\n' ' ')
  aicoding_block "${BASENAME} 缺少以下必要内容：${ESCAPED}请补充完整。"
fi

exit 0
