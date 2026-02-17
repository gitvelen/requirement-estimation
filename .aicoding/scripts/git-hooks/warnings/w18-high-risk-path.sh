#!/bin/bash
# aicoding-hooks-managed
# Warning 18: 高风险变更 CR 声明检查
HIGH_RISK_PATTERNS="db/migrations/*|db/schema*|*/migration*:schema/migration;auth/*|*/permission*|*/rbac*:auth/permission;api/*|*/swagger*|*/openapi*|*.proto:API contract;infra/*|k8s/*|terraform/*:infrastructure"

CHANGED_FILES=$(echo "$CHANGED" | grep -vE '\.(md|txt)$' || true)
[ -n "$CHANGED_FILES" ] && [ -f "$STATUS_FILE" ] || exit 0

HIGH_RISK=""
IFS=';' read -ra PATTERN_GROUPS <<< "$HIGH_RISK_PATTERNS"
for f in $CHANGED_FILES; do
  for group in "${PATTERN_GROUPS[@]}"; do
    patterns="${group%%:*}"
    label="${group##*:}"
    IFS='|' read -ra pats <<< "$patterns"
    for pat in "${pats[@]}"; do
      case "$f" in
        $pat) HIGH_RISK="${HIGH_RISK}\n  $f ($label)"; break 2 ;;
      esac
    done
  done
done

[ -n "$HIGH_RISK" ] || exit 0

ACTIVE_CRS=$(aicoding_active_crs "$STATUS_FILE")
if [ -z "$ACTIVE_CRS" ]; then
  warn "W18: 检测到高风险路径变更，但无 Active CR："
  echo -e "$HIGH_RISK" | head -5
  warn "W18: 建议创建 CR 并在 §3.4 勾选对应高风险项"
else
  HAS_ANY_FLAG=false
  for cr_id in $ACTIVE_CRS; do
    CR_FILE=$(find "${VERSION_DIR}cr/" -name "${cr_id}*.md" 2>/dev/null | head -1)
    [ -z "$CR_FILE" ] && continue
    awk '
      /^### 3\.4/{in_section=1; next}
      in_section && /^### /{exit}
      in_section && /^## /{exit}
      in_section && /^- \[[xX✓]\]/{print 1; exit}
    ' "$CR_FILE" | grep -q 1 && { HAS_ANY_FLAG=true; break; }
  done
  if [ "$HAS_ANY_FLAG" = false ]; then
    warn "W18: 检测到高风险路径变更，但 Active CR 的 §3.4 未勾选任何高风险项："
    echo -e "$HIGH_RISK" | head -5
  fi
fi
