#!/bin/bash
# aicoding-hooks-managed
# CC PreToolUse 统一入口：合并 phase-gate / doc-scope-guard / phase-entry-gate / phase-exit-gate / review-append-guard
# 将 5 个独立进程合并为 1 个，减少每次 Write/Edit 的进程开销

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=../lib/review_gate_common.sh
source "${SCRIPT_DIR}/../lib/review_gate_common.sh"
source "${SCRIPT_DIR}/../lib/common.sh"

aicoding_parse_cc_input
[ -z "$CC_FILE_PATH" ] && exit 0

# ============================================================
# Gate 1: review 文件追加保护（原 review-append-guard.sh）
# Write: 检查轮次数不减少
# Edit: 禁止注入新的 REVIEW-SUMMARY 块（防止覆盖已有摘要）
# ============================================================
if echo "$CC_FILE_PATH" | grep -qE 'review_[a-z_]+\.md$'; then
  if [ "$CC_TOOL_NAME" = "Write" ]; then
    if [ -f "$CC_FILE_PATH" ]; then
      EXISTING_ROUNDS=$(grep -c '## [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}.*第.*轮' "$CC_FILE_PATH" 2>/dev/null || echo 0)
      if [ "$EXISTING_ROUNDS" -gt 0 ]; then
        NEW_ROUNDS=$(echo "$CC_CONTENT" | grep -c '## [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}.*第.*轮' 2>/dev/null || echo 0)
        if [ "$NEW_ROUNDS" -lt "$EXISTING_ROUNDS" ]; then
          aicoding_block "review 文件已有 ${EXISTING_ROUNDS} 轮审查记录，新内容只有 ${NEW_ROUNDS} 轮。审查记录必须追加，不得覆盖。请使用 Edit 工具在文件末尾追加新一轮审查。"
        fi
      fi
    fi
  elif [ "$CC_TOOL_NAME" = "Edit" ] || [ "$CC_TOOL_NAME" = "MultiEdit" ]; then
    # 禁止通过 Edit 注入新的 REVIEW-SUMMARY 块
    if echo "$CC_CONTENT" | grep -q 'REVIEW-SUMMARY-BEGIN'; then
      if [ -f "$CC_FILE_PATH" ] && grep -q 'REVIEW-SUMMARY-BEGIN' "$CC_FILE_PATH" 2>/dev/null; then
        aicoding_block "review 文件已包含 REVIEW-SUMMARY 块，禁止通过 Edit 注入新的摘要块。如需更新摘要，请在现有块内修改。"
      fi
    fi
  fi
fi

# .aicoding/ 框架文件不触发后续门禁
echo "$CC_FILE_PATH" | grep -q '\.aicoding/' && exit 0

# ============================================================
# 公共初始化：版本目录 + 阶段检测
# ============================================================
# 以下门禁都需要版本目录和阶段信息
HAS_VERSION=false
HAS_PHASE=false
IS_STATUS_MD=false

echo "$CC_FILE_PATH" | grep -q 'status\.md$' && IS_STATUS_MD=true

if aicoding_detect_version_dir "$CC_FILE_PATH"; then
  HAS_VERSION=true
  if aicoding_get_phase; then
    HAS_PHASE=true
  fi
fi

# ============================================================
# Gate 2: 阶段推进拦截（原 phase-gate.sh）
# 仅 status.md + 人工介入期
# ============================================================
if [ "$IS_STATUS_MD" = true ] && [ "$HAS_PHASE" = true ]; then
  if aicoding_is_manual_phase; then
    if echo "$CC_CONTENT" | grep -qE '^_phase:[[:space:]]*(Design|Planning|Implementation|Testing|Deployment)[[:space:]]*$' || \
       echo "$CC_CONTENT" | grep -qE '当前阶段.*\| *(Design|Planning|Implementation|Testing|Deployment)'; then
      aicoding_block "当前处于人工介入期（$AICODING_PHASE），禁止 AI 自行推进阶段。请等待用户明确确认后再更新「当前阶段」。"
    fi
  fi
fi

# ============================================================
# Gate 3: 文档作用域控制（原 doc-scope-guard.sh）
# 仅 docs/vX.Y/ 下的文件
# ============================================================
if [ "$HAS_PHASE" = true ]; then
  if echo "$CC_FILE_PATH" | grep -qE 'docs/v[0-9]+\.[0-9]+/'; then
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
        ALLOWED="status.md|review_|cr/|plan.md|tasks/|design.md|requirements.md" ;;
      Testing)
        ALLOWED="status.md|test_report.md|review_|cr/|design.md|requirements.md" ;;
      Deployment)
        ALLOWED="status.md|deployment.md|test_report.md|review_|cr/" ;;
      *) ALLOWED="" ;;
    esac

    if [ -n "$ALLOWED" ]; then
      MATCH=false
      DOC_BASENAME=$(basename "$CC_FILE_PATH")
      for pattern in $(echo "$ALLOWED" | tr '|' ' '); do
        case "$pattern" in
          */) echo "$CC_FILE_PATH" | grep -q "/${pattern}" && { MATCH=true; break; } ;;
          *)  [ "$DOC_BASENAME" = "$pattern" ] && { MATCH=true; break; }
              echo "$DOC_BASENAME" | grep -q "^${pattern}" && { MATCH=true; break; } ;;
        esac
      done
      if [ "$MATCH" = false ]; then
        aicoding_block "当前阶段 $AICODING_PHASE，不允许创建/修改 $DOC_BASENAME。本阶段允许的文件：${ALLOWED//|/, }"
      fi
    fi
  fi
