#!/bin/bash
# aicoding-hooks-managed
# Warning 16: test_report.md 证据与结论完整性（准备交付时触发）
# minor 路径：status.md 内联 TEST-RESULT 块可替代 test_report.md（见 06-testing.md / 07-deployment.md）
[ -f "$STATUS_FILE" ] || exit 0
W16_PHASE=$(aicoding_yaml_value "_phase")
W16_RUN_STATUS=$(aicoding_yaml_value "_run_status")
W16_CHANGE_STATUS=$(aicoding_yaml_value "_change_status")
W16_CHANGE_LEVEL=$(aicoding_yaml_value "_change_level")

case "$W16_PHASE" in
  Testing|Deployment) ;;
  *) exit 0 ;;
esac
[ "$W16_RUN_STATUS" = "wait_confirm" ] || [ "$W16_CHANGE_STATUS" = "done" ] || exit 0
[ -n "$W16_CHANGE_LEVEL" ] || W16_CHANGE_LEVEL="major"

TEST_REPORT="${VERSION_DIR}test_report.md"
if [ ! -f "$TEST_REPORT" ]; then
  # minor 允许 status.md 内联 TEST-RESULT 块替代 test_report.md
  if [ "$W16_CHANGE_LEVEL" = "minor" ]; then
    if grep -q 'TEST-RESULT-BEGIN' "$STATUS_FILE" 2>/dev/null \
       && grep -q 'TEST_RESULT:' "$STATUS_FILE" 2>/dev/null; then
      exit 0
    fi
    warn "W16: minor 变更缺少测试证据（需要 test_report.md 或 status.md 内联 TEST-RESULT 块）"
  else
    warn "W16: ${TEST_REPORT} 不存在，交付前必须补齐"
  fi
  exit 0
fi

W16_FAIL=false

# 证据识别：命令块
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

# 证据识别：独立证据行
HAS_EVID_LINE=$(grep -nE '^(\*\*证据\*\*：|证据：|证据链接：|- 完整报告链接：).+' "$TEST_REPORT" 2>/dev/null \
  | grep -vF '命令输出/日志/截图链接（如适用）' \
  | grep -vE '\.\.\.|<[^>]+>' | head -1 || true)

# 证据识别：CR 验证表
HAS_CR_EVID=$(awk -F'|' '
  $0 ~ /^\|[ \t]*CR-[0-9]{8}-[0-9]{3}[ \t]*\|/ {
    gsub(/^[ \t]+|[ \t]+$/, "", $5);
    gsub(/^[ \t]+|[ \t]+$/, "", $6);
    if ($6 == "通过" && $5 != "" && $5 != "..." && $5 !~ /^<[^>]+>$/) {print 1; exit}
  }
' "$TEST_REPORT")

# 证据识别：集成/E2E 测试表格（模板主证据结构）
# 匹配 REQ-xxx 行且"结果"列包含通过标记
HAS_TABLE_EVID=$(awk -F'|' '
  $0 ~ /^\|[ \t]*REQ-[0-9]+/ {
    for (i=2; i<=NF; i++) {
      gsub(/^[ \t]+|[ \t]+$/, "", $i)
      if ($i ~ /✅|通过|PASS/) { print 1; exit }
    }
  }
' "$TEST_REPORT")

# 证据识别：GWT 覆盖矩阵（TEST-COVERAGE-MATRIX 块内的 GWT 行）
HAS_GWT_MATRIX=$(awk '
  /TEST-COVERAGE-MATRIX-BEGIN/{in_matrix=1; next}
  /TEST-COVERAGE-MATRIX-END/{in_matrix=0; next}
  in_matrix && /GWT-REQ-/ {
    split($0, cols, "|")
    for (i in cols) {
      gsub(/^[ \t]+|[ \t]+$/, "", cols[i])
      if (cols[i] ~ /✅|通过|PASS/) { print 1; exit }
    }
  }
' "$TEST_REPORT")

if [ -z "$HAS_CMD_BLOCK" ] && [ -z "$HAS_EVID_LINE" ] && [ -z "$HAS_CR_EVID" ] \
   && [ -z "$HAS_TABLE_EVID" ] && [ -z "$HAS_GWT_MATRIX" ]; then
  warn "W16: test_report.md 中未找到有效证据（请补充命令块/证据链接/CR验证表/集成测试表/GWT覆盖矩阵，至少满足其一）"
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
