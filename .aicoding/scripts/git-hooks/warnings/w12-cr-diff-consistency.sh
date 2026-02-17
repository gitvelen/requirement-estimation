#!/bin/bash
# aicoding-hooks-managed
# Warning 12: CR 影响面与 diff 一致性
[ -f "$STATUS_FILE" ] || exit 0
W12_ACTIVE_CRS=$(aicoding_active_crs "$STATUS_FILE")
[ -z "$W12_ACTIVE_CRS" ] && exit 0
CODE_CHANGED=$(echo "$CHANGED" | grep -vE '\.(md|txt|yaml|yml|json)$' || true)
[ -z "$CODE_CHANGED" ] && exit 0

ALL_DECLARED=""
for cr_id in $W12_ACTIVE_CRS; do
  CR_FILE=$(find "${VERSION_DIR}cr/" -name "${cr_id}*.md" 2>/dev/null | head -1)
  if [ -z "$CR_FILE" ]; then
    warn "Active CR $cr_id 的 CR 文件不存在"; continue
  fi
  DECLARED=$(awk '/### 3\.3/{found=1;next} /^#/{found=0} found && /\|/' "$CR_FILE" \
    | awk -F'|' '{gsub(/^[ \t]+|[ \t]+$/,"",$2);
      if($2!="" && $2!~/^-+$/ && $2!~/影响模块/ && $2!~/影响文件/) print $2}')
  if [ -z "$DECLARED" ]; then
    warn "$cr_id: §3.3 代码影响为空，但本次有代码变更"
  else
    ALL_DECLARED="${ALL_DECLARED}
${DECLARED}"
  fi
done
if [ -n "$ALL_DECLARED" ]; then
  for changed_file in $CODE_CHANGED; do
    COVERED=false
    while IFS= read -r decl; do
      [ -z "$decl" ] && continue
      echo "$changed_file" | grep -Fq "$decl" && { COVERED=true; break; }
    done <<< "$ALL_DECLARED"
    [ "$COVERED" = false ] && \
      warn "$changed_file 不在任何 Active CR 的 §3.3 声明范围内"
  done
fi
