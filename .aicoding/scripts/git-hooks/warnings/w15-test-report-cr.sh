#!/bin/bash
# aicoding-hooks-managed
# Warning 15: 测试报告覆盖 CR 验收标准
echo "$CHANGED" | grep -q 'test_report\.md$' || exit 0
[ -f "$STATUS_FILE" ] || exit 0
W15_ACTIVE_CRS=$(aicoding_active_crs "$STATUS_FILE")
[ -z "$W15_ACTIVE_CRS" ] && exit 0
TEST_REPORT="${VERSION_DIR}test_report.md"
[ -f "$TEST_REPORT" ] || { warn "test_report.md 不存在"; exit 0; }
for cr_id in $W15_ACTIVE_CRS; do
  CR_FILE=$(find "${VERSION_DIR}cr/" -name "${cr_id}*.md" 2>/dev/null | head -1)
  [ -z "$CR_FILE" ] && continue
  GWT_COUNT=$(grep -cE '^- Given ' "$CR_FILE" 2>/dev/null || echo 0)
  [ "$GWT_COUNT" -eq 0 ] && continue
  grep -q "$cr_id" "$TEST_REPORT" || \
    warn "$cr_id 有 $GWT_COUNT 条 GWT 验收标准，但 test_report.md 中未引用该 CR"
done
