#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
PHASE_EXIT_SRC="${ROOT_DIR}/scripts/cc-hooks/phase-exit-gate.sh"
LIB_SRC="${ROOT_DIR}/scripts/lib/review_gate_common.sh"
COMMON_SRC="${ROOT_DIR}/scripts/lib/common.sh"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

need_cmd git
need_cmd jq
need_cmd grep

tmp_dir=$(mktemp -d)
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT

cd "$tmp_dir"
git init -q
git config user.email "test@example.com"
git config user.name "test"

mkdir -p scripts/cc-hooks scripts/lib docs/v1.0
cp "$PHASE_EXIT_SRC" scripts/cc-hooks/phase-exit-gate.sh
cp "$LIB_SRC" scripts/lib/review_gate_common.sh
cp "$COMMON_SRC" scripts/lib/common.sh
chmod +x scripts/cc-hooks/phase-exit-gate.sh

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: manual
_run_status: wait_confirm
_change_status: in_progress
_change_level: major
_phase: Requirements
---
EOF_STATUS

cat > docs/v1.0/proposal.md <<'EOF_PROPOSAL'
# proposal
- P-DO-1: 用户可以查看主页
- P-DONT-1: 不做离线导出
EOF_PROPOSAL

cat > docs/v1.0/requirements.md <<'EOF_REQ'
## 1.4 Proposal 覆盖映射
| Proposal Anchor | Requirements |
|---|---|
| P-DO-1 | REQ-001 |
| P-DONT-1 | REQ-C001 |

## 3. 功能性需求

#### REQ-001：主页展示
- [ ] GWT-REQ-001-01: Given 用户已登录，When 打开主页，Then 显示欢迎语

#### REQ-C001：禁止越权
- [ ] GWT-REQ-C001-01: Given 普通用户，When 尝试访问管理员功能，Then 返回拒绝
EOF_REQ

NEW_STATUS_CONTENT=$(cat <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: major
_phase: Design
---
EOF_STATUS
)

run_gate() {
  local input output
  input=$(jq -n --arg tool_name "Write" --arg file_path "docs/v1.0/status.md" --arg content "$NEW_STATUS_CONTENT" \
    '{tool_name:$tool_name, tool_input:{file_path:$file_path, content:$content}}')
  output=$(echo "$input" | CLAUDE_PROJECT_DIR="$tmp_dir" bash scripts/cc-hooks/phase-exit-gate.sh 2>&1 || true)
  printf '%s\n' "$output"
}

output=$(run_gate)
echo "$output" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"' || fail "expected phase-exit-gate to block missing review_requirements.md"
echo "$output" | grep -q "review_requirements.md" || fail "expected missing review_requirements.md message"

cat > docs/v1.0/review_requirements.md <<'EOF_REVIEW'
## 禁止项/不做项确认清单

<!-- CONSTRAINTS-CHECKLIST-BEGIN -->
| ITEM | CLASS | TARGET | SOURCE |
|---|---|---|---|
| 禁止越权访问 | A | REQ-C001 | requirements.md#REQ-C001 |
| 不做离线导出 | B | NON_GOAL | proposal.md#P-DONT-1 |
<!-- CONSTRAINTS-CHECKLIST-END -->

<!-- CONSTRAINTS-CONFIRMATION-BEGIN -->
CONSTRAINTS_CONFIRMED: yes
CONFIRMED_BY: reviewer
CONFIRMED_AT: 2026-02-26
<!-- CONSTRAINTS-CONFIRMATION-END -->
EOF_REVIEW

output=$(run_gate)
if echo "$output" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"'; then
  fail "expected phase-exit-gate to allow Requirements->Design when checks pass, got: $output"
fi

echo "ok"
