#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
PASS=0
FAIL_COUNT=0

fail() {
  echo "FAIL: $*" >&2
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

pass() {
  echo "  ok: $1"
  PASS=$((PASS + 1))
}

tmp_dir=$(mktemp -d)
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT

export CLAUDE_PROJECT_DIR="$tmp_dir"
cd "$tmp_dir"
cat > "$tmp_dir/aicoding.config.yaml" <<'EOF_CFG'
version_dir_pattern: ^v([0-9]+\.[0-9]+\.[0-9]+)$
EOF_CFG

mkdir -p "$tmp_dir/docs/v1.0.0" "$tmp_dir/docs/v1.2.0"
cat > "$tmp_dir/docs/v1.0.0/status.md" <<'EOF_STATUS'
---
_phase: Proposal
---
EOF_STATUS

cat > "$tmp_dir/docs/v1.2.0/status.md" <<'EOF_STATUS'
---
_phase: Implementation
---
EOF_STATUS

source "$ROOT_DIR/scripts/lib/common.sh"
aicoding_load_config

echo "--- configurable version dirs ---"

aicoding_is_version_tag "v1.2.0" \
  && pass "custom version tag recognized" \
  || fail "expected v1.2.0 to match configured version_dir_pattern"

aicoding_detect_version_dir "docs/v1.0.0/design.md"
[ "$AICODING_VERSION_DIR" = "docs/v1.0.0/" ] \
  && pass "detect version dir from semver path" \
  || fail "expected docs/v1.0.0/, got: ${AICODING_VERSION_DIR:-<empty>}"

aicoding_detect_version_dir "$tmp_dir/docs/v1.0.0/design.md"
[ "$AICODING_VERSION_DIR" = "docs/v1.0.0/" ] \
  && pass "detect version dir from absolute semver path" \
  || fail "expected absolute path to resolve docs/v1.0.0/, got: ${AICODING_VERSION_DIR:-<empty>}"

latest_dir=$(aicoding_latest_version_dir "$tmp_dir")
[ "$latest_dir" = "docs/v1.2.0/" ] \
  && pass "latest semver version dir selected" \
  || fail "expected docs/v1.2.0/, got: ${latest_dir:-<empty>}"

aicoding_detect_version_dir "src/main.py"
[ "$AICODING_VERSION_DIR" = "docs/v1.2.0/" ] \
  && pass "fallback detection respects custom version pattern" \
  || fail "expected fallback docs/v1.2.0/, got: ${AICODING_VERSION_DIR:-<empty>}"

echo ""
echo "=== Results: $PASS passed, $FAIL_COUNT failed ==="
[ "$FAIL_COUNT" -eq 0 ] || exit 1
