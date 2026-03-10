# v2.6 文档分块与 Token 预算 部署指南

## 文档元信息
| 项 | 值 |
|---|---|
| 状态 | Review |
| 作者 | Codex |
| 日期 | 2026-03-09 |
| 版本 | v0.5 |
| 目标环境 | STAGING |
| 基线版本（对比口径） | `v2.5` |
| 部署版本 | `HEAD`（working tree） |

## 本次上线 CR 列表
| CR-ID | 标题 |
|---|---|
| CR-20260309-001 | 文档分块处理以适配内网 LLM Token 限制 |

## 环境要求
- Linux + Python 3.10
- 可执行 `pytest`、`git`、`curl`
- 需求目标模型口径与内网一致：`LLM_MODEL=Qwen3-32B`、`EMBEDDING_MODEL=Qwen3-Embedding-8B`

## 配置清单（🔴 MUST）
| 配置项 | 目标值 | 说明 |
|---|---|---|
| `LLM_MODEL` | `Qwen3-32B` | 生成总结模型 |
| `EMBEDDING_MODEL` | `Qwen3-Embedding-8B` | 向量化模型 |
| `LLM_MAX_CONTEXT_TOKENS` | `32000` | 模型最大上下文 |
| `LLM_INPUT_MAX_TOKENS` | `25000` | 单次输入正文预算 |
| `LLM_CHUNK_OVERLAP_PARAGRAPHS` | `2` | 段落重叠默认值 |
| `ENABLE_LLM_CHUNKING` | `true` | 分块开关；回滚优先级最高 |

## 发布前检查
| 项 | 命令 | 结果 |
|---|---|---|
| 配置核对 | `rg -n "LLM_MODEL=Qwen3-32B|EMBEDDING_MODEL=Qwen3-Embedding-8B|LLM_MAX_CONTEXT_TOKENS=32000|LLM_INPUT_MAX_TOKENS=25000|LLM_CHUNK_OVERLAP_PARAGRAPHS=2|ENABLE_LLM_CHUNKING=true" .env.backend .env.backend.example .env.backend.internal` | ✅ 三套环境文件均命中 |
| 项目级测试门禁 | `.venv/bin/python -m pytest -q --tb=short` | ✅ `210 passed in 63.61s` |
| 前端构建门禁 | `cd frontend && npm run build` | ✅ `Compiled successfully.` |
| 后端编译检查 | `.venv/bin/python -m compileall -q backend` | ✅ 无输出，退出码 0 |
| 回归门禁 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_token_counter.py tests/test_llm_client.py tests/test_profile_summary_service.py tests/test_system_profile_import_api.py tests/test_knowledge_import_api.py tests/test_knowledge_routes_helpers.py` | ✅ `61 passed, 1 warning in 20.49s` |
| 覆盖率门禁 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p pytest_cov --cov=backend.utils.token_counter --cov=backend.utils.llm_client --cov=backend.service.profile_summary_service --cov-report=term-missing tests/test_token_counter.py tests/test_llm_client.py tests/test_profile_summary_service.py` | ✅ 总覆盖率 `92%` |
| 依赖差异 | `git diff --unified=0 v2.5 -- requirements.txt backend/requirements.txt pyproject.toml` | ✅ 无新增运行时依赖 |
| 基线回滚点 | `git rev-parse --verify --quiet v2.5^{commit}` | ✅ `7a0c6befb88ad848459264ba2456543bea5f9b44` |

## 部署步骤
### 1. 切换代码并核对配置
```bash
cd /home/admin/Claude/requirement-estimation-system
git rev-parse --short HEAD
```

说明：
- 默认发布路径使用 `deploy-all.sh` / `docker-compose.yml`。
- 这台外网 STAGING 服务器当前默认发布路径仍使用仓库根 `.env`；`.env.backend` / `.env.backend.internal` 仅作为内网或等效环境的配置样例，不是本机默认配置源。

确认以下接口仍保持兼容：
- `POST /api/v1/knowledge/imports`
- `POST /api/v1/system-profiles/{system_id}/profile/import`
- `GET /api/v1/system-profiles/{system_id}/profile/extraction-status`

### 2. 更新环境变量
确保部署环境存在以下键：
```bash
LLM_MODEL=Qwen3-32B
EMBEDDING_MODEL=Qwen3-Embedding-8B
LLM_MAX_CONTEXT_TOKENS=32000
LLM_INPUT_MAX_TOKENS=25000
LLM_CHUNK_OVERLAP_PARAGRAPHS=2
ENABLE_LLM_CHUNKING=true
```

### 3. 执行发布前门禁
```bash
.venv/bin/python -m pytest -q --tb=short
(cd frontend && npm run build)
.venv/bin/python -m compileall -q backend

PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q \
  tests/test_token_counter.py \
  tests/test_llm_client.py \
  tests/test_profile_summary_service.py \
  tests/test_system_profile_import_api.py \
  tests/test_knowledge_import_api.py \
  tests/test_knowledge_routes_helpers.py
```

### 4. 执行部署
- 采用项目既有部署方式发布 backend。
- 不需要新增数据库迁移。
- 不需要修改前端路由或请求契约。
- STAGING 默认命令：`printf '2\n' | bash deploy-all.sh`

### 5. 发布后验证
至少验证以下链路：
1. `POST /api/v1/system-profiles/{system_id}/profile/import` 成功后返回 `extraction_task_id`。
2. `POST /api/v1/knowledge/imports` 绑定系统导入成功。
3. `GET /api/v1/system-profiles/{system_id}/profile/extraction-status` 能查询到异步任务状态。
4. 超长文档场景不再报 Token 超限。

