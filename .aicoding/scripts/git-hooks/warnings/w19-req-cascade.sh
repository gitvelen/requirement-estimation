#!/bin/bash
# aicoding-hooks-managed
# Warning 19: 需求变更级联告警
echo "$CHANGED" | grep -q 'requirements\.md$' || exit 0
[ -n "$VERSION_DIR" ] || exit 0

CURRENT_HASH=$(grep -oE 'GWT-REQ-C?[0-9]+-[0-9]+:.*' "${VERSION_DIR}requirements.md" 2>/dev/null | LC_ALL=C sort | git hash-object --stdin 2>/dev/null)
[ -z "$CURRENT_HASH" ] && exit 0

for doc in review_implementation review_testing review_planning review_design test_report plan; do
  DOC_FILE="${VERSION_DIR}${doc}.md"
  [ ! -f "$DOC_FILE" ] && continue
  SAVED_HASH=$(aicoding_summary_value_from_file "$DOC_FILE" "REQ_BASELINE_HASH")
  [ -z "$SAVED_HASH" ] && continue
  if [ "$SAVED_HASH" != "$CURRENT_HASH" ]; then
    warn "W19: requirements.md 已变更，${doc}.md 的 REQ_BASELINE_HASH 已过期（saved=${SAVED_HASH}, current=${CURRENT_HASH}），建议重新审查/同步文档"
  fi
done
