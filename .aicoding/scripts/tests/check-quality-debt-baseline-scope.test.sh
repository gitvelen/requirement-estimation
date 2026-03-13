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

cat > .aicoding/aicoding.config.yaml <<'EOF_CFG'
quality_debt_max_total: 10
quality_debt_high_risk_max: 5
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
| QD-002 | 测试覆盖 | a | 高 | v1.1 | Open |
| QD-003 | 测试覆盖 | a | 高 | v1.1 | Open |
| QD-004 | 测试覆盖 | a | 高 | v1.1 | Open |
| QD-005 | 测试覆盖 | a | 高 | v1.1 | Open |
| QD-006 | 测试覆盖 | a | 高 | v1.1 | Open |
EOF_OLD

# 先提交基线和脚本，使 v1.0/status.md 成为已提交的基线
git add -A
git commit -q -m "base"

# Test 1: 新版本启动时基线高风险债务超限应拦截
cat > docs/v1.1/status.md <<'EOF_NEW'
---
_baseline: v1.0
_phase: Proposal
---

## 质量债务登记
| 债务 ID | 类型 | 描述 | 风险等级 | 计划偿还版本 | 状态 |
|--------|------|------|---------|-------------|------|
EOF_NEW

git add docs/v1.1/status.md
if CLAUDE_PROJECT_DIR="$tmp_dir" .aicoding/check_quality_debt.sh; then
  fail "expected new-version startup to be blocked by baseline high-risk debt"
fi

# Test 2: CR 驱动流程应跳过新版本债务门禁
cat > docs/v1.1/status.md <<'EOF_NEW'
---
_baseline: v1.0
_phase: Proposal
---

## Active CR 列表（🔴 MUST，CR场景）
| CR-ID | 状态 | 标题 | 影响面（文档/模块/ID） | 链接 |
|---|---|---|---|---|
| CR-20260306-001 | InProgress | same-version patch | requirements / REQ-001 | `cr/CR-20260306-001.md` |
EOF_NEW

git add docs/v1.1/status.md
if ! CLAUDE_PROJECT_DIR="$tmp_dir" .aicoding/check_quality_debt.sh; then
  fail "expected CR-driven flow to skip new-version debt gate"
fi

echo "ok"
