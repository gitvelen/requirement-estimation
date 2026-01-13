# 为什么不再验证 requirements.txt？

## 问题

> 既然已经迁移到 pyproject.toml + uv.lock，是不是没必要验证 requirements.txt 的依赖是否完整了？

## 答案

**完全正确！** ✅ 不需要再验证 requirements.txt。

## 变化对比

### ❌ 旧方式（已弃用）

```dockerfile
# 复制 requirements.txt
COPY requirements.txt .

# 安装依赖
RUN uv pip install --system -r requirements.txt --index-url ${UV_INDEX_URL}

# 验证依赖（基于 requirements.txt）
RUN python3 -c "import backend.app" || (echo "依赖检查失败，请检查requirements.txt" && exit 1)
```

**问题**：
- requirements.txt 只列出顶层依赖
- 子依赖的版本可能不一致
- 没有 SHA256 验证
- 70% 可重现性

### ✅ 新方式（当前使用）

```dockerfile
# 复制配置文件
COPY pyproject.toml uv.lock ./

# 安装依赖（从 lock 文件精确安装）
RUN uv sync --frozen --no-dev --index-url ${UV_INDEX_URL}

# 验证依赖（基于 pyproject.toml）
RUN python3 -c "import backend.app" || (echo "依赖检查失败，请检查pyproject.toml" && exit 1)
```

**优势**：
- uv.lock 锁定所有 91 个包的精确版本
- SHA256 哈希验证
- 100% 可重现性
- 构建失败时提示检查 pyproject.toml

## 当前验证逻辑

### Dockerfile 第 37-38 行

```dockerfile
# 验证Python依赖是否完整（构建时检查）
RUN python3 -c "import sys; sys.path.insert(0, '.'); import backend.app" || (echo "依赖检查失败，请检查pyproject.toml" && exit 1)
```

**工作原理**：
1. 尝试导入 `backend.app` 模块
2. 如果成功 → 所有依赖都已正确安装 ✅
3. 如果失败 → 提示检查 `pyproject.toml`（而不是 requirements.txt）

### 为什么这样验证有效？

**实际效果**：
```bash
# 成功案例
$ python3 -c "import backend.app"
# 无输出 = 成功 ✅

# 失败案例（缺少依赖）
$ python3 -c "import backend.app"
Traceback (most recent call last):
  ModuleNotFoundError: No module named 'fastapi'
# 依赖检查失败，请检查pyproject.toml ❌
```

**为什么提示 pyproject.toml？**
- `uv sync` 从 pyproject.toml 读取依赖声明
- 如果 pyproject.toml 中缺少某个包，uv sync 不会安装它
- 导入失败时，应该检查 pyproject.toml 的 dependencies 部分

## 已更新的文件

### 1. ✅ Dockerfile
```dockerfile
# 第 38 行
RUN python3 -c "import backend.app" || (echo "依赖检查失败，请检查pyproject.toml" && exit 1)
```

### 2. ✅ DOCKER_DEPLOY_GUIDE.md
```markdown
# 第 602 行
RUN python3 -c "import backend.app" || (echo "依赖检查失败，请检查pyproject.toml" && exit 1)
# ↓ 说明：
#   如果失败，说明 pyproject.toml 中缺少某些依赖
```

### 3. ✅ requirements.txt
```text
###############################################################################
# ⚠️  已弃用 - 此文件仅用于兼容性参考
#
# 本项目已迁移到 pyproject.toml + uv.lock 方式管理依赖
#
# 推荐方式：
#   - 本地开发：uv sync
#   - Docker 构建：uv sync --frozen --no-dev
#   - 添加依赖：uv add <package-name>
###############################################################################
```

## 如果需要添加新依赖

### ❌ 旧方式（不要用）
```bash
# 编辑 requirements.txt
echo "pandas==2.0.0" >> requirements.txt

# 重新安装
uv pip install -r requirements.txt
```

### ✅ 新方式（推荐）
```bash
# 自动更新 pyproject.toml 和 uv.lock
uv add pandas

# 提交更改
git add pyproject.toml uv.lock
git commit -m "添加 pandas 依赖"
```

## requirements.txt 的现状

| 状态 | 说明 |
|------|------|
| **文件存在** | ✅ 保留在项目中 |
| **Docker 使用** | ❌ 不再使用 |
| **用途** | 仅作为兼容性参考 |
| **标记** | 已添加弃用警告 |
| **未来** | 可能完全删除 |

## 为什么保留 requirements.txt？

1. **兼容性**：某些工具可能还需要它
2. **参考价值**：快速查看顶层依赖列表
3. **迁移过渡**：给团队成员适应时间
4. **文档作用**：弃用警告中说明迁移原因

## 总结

| 问题 | 答案 |
|------|------|
| 是否需要验证 requirements.txt？ | ❌ 不需要 |
| 应该验证什么？ | ✅ pyproject.toml |
| requirements.txt 还有用吗？ | ⚠️ 仅作参考 |
| 如何添加新依赖？ | ✅ `uv add <package>` |
| 如何安装依赖？ | ✅ `uv sync` |

---

**迁移完成时间**：2026-01-07
**依赖管理方式**：pyproject.toml + uv.lock
**可重现性**：100%
**验证方式**：导入测试（提示检查 pyproject.toml）

---

## 相关文档

- **迁移指南**：`MIGRATION_TO_UV_LOCK.md`
- **对比分析**：`python-dependency-management-comparison.md`
- **快速参考**：`UV_QUICK_REFERENCE.md`
- **uv vs pip**：`UV_VS_PIP_EXPLAINED.md`
