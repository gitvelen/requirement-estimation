#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 3: 文档作用域控制（PreToolUse）
# 阻止 AI 在当前阶段创建/修改不属于该阶段的产出物

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/../lib/common.sh"

aicoding_parse_cc_input
[ -z "$CC_FILE_PATH" ] && exit 0

# 只关心 docs/vX.Y/ 下的文件
echo "$CC_FILE_PATH" | grep -qE 'docs/v[0-9]+\.[0-9]+/' || exit 0

aicoding_detect_version_dir "$CC_FILE_PATH" || exit 0
aicoding_get_phase || exit 0

# 各阶段允许的产出文件白名单
# review_*.md 在任何阶段都允许（审查可随时发起）
# status.md 在任何阶段都允许（状态更新）
case "$AICODING_PHASE" in
  "Change Management"|ChangeManagement)
    ALLOWED="status.md|review_|cr/" ;;
  Proposal)
    ALLOWED="status.md|proposal.md|review_|cr/" ;;
  Requirements)
    ALLOWED="status.md|requirements.md|proposal.md|review_|cr/" ;;
  Design)
    ALLOWED="status.md|design.md|review_|cr/" ;;
  Planning)
    ALLOWED="status.md|plan.md|review_|cr/" ;;
  Implementation)
    ALLOWED="status.md|review_|spotcheck_|cr/|plan.md|tasks/|design.md|requirements.md" ;;
  Testing)
    ALLOWED="status.md|test_report.md|review_|spotcheck_|cr/|design.md|requirements.md" ;;
  Deployment)
    ALLOWED="status.md|deployment.md|test_report.md|review_|spotcheck_|cr/" ;;
  *) exit 0 ;;
esac

MATCH=false
DOC_BASENAME=$(basename "$CC_FILE_PATH")
DOC_DIRNAME=$(dirname "$CC_FILE_PATH")
for pattern in $(echo "$ALLOWED" | tr '|' ' '); do
  # 目录模式（如 cr/）匹配路径，文件模式匹配 basename
  case "$pattern" in
    */) echo "$CC_FILE_PATH" | grep -q "/${pattern}" && { MATCH=true; break; } ;;
    *)  [ "$DOC_BASENAME" = "$pattern" ] && { MATCH=true; break; }
        echo "$DOC_BASENAME" | grep -q "^${pattern}" && { MATCH=true; break; } ;;
  esac
done

if [ "$MATCH" = false ]; then
  BASENAME=$(basename "$CC_FILE_PATH")
  aicoding_block "当前阶段 $AICODING_PHASE，不允许创建/修改 $BASENAME。本阶段允许的文件：${ALLOWED//|/, }"
fi
exit 0
