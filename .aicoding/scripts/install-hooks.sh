#!/bin/bash
# aicoding-hooks-managed
# Git hooks 安装脚本
# 从任意目录执行都能定位 repo root；支持备份现有 hooks；可重复安装
set -euo pipefail

# 定位 repo root（无论从哪个目录执行）
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ]; then
  echo "❌ 当前不在 git 仓库中，请在项目目录下执行" >&2
  exit 1
fi

HOOK_DIR="${REPO_ROOT}/.git/hooks"
SCRIPT_DIR="${REPO_ROOT}/.aicoding/scripts/git-hooks"
BACKUP_DIR="${HOOK_DIR}/backup-$(date +%Y%m%d%H%M%S)"

# 依赖检查
for cmd in jq awk grep; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "❌ 缺少依赖: $cmd" >&2; exit 1; }
done

BACKED_UP=false
for hook in pre-commit commit-msg post-commit; do
  SOURCE="${SCRIPT_DIR}/${hook}"
  TARGET="${HOOK_DIR}/${hook}"

  if [ ! -f "$SOURCE" ]; then
    echo "⚠️  源文件不存在，跳过: $SOURCE"
    continue
  fi

  # 备份已有 hook（非本框架安装的）
  if [ -f "$TARGET" ]; then
    if ! grep -q '# aicoding-hooks-managed' "$TARGET" 2>/dev/null; then
      [ "$BACKED_UP" = false ] && mkdir -p "$BACKUP_DIR" && BACKED_UP=true
      cp "$TARGET" "${BACKUP_DIR}/${hook}"
      echo "📦 已备份原有 $hook → ${BACKUP_DIR}/${hook}"
    fi
  fi

  cp "$SOURCE" "$TARGET"
  chmod +x "$TARGET"
  echo "✅ 已安装 $hook"
done

echo ""
echo "✅ Git hooks 安装完成"
[ "$BACKED_UP" = true ] && echo "📦 原有 hooks 已备份至 ${BACKUP_DIR}/"
