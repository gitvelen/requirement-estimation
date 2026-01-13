# Python 依赖管理方式对比

## 方式对比

### 方式 1：requirements.txt（传统方式）

**目录结构**：
```
requirement-estimation-system/
├── requirements.txt          # 所有依赖
├── requirements-dev.txt      # 开发依赖
└── requirements-prod.txt     # 生产依赖
```

**requirements.txt**：
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
```

**优点**：
- ✅ 简单直观
- ✅ 广泛支持
- ✅ 易于理解

**缺点**：
- ❌ 无法锁定子依赖版本
- ❌ 无法记录项目元信息
- ❌ 需要多个文件管理不同环境
- ❌ 不同时间安装可能得到不同版本

---

### 方式 2：pyproject.toml + requirements.txt（混合方式）

**目录结构**：
```
requirement-estimation-system/
├── pyproject.toml            # 项目配置 + 核心依赖
├── requirements.txt          # 由 pyproject.toml 导出
```

**pyproject.toml**：
```toml
[project]
name = "requirement-estimation-system"
version = "1.0.0"
dependencies = [
    "fastapi==0.104.1",
    "uvicorn[standard]==0.24.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0.0"]
```

**生成 requirements.txt**：
```bash
# 使用 pip 导出
pip-compile pyproject.toml -o requirements.txt

# 或使用 uv 导出
uv pip compile pyproject.toml -o requirements.txt
```

**优点**：
- ✅ 有项目元信息
- ✅ 兼容传统工具
- ✅ 可以导出 requirements.txt 供 Docker 使用

**缺点**：
- ❌ 需要维护两套文件
- ❌ 没有锁文件，子依赖版本仍可能变化

---

### 方式 3：pyproject.toml + uv.lock（现代方式，推荐）

**目录结构**：
```
requirement-estimation-system/
├── pyproject.toml            # 项目配置 + 依赖声明
└── uv.lock                   # 锁定所有依赖版本
```

**pyproject.toml**：
```toml
[project]
name = "requirement-estimation-system"
version = "1.0.0"
dependencies = [
    "fastapi>=0.104.0",  # 可以用 >=，由 lock 文件锁定
    "uvicorn[standard]>=0.24.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0.0"]
```

**生成 uv.lock**：
```bash
uv lock
# 或直接安装时自动生成
uv sync
```

**uv.lock**（自动生成）：
```toml
[[package]]
name = "fastapi"
version = "0.104.1"
source = { registry = "https://pypi.org/simple" }
dependencies = [
    { name = "starlette", version = "0.27.0" },
]
checksum = "abc123..."

[[package]]
name = "starlette"
version = "0.27.0"
# ...
```

**安装依赖**：
```bash
# 本地开发
uv sync

# Docker 构建
COPY pyproject.toml uv.lock .
RUN uv pip install --system -e .
# 或
RUN uv sync --frozen
```

**优点**：
- ✅ 锁定所有依赖版本（包括子依赖）
- ✅ 100% 可重现构建
- ✅ 符合 Python 标准（PEP 518/621）
- ✅ 支持依赖分组（dev、prod、test）
- ✅ 包含项目元信息
- ✅ 只需维护一个源文件（pyproject.toml）

**缺点**：
- ⚠️ 需要团队学习新工具（uv）
- ⚠️ 某些老旧工具可能不支持

---

## 📊 三种方式详细对比

| 特性 | requirements.txt | pyproject.toml + txt | pyproject.toml + lock |
|------|------------------|---------------------|----------------------|
| **依赖声明** | requirements.txt | pyproject.toml | pyproject.toml |
| **版本锁定** | ⚠️ 部分锁定（==） | ⚠️ 部分锁定（==） | ✅ 完全锁定（锁文件） |
| **子依赖锁定** | ❌ 不支持 | ❌ 不支持 | ✅ 支持 |
| **项目元信息** | ❌ 不支持 | ✅ 支持 | ✅ 支持 |
| **依赖分组** | ⚠️ 需要多文件 | ⚠️ 需要多文件 | ✅ 支持 |
| **可重现构建** | ⚠️ 70% | ⚠️ 80% | ✅ 100% |
| **Python 标准** | ❌ 约定俗成 | ✅ PEP 518 | ✅ PEP 518 + 621 |
| **工具兼容性** | ✅ 广泛支持 | ✅ 广泛支持 | ⚠️ 需要 uv |
| **学习曲线** | ✅ 简单 | ⚠️ 中等 | ⚠️ 中等 |
| **文件数量** | 多（3个+） | 中（2个+） | 少（2个） |

---

## 🎯 选择建议

### 使用 requirements.txt（方式 1）
```
适用场景：
✅ 简单脚本或小型项目
✅ 个人项目，不需要团队协作
✅ 依赖很少（<10个）
✅ 不需要可重现构建

示例：
- 数据分析脚本
- 自动化工具
- 学习项目
```

### 使用 pyproject.toml + requirements.txt（方式 2）
```
适用场景：
✅ 中型项目
✅ 需要发布到 PyPI
✅ 团队协作
✅ 需要兼容传统工具

示例：
- 开源库
- 企业内部工具
- 需要打包的项目
```

### 使用 pyproject.toml + uv.lock（方式 3）
```
适用场景：
✅ 大型项目（依赖 >20个）
✅ 需要严格的版本控制
✅ CI/CD 自动化
✅ 多人团队协作
✅ 需要可重现构建

