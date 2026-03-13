#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

tmp_dir=$(mktemp -d)
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT

cd "$tmp_dir"
git init -q
git config user.email "test@example.com"
git config user.name "test"
mkdir -p .aicoding/lib docs/v1.0 docs/v1.1
cp "$ROOT_DIR/scripts/check_quality_debt.sh" .aicoding/check_quality_debt.sh
cp "$ROOT_DIR/scripts/lib/common.sh" .aicoding/lib/common.sh
chmod +x .aicoding/check_quality_debt.sh

cat > aicoding.config.yaml <<'EOF_CFG'
quality_debt_max_total: 10
quality_debt_high_risk_max: 1
tech_debt_max_total: 15
EOF_CFG

cat > docs/v1.0/status.md <<'EOF_OLD'
---
_phase: Deployment
---

## 质量债务登记
| 债务 ID | 类型 | 描述 | 风险等级 | 计划偿还版本 | 状态 |
|--------|------|------|---------|-------------|------|
| QD-001 | 测试覆盖 | a | 高 | v1.1 | Open |
EOF_OLD

git add -A
git commit -q -m "base"

cat > docs/v1.1/status.md <<'EOF_NEW'
---
_baseline: v1.0
_phase: Proposal
---

## 质量债务登记
| 债务 ID | 类型 | 描述 | 风险等级 | 计划偿还版本 | 状态 |
|--------|------|------|---------|-------------|------|
EOF_NEW

git add aicoding.config.yaml docs/v1.1/status.md
output=$(CLAUDE_PROJECT_DIR="$tmp_dir" .aicoding/check_quality_debt.sh 2>&1 || true)
if ! printf '%s\n' "$output" | grep -q "高风险质量债务数量达到阈值"; then
  printf '%s\n' "$output" >&2
  fail "expected root-level config debt threshold to produce the standard high-risk debt gate message"
fi

if CLAUDE_PROJECT_DIR="$tmp_dir" .aicoding/check_quality_debt.sh; then
  fail "expected root-level config debt threshold to be honored"
fi

echo "ok"
