#!/bin/bash
# aicoding-hooks-managed
# Warning 17: plan.md 任务缺少验证命令（准备交付时触发）
[ -f "$STATUS_FILE" ] || exit 0
W17_PHASE=$(aicoding_yaml_value "_phase")
W17_RUN_STATUS=$(aicoding_yaml_value "_run_status")
W17_CHANGE_STATUS=$(aicoding_yaml_value "_change_status")

case "$W17_PHASE" in
  Testing|Deployment) ;;
  *) exit 0 ;;
esac
[ "$W17_RUN_STATUS" = "wait_confirm" ] || [ "$W17_CHANGE_STATUS" = "done" ] || exit 0

PLAN="${VERSION_DIR}plan.md"
[ -f "$PLAN" ] || exit 0
TASK_COUNT=$(grep -cE '^### (T[0-9]|任务)' "$PLAN" || echo 0)
[ "$TASK_COUNT" -gt 0 ] || exit 0

MISSING=$(awk '
  function flush(){
    if(task_title!="" && has_cmd==0) {
      missing++
      print "  - " task_title
    }
  }
  /^### (T[0-9]+|任务)/{
    flush()
    task_title=$0
    has_cmd=0
    in_verify=0
    next
  }
  /验证方式/ {in_verify=1}
  in_verify && /^- *命令：/{
    if(match($0, /`[^`]+`/)) {
      cmd=substr($0, RSTART+1, RLENGTH-2)
      gsub(/^[ \t]+|[ \t]+$/, "", cmd)
      if(cmd!="" && cmd!="..." && cmd !~ /^<[^>]+>$/) has_cmd=1
    }
  }
  END{
    flush()
  }
' "$PLAN")

if [ -n "$MISSING" ]; then
  warn 'W17: plan.md 存在缺少验证命令的任务（请在"验证方式"中补充可复现命令）：'
  echo "$MISSING" | head -20
fi
