#!/bin/bash
# aicoding-hooks-managed
# Warning 28: 高风险项前移收敛检查
# 来源：lessons_learned 2026-02-24 — 兼容/回滚/权限/REQ-C/迁移等高风险项不得留到后续阶段
[ -f "$STATUS_FILE" ] || exit 0

PHASE=$(aicoding_yaml_value "_phase")
case "$PHASE" in
  Design|Planning) ;;
  *) exit 0 ;;
esac

# 从配置读取高风险关键词（默认值兜底）
HR_PATTERNS="${AICODING_HIGH_RISK_REVIEW_PATTERNS:-兼容,回滚,权限,REQ-C,deprecated,confirm,迁移,越权,鉴权,安全}"

# 构建 grep 模式
GREP_PATTERN=$(echo "$HR_PATTERNS" | tr ',' '|')

# 确定扫描文档
SCAN_FILE=""
case "$PHASE" in
  Design)
    [ -f "${VERSION_DIR}design.md" ] && SCAN_FILE="${VERSION_DIR}design.md" ;;
  Planning)
    [ -f "${VERSION_DIR}plan.md" ] && SCAN_FILE="${VERSION_DIR}plan.md" ;;
esac
[ -n "$SCAN_FILE" ] || exit 0

# 扫描高风险关键词出现位置
HITS=$(grep -nEi "$GREP_PATTERN" "$SCAN_FILE" 2>/dev/null \
  | grep -v '^\s*<!--' \
  | grep -v 'lessons_learned' \
  | head -15 || true)
[ -n "$HITS" ] || exit 0

HIT_COUNT=$(echo "$HITS" | wc -l | tr -d ' ')

# 检查对应 review 文件是否存在且有充分证据
PHASE_LOWER=$(echo "$PHASE" | tr '[:upper:]' '[:lower:]')
REVIEW_FILE="${VERSION_DIR}review_${PHASE_LOWER}.md"

if [ ! -f "$REVIEW_FILE" ]; then
  warn "W28: ${SCAN_FILE##*/} 包含 ${HIT_COUNT} 处高风险关键词，但尚无 review 报告（高风险项必须在本阶段收敛）："
  echo "$HITS" | head -5 | sed 's/^/     /'
  exit 0
fi

# 检查 review 中是否提及这些高风险关键词（至少有覆盖意识）
REVIEW_COVERAGE=$(grep -ciE "$GREP_PATTERN" "$REVIEW_FILE" 2>/dev/null || echo 0)
if [ "$REVIEW_COVERAGE" -lt 1 ]; then
  warn "W28: ${SCAN_FILE##*/} 包含 ${HIT_COUNT} 处高风险关键词，但 ${REVIEW_FILE##*/} 未提及任何高风险项（建议在审查中重点覆盖）："
  echo "$HITS" | head -5 | sed 's/^/     /'
fi
