#!/bin/bash
# aicoding-hooks-managed
# Warning 11: 文档变更日志同步
for doc_name in requirements.md design.md plan.md; do
  echo "$CHANGED" | grep -q "$doc_name" || continue
  doc_path="${VERSION_DIR}${doc_name}"
  [ ! -f "$doc_path" ] && continue
  if ! grep -qE '(变更记录|版本|修订|Changelog)' "$doc_path"; then
    warn "$doc_name 被修改但未找到变更记录章节"
  fi
done