示例：
- 生产级应用
- 微服务架构
- SaaS 产品
- 企业核心系统
```

---

## 💡 最佳实践建议

### 小型项目（<10 个依赖）
```bash
# 使用 requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
```

### 中型项目（10-50 个依赖）
```bash
# 使用 pyproject.toml
[project]
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
]

# 导出 requirements.txt 给 Docker 使用
uv pip compile pyproject.toml -o requirements.txt
```

### 大型项目（>50 个依赖）
```bash
# 使用 pyproject.toml + uv.lock
[project]
dependencies = [
    "fastapi",  # 不指定版本，由 lock 文件锁定
]

# 团队成员只需执行
uv sync
```

---

## 🔄 从 requirements.txt 迁移到 pyproject.toml

### 自动迁移（推荐）

```bash
# 1. 安装 uv
pip install uv

# 2. 自动转换 requirements.txt 为 pyproject.toml
uv init --lib  # 或 uv init
# 会自动生成 pyproject.toml

# 3. 从 requirements.txt 导入依赖
uv add $(cat requirements.txt)

# 4. 生成锁文件
uv lock

# 5. 安装依赖
uv sync
```

### 手动迁移

**步骤 1：创建 pyproject.toml**
```bash
cat > pyproject.toml << 'EOF'
[project]
name = "requirement-estimation-system"
version = "1.0.0"
description = "业务需求工作量评估系统"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    # ... 从 requirements.txt 复制其他依赖
]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
EOF
```

**步骤 2：生成锁文件**
```bash
uv lock
```

**步骤 3：修改 Dockerfile**
```dockerfile
# 复制 pyproject.toml 和 uv.lock
COPY pyproject.toml uv.lock .

# 使用 uv sync 安装（自动从 lock 文件读取）
RUN uv sync --frozen --no-dev
```

---

## 📝 实际案例对比

### 场景：团队成员协作

**方式 1：requirements.txt**
```bash
# 开发者 A（1月1日）
pip install -r requirements.txt
# 安装：fastapi==0.104.1, starlette==0.27.0

# 开发者 B（2月1日）
pip install -r requirements.txt
# 安装：fastapi==0.104.1, starlette==0.28.0  ← 子依赖版本不同！
# 可能导致：API 行为不一致
```

**方式 2：pyproject.toml + uv.lock**
```bash
# 开发者 A（1月1日）
uv sync
# 安装：fastapi==0.104.1, starlette==0.27.0
git add uv.lock
git commit -m "Add lock file"

# 开发者 B（2月1日）
git pull
uv sync
# 安装：fastapi==0.104.1, starlette==0.27.0  ← 完全一致！
# 保证：开发环境和生产环境完全相同
```

---

## ❓ 常见问题

### Q1：uv.lock 需要手动维护吗？
**A**：不需要！由 uv 自动生成和维护，你只需要提交到 Git。

### Q2：pyproject.toml 可以和 requirements.txt 共存吗？
**A**：可以！很多项目用 pyproject.toml 管理源，导出 requirements.txt 给 Docker 使用。

### Q3：如何在 Docker 中使用 uv.lock？
**A**：
```dockerfile
COPY pyproject.toml uv.lock .
RUN uv sync --frozen  # --frozen 确保不修改 lock 文件
```

### Q4：更新依赖后怎么办？
**A**：
```bash
# 1. 更新 pyproject.toml
vim pyproject.toml

# 2. 更新锁文件
uv lock

# 3. 提交两个文件
git add pyproject.toml uv.lock
git commit -m "Update dependencies"
```

---

## 🎯 本项目是否需要迁移？

### 当前状态分析
```
项目类型：业务需求评估系统
依赖数量：约 10 个
部署方式：Docker + 内网私服
团队规模：小团队

当前方案：requirements.txt
```

### 建议

**选项 A：保持现状（推荐，如果团队小、依赖少）**
```bash
✅ 优点：
- 简单，无需改动
- 团队熟悉
- Dockerfile 已经优化过

⚠️ 缺点：
- 子依赖版本不锁定
- 长期可能有依赖冲突风险
```

**选项 B：迁移到 pyproject.toml + uv.lock（推荐，如果要长期维护）**
```bash
✅ 优点：
- 100% 可重现构建
- 符合现代 Python 标准
- 更好的依赖管理
- 支持依赖分组（dev/prod/test）

⚠️ 缺点：
- 需要团队学习 uv
- 需要修改 Dockerfile
- 迁移成本（一次性）
```

---

## 📚 总结

| 项目规模 | 推荐方案 | 文件结构 |
|---------|---------|---------|
| 小型（<10 依赖） | requirements.txt | `requirements.txt` |
| 中型（10-50 依赖） | pyproject.toml + 导出 txt | `pyproject.toml` → `requirements.txt` |
| 大型（>50 依赖） | pyproject.toml + lock | `pyproject.toml` + `uv.lock` |

**本项目建议**：
- 如果依赖 < 15 个：保持 requirements.txt
- 如果依赖 > 15 个：迁移到 pyproject.toml + uv.lock
- 如果要长期维护（>1年）：建议迁移

**是否立即迁移**：
```
✅ 需要：
- 依赖数量快速增长
- 团队扩大（>3人）
- 需要严格的可重现构建
- 计划发布到 PyPI

❌ 不需要：
- 依赖稳定（很少变化）
- 小团队（1-2人）
- 快速原型/MVP
```

---

*更新时间：2026-01-07*
