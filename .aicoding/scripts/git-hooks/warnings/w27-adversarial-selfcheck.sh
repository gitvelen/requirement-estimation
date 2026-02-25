#!/bin/bash
# aicoding-hooks-managed
# Warning 27: 对抗性自检缺失检查
# 来源：lessons_learned 2026-02-24 — 自审偏差缓解，review 报告必须包含对抗性自检清单
[ -f "$STATUS_FILE" ] || exit 0

PHASE=$(aicoding_yaml_value "_phase")
case "$PHASE" in
  Design|Planning|Implementation|Testing) ;;
  *) exit 0 ;;
esac

# 检查当前阶段的 review 文件
PHASE_LOWER=$(echo "$PHASE" | tr '[:upper:]' '[:lower:]')
REVIEW_FILE="${VERSION_DIR}review_${PHASE_LOWER}.md"
[ -f "$REVIEW_FILE" ] || exit 0

# 检查 REVIEW_RESULT 是否为 pass
RESULT=$(aicoding_summary_value_from_file "$REVIEW_FILE" "REVIEW_RESULT")
[ "$RESULT" = "pass" ] || exit 0

# 检查是否包含对抗性自检 section
if ! grep -q '对抗性自检' "$REVIEW_FILE" 2>/dev/null; then
  warn "W27: ${REVIEW_FILE##*/} REVIEW_RESULT=pass，但缺少"对抗性自检"章节（自审时必填，用于缓解自审偏差）"
  exit 0
fi

# 检查清单项是否至少有一项被勾选
CHECKED_COUNT=$(grep -cE '^\s*-\s*\[[xX✓]\]' "$REVIEW_FILE" 2>/dev/null || echo 0)
# 从对抗性自检 section 提取勾选项
SELFCHECK_SECTION=$(awk '/对抗性自检/{found=1; next} found && /^### /{exit} found && /^## /{exit} found{print}' "$REVIEW_FILE")
SELFCHECK_CHECKED=$(echo "$SELFCHECK_SECTION" | grep -cE '^\s*-\s*\[[xX✓]\]' 2>/dev/null || echo 0)
SELFCHECK_TOTAL=$(echo "$SELFCHECK_SECTION" | grep -cE '^\s*-\s*\[' 2>/dev/null || echo 0)

if [ "$SELFCHECK_TOTAL" -gt 0 ] && [ "$SELFCHECK_CHECKED" -eq 0 ]; then
  warn "W27: ${REVIEW_FILE##*/} 对抗性自检清单共 ${SELFCHECK_TOTAL} 项，但无一勾选（建议逐项确认后勾选）"
fi
