#!/bin/bash
# aicoding-hooks-managed
# Warning 9: REQ 引用存在性
DOC_FILES=$(echo "$CHANGED" | grep -E '(plan|design)\.md$' || true)
if [ -n "$DOC_FILES" ]; then
  REQ_FILE="${VERSION_DIR}requirements.md"
  if [ ! -f "$REQ_FILE" ]; then
    warn "requirements.md 不存在，无法校验 REQ 引用"
  else
    REQ_PATTERN='REQ-C?[0-9]+'
    DEFINED=$(grep -oE "$REQ_PATTERN" "$REQ_FILE" | sort -u)
    for doc in $DOC_FILES; do
      [ ! -f "$doc" ] && continue
      REFS=$(grep -oE "$REQ_PATTERN" "$doc" | sort -u)
      for ref in $REFS; do
        echo "$DEFINED" | grep -qx "$ref" || warn "$doc 引用了 $ref，但 requirements.md 中不存在"
      done
    done
  fi
fi
