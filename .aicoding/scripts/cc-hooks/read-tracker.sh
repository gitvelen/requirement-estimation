#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 7b: Read 追踪器（PostToolUse on Read）
# 记录 AI 的 Read 调用到临时日志，供 CC-7 入口门禁检查。

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/../lib/common.sh"

aicoding_parse_cc_input
[ -z "$CC_FILE_PATH" ] && exit 0

SESSION_KEY=$(aicoding_session_key)
READ_LOG="/tmp/aicoding-reads-${SESSION_KEY}.log"
echo "$CC_FILE_PATH" >> "$READ_LOG"

exit 0
