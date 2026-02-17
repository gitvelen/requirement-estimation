#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PASS=0; FAIL=0; SKIP=0

for t in "$SCRIPT_DIR"/*.test.sh; do
  [ -f "$t" ] || continue
  name=$(basename "$t")
  echo "=== $name ==="
  if bash "$t" 2>&1; then
    ((PASS+=1))
  else
    echo "--- $name FAILED ---"
    ((FAIL+=1))
  fi
  echo ""
done

echo "==============================="
echo "Total: $((PASS+FAIL)) | Pass: $PASS | Fail: $FAIL"
echo "==============================="
[ "$FAIL" -eq 0 ] || exit 1
