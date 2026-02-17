#!/bin/bash
# aicoding-hooks-managed
# Warning 10: 基线版本可达性
[ -f "$STATUS_FILE" ] || exit 0
BASELINE=$(aicoding_yaml_value "_baseline")
if [ -n "$BASELINE" ]; then
  git rev-parse --verify "${BASELINE}^{commit}" 2>/dev/null || \
    warn "基线版本 $BASELINE 不可达（git rev-parse 失败）"
fi
