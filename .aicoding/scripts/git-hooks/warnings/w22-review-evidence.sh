#!/bin/bash
# aicoding-hooks-managed
# Warning 22: review 证据列非空（准备交付且 REVIEW_RESULT=pass 时触发）
# minor 模板为 4 列：GWT-ID | RESULT | EVIDENCE_TYPE | EVIDENCE
# major 模板为 6 列：GWT-ID | REQ-ID | 判定 | 备注 | 证据类型 | 证据
[ -f "$STATUS_FILE" ] || exit 0
W22_PHASE=$(aicoding_yaml_value "_phase")
W22_RUN_STATUS=$(aicoding_yaml_value "_run_status")
W22_CHANGE_STATUS=$(aicoding_yaml_value "_change_status")
W22_CHANGE_LEVEL=$(aicoding_yaml_value "_change_level")

case "$W22_PHASE" in
  Testing|Deployment) ;;
  *) exit 0 ;;
esac
[ "$W22_RUN_STATUS" = "wait_confirm" ] || [ "$W22_CHANGE_STATUS" = "done" ] || exit 0
[ -n "$W22_CHANGE_LEVEL" ] || W22_CHANGE_LEVEL="major"

if [ "$W22_CHANGE_LEVEL" = "minor" ]; then
  REVIEW_DOCS="review_minor"
else
  REVIEW_DOCS="review_implementation review_testing"
fi

for doc in $REVIEW_DOCS; do
  f="${VERSION_DIR}${doc}.md"
  [ -f "$f" ] || continue

  RESULT=$(aicoding_summary_value_from_file "$f" "REVIEW_RESULT")
  [ "$RESULT" = "pass" ] || continue

  TABLE_ROWS=$(aicoding_last_gwt_table_rows < "$f")
  [ -n "$TABLE_ROWS" ] || continue

  # 检测表头列数以适配 minor(4列) vs major(6列)
  HEADER_LINE=$(grep -E '^\|[[:space:]]*GWT-ID[[:space:]]*\|' "$f" | tail -1 || true)
  COL_COUNT=$(echo "$HEADER_LINE" | awk -F'|' '{print NF - 2}')

  if [ "$COL_COUNT" -le 4 ]; then
    # minor 4列: | GWT-ID | RESULT | EVIDENCE_TYPE | EVIDENCE |
    EVID_TYPE_COL=3
    EVID_COL=4
  else
    # major 6列: | GWT-ID | REQ-ID | 判定 | 备注 | 证据类型 | 证据 |
    EVID_TYPE_COL=5
    EVID_COL=6
  fi

  MISSING_EVID=$(echo "$TABLE_ROWS" | awk -F'|' -v etc="$EVID_TYPE_COL" -v ec="$EVID_COL" '
    function trim(s){ gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
    $0 ~ /GWT-REQ-/ {
      gwt=trim($2)
      evid_type=trim($(etc+1))
      evid=trim($(ec+1))
      if (evid_type=="" || evid_type=="..." || evid_type ~ /^<[^>]+>$/ ||
          evid=="" || evid=="..." || evid ~ /^<[^>]+>$/) {
        print gwt
      }
    }
  ' | LC_ALL=C sort -u)

  if [ -n "$MISSING_EVID" ]; then
    warn "W22: ${doc}.md REVIEW_RESULT=pass，但以下 GWT 行证据字段为空/占位（建议补齐证据类型与可复现证据）："
    echo "$MISSING_EVID" | head -20 | sed 's/^/     - /'
  fi
done
