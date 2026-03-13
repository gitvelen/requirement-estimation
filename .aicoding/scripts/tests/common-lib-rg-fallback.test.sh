#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

tmp_dir=$(mktemp -d)
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT

mkdir -p "$tmp_dir/bin"
grep_path=$(command -v grep)
[ -n "$grep_path" ] || fail "grep not found"
ln -s "$grep_path" "$tmp_dir/bin/grep"

source "$ROOT_DIR/scripts/lib/common.sh"

sample_file="$tmp_dir/files.txt"
cat > "$sample_file" <<'EOF_FILES'
frontend/src/pages/home.tsx
frontend/src/utils/date.ts
EOF_FILES

output=$(PATH="$tmp_dir/bin" aicoding_regex_search lines "frontend/src/pages/|backend/app/api/" "$sample_file")
[ "$output" = "frontend/src/pages/home.tsx" ] || fail "expected grep fallback to return matched lines"

if ! PATH="$tmp_dir/bin" aicoding_regex_search quiet "^frontend/src/pages/home\\.tsx$" "$sample_file"; then
  fail "expected grep fallback quiet mode to detect matches"
fi

echo "ok"
