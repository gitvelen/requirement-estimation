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
mkdir -p .aicoding/lib docs/v1.0.0 docs/v1.1.0
cp "$ROOT_DIR/scripts/check_quality_debt.sh" .aicoding/check_quality_debt.sh
cp "$ROOT_DIR/scripts/lib/common.sh" .aicoding/lib/common.sh
chmod +x .aicoding/check_quality_debt.sh

cat > .aicoding/aicoding.config.yaml <<'EOF_CFG'
quality_debt_max_total: 10
quality_debt_high_risk_max: 5
tech_debt_max_total: 15
version_dir_pattern: ^v([0-9]+\.[0-9]+\.[0-9]+)$
EOF_CFG

cat > docs/v1.0.0/status.md <<'EOF_OLD'
---
_phase: Deployment
---

## 质量债务登记
| 债务 ID | 类型 | 描述 | 风险等级 | 计划偿还版本 | 状态 |
|--------|------|------|---------|-------------|------|
| QD-001 | 测试覆盖 | a | 高 | v1.1.0 | Open |
| QD-002 | 测试覆盖 | a | 高 | v1.1.0 | Open |
| QD-003 | 测试覆盖 | a | 高 | v1.1.0 | Open |
| QD-004 | 测试覆盖 | a | 高 | v1.1.0 | Open |
| QD-005 | 测试覆盖 | a | 高 | v1.1.0 | Open |
| QD-006 | 测试覆盖 | a | 高 | v1.1.0 | Open |
EOF_OLD

git add -A
git commit -q -m "base"

cat > docs/v1.1.0/status.md <<'EOF_NEW'
---
_baseline: v1.0.0
_phase: Proposal
---

## 质量债务登记
| 债务 ID | 类型 | 描述 | 风险等级 | 计划偿还版本 | 状态 |
|--------|------|------|---------|-------------|------|
EOF_NEW

git add .aicoding/aicoding.config.yaml docs/v1.1.0/status.md
if CLAUDE_PROJECT_DIR="$tmp_dir" .aicoding/check_quality_debt.sh; then
  fail "expected semver new-version startup to be blocked by baseline high-risk debt"
fi

grep -q "高风险质量债务数量达到阈值" <(CLAUDE_PROJECT_DIR="$tmp_dir" .aicoding/check_quality_debt.sh 2>&1 || true) \
  || fail "expected high-risk debt gate message for semver version dirs"

echo "ok"
