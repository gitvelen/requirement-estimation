#!/bin/bash
# aicoding-hooks-managed
# Create the release tag and push branch + tag together.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

if [ -f "${REPO_ROOT}/.aicoding/scripts/lib/common.sh" ]; then
  # shellcheck source=./lib/common.sh
  source "${REPO_ROOT}/.aicoding/scripts/lib/common.sh"
else
  # shellcheck source=./lib/common.sh
  source "${SCRIPT_DIR}/lib/common.sh"
fi
aicoding_load_config

usage() {
  echo "Usage: $0 <version-tag> [remote]"
  echo "Example: $0 v1.0 origin"
}

version_tag="${1:-}"
remote_name="${2:-origin}"

[ -n "$version_tag" ] || { usage; exit 2; }
aicoding_is_version_tag "$version_tag" || {
  echo "❌ 版本 tag 格式非法：${version_tag}（期望匹配 ${AICODING_VERSION_DIR_PATTERN}）"
  exit 1
}

current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)
if ! { [ "$current_branch" = "main" ] || [ "$current_branch" = "master" ]; }; then
  echo "❌ release helper 只能在 main/master 分支执行（当前：${current_branch:-<unknown>}）"
  exit 1
fi

git diff --quiet || {
  echo "❌ 工作区存在未提交修改；请先提交或清理后再执行 release helper"
  exit 1
}
git diff --cached --quiet || {
  echo "❌ 暂存区存在未提交修改；请先完成提交后再执行 release helper"
  exit 1
}

status_path="docs/${version_tag}/status.md"
deployment_path="docs/${version_tag}/deployment.md"

[ -f "$status_path" ] || {
  echo "❌ 缺少 status.md：${status_path}"
  echo "   提示：版本 tag 必须与版本目录名一致（如 tag v1.0 对应 docs/v1.0/）"
  exit 1
}
[ -f "$deployment_path" ] || {
  echo "❌ 缺少 deployment.md：${deployment_path}"
  exit 1
}

run_status=$(aicoding_yaml_value "_run_status" "$status_path")
change_status=$(aicoding_yaml_value "_change_status" "$status_path")
phase_name=$(aicoding_yaml_value "_phase" "$status_path")

[ "$phase_name" = "Deployment" ] || {
  echo "❌ ${status_path} 当前不在 Deployment 阶段（当前：${phase_name:-<empty>}）"
  exit 1
}
[ "$run_status" = "completed" ] || {
  echo "❌ ${status_path} 尚未标记 completed（当前：${run_status:-<empty>}）"
  exit 1
}
[ "$change_status" = "done" ] || {
  echo "❌ ${status_path} 尚未标记 done（当前：${change_status:-<empty>}）"
  exit 1
}

grep -q "验收结论：[[:space:]]*通过" "$deployment_path" || {
  echo "❌ ${deployment_path} 缺少“验收结论：通过”记录"
  exit 1
}

head_commit=$(git rev-parse HEAD)
if git rev-parse -q --verify "refs/tags/${version_tag}" >/dev/null 2>&1; then
  tag_commit=$(git rev-parse "refs/tags/${version_tag}^{commit}")
  if [ "$tag_commit" != "$head_commit" ]; then
    echo "❌ 已存在 tag ${version_tag}，但未指向当前提交"
    echo "   当前提交：${head_commit}"
    echo "   tag 提交：${tag_commit}"
    exit 1
  fi
else
  git tag -a "$version_tag" -m "Release ${version_tag}"
fi

git push "$remote_name" "refs/heads/${current_branch}:refs/heads/${current_branch}" "refs/tags/${version_tag}:refs/tags/${version_tag}"