fi

# ============================================================
# Gate 4: 阶段入口门禁（原 phase-entry-gate.sh）
# review_*.md 和 status.md 不触发
# 当核心文档被修改时，清除入口缓存以强制重新读取
# ============================================================
if [ "$HAS_PHASE" = true ] && [ "$HAS_VERSION" = true ]; then
  # 核心文档被修改时，清除该版本所有阶段的入口缓存
  GATE_BASENAME=$(basename "$CC_FILE_PATH")
  case "$GATE_BASENAME" in
    requirements.md|design.md|plan.md|proposal.md|status.md)
      VERSION_SLUG=$(echo "$AICODING_VERSION_DIR" | tr '/' '_')
      rm -f /tmp/aicoding-entry-passed-*-"${VERSION_SLUG}"-* 2>/dev/null || true
      ;;
  esac
fi
if [ "$HAS_PHASE" = true ]; then
  BASENAME=$(basename "$CC_FILE_PATH")
  case "$BASENAME" in
    review_*|status.md) ;; # 跳过
    *)
      IS_VERSIONED_DOC=false
      echo "$CC_FILE_PATH" | grep -qE 'docs/v[0-9]+\.[0-9]+/' && IS_VERSIONED_DOC=true

      SHOULD_CHECK=false
      case "$AICODING_PHASE" in
        Implementation)
          if [ "$IS_VERSIONED_DOC" = true ]; then
            SHOULD_CHECK=true
          elif ! echo "$CC_FILE_PATH" | grep -q 'docs/'; then
            SHOULD_CHECK=true
          fi ;;
        Deployment)
          if [ "$IS_VERSIONED_DOC" = true ]; then
            SHOULD_CHECK=true
          elif echo "$CC_FILE_PATH" | grep -q 'docs/'; then
            SHOULD_CHECK=true
          fi ;;
        *)
          [ "$IS_VERSIONED_DOC" = true ] && SHOULD_CHECK=true ;;
      esac

      if [ "$SHOULD_CHECK" = true ]; then
        VERSION_SLUG=$(echo "$AICODING_VERSION_DIR" | tr '/' '_')
        GATE_PASSED="/tmp/aicoding-entry-passed-${AICODING_PHASE}-${VERSION_SLUG}-$(aicoding_session_key)"
        if [ ! -f "$GATE_PASSED" ]; then
          case "$AICODING_PHASE" in
            ChangeManagement)
              REQUIRED_PATTERNS="${AICODING_VERSION_DIR}status.md
phases/00-change-management.md
templates/cr_template.md" ;;
            Proposal)
              REQUIRED_PATTERNS="${AICODING_VERSION_DIR}status.md
phases/01-proposal.md
templates/proposal_template.md" ;;
            Requirements)
              REQUIRED_PATTERNS="${AICODING_VERSION_DIR}status.md
${AICODING_VERSION_DIR}proposal.md
phases/02-requirements.md
templates/requirements_template.md" ;;
            Design)
              REQUIRED_PATTERNS="${AICODING_VERSION_DIR}status.md
${AICODING_VERSION_DIR}requirements.md
phases/03-design.md
templates/design_template.md" ;;
            Planning)
              REQUIRED_PATTERNS="${AICODING_VERSION_DIR}status.md
${AICODING_VERSION_DIR}design.md
${AICODING_VERSION_DIR}requirements.md
phases/04-planning.md
templates/plan_template.md" ;;
            Implementation)
              REQUIRED_PATTERNS="${AICODING_VERSION_DIR}status.md
${AICODING_VERSION_DIR}plan.md
${AICODING_VERSION_DIR}design.md
${AICODING_VERSION_DIR}requirements.md
phases/05-implementation.md
templates/implementation_checklist_template.md" ;;
            Testing)
              REQUIRED_PATTERNS="${AICODING_VERSION_DIR}status.md
${AICODING_VERSION_DIR}requirements.md
${AICODING_VERSION_DIR}plan.md
phases/06-testing.md
templates/test_report_template.md" ;;
            Deployment)
              REQUIRED_PATTERNS="${AICODING_VERSION_DIR}status.md
