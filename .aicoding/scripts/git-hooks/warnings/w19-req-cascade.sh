#!/bin/bash
# aicoding-hooks-managed
# Warning 19: 需求变更级联告警
echo "$CHANGED" | grep -q 'requirements\.md$' || exit 0
[ -n "$VERSION_DIR" ] || exit 0

CURRENT_HASH=$(grep -oE 'GWT-REQ-C?[0-9]+-[0-9]+:.*' "${VERSION_DIR}requirements.md" 2>/dev/null | LC_ALL=C sort | git hash-object --stdin 2>/dev/null)
[ -z "$CURRENT_HASH" ] && exit 0

# 全文 hash 用于检测 prose 变更（GWT 行不变但说明文字变了）
CURRENT_FULL_HASH=$(git hash-object "${VERSION_DIR}requirements.md" 2>/dev/null)

# 上一次 commit 的两种 hash（用于判断本次变更类型）
PREV_GWT_HASH=$(git show HEAD:"${VERSION_DIR}requirements.md" 2>/dev/null | grep -oE 'GWT-REQ-C?[0-9]+-[0-9]+:.*' | LC_ALL=C sort | git hash-object --stdin 2>/dev/null)
PREV_FULL_HASH=$(git show HEAD:"${VERSION_DIR}requirements.md" 2>/dev/null | git hash-object --stdin 2>/dev/null)

# 判断变更类型
GWT_CHANGED=false
PROSE_CHANGED=false
[ "$CURRENT_HASH" != "$PREV_GWT_HASH" ] && GWT_CHANGED=true
[ "$CURRENT_FULL_HASH" != "$PREV_FULL_HASH" ] && [ "$GWT_CHANGED" = "false" ] && PROSE_CHANGED=true

for doc in review_implementation review_testing review_planning review_design test_report plan; do
  DOC_FILE="${VERSION_DIR}${doc}.md"
  [ ! -f "$DOC_FILE" ] && continue
  SAVED_HASH=$(aicoding_summary_value_from_file "$DOC_FILE" "REQ_BASELINE_HASH")
  [ -z "$SAVED_HASH" ] && continue
  if [ "$SAVED_HASH" != "$CURRENT_HASH" ]; then
    warn "W19: requirements.md GWT 定义已变更，${doc}.md 的 REQ_BASELINE_HASH 已过期（saved=${SAVED_HASH}, current=${CURRENT_HASH}），建议重新审查/同步文档"
  fi
done

if [ "$PROSE_CHANGED" = "true" ]; then
  warn "W19: requirements.md 说明文字已变更（GWT 定义行未变），请确认下游文档（design/plan/review）的描述仍与需求一致"
fi
