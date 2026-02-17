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

cd "$tmp_dir"
git init -q

cat > aicoding.config.yaml <<'EOF'
abc: wrong
a.c: right
EOF

mkdir -p docs/v1.0
cat > docs/v1.0/status.md <<'EOF'
---
axb: wrong
a.b: right
_phase: Implementation
---
EOF

export CLAUDE_PROJECT_DIR="$tmp_dir"
source "$ROOT_DIR/scripts/lib/common.sh"
AICODING_STATUS_FILE="$tmp_dir/docs/v1.0/status.md"

yaml_val=$(aicoding_yaml_value "a.b")
[ "$yaml_val" = "right" ] || fail "expected exact YAML key match for a.b, got: ${yaml_val:-<empty>}"

config_val=$(aicoding_config_value "a.c")
[ "$config_val" = "right" ] || fail "expected exact config key match for a.c, got: ${config_val:-<empty>}"

unset CLAUDE_SESSION_ID || true
session_key=$(aicoding_session_key)
echo "$session_key" | grep -qE '^[0-9]{8}-[0-9]{6}-[0-9]+$' || fail "expected fallback session key format YYYYMMDD-HHMMSS-<pid>, got: ${session_key}"

echo "ok"
