#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

need_cmd git
need_cmd awk
need_cmd grep
need_cmd sed

tmp_dir=$(mktemp -d)
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT

cd "$tmp_dir"
git init -q
git config user.email "test@example.com"
git config user.name "test"

# 复制 post-commit dispatcher + warnings + common.sh
mkdir -p scripts/git-hooks/warnings scripts/lib docs/v1.0
cp "$ROOT_DIR/scripts/git-hooks/post-commit" scripts/git-hooks/post-commit
cp "$ROOT_DIR/scripts/lib/common.sh" scripts/lib/common.sh
for w in "$ROOT_DIR"/scripts/git-hooks/warnings/w*.sh; do
  [ -f "$w" ] && cp "$w" scripts/git-hooks/warnings/
done
chmod +x scripts/git-hooks/post-commit

cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_phase: Implementation
---
EOF

cat > docs/v1.0/requirements.md <<'EOF'
## 1. 概述

#### REQ-001：示例需求
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-001-01: Given 用户已登录，When 打开首页，Then 显示欢迎语
EOF

git add -A
git commit -q -m "feat: base"

# 第二次提交：模拟"准备交付"阶段的常见错误
cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: HEAD
_workflow_mode: semi-auto
_run_status: wait_confirm
_change_status: done
_phase: Deployment
---
EOF

cat > docs/v1.0/requirements.md <<'EOF'
## 1. 概述

#### REQ-001：示例需求
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-001-01: Given 用户已登录，When 打开首页，Then 显示欢迎语
- [ ] GWT-REQ-001-01: Given 用户已登录，When 打开首页，Then 显示欢迎语（重复 ID）
EOF

cat > docs/v1.0/review_implementation.md <<'EOF'
## 2026-02-13 第1轮

| GWT-ID | REQ-ID | 判定 | 证据类型 | 证据（可复现） | 备注 |
|---|---|---|---|---|---|
| GWT-REQ-001-01 | REQ-001 | ✅ |  |  | 风险：证据列为空时应提示 |

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: implementation
REVIEW_SCOPE: full
REVIEW_MODES: TECH,REQ
CODE_BASELINE: HEAD
REQ_BASELINE_HASH: dummy
GWT_TOTAL: 1
GWT_CHECKED: 1
GWT_CARRIED: 0
CARRIED_FROM_COMMIT: N/A
GWT_FAIL: 0
GWT_WARN: 0
SPOT_CHECK_GWTS: GWT-REQ-001-01,GWT-REQ-001-01,GWT-REQ-001-01
REVIEW_RESULT: pass
<!-- REVIEW-SUMMARY-END -->
EOF

git add -A
git commit -q -m "feat: prepare delivery"

output=$(bash scripts/git-hooks/post-commit 2>&1 || true)

echo "$output" | grep -q "W20" || fail "expected W20 warning, got: ${output}"
echo "$output" | grep -q "W21" || fail "expected W21 warning, got: ${output}"
echo "$output" | grep -q "W22" || fail "expected W22 warning, got: ${output}"
echo "$output" | grep -q "本次提交触发" || fail "expected post-commit summary line, got: ${output}"
[ -f .git/aicoding/gate-warnings.log ] || fail "expected gate warning log file"
grep -q "W22" .git/aicoding/gate-warnings.log || fail "expected warning log to include W22 entry"

echo "ok"
