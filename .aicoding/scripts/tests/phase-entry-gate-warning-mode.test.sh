#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

tmp_dir=$(mktemp -d)
cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

mkdir -p "$tmp_dir/scripts/cc-hooks" "$tmp_dir/scripts/lib" "$tmp_dir/docs/v1.0"
cp "$ROOT_DIR/scripts/cc-hooks/phase-entry-gate.sh" "$tmp_dir/scripts/cc-hooks/phase-entry-gate.sh"
cp "$ROOT_DIR/scripts/lib/common.sh" "$tmp_dir/scripts/lib/common.sh"
chmod +x "$tmp_dir/scripts/cc-hooks/phase-entry-gate.sh"

cat > "$tmp_dir/aicoding.config.yaml" <<'EOF'
entry_gate_mode: warn
EOF

cat > "$tmp_dir/docs/v1.0/status.md" <<'EOF'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_phase: Implementation
---
EOF

output=$(
  rm -f /tmp/aicoding-reads-test-entry-warn.log 2>/dev/null || true
  rm -f /tmp/aicoding-entry-passed-*test-entry-warn* 2>/dev/null || true
  CLAUDE_PROJECT_DIR="$tmp_dir" \
  CLAUDE_SESSION_ID="test-entry-warn" \
  bash "$tmp_dir/scripts/cc-hooks/phase-entry-gate.sh" 2>&1 <<'EOF'
{"tool_name":"Write","tool_input":{"file_path":"docs/v1.0/implementation_checklist.md","content":"x"}}
EOF
)

echo "$output" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"' && fail "expected CC-7 warn mode to avoid hard block"
echo "$output" | grep -q "CC-7" || fail "expected warning hint when required files are not read"

echo "ok"
