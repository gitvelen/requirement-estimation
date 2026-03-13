#!/bin/bash
# aicoding-hooks-managed
# Warning 8: 阶段产出文件存在性
[ -f "$STATUS_FILE" ] || exit 0
W8_PHASE=$(aicoding_yaml_value "_phase")
W8_CHANGE_LEVEL=$(aicoding_yaml_value "_change_level")
[ -z "$W8_PHASE" ] && exit 0
[ -n "$W8_CHANGE_LEVEL" ] || W8_CHANGE_LEVEL="major"
check_exists() {
  [ ! -f "${VERSION_DIR}$1" ] && warn "当前阶段 $W8_PHASE，但 $1 不存在"
}
case "$W8_PHASE" in
  Requirements)
    check_exists "proposal.md" ;;
  Design)
    check_exists "requirements.md" ;;
  Planning)
    check_exists "design.md" ;;
  Implementation)
    check_exists "plan.md" ;;
  Testing)
    ;; # test_report.md 本阶段产出，允许后补
  Deployment)
    [ "$W8_CHANGE_LEVEL" = "minor" ] || check_exists "test_report.md" ;;
esac
