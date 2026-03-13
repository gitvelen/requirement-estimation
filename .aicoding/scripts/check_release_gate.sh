#!/bin/bash
# aicoding-hooks-managed
# Shared release gate for completed Deployment state.

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

ZERO_SHA="0000000000000000000000000000000000000000"

is_zero_sha() {
  local sha="${1:-}"
  [ -n "$sha" ] || return 0
  echo "$sha" | grep -qE '^0+$'
}

is_mainline_branch() {
  local branch="${1:-}"
  [ "$branch" = "main" ] || [ "$branch" = "master" ]
}

yaml_value_from_content() {
  local content="${1:-}"
  local key="${2:-}"
  printf '%s\n' "$content" | awk -v k="$key" '
    NR==1 && $0!="---" {exit}
    NR==1 {in_front=1; next}
    in_front && $0=="---" {exit}
    in_front {
      line=$0
      if (line ~ "^" k ":") {
        sub("^[^:]*:[[:space:]]*", "", line)
        gsub(/[[:space:]]+$/, "", line)
        print line
        exit
      }
    }
  '
}

status_is_completed_content() {
  local content="${1:-}"
  local run_status change_status
  run_status=$(yaml_value_from_content "$content" "_run_status")
  change_status=$(yaml_value_from_content "$content" "_change_status")
  [ "$run_status" = "completed" ] && [ "$change_status" = "done" ]
}

version_tag_from_status_path() {
  local path="${1:-}"
  local version_dir
  version_dir=$(aicoding_extract_version_dir_from_path "$path" || true)
  [ -n "$version_dir" ] || return 1
  basename "${version_dir%/}"
}

candidate_status_paths_for_range() {
  local base_sha="${1:-}"
  local head_sha="${2:-}"
  local path

  if is_zero_sha "$head_sha"; then
    return 0
  fi

  if is_zero_sha "$base_sha"; then
    git ls-tree -r --name-only "$head_sha" 2>/dev/null || true
  else
    git diff --name-only "$base_sha" "$head_sha" 2>/dev/null || true
  fi | while IFS= read -r path; do
    [ -n "$path" ] || continue
    [ "$(basename "$path")" = "status.md" ] || continue
    aicoding_extract_version_dir_from_path "$path" >/dev/null 2>&1 || continue
    printf '%s\n' "$path"
  done | LC_ALL=C sort -u
}

completed_status_paths_for_range() {
  local base_sha="${1:-}"
  local head_sha="${2:-}"
  local path content

  while IFS= read -r path; do
    [ -n "$path" ] || continue
    content=$(git show "${head_sha}:${path}" 2>/dev/null || true)
    [ -n "$content" ] || continue
    status_is_completed_content "$content" || continue
    printf '%s\n' "$path"
  done < <(candidate_status_paths_for_range "$base_sha" "$head_sha")
}

peel_to_commit() {
  local ref="${1:-}"
  git rev-parse "${ref}^{commit}" 2>/dev/null || true
}

tag_commit_from_pushed_refs() {
  local tag_name="${1:-}"
  while IFS='|' read -r current_tag current_commit; do
    [ -n "$current_tag" ] || continue
    if [ "$current_tag" = "$tag_name" ]; then
      printf '%s\n' "$current_commit"
      return 0
    fi
  done <<< "${PUSHED_TAG_COMMITS:-}"
  return 1
}

pre_push_mainline_error() {
  echo "❌ 禁止直接在 main/master 分支上开发并 push"
  echo "   请从 main/master 切出工作分支（如 feat/xxx 或 cr/CR-xxx）后再提交"
  echo ""
  echo "   建议操作："
  echo "   1. git checkout -b feat/your-feature-name"
  echo "   2. git cherry-pick <your-commits>"
  echo "   3. git push -u origin feat/your-feature-name"
  echo "   4. 创建 Pull Request 合并到 main/master"
}

