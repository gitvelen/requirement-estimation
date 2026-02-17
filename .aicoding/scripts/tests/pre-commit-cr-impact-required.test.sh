#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
PRE_COMMIT_SRC="${ROOT_DIR}/scripts/git-hooks/pre-commit"
LIB_SRC="${ROOT_DIR}/scripts/lib/review_gate_common.sh"
COMMON_SRC="${ROOT_DIR}/scripts/lib/common.sh"

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

mkdir -p scripts/git-hooks scripts/lib docs/v1.0/cr
cp "$PRE_COMMIT_SRC" scripts/git-hooks/pre-commit
cp "$LIB_SRC" scripts/lib/review_gate_common.sh
cp "$COMMON_SRC" scripts/lib/common.sh
chmod +x scripts/git-hooks/pre-commit

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: major
_phase: ChangeManagement
---
EOF_STATUS

git add -A
git commit -q -m "base"

cat > docs/v1.0/cr/CR-20260216-001.md <<'EOF_CR'
## 3.1 阶段文档影响
| 影响文档 | 是/否（🔴必填） | 影响章节/内容 | 影响 ID |
|---------|----------------|-------------|---------|
| proposal | [ ]是 [ ]否 |  |  |
| requirements | [✓]是 [ ]否 | 新增需求 | REQ-001 |

## 3.2 主文档影响
| 主文档 | [✓]是 / [✓]否（🔴二选一，必填） | 影响说明 | 关联 ID |
|--------|------------------------------|---------|---------|
| 系统功能说明书.md | [ ]是 [ ]否 |  |  |
| 技术方案设计.md | [✓]是 [ ]否 | 新增章节 | DES-001 |
EOF_CR

git add docs/v1.0/cr/CR-20260216-001.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to reject CR impact rows without binary selection"
fi

cat > docs/v1.0/cr/CR-20260216-001.md <<'EOF_CR'
## 3.1 阶段文档影响
| 影响文档 | 是/否（🔴必填） | 影响章节/内容 | 影响 ID |
|---------|----------------|-------------|---------|
| proposal | [ ]是 [✓]否 | N/A | N/A |
| requirements | [✓]是 [ ]否 | 新增需求 | REQ-001 |

## 3.2 主文档影响
| 主文档 | [✓]是 / [✓]否（🔴二选一，必填） | 影响说明 | 关联 ID |
|--------|------------------------------|---------|---------|
| 系统功能说明书.md | [ ]是 [✓]否 | N/A | N/A |
| 技术方案设计.md | [✓]是 [ ]否 | 新增章节 | DES-001 |
EOF_CR

git add docs/v1.0/cr/CR-20260216-001.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected pre-commit to allow valid CR impact matrix"
fi

echo "ok"
