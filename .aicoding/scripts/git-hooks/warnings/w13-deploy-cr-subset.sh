#!/bin/bash
# aicoding-hooks-managed
# Warning 13: 部署阶段 CR 子集验证
[ -f "$STATUS_FILE" ] || exit 0
W13_PHASE=$(aicoding_yaml_value "_phase")
[ "$W13_PHASE" = "Deployment" ] || exit 0
W13_BASELINE=$(aicoding_yaml_value "_baseline")
[ -z "$W13_BASELINE" ] && exit 0
W13_ACTIVE_CRS=$(aicoding_active_crs "$STATUS_FILE")
[ -z "$W13_ACTIVE_CRS" ] && exit 0
COMMITS=$(git log "${W13_BASELINE}..HEAD" --format=%B 2>/dev/null)
for cr_id in $W13_ACTIVE_CRS; do
  echo "$COMMITS" | grep -q "$cr_id" || \
    warn "Active CR $cr_id 未出现在 ${W13_BASELINE}..HEAD 的 commit message 中"
done
