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
cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

cd "$tmp_dir"
git init -q
git config user.email "test@example.com"
git config user.name "test"

mkdir -p scripts/git-hooks scripts/lib docs/v1.0 src
cp "$PRE_COMMIT_SRC" scripts/git-hooks/pre-commit
cp "$LIB_SRC" scripts/lib/review_gate_common.sh
cp "$COMMON_SRC" scripts/lib/common.sh
chmod +x scripts/git-hooks/pre-commit

cat > aicoding.config.yaml <<'EOF'
enable_hotfix: true
hotfix_max_diff_files: 2
EOF

cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: major
_phase: Implementation
---
EOF

cat > docs/v1.0/review_minor.md <<'EOF'
## review minor

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_RESULT: pass
REQ_BASELINE_HASH: base
<!-- REVIEW-SUMMARY-END -->

| GWT-ID | REQ-ID | 判定 | 证据类型 | 证据（可复现） | 备注 |
|---|---|---|---|---|---|
| GWT-REQ-001-01 | REQ-001 | ✅ | RUN_OUTPUT | pytest -k smoke | smoke |
EOF

git add -A
git commit -q -m "base"

# case 1: _change_level=hotfix should be accepted by enum gate
cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: 1111111
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: hotfix
_phase: Implementation
---
EOF

git add docs/v1.0/status.md
if ! bash scripts/git-hooks/pre-commit; then
  fail "expected hotfix change_level to pass enum gate"
fi

# case 2: hotfix diff file count over limit must be blocked
git reset --hard -q HEAD
cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: 2222222
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: hotfix
_phase: Implementation
---
EOF
echo "a" > src/a.txt
echo "b" > src/b.txt
echo "c" > src/c.txt
git add docs/v1.0/status.md src/a.txt src/b.txt src/c.txt
if bash scripts/git-hooks/pre-commit; then
  fail "expected hotfix diff count gate to block when staged files exceed hotfix_max_diff_files"
fi

# case 3: hotfix touching REQ-C should be blocked
git reset --hard -q HEAD
cat > docs/v1.0/status.md <<'EOF'
---
_baseline: v0.9
_current: 3333333
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: hotfix
_phase: Implementation
---
EOF
cat > docs/v1.0/requirements.md <<'EOF'
#### REQ-C001：禁止暴露内部字段
- [ ] GWT-REQ-C001-01: Given...
EOF
git add docs/v1.0/status.md docs/v1.0/requirements.md
if bash scripts/git-hooks/pre-commit; then
  fail "expected hotfix REQ-C boundary gate to block"
fi

echo "ok"
