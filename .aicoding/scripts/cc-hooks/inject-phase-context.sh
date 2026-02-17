#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 4: 会话上下文注入（SessionStart）
# 在新会话开始时注入当前项目状态和阶段入口必读清单到 AI 上下文

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/../lib/common.sh"
aicoding_load_config

# 清理过期临时文件（>2小时）
find /tmp -name 'aicoding-*' -mmin +120 -delete 2>/dev/null || true

PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(aicoding_repo_root)}"
if [ -z "${CLAUDE_PROJECT_DIR:-}" ]; then
  CLAUDE_PROJECT_DIR="$PROJECT_ROOT"
fi

AICODING_VERSION_DIR=$(aicoding_latest_version_dir "$PROJECT_ROOT" || true)
if [ -z "$AICODING_VERSION_DIR" ]; then
  echo '{"hookSpecificOutput":{"additionalContext":"[项目状态] 当前无活跃版本目录，无 status.md。"}}'
  exit 0
fi

AICODING_STATUS_FILE="${PROJECT_ROOT}/${AICODING_VERSION_DIR}status.md"
[ -f "$AICODING_STATUS_FILE" ] || {
  echo '{"hookSpecificOutput":{"additionalContext":"[项目状态] 当前无可读取 status.md。"}}'
  exit 0
}

aicoding_get_phase || true
RUN_STATUS=$(aicoding_yaml_value "_run_status")

# 收集 Active CR
ACTIVE_CRS=$(aicoding_active_crs | tr '\n' ',' | sed 's/,$//')

CONTEXT="[项目状态] 版本目录: ${AICODING_VERSION_DIR} | 当前阶段: ${AICODING_PHASE} | 运行状态: ${RUN_STATUS}"
[ -n "$ACTIVE_CRS" ] && CONTEXT="${CONTEXT} | Active CRs: ${ACTIVE_CRS}"

# 人工介入期提示
if aicoding_is_manual_phase; then
  CONTEXT="${CONTEXT} | 当前处于人工介入期，阶段推进需用户明确确认。"
fi

# 阶段入口必读清单（单源）
ENTRY_REQUIRED=$(aicoding_phase_entry_required "$AICODING_PHASE" "$AICODING_VERSION_DIR" | tr '\n' ',' | sed 's/,$//')
[ -n "$ENTRY_REQUIRED" ] && CONTEXT="${CONTEXT} | [入口必读] ${ENTRY_REQUIRED}"
CONTEXT="${CONTEXT} | [读取建议] 模板文件优先阅读到 SKELETON-END 标记处。"

echo "{\"hookSpecificOutput\":{\"additionalContext\":\"${CONTEXT}\"}}"
exit 0
