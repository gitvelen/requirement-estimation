#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 7: 阶段入口提示兼容 shim
# 入口必读清单改为 SessionStart 注入提示，不再在写入期维护读取状态。

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/../lib/common.sh"
aicoding_parse_cc_input
[ -z "$CC_FILE_PATH" ] && exit 0

aicoding_detect_version_dir "$CC_FILE_PATH" || exit 0
aicoding_get_phase || exit 0
aicoding_phase_entry_required "$AICODING_PHASE" "$AICODING_VERSION_DIR" >/dev/null 2>&1 || true
exit 0
