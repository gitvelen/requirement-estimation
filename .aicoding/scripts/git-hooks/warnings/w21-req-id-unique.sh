#!/bin/bash
# aicoding-hooks-managed
# Warning 21: requirements.md ID 唯一性
echo "$CHANGED" | grep -q 'requirements\.md$' || exit 0
REQ_FILE="${VERSION_DIR}requirements.md"
[ -f "$REQ_FILE" ] || exit 0

REQ_DEFS=$(grep -oE '^####[[:space:]]REQ-C?[0-9]+' "$REQ_FILE" 2>/dev/null | sed 's/^####[[:space:]]*//' || true)
REQ_DUP=$(echo "$REQ_DEFS" | LC_ALL=C sort | uniq -d || true)
if [ -n "$REQ_DUP" ]; then
  warn "W21: requirements.md 存在重复 REQ 定义（ID 必须唯一）："
  echo "$REQ_DUP" | head -20 | sed 's/^/     - /'
fi

GWT_IDS=$(grep -oE 'GWT-REQ-C?[0-9]+-[0-9]+' "$REQ_FILE" 2>/dev/null || true)
GWT_DUP=$(echo "$GWT_IDS" | LC_ALL=C sort | uniq -d || true)
if [ -n "$GWT_DUP" ]; then
  warn "W21: requirements.md 存在重复 GWT-ID（外键必须唯一）："
  echo "$GWT_DUP" | head -20 | sed 's/^/     - /'
fi

if [ -n "$REQ_DEFS" ] && [ -n "$GWT_IDS" ]; then
  GWT_PREFIXES=$(echo "$GWT_IDS" | sed -E 's/^GWT-(REQ-C?[0-9]+)-.*/\1/' | LC_ALL=C sort -u)
  UNDEFINED=$(LC_ALL=C comm -23 <(echo "$GWT_PREFIXES") <(echo "$REQ_DEFS" | LC_ALL=C sort -u) || true)
  if [ -n "$UNDEFINED" ]; then
    warn "W21: requirements.md 存在引用未定义 REQ-ID 的 GWT（请补充对应 #### REQ-xxx/REQ-Cxxx 定义）："
    echo "$UNDEFINED" | head -20 | sed 's/^/     - /'
  fi
fi
