#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 7: 阶段入口门禁（PreToolUse）
# 在 AI 首次写入阶段产出物时，检查是否已读取入口协议中的必读文件。

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/../lib/common.sh"
aicoding_load_config

aicoding_parse_cc_input
[ -z "$CC_FILE_PATH" ] && exit 0

# .aicoding/ 框架文件不触发
echo "$CC_FILE_PATH" | grep -q '\.aicoding/' && exit 0

# review_*.md 和 status.md 的写入不触发入口检查
BASENAME=$(basename "$CC_FILE_PATH")
case "$BASENAME" in
  review_*|status.md) exit 0 ;;
esac

aicoding_detect_version_dir "$CC_FILE_PATH" || exit 0
aicoding_get_phase || exit 0
CHANGE_LEVEL=$(aicoding_yaml_value "_change_level")
[ "$CHANGE_LEVEL" = "hotfix" ] && exit 0

# 阶段感知的路径过滤
IS_VERSIONED_DOC=false
echo "$CC_FILE_PATH" | grep -qE 'docs/v[0-9]+\.[0-9]+/' && IS_VERSIONED_DOC=true

case "$AICODING_PHASE" in
  Implementation)
    if [ "$IS_VERSIONED_DOC" = false ]; then
      echo "$CC_FILE_PATH" | grep -q 'docs/' && exit 0
    fi ;;
  Deployment)
    if [ "$IS_VERSIONED_DOC" = false ]; then
      echo "$CC_FILE_PATH" | grep -q 'docs/' || exit 0
    fi ;;
  *)
    [ "$IS_VERSIONED_DOC" = false ] && exit 0 ;;
esac

# 入口门禁已通过标记（避免每次写入都检查）
VERSION_SLUG=$(echo "$AICODING_VERSION_DIR" | tr '/' '_')
SESSION_KEY=$(aicoding_session_key)
GATE_PASSED="/tmp/aicoding-entry-passed-${AICODING_PHASE}-${VERSION_SLUG}-${SESSION_KEY}"
[ -f "$GATE_PASSED" ] && exit 0

REQUIRED_PATTERNS=$(aicoding_phase_entry_required "$AICODING_PHASE" "$AICODING_VERSION_DIR")
[ -z "$REQUIRED_PATTERNS" ] && exit 0

# 读取已记录的 Read 调用日志
READ_LOG="/tmp/aicoding-reads-${SESSION_KEY}.log"
[ ! -f "$READ_LOG" ] && READ_LOG_CONTENT="" || READ_LOG_CONTENT=$(cat "$READ_LOG")

# 检查每个必读模式是否已被读取
MISSING=""
while IFS= read -r pattern; do
  [ -z "$pattern" ] && continue
  if ! echo "$READ_LOG_CONTENT" | grep -qF "$pattern"; then
    MISSING="${MISSING}\n  - ${pattern}"
  fi
done <<< "$REQUIRED_PATTERNS"

if [ -n "$MISSING" ]; then
  WARN_MSG="CC-7 阶段入口门禁（${AICODING_PHASE}）：写入前建议先读取：$(echo -e "$MISSING" | tr '\n' ' ')"
  if [ "$AICODING_ENTRY_GATE_MODE" = "block" ]; then
    aicoding_block "${WARN_MSG}当前模式=block，已阻断。"
  fi
  echo "⚠️  [CC-7] ${WARN_MSG}" >&2
  aicoding_gate_log_warning "${WARN_MSG}"
fi

# 入口门禁通过，标记本阶段已通过
touch "$GATE_PASSED"
exit 0
