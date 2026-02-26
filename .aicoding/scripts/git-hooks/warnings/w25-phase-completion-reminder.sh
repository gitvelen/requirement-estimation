#!/bin/bash
# W25: 手动期阶段完成提醒
# 当手动期阶段的核心产出物已存在，但 _run_status 未切换为 wait_confirm 时发出警告
# 防止 AI 在完成当前阶段后无缝继续下一阶段的工作

[ -z "$VERSION_DIR" ] && return 0
[ ! -f "$STATUS_FILE" ] && return 0

W25_PHASE=$(aicoding_yaml_value "_phase" "$STATUS_FILE")
W25_RUN_STATUS=$(aicoding_yaml_value "_run_status" "$STATUS_FILE")

# 仅手动期阶段触发
case "$W25_PHASE" in
  ChangeManagement|Proposal|Requirements) ;;
  *) return 0 ;;
esac

# 已经是 wait_confirm 则无需提醒
[ "$W25_RUN_STATUS" = "wait_confirm" ] && return 0

W25_COMPLETE=false
case "$W25_PHASE" in
  ChangeManagement)
    [ -f "${VERSION_DIR}review_change_management.md" ] && W25_COMPLETE=true ;;
  Proposal)
    [ -f "${VERSION_DIR}proposal.md" ] && [ -f "${VERSION_DIR}review_proposal.md" ] && W25_COMPLETE=true ;;
  Requirements)
    [ -f "${VERSION_DIR}requirements.md" ] && [ -f "${VERSION_DIR}review_requirements.md" ] && W25_COMPLETE=true ;;
esac

if [ "$W25_COMPLETE" = true ]; then
  warn "W25: 当前阶段 ${W25_PHASE} 的核心产出物已存在，但 _run_status=${W25_RUN_STATUS}（非 wait_confirm）。建议设置 _run_status: wait_confirm 并等待用户确认阶段推进。"
fi
