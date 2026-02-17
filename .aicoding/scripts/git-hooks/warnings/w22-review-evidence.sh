#!/bin/bash
# aicoding-hooks-managed
# Warning 22: review 证据列非空（准备交付且 REVIEW_RESULT=pass 时触发）
[ -f "$STATUS_FILE" ] || exit 0
W22_RUN_STATUS=$(aicoding_yaml_value "_run_status")
W22_CHANGE_STATUS=$(aicoding_yaml_value "_change_status")
[ "$W22_RUN_STATUS" = "wait_confirm" ] || [ "$W22_CHANGE_STATUS" = "done" ] || exit 0

for doc in review_implementation review_testing; do
  f="${VERSION_DIR}${doc}.md"
  [ -f "$f" ] || continue

  RESULT=$(aicoding_summary_value_from_file "$f" "REVIEW_RESULT")
  [ "$RESULT" = "pass" ] || continue

  TABLE_ROWS=$(aicoding_last_gwt_table_rows < "$f")
  [ -n "$TABLE_ROWS" ] || continue

  MISSING_EVID=$(echo "$TABLE_ROWS" | awk -F'|' '
    function trim(s){ gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
    $0 ~ /GWT-REQ-/ {
      gwt=trim($2)
      evid_type=trim($5)
      evid=trim($6)
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
