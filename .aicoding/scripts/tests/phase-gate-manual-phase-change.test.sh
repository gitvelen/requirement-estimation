#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
PHASE_GATE_SRC="${ROOT_DIR}/scripts/cc-hooks/phase-gate.sh"
COMMON_SRC="${ROOT_DIR}/scripts/lib/common.sh"
VALIDATION_SRC="${ROOT_DIR}/scripts/lib/validation.sh"

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
cp "$PHASE_GATE_SRC" scripts/cc-hooks/phase-gate.sh
cp "$COMMON_SRC" scripts/lib/common.sh
cp "$VALIDATION_SRC" scripts/lib/validation.sh
chmod +x scripts/cc-hooks/phase-gate.sh

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: major
_phase: Proposal
---
EOF_STATUS

NEW_STATUS_CONTENT=$(cat <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: major
_phase: Requirements
---
EOF_STATUS
)

INPUT=$(jq -n --arg tool_name "Write" --arg file_path "docs/v1.0/status.md" --arg content "$NEW_STATUS_CONTENT" \
  '{tool_name:$tool_name, tool_input:{file_path:$file_path, content:$content}}')

OUTPUT=$(echo "$INPUT" | CLAUDE_PROJECT_DIR="$tmp_dir" bash scripts/cc-hooks/phase-gate.sh 2>&1)
echo "$OUTPUT" | jq -e '.decision=="block"' >/dev/null 2>&1 \
  || fail "expected phase-gate to block manual-phase transition without wait_confirm, got: $OUTPUT"
echo "$OUTPUT" | grep -q "禁止 AI 自行推进阶段" || fail "expected manual-phase block message, got: $OUTPUT"

cat > docs/v1.0/status.md <<'EOF_STATUS'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: manual
_run_status: wait_confirm
_change_status: in_progress
_change_level: major
_phase: Proposal
---
EOF_STATUS

if ! echo "$INPUT" | CLAUDE_PROJECT_DIR="$tmp_dir" bash scripts/cc-hooks/phase-gate.sh >/dev/null 2>&1; then
  fail "expected phase-gate to allow manual-phase transition when run_status=wait_confirm"
fi

echo "ok"