## 回滚方案
### L1（开关级回滚，优先）
触发条件：
- 超长文档分块后失败率升高
- 异步总结任务耗时异常
- 线上出现与 chunking 直接相关的问题

执行步骤：
```bash
ENABLE_LLM_CHUNKING=false
```

验证：
- 普通文档仍可通过单次调用处理
- 超长文档返回固定错误提示，不再进入分块

### L2（版本级回滚）
触发条件：
- L1 无法止损
- 接口兼容性或总结链路发生系统性回归

执行步骤：
```bash
git checkout v2.5
# 按项目既有发布流程重新部署 backend
```

基线证据：
- `git rev-parse --verify --quiet v2.5^{commit}` -> `7a0c6befb88ad848459264ba2456543bea5f9b44`

## 当前状态
- 本轮已完成发布 runbook、配置核对、回滚步骤与基线定位。
- Testing 阶段项目级结果门禁已通过：`210 passed` + `frontend build` + `compileall`。
- STAGING 已执行实际发布纠偏：当前这台外网服务器继续使用根 `.env`，实际运行 `qwen-turbo` / `text-embedding-v2` + `ENABLE_LLM_CHUNKING=true`；文档中的 `Qwen3-32B` / `Qwen3-Embedding-8B` 为 v2.6 需求目标口径。

## 部署执行结果（STAGING）
| 项 | 命令 | 结果 |
|---|---|---|
| STAGING 实际发布 | `printf '2\n' \| bash deploy-all.sh` | ✅ 成功；buildx<0.17 时自动回退经典构建，backend 镜像重建并重启 |
| backend 健康检查 | `curl -fsS http://127.0.0.1:443/api/v1/health` | ✅ `{"status":"healthy","service":"业务需求工作量评估系统","version":"1.0.0"}` |
| API 网关健康检查 | `curl -fsS http://127.0.0.1/api/v1/health` | ✅ `{"status":"healthy","service":"业务需求工作量评估系统","version":"1.0.0"}` |
| 容器状态 | `docker-compose ps` | ✅ `requirement-backend=Up (healthy)`；`requirement-frontend=Up` |
| backend 应用配置核验（本机） | `docker exec requirement-backend /app/.venv/bin/python -c "from backend.config.config import settings; ..."` | ✅ 当前 STAGING 服务器实际读取根 `.env`：`DASHSCOPE_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1`、`LLM_MODEL=qwen-turbo`、`EMBEDDING_MODEL=text-embedding-v2`、`ENABLE_LLM_CHUNKING=true` |
| frontend 入口可达 | `curl -i -s http://127.0.0.1/ \| head -n 10` | ✅ `HTTP/1.1 200 OK`，返回 `index.html` 与 `main.011cab13.js` |
| frontend 容器重建 | `docker-compose up -d --force-recreate frontend` | ✅ 已执行；修复 `rm -rf frontend/build` 后 bind mount 持有旧空目录导致的 403 |

说明：
- `deploy-all.sh` 只重建 backend，frontend 仍保持运行；本次因为 `npm run build` 会删除并重建 `frontend/build/`，旧 frontend 容器继续绑定旧目录 inode，必须额外 `--force-recreate frontend` 才能看到新产物。
- v2.6 需求口径与这台 STAGING 服务器的实际运行口径需要分开记录：前者用于分块阈值与内网等效测试，后者以本机根 `.env` 的外网配置为准。

## 验收记录
- 验收时间：2026-03-10 09:23:15 CST
- 验收人：User
- 验收结论：通过
- 验收说明：验收通过，要求提交并推送到远端 master

## 逃生通道审计说明
- 触发时间：2026-03-10
- 触发场景：提交 `docs/v2.6/status.md` 时，仓库 pre-commit 规则要求“新建 status.md 首次提交 `_phase` 必须为 `ChangeManagement`”，与本次“v2.6 整体一次性交付并以完成态收口”冲突。
- 用户授权：已明确授权继续并使用 `--no-verify`。
- 实际操作：仅对本次 release 收口提交使用 `git commit --no-verify`，不使用 `--no-verify` 跳过后续验证、合并结果复验或推送前检查。
- 风险评估：低到中（主要是流程性文档门禁绕过；运行时代码已完成项目级测试、前端构建与后端编译检查）。
- 补偿控制：已保留并复核新鲜验证证据：`.venv/bin/python -m pytest -q --tb=short`=`210 passed`、`cd frontend && npm run build`=`Compiled successfully.`、`python3 -m compileall -q /home/admin/Claude/requirement-estimation-system/backend`=退出码 0。

## 变更记录
| 版本 | 日期 | 说明 | 作者 |
|---|---|---|---|
| v0.1 | 2026-03-09 | 初始化 v2.6 部署指南，补齐配置键、门禁、回滚开关与基线 tag | Codex |
| v0.2 | 2026-03-09 | 补记项目级结果门禁与发布前检查口径 | Codex |
| v0.3 | 2026-03-09 | 首次补记部署路径与环境配置关系（后续已在 v0.5 更正为按环境区分配置源） | Codex |
| v0.4 | 2026-03-09 | 回填 STAGING 实际发布结果、健康检查、容器 env 核验与 frontend 强制重建证据 | Codex |
| v0.5 | 2026-03-09 | 修正模型命名漂移与部署环境口径混写，明确区分需求目标模型与当前 STAGING 实际运行配置 | Codex |
| v0.6 | 2026-03-10 | 补记用户验收通过结论，准备合入主分支并推送远端 | Claude |
| v0.7 | 2026-03-10 | 记录 `--no-verify` 授权与补偿控制，支持本次一次性交付收口提交 | Claude |
