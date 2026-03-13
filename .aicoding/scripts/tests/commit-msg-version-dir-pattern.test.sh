#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
COMMIT_MSG_SRC="${ROOT_DIR}/scripts/git-hooks/commit-msg"
COMMON_SRC="${ROOT_DIR}/scripts/lib/common.sh"
VALIDATION_SRC="${ROOT_DIR}/scripts/lib/validation.sh"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

tmp_dir=$(mktemp -d)
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT

cd "$tmp_dir"
git init -q
git config user.email "test@example.com"
git config user.name "test"

mkdir -p .aicoding scripts/git-hooks scripts/lib docs/v1.0.0 docs/v1.1.0
cp "$COMMIT_MSG_SRC" scripts/git-hooks/commit-msg
cp "$COMMON_SRC" scripts/lib/common.sh
cp "$VALIDATION_SRC" scripts/lib/validation.sh
chmod +x scripts/git-hooks/commit-msg

cat > .aicoding/aicoding.config.yaml <<'EOF_CFG'
version_dir_pattern: ^v([0-9]+\.[0-9]+\.[0-9]+)$
EOF_CFG

cat > docs/v1.0.0/status.md <<'EOF_STATUS'
---
_phase: Deployment
_change_level: major
---
EOF_STATUS

cat > docs/v1.1.0/status.md <<'EOF_STATUS'
---
_phase: Proposal
_change_level: major
---
EOF_STATUS

cat > msg.txt <<'EOF_MSG'
feat: multi version semver commit
EOF_MSG

git add .aicoding/aicoding.config.yaml docs/v1.0.0/status.md docs/v1.1.0/status.md
if bash scripts/git-hooks/commit-msg msg.txt; then
  fail "expected commit-msg to block multi-version staged changes for semver version dirs"
fi

grep -q "多版本" <(bash scripts/git-hooks/commit-msg msg.txt 2>&1 || true) \
  || fail "expected multi-version error message for semver version dirs"

echo "ok"
