#!/bin/bash
# aicoding-hooks-managed
# Warning 26: 歧义表述扫描（语义门禁辅助）
# 来源：lessons_learned 2026-02-24 — "可选/二选一/仅提示"等表述应默认按 P1 处理
[ -f "$STATUS_FILE" ] || exit 0

PHASE=$(aicoding_yaml_value "_phase")
case "$PHASE" in
  Design|Planning|Implementation|Testing) ;;
  *) exit 0 ;;
esac

# 歧义模式（中文 + 英文）
AMBIGUOUS_PATTERN='可选|或者|二选一|仅提示|暂不|后续再|待定|待确认|待讨论|TBD|TODO|FIXME|optional|either[[:space:]]+or|to be determined|to be decided|might|maybe[[:space:]]+(we|should)|if needed'

# 扫描目标文档（按阶段选择）
SCAN_FILES=""
case "$PHASE" in
  Design)
    [ -f "${VERSION_DIR}design.md" ] && SCAN_FILES="${VERSION_DIR}design.md" ;;
  Planning)
    [ -f "${VERSION_DIR}plan.md" ] && SCAN_FILES="${VERSION_DIR}plan.md" ;;
  Implementation|Testing)
    for doc in design.md plan.md requirements.md; do
      [ -f "${VERSION_DIR}${doc}" ] && SCAN_FILES="${SCAN_FILES} ${VERSION_DIR}${doc}"
    done ;;
esac

[ -n "$SCAN_FILES" ] || exit 0

HITS=""
for f in $SCAN_FILES; do
  BASENAME=$(basename "$f")
  # 排除注释行（HTML comment）和代码块内容
  MATCHES=$(grep -nEi "$AMBIGUOUS_PATTERN" "$f" 2>/dev/null \
    | grep -v '^\s*<!--' \
    | grep -v '^\s*#.*aicoding' \
    | grep -v 'lessons_learned' \
    | head -10 || true)
  [ -n "$MATCHES" ] || continue
  HITS="${HITS}\n  ${BASENAME}:"
  while IFS= read -r line; do
    HITS="${HITS}\n    ${line}"
  done <<< "$MATCHES"
done

if [ -n "$HITS" ]; then
  warn "W26: 检测到歧义/未决表述（建议在进入下一阶段前收敛为单一口径，否则按 P1 处理）："
  echo -e "$HITS"
fi
