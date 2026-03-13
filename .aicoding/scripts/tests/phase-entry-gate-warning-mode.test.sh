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
cp "$ROOT_DIR/scripts/lib/validation.sh" "$tmp_dir/scripts/lib/validation.sh"
chmod +x "$tmp_dir/scripts/cc-hooks/phase-entry-gate.sh"

cat > "$tmp_dir/aicoding.config.yaml" <<'EOF'
entry_gate_mode: warn
EOF

cat > "$tmp_dir/docs/v1.0/status.md" <<'EOF'
---
_baseline: v0.9
_current: 0000000
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_phase: Implementation
---
EOF

output=$(
  cd "$tmp_dir"
  CLAUDE_PROJECT_DIR="$tmp_dir" \
  bash "$tmp_dir/scripts/cc-hooks/phase-entry-gate.sh" 2>&1 <<'EOF'
{"tool_name":"Write","tool_input":{"file_path":"docs/v1.0/implementation_checklist.md","content":"x"}}
EOF
)

[ -z "$output" ] || fail "expected legacy phase-entry-gate shim to stay silent, got: $output"

echo "ok"
