#!/bin/bash
# aicoding-hooks-managed
# Warning 6: 文档阶段出现代码文件变更
[ -f "$STATUS_FILE" ] || exit 0
PHASE=$(aicoding_yaml_value "_phase")
[ -z "$PHASE" ] && exit 0
case "$PHASE" in
  Proposal|Requirements|Design|Planning)
    CODE_FILES=$(echo "$CHANGED" | grep -vE '\.(md|txt|yaml|yml|json)$' || true)
    CODE_FILES=$(echo "$CODE_FILES" | head -5)
    if [ -n "$CODE_FILES" ]; then
      warn "当前阶段为 $PHASE，但检测到代码文件变更："
      echo "$CODE_FILES" | sed 's/^/     /'
      warn "请确认是否应先完成文档阶段"
    fi ;;
esac