validate_pre_push_release_gate() {
  local current_branch local_ref local_sha remote_ref remote_sha
  local local_branch remote_branch completed_paths branch_commit version_tag tag_commit
  local tmp_input

  tmp_input=$(mktemp)
  trap "rm -f '$tmp_input'" RETURN
  cat > "$tmp_input"

  PUSHED_TAG_COMMITS=""
  while IFS=' ' read -r local_ref local_sha remote_ref remote_sha; do
    [ -n "${local_ref:-}" ] || continue
    case "$local_ref" in
      refs/tags/*)
        is_zero_sha "$local_sha" && continue
        version_tag=${local_ref#refs/tags/}
        tag_commit=$(peel_to_commit "$local_ref")
        [ -n "$tag_commit" ] || tag_commit=$(peel_to_commit "$local_sha")
        [ -n "$tag_commit" ] || continue
        PUSHED_TAG_COMMITS="${PUSHED_TAG_COMMITS}${PUSHED_TAG_COMMITS:+$'\n'}${version_tag}|${tag_commit}"
        ;;
    esac
  done < "$tmp_input"

  current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)

  while IFS=' ' read -r local_ref local_sha remote_ref remote_sha; do
    [ -n "${local_ref:-}" ] || continue
    case "$local_ref" in
      refs/heads/*) ;;
      *) continue ;;
    esac

    local_branch=${local_ref#refs/heads/}
    remote_branch=${remote_ref#refs/heads/}
    completed_paths=$(completed_status_paths_for_range "$remote_sha" "$local_sha")

    if [ -n "$completed_paths" ]; then
      if ! is_mainline_branch "$remote_branch"; then
        echo "❌ 检测到 Deployment completed 状态，但目标分支不是 main/master：${remote_branch:-<unknown>}"
        echo "   completed 只允许在主分支基线发布时推送；请先合入 main/master 并附带版本 tag"
        echo "$completed_paths" | sed 's/^/   - /'
        return 1
      fi

      if ! is_mainline_branch "$local_branch"; then
        echo "❌ 检测到 Deployment completed 状态，但本地分支不是 main/master：${local_branch:-<unknown>}"
        echo "   completed 只允许在主分支基线发布时推送；请先在 main/master 上完成收口"
        echo "$completed_paths" | sed 's/^/   - /'
        return 1
      fi

      branch_commit=$(peel_to_commit "$local_sha")
      while IFS= read -r path; do
        [ -n "$path" ] || continue
        version_tag=$(version_tag_from_status_path "$path" || true)
        [ -n "$version_tag" ] || {
          echo "❌ 无法从 ${path} 推断版本 tag"
          return 1
        }

        tag_commit=$(tag_commit_from_pushed_refs "$version_tag" || true)
        if [ -z "$tag_commit" ]; then
          echo "❌ ${path} 已标记 completed，但本次 push 未包含匹配版本 tag：${version_tag}"
          echo "   请在同一次 push 中推送主分支和 tag（例如：git push origin ${local_branch} refs/tags/${version_tag}）"
          return 1
        fi

        if [ "$tag_commit" != "$branch_commit" ]; then
          echo "❌ ${path} 已标记 completed，但 tag ${version_tag} 未指向当前发布提交"
          echo "   期望提交：${branch_commit}"
          echo "   实际提交：${tag_commit}"
          return 1
        fi
      done <<< "$completed_paths"
      continue
    fi

    if is_mainline_branch "$remote_branch"; then
      if [ -n "${CI:-}" ] || [ -n "${GITHUB_ACTIONS:-}" ] || [ -n "${GITLAB_CI:-}" ]; then
        continue
      fi

      if is_mainline_branch "$current_branch"; then
        pre_push_mainline_error
        return 1
      fi
    fi
  done < "$tmp_input"
}

validate_ci_release_gate() {
  local event_name="${1:-}"
  local branch_name="${2:-}"
  local base_sha="${3:-}"
  local head_sha="${4:-}"
  local completed_paths path version_tag tag_commit head_commit

  completed_paths=$(completed_status_paths_for_range "$base_sha" "$head_sha")
  [ -n "$completed_paths" ] || return 0

  case "$event_name" in
    pull_request)
      # PR 中出现 completed 仅做告警，不阻断。
      # 原因：STRUCTURE.md 推荐通过 PR 合入主分支（Squash and merge），
      # completed 状态会随 PR diff 出现在 PR 中，这是正常流程。
      # 真正的 release gate 由 merge 后的 push 事件 + pre-push hook 保证。
      echo "⚠️ PR 中检测到 completed 状态，合入后将由 push 事件的 release gate 校验基线完整性"
      echo "$completed_paths" | sed 's/^/   - /'
      return 0
      ;;
    push)
      if ! is_mainline_branch "$branch_name"; then
        echo "❌ 检测到 completed 状态推送到非 main/master 分支：${branch_name:-<unknown>}"
        echo "$completed_paths" | sed 's/^/   - /'
        return 1
      fi

      head_commit=$(peel_to_commit "$head_sha")
      while IFS= read -r path; do
        [ -n "$path" ] || continue
        version_tag=$(version_tag_from_status_path "$path" || true)
        [ -n "$version_tag" ] || {
          echo "❌ 无法从 ${path} 推断版本 tag"
          return 1
        }
        if ! git rev-parse -q --verify "refs/tags/${version_tag}" >/dev/null 2>&1; then
          echo "❌ ${path} 已标记 completed，但仓库中缺少匹配 tag：${version_tag}"
          return 1
        fi
        tag_commit=$(peel_to_commit "refs/tags/${version_tag}")
        if [ "$tag_commit" != "$head_commit" ]; then
          echo "❌ ${path} 已标记 completed，但 tag ${version_tag} 未指向当前主分支提交"
          echo "   期望提交：${head_commit}"
          echo "   实际提交：${tag_commit}"
          return 1
        fi
      done <<< "$completed_paths"
      ;;
    *)
      echo "❌ 不支持的 CI release gate 模式：${event_name}"
      return 2
      ;;
  esac
}

main() {
  local mode="${1:-}"
  shift || true

  case "$mode" in
    pre-push)
      validate_pre_push_release_gate "$@"
      ;;
    ci)
      validate_ci_release_gate "$@"
      ;;
    *)
      echo "Usage: $0 pre-push [remote_name remote_url] < stdin"
      echo "   or: $0 ci <pull_request|push> <branch> <base_sha> <head_sha>"
      exit 2
      ;;
  esac
}

main "$@"
