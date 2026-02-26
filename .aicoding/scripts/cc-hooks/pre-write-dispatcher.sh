#!/bin/bash
# aicoding-hooks-managed
# CC PreToolUse 统一入口：合并 phase-gate / doc-scope-guard / phase-entry-gate / phase-exit-gate / review-append-guard
# 将 5 个独立进程合并为 1 个，减少每次 Write/Edit 的进程开销

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=../lib/review_gate_common.sh
source "${SCRIPT_DIR}/../lib/review_gate_common.sh"
source "${SCRIPT_DIR}/../lib/common.sh"
aicoding_load_config

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
    # wait_confirm 状态下放行：说明 AI 已暂停等待过用户确认，此时代为更新 _phase 是合法的
    CURRENT_RUN_STATUS=$(aicoding_yaml_value "_run_status")
    if [ "$CURRENT_RUN_STATUS" != "wait_confirm" ]; then
      # 提取内容中的 _phase 值（YAML 行）
      NEW_PHASE_IN_CONTENT=$(echo "$CC_CONTENT" | grep -oE '^_phase:[[:space:]]*[A-Za-z]+' | sed 's/^_phase:[[:space:]]*//' | head -1)
      if [ -n "$NEW_PHASE_IN_CONTENT" ] && [ "$NEW_PHASE_IN_CONTENT" != "$AICODING_PHASE" ]; then
        aicoding_block "当前处于人工介入期（$AICODING_PHASE），禁止 AI 自行推进阶段至 ${NEW_PHASE_IN_CONTENT}。请先设置 _run_status: wait_confirm 并等待用户明确确认后再更新。"
      fi
      # 同样拦截表格行的阶段变更
      TABLE_PHASE=$(echo "$CC_CONTENT" | grep -oE '当前阶段.*\|[[:space:]]*[A-Za-z]+' | grep -oE '[A-Za-z]+$' | head -1)
      if [ -n "$TABLE_PHASE" ] && [ "$TABLE_PHASE" != "$AICODING_PHASE" ]; then
        aicoding_block "当前处于人工介入期（$AICODING_PHASE），禁止 AI 自行推进阶段至 ${TABLE_PHASE}。请先设置 _run_status: wait_confirm 并等待用户明确确认后再更新。"
      fi
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
      ChangeManagement)
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
        ALLOWED="status.md|review_|spotcheck_|cr/|plan.md|tasks/|design.md|requirements.md|implementation_checklist.md" ;;
      Testing)
        ALLOWED="status.md|test_report.md|review_|spotcheck_|cr/|design.md|requirements.md|plan.md" ;;
      Deployment)
        ALLOWED="status.md|deployment.md|test_report.md|review_|spotcheck_|cr/" ;;
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
      CHANGE_LEVEL=$(aicoding_yaml_value "_change_level")
      [ "$CHANGE_LEVEL" = "hotfix" ] && SHOULD_CHECK=false
      IS_VERSIONED_DOC=false
      echo "$CC_FILE_PATH" | grep -qE 'docs/v[0-9]+\.[0-9]+/' && IS_VERSIONED_DOC=true

      if [ "$CHANGE_LEVEL" != "hotfix" ]; then
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
      fi

      if [ "$SHOULD_CHECK" = true ]; then
        VERSION_SLUG=$(echo "$AICODING_VERSION_DIR" | tr '/' '_')
        SESSION_KEY=$(aicoding_session_key)
        GATE_PASSED="/tmp/aicoding-entry-passed-${AICODING_PHASE}-${VERSION_SLUG}-${SESSION_KEY}"
        if [ ! -f "$GATE_PASSED" ]; then
          REQUIRED_PATTERNS=$(aicoding_phase_entry_required "$AICODING_PHASE" "$AICODING_VERSION_DIR")

          if [ -n "$REQUIRED_PATTERNS" ]; then
            SESSION_KEY=$(aicoding_session_key)
            READ_LOG="/tmp/aicoding-reads-${SESSION_KEY}.log"
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
              WARN_MSG="阶段入口门禁（${AICODING_PHASE}）：写入产出物前必须先读取以下文件：${ESCAPED}请先 Read 上述文件，再继续写入。"
              aicoding_load_config
              if [ "$AICODING_ENTRY_GATE_MODE" = "block" ]; then
                aicoding_block "${WARN_MSG}"
              else
                echo "⚠️  [CC-7] ${WARN_MSG}" >&2
                aicoding_gate_log_warning "${WARN_MSG}"
              fi
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
# 仅 status.md + Requirements/AI 自动期（Requirements/Design/Planning/Implementation/Testing）
# ============================================================

