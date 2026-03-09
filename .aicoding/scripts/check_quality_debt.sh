#!/bin/bash
# aicoding-hooks-managed
# 质量债务检查脚本：检查债务总量和高风险债务数量
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
aicoding_load_config_debt() {
  local config_file="${REPO_ROOT}/.aicoding/aicoding.config.yaml"
  [ -f "$config_file" ] || return 0

  QUALITY_DEBT_MAX_TOTAL=$(grep '^quality_debt_max_total:' "$config_file" | awk '{print $2}' || echo "10")
  QUALITY_DEBT_HIGH_RISK_MAX=$(grep '^quality_debt_high_risk_max:' "$config_file" | awk '{print $2}' || echo "5")
  TECH_DEBT_MAX_TOTAL=$(grep '^tech_debt_max_total:' "$config_file" | awk '{print $2}' || echo "15")
}

# ============================================================
# 债务统计
# ============================================================
aicoding_count_debt() {
  local status_file="$1"
  local debt_type="$2"  # "quality" or "tech"

  [ -f "$status_file" ] || { echo "0"; return; }

  # 查找债务表格并统计 Open 状态的行数
  if [ "$debt_type" = "quality" ]; then
    # 质量债务登记表格
    awk '
      /^## 质量债务登记/ {in_table=1; next}
      in_table && /^## / {exit}
      in_table && /^\|/ && !/^| 债务 ID/ && !/^|---/ && /Open/ {count++}
      END {print count+0}
    ' "$status_file"
  else
    # 技术债务登记表格
    awk '
      /^## 技术债务登记/ {in_table=1; next}
      in_table && /^## / {exit}
      in_table && /^\|/ && !/^| 来源阶段/ && !/^|---/ && /Open/ {count++}
      END {print count+0}
    ' "$status_file"
  fi
}

aicoding_count_high_risk_debt() {
  local status_file="$1"

  [ -f "$status_file" ] || { echo "0"; return; }

  # 统计高风险质量债务（风险等级=高 且 状态=Open）
  awk '
    /^## 质量债务登记/ {in_table=1; next}
    in_table && /^## / {exit}
    in_table && /^\|/ && !/^| 债务 ID/ && !/^|---/ && /高/ && /Open/ {count++}
    END {print count+0}
  ' "$status_file"
}

# ============================================================
# 主逻辑
# ============================================================
main() {
  # 检测版本目录
  aicoding_detect_version_dir || {
    # 没有版本目录，跳过检查
    exit 0
  }

  # 检查是否是新版本启动（_phase=ChangeManagement 且 _baseline 变化）
  local current_phase=$(aicoding_yaml_value "_phase")
  local current_baseline=$(aicoding_yaml_value "_baseline")

  # 只在 ChangeManagement 阶段检查
  [ "$current_phase" = "ChangeManagement" ] || exit 0

  # 加载配置
  aicoding_load_config
  aicoding_load_config_debt

  # 统计债务
  local quality_debt_total=$(aicoding_count_debt "$AICODING_STATUS_FILE" "quality")
  local tech_debt_total=$(aicoding_count_debt "$AICODING_STATUS_FILE" "tech")
  local high_risk_debt=$(aicoding_count_high_risk_debt "$AICODING_STATUS_FILE")

  # 检查质量债务总量
  if [ "$quality_debt_total" -gt "$QUALITY_DEBT_MAX_TOTAL" ]; then
    echo "❌ 质量债务总量超过上限：$quality_debt_total > $QUALITY_DEBT_MAX_TOTAL"
    echo "   请先偿还部分质量债务再启动新版本"
    echo "   查看债务清单：$AICODING_STATUS_FILE"
    exit 1
  fi

  # 检查高风险债务数量（≥5 时必须偿还至少 3 个才能启动新版本）
  if [ "$high_risk_debt" -ge "$QUALITY_DEBT_HIGH_RISK_MAX" ]; then
    echo "❌ 高风险质量债务数量达到阈值：$high_risk_debt >= $QUALITY_DEBT_HIGH_RISK_MAX"
    echo "   必须先偿还至少 3 个高风险债务才能启动新版本"
    echo "   查看债务清单：$AICODING_STATUS_FILE"
    exit 1
  fi

  # 检查技术债务总量（告警）
  if [ "$tech_debt_total" -gt "$TECH_DEBT_MAX_TOTAL" ]; then
    echo "⚠️  技术债务总量超过建议值：$tech_debt_total > $TECH_DEBT_MAX_TOTAL"
    echo "   建议在本版本偿还部分技术债务"
    echo "   查看债务清单：$AICODING_STATUS_FILE"
    # 不阻断，仅告警
  fi

  # 检查通过
  if [ "$quality_debt_total" -gt 0 ] || [ "$tech_debt_total" -gt 0 ]; then
    echo "✅ 债务检查通过（质量债务: $quality_debt_total, 技术债务: $tech_debt_total, 高风险: $high_risk_debt）"
  fi

  exit 0
}

main "$@"
