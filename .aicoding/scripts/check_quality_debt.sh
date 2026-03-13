#!/bin/bash
# aicoding-hooks-managed
# 质量债务检查脚本：检查基线版本债务总量和高风险债务数量
# 用于 pre-commit hook 中阻断新版本启动

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
[ -z "$REPO_ROOT" ] && { echo "❌ 不在 git 仓库中" >&2; exit 1; }

# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

# ============================================================
# 配置读取
# ============================================================
# ============================================================
# 债务统计
# ============================================================
aicoding_count_debt() {
  local status_file="$1"
  local debt_type="$2"  # "quality" or "tech"

  [ -f "$status_file" ] || { echo "0"; return; }

  if [ "$debt_type" = "quality" ]; then
    awk '
      /^## 质量债务登记/ {in_table=1; next}
      in_table && /^## / {exit}
      in_table && /^\|/ && !/^\| 债务 ID/ && !/^\|---/ && /Open/ {count++}
      END {print count+0}
    ' "$status_file"
  else
    awk '
      /^## 技术债务登记/ {in_table=1; next}
      in_table && /^## / {exit}
      in_table && /^\|/ && !/^\| 来源阶段/ && !/^\|---/ && /Open/ {count++}
      END {print count+0}
    ' "$status_file"
  fi
}

aicoding_count_high_risk_debt() {
  local status_file="$1"

  [ -f "$status_file" ] || { echo "0"; return; }

  awk '
    /^## 质量债务登记/ {in_table=1; next}
    in_table && /^## / {exit}
    in_table && /^\|/ && !/^\| 债务 ID/ && !/^\|---/ && /高/ && /Open/ {count++}
    END {print count+0}
  ' "$status_file"
}

# ============================================================
# 启动语义判断
# ============================================================
aicoding_is_new_version_startup() {
  local phase="$1"
  local status_file="$2"
  local active_crs

  [ "$phase" = "Proposal" ] || return 1
  active_crs=$(aicoding_active_crs "$status_file")
  [ -z "$active_crs" ] || return 1
  return 0
}

aicoding_baseline_status_file() {
  local baseline_ref="$1"

  aicoding_is_version_tag "$baseline_ref" || {
    echo "⚠️  基线版本 $baseline_ref 不符合版本 tag 格式（期望：${AICODING_VERSION_DIR_PATTERN}）" >&2
    return 1
  }

  local baseline_status="${REPO_ROOT}/docs/${baseline_ref}/status.md"
  if [ -f "$baseline_status" ]; then
    printf '%s\n' "$baseline_status"
    return 0
  fi

  echo "⚠️  基线版本 $baseline_ref 对应的 status.md 不存在：$baseline_status" >&2
  echo "   请检查版本目录命名是否与 aicoding.config.yaml 中的 version_dir_pattern 一致" >&2
  return 1
}

# ============================================================
# 主逻辑
# ============================================================
main() {
  aicoding_load_config

  # 从暂存区探测版本目录，避免被工作区无关高版本目录带偏
  local staged_status_files
  staged_status_files=""
  while IFS= read -r staged_file; do
    [ -z "$staged_file" ] && continue
    [ "$(basename "$staged_file")" = "status.md" ] || continue
    aicoding_extract_version_dir_from_path "$staged_file" >/dev/null 2>&1 || continue
    staged_status_files="$staged_file"
    break
  done < <(git diff --cached --name-only --diff-filter=AM)

  if [ -n "$staged_status_files" ]; then
    # 暂存区有 status.md，直接使用其版本目录
    AICODING_VERSION_DIR=$(dirname "$staged_status_files")/
    AICODING_STATUS_FILE="$staged_status_files"
  else
    # 暂存区无 status.md，尝试从其他暂存文件推断版本
    local any_staged_doc
    any_staged_doc=""
    while IFS= read -r staged_file; do
      [ -z "$staged_file" ] && continue
      aicoding_extract_version_dir_from_path "$staged_file" >/dev/null 2>&1 || continue
      any_staged_doc="$staged_file"
      break
    done < <(git diff --cached --name-only --diff-filter=AM)
    if [ -n "$any_staged_doc" ]; then
      aicoding_detect_version_dir "$any_staged_doc" || exit 0
    else
      # 无任何版本文档变更，跳过检查
      exit 0
    fi
  fi

  local current_phase current_baseline baseline_status_file
  current_phase=$(aicoding_yaml_value "_phase")
  current_baseline=$(aicoding_yaml_value "_baseline")

  aicoding_is_new_version_startup "$current_phase" "$AICODING_STATUS_FILE" || exit 0

  baseline_status_file=$(aicoding_baseline_status_file "$current_baseline") || {
    echo "❌ _baseline 必须为可识别版本 tag（匹配 ${AICODING_VERSION_DIR_PATTERN}，当前：${current_baseline:-<empty>}）"
    exit 1
  }
  [ -f "$baseline_status_file" ] || {
    echo "❌ 基线状态文件不存在：$baseline_status_file"
    exit 1
  }

  QUALITY_DEBT_MAX_TOTAL="${AICODING_QUALITY_DEBT_MAX_TOTAL:-10}"
  QUALITY_DEBT_HIGH_RISK_MAX="${AICODING_QUALITY_DEBT_HIGH_RISK_MAX:-5}"
  TECH_DEBT_MAX_TOTAL="${AICODING_TECH_DEBT_MAX_TOTAL:-15}"

  local quality_debt_total tech_debt_total high_risk_debt
  quality_debt_total=$(aicoding_count_debt "$baseline_status_file" "quality")
  tech_debt_total=$(aicoding_count_debt "$baseline_status_file" "tech")
  high_risk_debt=$(aicoding_count_high_risk_debt "$baseline_status_file")

  if [ "$quality_debt_total" -gt "$QUALITY_DEBT_MAX_TOTAL" ]; then
    echo "❌ 基线版本质量债务总量超过上限：$quality_debt_total > $QUALITY_DEBT_MAX_TOTAL"
    echo "   请先处理上一版本的部分质量债务再启动新版本"
    echo "   查看债务清单：$baseline_status_file"
    exit 1
  fi

  if [ "$high_risk_debt" -ge "$QUALITY_DEBT_HIGH_RISK_MAX" ]; then
    echo "❌ 基线版本高风险质量债务数量达到阈值：$high_risk_debt >= $QUALITY_DEBT_HIGH_RISK_MAX"
    echo "   请先将上一版本的高风险债务降到阈值以下再启动新版本"
    echo "   查看债务清单：$baseline_status_file"
    exit 1
  fi

  if [ "$tech_debt_total" -gt "$TECH_DEBT_MAX_TOTAL" ]; then
    echo "⚠️  基线版本技术债务总量超过建议值：$tech_debt_total > $TECH_DEBT_MAX_TOTAL"
    echo "   建议在本版本偿还部分技术债务"
    echo "   查看债务清单：$baseline_status_file"
  fi

  if [ "$quality_debt_total" -gt 0 ] || [ "$tech_debt_total" -gt 0 ]; then
    echo "✅ 债务检查通过（基线质量债务: $quality_debt_total, 基线技术债务: $tech_debt_total, 基线高风险: $high_risk_debt）"
  fi

  exit 0
}

main "$@"
