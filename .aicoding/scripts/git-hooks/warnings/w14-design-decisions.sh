#!/bin/bash
# aicoding-hooks-managed
# Warning 14: 设计文档决策记录非空
echo "$CHANGED" | grep -q 'design\.md$' || exit 0
DESIGN="${VERSION_DIR}design.md"
[ -f "$DESIGN" ] || exit 0
HAS_RECORD=$(awk -F'|' '
  /^### 技术决策/{found=1; next}
  found && /^#/{found=0}
  found && /\|/ && !/---/ && !/编号.*决策项/ && !/决策项.*用户选择/ {
    gsub(/^[ \t]+|[ \t]+$/, "", $4);
    if ($4 != "" && $4 !~ /^[ \t]*$/) { print; exit }
  }
' "$DESIGN")
[ -z "$HAS_RECORD" ] && warn "design.md 的技术决策表中'用户选择'列全部为空"