${AICODING_VERSION_DIR}test_report.md
${AICODING_VERSION_DIR}design.md
${AICODING_VERSION_DIR}requirements.md
phases/07-deployment.md
templates/deployment_template.md" ;;
            *) REQUIRED_PATTERNS="" ;;
          esac

          if [ -n "$REQUIRED_PATTERNS" ]; then
            READ_LOG="/tmp/aicoding-reads-$(aicoding_session_key).log"
            [ ! -f "$READ_LOG" ] && READ_LOG_CONTENT="" || READ_LOG_CONTENT=$(< "$READ_LOG")
            MISSING=""
            while IFS= read -r pattern; do
              [ -z "$pattern" ] && continue
              if ! echo "$READ_LOG_CONTENT" | grep -qF "$pattern"; then
                MISSING="${MISSING}\n  - ${pattern}"
              fi
            done <<< "$REQUIRED_PATTERNS"

            if [ -n "$MISSING" ]; then
              ESCAPED=$(echo -e "$MISSING" | tr '\n' ' ')
              aicoding_block "阶段入口门禁（${AICODING_PHASE}）：写入产出物前必须先读取以下文件：${ESCAPED}请先 Read 上述文件，再继续写入。"
            fi
            touch "$GATE_PASSED"
          fi
        fi
      fi
    ;;
  esac
fi

# ============================================================
# Gate 5: 阶段出口门禁（原 phase-exit-gate.sh）
# 仅 status.md + AI 自动期（Design/Planning/Implementation/Testing）
# ============================================================
if [ "$IS_STATUS_MD" = true ] && [ "$HAS_PHASE" = true ]; then
  NEW_PHASE=$(echo "$CC_CONTENT" | grep -oE '_phase:[[:space:]]*(ChangeManagement|Proposal|Requirements|Design|Planning|Implementation|Testing|Deployment)' \
    | sed 's/_phase:[[:space:]]*//' | head -1)

  if [ -n "$NEW_PHASE" ] && [ "$AICODING_PHASE" != "$NEW_PHASE" ]; then
    case "$AICODING_PHASE" in
      Design|Planning|Implementation|Testing)
        NEW_CURRENT=$(echo "$CC_CONTENT" | awk '/^_current:/{sub(/^_current:[[:space:]]*/, "", $0); gsub(/[[:space:]]+$/, "", $0); print; exit}')
        STATUS_CURRENT=$(aicoding_yaml_value "_current")
        STATUS_CURRENT_REF="${NEW_CURRENT:-$STATUS_CURRENT}"

        VERSION_PATH="${CLAUDE_PROJECT_DIR}/${AICODING_VERSION_DIR}"
        if [ -n "${CLAUDE_PROJECT_DIR:-}" ] && [ -d "$CLAUDE_PROJECT_DIR" ]; then
          cd "$CLAUDE_PROJECT_DIR" || true
        fi

        EXIT_MISSING=""
        _check_exit_file() {
          [ ! -f "${VERSION_PATH}$1" ] && EXIT_MISSING="${EXIT_MISSING}\n  - $1"
        }

        case "$AICODING_PHASE" in
          Design)
            _check_exit_file "design.md"
            _check_exit_file "review_design.md" ;;
          Planning)
            _check_exit_file "plan.md"
            _check_exit_file "review_planning.md" ;;
          Implementation)
            _check_exit_file "review_implementation.md" ;;
          Testing)
            _check_exit_file "test_report.md"
            _check_exit_file "review_testing.md" ;;
        esac

        if [ -n "$EXIT_MISSING" ]; then
          ESCAPED=$(echo -e "$EXIT_MISSING" | tr '\n' ' ')
          aicoding_block "阶段出口门禁（${AICODING_PHASE} → ${NEW_PHASE}）：以下必要产出物缺失：${ESCAPED}请补充完整后再推进阶段。"
        fi

        # 内容级门禁
        REQ_FILE="${VERSION_PATH}requirements.md"
        REQ_LABEL="${AICODING_VERSION_DIR}requirements.md"
        case "$AICODING_PHASE" in
          Design)
            review_gate_validate_design_trace_coverage "$REQ_LABEL" "$REQ_FILE" "${AICODING_VERSION_DIR}design.md" "${VERSION_PATH}design.md" || { aicoding_block "Design 追溯覆盖校验失败"; } ;;
          Planning)
            review_gate_validate_plan_reverse_coverage "$REQ_LABEL" "$REQ_FILE" "${AICODING_VERSION_DIR}plan.md" "${VERSION_PATH}plan.md" || { aicoding_block "Planning 覆盖校验失败"; } ;;
          Implementation)
            review_gate_validate_review_summary_and_coverage "${AICODING_VERSION_DIR}review_implementation.md" "${VERSION_PATH}review_implementation.md" "$REQ_LABEL" "$REQ_FILE" "$STATUS_CURRENT_REF" "${AICODING_VERSION_DIR}review_implementation.md" || { aicoding_block "Implementation 审查摘要校验失败"; } ;;
          Testing)
            review_gate_validate_review_summary_and_coverage "${AICODING_VERSION_DIR}review_testing.md" "${VERSION_PATH}review_testing.md" "$REQ_LABEL" "$REQ_FILE" "$STATUS_CURRENT_REF" "${AICODING_VERSION_DIR}review_testing.md" || { aicoding_block "Testing 审查摘要校验失败"; }
            review_gate_validate_test_report_gwt_coverage "$REQ_LABEL" "$REQ_FILE" "${AICODING_VERSION_DIR}test_report.md" "${VERSION_PATH}test_report.md" || { aicoding_block "Testing GWT 覆盖校验失败"; } ;;
        esac
      ;;
    esac
  fi
fi

exit 0
