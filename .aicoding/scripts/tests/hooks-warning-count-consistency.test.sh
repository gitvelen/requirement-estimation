#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

expected=$(sed -n 's/.*post-commit（软警告，\([0-9][0-9]*\) 个）.*/\1/p' "$ROOT_DIR/hooks.md" | head -1)
[ -n "$expected" ] || fail "cannot parse warning count from hooks.md"

actual=$(find "$ROOT_DIR/scripts/git-hooks/warnings" -maxdepth 1 -name 'w*.sh' -type f | wc -l | tr -d ' ')

[ "$expected" = "$actual" ] || fail "hooks.md says ${expected} warnings, but scripts/git-hooks/warnings has ${actual}"

echo "ok"
