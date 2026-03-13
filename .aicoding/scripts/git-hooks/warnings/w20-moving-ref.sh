#!/bin/bash
# aicoding-hooks-managed
# Warning 20: CODE_BASELINE 使用移动引用风险（准备交付时触发）
[ -f "$STATUS_FILE" ] || exit 0
W20_PHASE=$(aicoding_yaml_value "_phase")
W20_RUN_STATUS=$(aicoding_yaml_value "_run_status")
W20_CHANGE_STATUS=$(aicoding_yaml_value "_change_status")
W20_CHANGE_LEVEL=$(aicoding_yaml_value "_change_level")

case "$W20_PHASE" in
  Testing|Deployment) ;;
  *) exit 0 ;;
esac
[ "$W20_RUN_STATUS" = "wait_confirm" ] || [ "$W20_CHANGE_STATUS" = "done" ] || exit 0
[ -n "$W20_CHANGE_LEVEL" ] || W20_CHANGE_LEVEL="major"

CURRENT_REF=$(aicoding_yaml_value "_current")
if [ -n "$CURRENT_REF" ] && ! aicoding_is_commit_sha "$CURRENT_REF"; then
  warn "W20: status.md 的 _current=${CURRENT_REF} 不是 commit SHA（移动引用风险）。建议改为 \`git rev-parse HEAD\` 的输出，避免基线漂移不被发现。"
fi

if [ "$W20_CHANGE_LEVEL" = "minor" ]; then
  REVIEW_DOCS="review_minor"
else
  REVIEW_DOCS="review_implementation review_testing"
fi

for doc in $REVIEW_DOCS; do
  f="${VERSION_DIR}${doc}.md"
  [ -f "$f" ] || continue
  CODE_BASELINE=$(aicoding_summary_value_from_file "$f" "CODE_BASELINE")
  RESULT=$(aicoding_summary_value_from_file "$f" "REVIEW_RESULT")
  if [ "$RESULT" = "pass" ] && [ -n "$CODE_BASELINE" ] && ! aicoding_is_commit_sha "$CODE_BASELINE"; then
    warn "W20: ${doc}.md 的 CODE_BASELINE=${CODE_BASELINE} 不是 commit SHA（移动引用风险）。建议用 commit SHA 固化审查基线。"
  fi
done
