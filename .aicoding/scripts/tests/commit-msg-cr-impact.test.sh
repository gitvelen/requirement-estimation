#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
COMMIT_MSG_SRC="${ROOT_DIR}/scripts/git-hooks/commit-msg"
COMMON_SRC="${ROOT_DIR}/scripts/lib/common.sh"
VALIDATION_SRC="${ROOT_DIR}/scripts/lib/validation.sh"

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

mkdir -p scripts/git-hooks scripts/lib docs/v1.0/cr src
cp "$COMMIT_MSG_SRC" scripts/git-hooks/commit-msg
cp "$COMMON_SRC" scripts/lib/common.sh
cp "$VALIDATION_SRC" scripts/lib/validation.sh
chmod +x scripts/git-hooks/commit-msg

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: major
_phase: Implementation
---

## Active CR 列表
| CR-ID | 状态 | 标题 | 影响面（文档/模块/ID） | 链接 |
|---|---|---|---|---|
| CR-20260216-001 | Accepted | A | src/a.ts | `cr/CR-20260216-001.md` |
| CR-20260216-002 | InProgress | B | src/b.ts | `cr/CR-20260216-002.md` |
EOF_STATUS

cat > docs/v1.0/cr/CR-20260216-001.md <<'EOF_CR1'
## 3.3 代码影响
| 影响模块/文件 | 变更类型 |
|--------------|---------|
| src/a.ts | 修改 |
EOF_CR1

cat > docs/v1.0/cr/CR-20260216-002.md <<'EOF_CR2'
## 3.3 代码影响
| 影响模块/文件 | 变更类型 |
|--------------|---------|
| src/b.ts | 修改 |
EOF_CR2

cat > src/b.ts <<'EOF_SRC'
export const b = 1;
EOF_SRC

git add -A
git commit -q -m "base"

echo "export const b = 2;" > src/b.ts
git add src/b.ts

cat > msg.txt <<'EOF_MSG'
feat: adjust b [CR-20260216-001]
EOF_MSG
if bash scripts/git-hooks/commit-msg msg.txt; then
  fail "expected commit-msg to require impacted CR ID"
fi

cat > msg.txt <<'EOF_MSG'
feat: adjust b [CR-20260216-002]
EOF_MSG
if ! bash scripts/git-hooks/commit-msg msg.txt; then
  fail "expected commit-msg to pass when impacted CR ID is present"
fi

# no docs/vX.Y staged: fallback should use latest version dir (v2.0), not older v1.0
mkdir -p docs/v2.0/cr
cat > docs/v2.0/status.md <<'EOF_STATUS_V2'
---
_baseline: v1.0
_current: 1111111
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: major
_phase: Implementation
---

## Active CR 列表
| CR-ID | 状态 | 标题 | 影响面（文档/模块/ID） | 链接 |
|---|---|---|---|---|
| CR-20260216-101 | Accepted | C | src/c.ts | `cr/CR-20260216-101.md` |
EOF_STATUS_V2

cat > docs/v2.0/cr/CR-20260216-101.md <<'EOF_CR3'
## 3.3 代码影响
| 影响模块/文件 | 变更类型 |
|--------------|---------|
| src/c.ts | 修改 |
EOF_CR3

cat > src/c.ts <<'EOF_SRC_C'
export const c = 1;
EOF_SRC_C

git add docs/v2.0/status.md docs/v2.0/cr/CR-20260216-101.md src/c.ts
git commit -q -m "add v2 baseline"

echo "export const c = 2;" > src/c.ts
git add src/c.ts

cat > msg.txt <<'EOF_MSG'
feat: adjust c [CR-20260216-001]
EOF_MSG
if bash scripts/git-hooks/commit-msg msg.txt; then
  fail "expected commit-msg to reject old-version CR when latest version has impacted CR"
fi

cat > msg.txt <<'EOF_MSG'
feat: adjust c [CR-20260216-101]
EOF_MSG
if ! bash scripts/git-hooks/commit-msg msg.txt; then
  fail "expected commit-msg to use latest version CR mapping when no docs are staged"
fi

echo "ok"