_validate_minor_review_file() {
  local file="$1"
  [ -f "$file" ] || return 1
  grep -q 'REVIEW-SUMMARY-BEGIN' "$file" || return 1
  grep -q 'REVIEW_RESULT:[[:space:]]*pass' "$file" || return 1
  grep -q 'REQ_BASELINE_HASH:' "$file" || return 1
}
_has_minor_test_evidence() {
  local status_file="$1"
  [ -f "${VERSION_PATH}test_report.md" ] && return 0
  grep -q 'TEST-RESULT-BEGIN' "$status_file" 2>/dev/null && return 0
  return 1
}
_validate_minor_testing_round_file() {
  local review_file="$1"
  local block phase result round_at phase_norm result_norm
  [ -f "$review_file" ] || return 1
  block=$(
    awk '
      /MINOR-TESTING-ROUND-BEGIN/ {in_block=1; buf=""; next}
      /MINOR-TESTING-ROUND-END/ {
        if (in_block) {last=buf}
        in_block=0
        next
      }
      in_block {buf = buf $0 "\n"}
      END {printf "%s", last}
    ' "$review_file"
  )
  [ -n "$block" ] || return 1

  phase=$(printf '%s\n' "$block" | sed -n 's/^ROUND_PHASE:[[:space:]]*//p' | tail -1)
  result=$(printf '%s\n' "$block" | sed -n 's/^ROUND_RESULT:[[:space:]]*//p' | tail -1)
  round_at=$(printf '%s\n' "$block" | sed -n 's/^ROUND_AT:[[:space:]]*//p' | tail -1)
  phase_norm=$(printf '%s' "$phase" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')
  result_norm=$(printf '%s' "$result" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')

  [ "$phase_norm" = "testing" ] || return 1
  [ "$result_norm" = "pass" ] || return 1
  echo "$round_at" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' || return 1
  return 0
}
_validate_constraints_confirmation_file() {
  local review_label="$1" review_file="$2" req_label="$3" req_file="$4" proposal_label="$5" proposal_file="$6"
  review_gate_validate_constraints_confirmation \
    "$review_label" "$review_file" "$req_label" "$req_file" "$proposal_label" "$proposal_file"
}
_validate_proposal_coverage_file() {
  local proposal_label="$1" proposal_file="$2" req_label="$3" req_file="$4"
  [ -f "$proposal_file" ] || return 0
  review_gate_validate_proposal_coverage "$proposal_label" "$proposal_file" "$req_label" "$req_file"
}

if [ "$IS_STATUS_MD" = true ] && [ "$HAS_PHASE" = true ]; then
  NEW_PHASE=$(echo "$CC_CONTENT" | grep -oE '_phase:[[:space:]]*(ChangeManagement|Proposal|Requirements|Design|Planning|Implementation|Testing|Deployment)' \
    | sed 's/_phase:[[:space:]]*//' | head -1)

  if [ -n "$NEW_PHASE" ] && [ "$AICODING_PHASE" != "$NEW_PHASE" ]; then
    case "$AICODING_PHASE" in
      Requirements|Design|Planning|Implementation|Testing)
        NEW_CURRENT=$(echo "$CC_CONTENT" | awk '/^_current:/{sub(/^_current:[[:space:]]*/, "", $0); gsub(/[[:space:]]+$/, "", $0); print; exit}')
        STATUS_CURRENT=$(aicoding_yaml_value "_current")
        STATUS_CURRENT_REF="${NEW_CURRENT:-$STATUS_CURRENT}"

        CHANGE_LEVEL=$(aicoding_yaml_value "_change_level")
        [ -z "$CHANGE_LEVEL" ] && CHANGE_LEVEL="major"

        OLD_RANK=$(aicoding_phase_rank "$AICODING_PHASE")
        NEW_RANK=$(aicoding_phase_rank "$NEW_PHASE")
        FORWARD_JUMP=$((NEW_RANK - OLD_RANK))
        if [ "$FORWARD_JUMP" -gt 1 ]; then
          aicoding_block "阶段跳跃（${AICODING_PHASE} → ${NEW_PHASE}，跨度 ${FORWARD_JUMP}）：只允许推进到相邻的下一阶段，不允许跳跃。"
        fi

        VERSION_PATH="${CLAUDE_PROJECT_DIR}/${AICODING_VERSION_DIR}"
        if [ -n "${CLAUDE_PROJECT_DIR:-}" ] && [ -d "$CLAUDE_PROJECT_DIR" ]; then
          cd "$CLAUDE_PROJECT_DIR" || true
        fi

        EXIT_MISSING=""
        _check_exit_file() {
          [ ! -f "${VERSION_PATH}$1" ] && EXIT_MISSING="${EXIT_MISSING}\n  - $1"
        }

        while IFS= read -r required_doc; do
          [ -z "$required_doc" ] && continue
          _check_exit_file "$required_doc"
        done < <(aicoding_phase_exit_required "$AICODING_PHASE" "$CHANGE_LEVEL")

        if [ "$AICODING_PHASE" = "Testing" ] && [ "$CHANGE_LEVEL" = "minor" ]; then
          [ -f "${VERSION_PATH}test_report.md" ] || \
            [ -n "$(grep -n 'TEST-RESULT-BEGIN' "${VERSION_PATH}status.md" 2>/dev/null || true)" ] || \
            EXIT_MISSING="${EXIT_MISSING}\n  - test_report.md 或 status.md 内联 TEST-RESULT 块"
        fi

        if [ -n "$EXIT_MISSING" ]; then
          ESCAPED=$(echo -e "$EXIT_MISSING" | tr '\n' ' ')
          aicoding_block "阶段出口门禁（${AICODING_PHASE} → ${NEW_PHASE}）：以下必要产出物缺失：${ESCAPED}请补充完整后再推进阶段。"
        fi

        # 内容级门禁
        REQ_FILE="${VERSION_PATH}requirements.md"
        REQ_LABEL="${AICODING_VERSION_DIR}requirements.md"
        case "$AICODING_PHASE" in
          Requirements)
            _validate_constraints_confirmation_file \
              "${AICODING_VERSION_DIR}review_requirements.md" "${VERSION_PATH}review_requirements.md" \
              "$REQ_LABEL" "$REQ_FILE" \
              "${AICODING_VERSION_DIR}proposal.md" "${VERSION_PATH}proposal.md" \
              || { aicoding_block "Requirements 禁止项确认校验失败"; }
            _validate_proposal_coverage_file \
              "${AICODING_VERSION_DIR}proposal.md" "${VERSION_PATH}proposal.md" \
              "$REQ_LABEL" "$REQ_FILE" \
              || { aicoding_block "Requirements Proposal 覆盖校验失败"; }
            ;;
          Design)
            review_gate_validate_design_trace_coverage "$REQ_LABEL" "$REQ_FILE" \
              "${AICODING_VERSION_DIR}design.md" "${VERSION_PATH}design.md" \
              || { aicoding_block "Design 追溯覆盖校验失败"; }
            api_result=$(review_gate_validate_design_api_contracts \
              "${AICODING_VERSION_DIR}design.md" "${VERSION_PATH}design.md" 2>&1 || true)
            [ -z "$api_result" ] || echo "$api_result" >&2
            ;;
          Planning)
            review_gate_validate_plan_reverse_coverage "$REQ_LABEL" "$REQ_FILE" \
              "${AICODING_VERSION_DIR}plan.md" "${VERSION_PATH}plan.md" \
              || { aicoding_block "Planning 覆盖校验失败"; } ;;
          Implementation)
            if [ "$CHANGE_LEVEL" = "minor" ]; then
              _validate_minor_review_file "${VERSION_PATH}review_minor.md" \
                || { aicoding_block "Implementation minor 审查校验失败（review_minor.md 不完整）"; }
            else
              review_gate_validate_review_summary_and_coverage \
                "${AICODING_VERSION_DIR}review_implementation.md" \
                "${VERSION_PATH}review_implementation.md" "$REQ_LABEL" "$REQ_FILE" \
                "$STATUS_CURRENT_REF" "${AICODING_VERSION_DIR}review_implementation.md" \
                || { aicoding_block "Implementation 审查摘要校验失败"; }
            fi ;;
          Testing)
            if [ "$CHANGE_LEVEL" = "minor" ]; then
              _validate_minor_review_file "${VERSION_PATH}review_minor.md" \
                || { aicoding_block "Testing minor 审查校验失败（review_minor.md 不完整）"; }
              _has_minor_test_evidence "${VERSION_PATH}status.md" \
                || { aicoding_block "Testing minor 缺少测试证据"; }
              _validate_minor_testing_round_file "${VERSION_PATH}review_minor.md" \
                || { aicoding_block "Testing minor 缺少 Testing 轮次机器可读结论（MINOR-TESTING-ROUND）"; }
            else
              review_gate_validate_review_summary_and_coverage \
                "${AICODING_VERSION_DIR}review_testing.md" \
                "${VERSION_PATH}review_testing.md" "$REQ_LABEL" "$REQ_FILE" \
                "$STATUS_CURRENT_REF" "${AICODING_VERSION_DIR}review_testing.md" \
                || { aicoding_block "Testing 审查摘要校验失败"; }
              review_gate_validate_test_report_gwt_coverage "$REQ_LABEL" "$REQ_FILE" \
                "${AICODING_VERSION_DIR}test_report.md" "${VERSION_PATH}test_report.md" \
                || { aicoding_block "Testing GWT 覆盖校验失败"; }
            fi ;;
        esac
      ;;
    esac
  fi
fi

exit 0
