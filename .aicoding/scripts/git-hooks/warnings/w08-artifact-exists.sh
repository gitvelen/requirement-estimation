#!/bin/bash
# aicoding-hooks-managed
# Warning 8: 阶段产出文件存在性
[ -f "$STATUS_FILE" ] || exit 0
W8_PHASE=$(aicoding_yaml_value "_phase")
[ -z "$W8_PHASE" ] && exit 0
IS_MINOR=$(grep -c '\[Minor\]' "$STATUS_FILE" || true)
check_exists() {
  [ ! -f "${VERSION_DIR}$1" ] && warn "当前阶段 $W8_PHASE，但 $1 不存在"
}
case "$W8_PHASE" in
  Requirements)
    [ "$IS_MINOR" -eq 0 ] && check_exists "proposal.md" ;;
  Design)
    check_exists "requirements.md" ;;
  Planning)
    check_exists "design.md" ;;
  Implementation)
    check_exists "plan.md" ;;
  Testing)
    ;; # test_report.md 本阶段产出，允许后补
  Deployment)
    check_exists "test_report.md" ;;
esac
