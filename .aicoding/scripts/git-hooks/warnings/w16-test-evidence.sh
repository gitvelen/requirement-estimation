#!/bin/bash
# aicoding-hooks-managed
# Warning 16: test_report.md 证据与结论完整性（准备交付时触发）
[ -f "$STATUS_FILE" ] || exit 0
W16_PHASE=$(aicoding_yaml_value "_phase")
W16_RUN_STATUS=$(aicoding_yaml_value "_run_status")
W16_CHANGE_STATUS=$(aicoding_yaml_value "_change_status")

case "$W16_PHASE" in
  Testing|Deployment) ;;
  *) exit 0 ;;
esac
[ "$W16_RUN_STATUS" = "wait_confirm" ] || [ "$W16_CHANGE_STATUS" = "done" ] || exit 0

TEST_REPORT="${VERSION_DIR}test_report.md"
if [ ! -f "$TEST_REPORT" ]; then
  warn "W16: ${TEST_REPORT} 不存在，交付前必须补齐"
  exit 0
fi

W16_FAIL=false

HAS_CMD_BLOCK=$(awk '
  /```(bash|sh)[ \t]*$/{in_block=1; next}
  in_block && /```/{in_block=0; next}
  in_block{
    line=$0
    gsub(/^[ \t-]+/, "", line)
    gsub(/[ \t]+$/, "", line)
    if(line!="" && line!="..." && line !~ /^<[^>]+>$/) {print 1; exit}
  }
' "$TEST_REPORT")

HAS_EVID_LINE=$(grep -nE '^(\*\*证据\*\*：|证据：|证据链接：|- 完整报告链接：).+' "$TEST_REPORT" 2>/dev/null \
  | grep -vF '命令输出/日志/截图链接（如适用）' \
  | grep -vE '\.\.\.|<[^>]+>' | head -1 || true)

HAS_CR_EVID=$(awk -F'|' '
  $0 ~ /^\|[ \t]*CR-[0-9]{8}-[0-9]{3}[ \t]*\|/ {
    gsub(/^[ \t]+|[ \t]+$/, "", $5);
    gsub(/^[ \t]+|[ \t]+$/, "", $6);
    if ($6 == "通过" && $5 != "" && $5 != "..." && $5 !~ /^<[^>]+>$/) {print 1; exit}
  }
' "$TEST_REPORT")

if [ -z "$HAS_CMD_BLOCK" ] && [ -z "$HAS_EVID_LINE" ] && [ -z "$HAS_CR_EVID" ]; then
  warn "W16: test_report.md 中未找到有效证据（请补充命令块/证据链接/CR验证证据表，至少满足其一）"
  W16_FAIL=true
fi
CONCLUSION=$(grep -E '^-[[:space:]]*整体结论[：:]' "$TEST_REPORT" \
  | sed 's/^-[[:space:]]*整体结论[：:][[:space:]]*//;s/[[:space:]]*$//' \
  | head -1 || true)
if [ -z "$CONCLUSION" ]; then
  warn 'W16: test_report.md 的"整体结论"为空，交付前必须填写'
  W16_FAIL=true
elif ! echo "$CONCLUSION" | grep -qE '^(通过|不通过)$'; then
  warn "W16: test_report.md 的\"整体结论\"必须为\"通过\"或\"不通过\"（当前值: ${CONCLUSION}）"
  W16_FAIL=true
elif [ "$CONCLUSION" = "不通过" ]; then
  warn 'W16: test_report.md 的整体结论为"不通过"，禁止进入确认/交付'
  W16_FAIL=true
fi
