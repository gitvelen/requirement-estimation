# v2.7 Skill Runtime、Memory 与画像联动 部署指南

## 文档元信息
| 项 | 值 |
|---|---|
| 状态 | Completed |
| 作者 | Codex |
| 日期 | 2026-03-15 |
| 版本 | v0.3 |
| 目标环境 | STAGING / TEST |
| 基线版本（对比口径） | `v2.6` |
| 部署版本 | `HEAD`（working tree） |

## 本次上线CR列表
| CR-ID | 标题 |
|---|---|
| （无 CR，新版本首次交付） | v2.7 新版本首次交付；回溯记录 `CR-20260314-001` 已实施，不作为上线前 Active CR |

## 环境要求
- Linux + Docker + Docker Compose
- 可执行 `pytest`、`curl`
- backend 正式发布配置源固定为 `.env.backend.internal`
- frontend 内网部署需提供 `FRONTEND_BACKEND_UPSTREAM`

## 配置清单（🔴 MUST）
| 配置项 | 目标值/口径 | 说明 |
|---|---|---|
| backend 配置源 | `.env.backend.internal` | `deploy-backend-internal.sh` 会复制到 `.env.backend` 后发布 |
| `ENABLE_V27_PROFILE_SCHEMA` | `true/false` | v2.7 schema 基座开关 |
| `ENABLE_V27_RUNTIME` | `true/false` | Skill Runtime、execution-status、Memory 查询开关 |
| `ENABLE_SERVICE_GOVERNANCE_IMPORT` | `true/false` | admin 服务治理导入开关 |
| `ENABLE_SYSTEM_CATALOG_PROFILE_INIT` | `true/false` | 系统清单 confirm 空画像初始化开关 |
| `DASHSCOPE_API_KEY` | 非空 | 内网后端脚本强校验 |
| `DASHSCOPE_API_BASE` | 非空 | 内网后端脚本强校验 |
| `EMBEDDING_API_BASE` | 非空 | 内网后端脚本强校验 |
| `EMBEDDING_MODEL` | 非空 | 内网后端脚本强校验 |
| `FRONTEND_BACKEND_UPSTREAM` | `<backend-host>:<port>` | 前后端分离内网部署时渲染 runtime nginx upstream |

## 发布前检查
| 项 | 命令 | 结果 |
|---|---|---|
| 清理脚本 + 内网部署脚本回归 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_cleanup_v27.py tests/test_deploy_backend_internal_script.py tests/test_deploy_frontend_internal_script.py` | ✅ `7 passed in 1.46s` |

## 发布步骤

### 1. 备份运行数据
至少备份以下文件或目录：

```bash
mkdir -p backups/v2.7_predeploy_$(date +%Y%m%d_%H%M%S)
cp -a data uploads logs backups/v2.7_predeploy_$(date +%Y%m%d_%H%M%S)/
```

如果只做文件级备份，至少覆盖：
- `data/system_profiles.json`
- `data/import_history.json`
- `data/knowledge_store.json`
- `data/memory_records.json`
- `data/runtime_executions.json`
- `data/extraction_tasks.json`

### 2. 首次 v2.7 发布前执行清理
此步骤仅用于首次切入 v2.7 时清理旧 schema / `history_report` 残留。后续月度系统清单更新不应重复执行此脚本来“重置画像”。

```bash
python scripts/cleanup_v27_profile_assets.py \
  --data-dir data \
  --backup-dir backups/v2.7_cleanup_$(date +%Y%m%d_%H%M%S)
```

验收口径：
- `legacy_profile_records.after = 0`
- `history_report_import_records.after = 0`
- `history_report_knowledge_records.after = 0`

### 3. 配置 `.env.backend.internal`
在 `.env.backend.internal` 中准备 v2.7 目标配置，至少确认：

```bash
ENABLE_V27_PROFILE_SCHEMA=false
ENABLE_V27_RUNTIME=false
ENABLE_SERVICE_GOVERNANCE_IMPORT=false
ENABLE_SYSTEM_CATALOG_PROFILE_INIT=false
```

说明：
- 发布时按步骤逐个打开，不建议四个开关一次性同时打开。
- `deploy-backend-internal.sh` 会把 `.env.backend.internal` 复制为 `.env.backend`，并校验 `DASHSCOPE_API_KEY`、`DASHSCOPE_API_BASE`、`EMBEDDING_API_BASE`、`EMBEDDING_MODEL`。

### 4. 按固定顺序启用后端开关
固定启用顺序：
1. `ENABLE_V27_PROFILE_SCHEMA`
2. `ENABLE_V27_RUNTIME`
3. `ENABLE_SERVICE_GOVERNANCE_IMPORT`
4. `ENABLE_SYSTEM_CATALOG_PROFILE_INIT`

每启用一步后都执行一次后端部署：

```bash
bash deploy-backend-internal.sh
```

推荐在每一步后至少验证：
- `curl -fsS http://<backend-host>/api/v1/health`
- 关键接口未返回 5xx

### 5. 构建并部署前端
先在仓库内生成前端产物，再执行内网前端部署：

```bash
cd frontend && npm run build
cd ..
FRONTEND_BACKEND_UPSTREAM=<backend-host>:<port> bash deploy-frontend-internal.sh
```

说明：
- `deploy-frontend-internal.sh` 会在部署前后执行 `nginx -t`
- 运行时 nginx 配置文件为 `frontend/nginx.internal.runtime.conf`

### 6. 发布后验证
至少验证以下链路：

```bash
curl -fsS http://<backend-host>/api/v1/health
curl -fsS http://<frontend-host>/
curl -fsS http://<backend-host>/api/v1/system-profiles/<system_id>/profile/execution-status
```

需要重点确认：
- PM 导入页运行态查询走 `profile/execution-status`
- `profile/extraction-status` 兼容路径仍可读取相同 execution 结果
- admin 服务治理页可打开，非 admin 不得执行全局治理导入
- 系统清单 confirm 仅初始化空画像；非空画像返回 `profile_not_blank` 或等效跳过原因

## 业务规则提示（🔴 MUST）
- 系统清单每月更新时，不得把解析结果粗暴覆盖到已有画像。
- 只有在“首次初始化”或“D1-D5 canonical 全空画像”场景下，系统清单 confirm 才允许自动写入画像。
- 判空时只看 `profile_data` 下 D1-D5 `canonical` 字段；忽略 `field_sources`、`ai_suggestions` 和 Memory 记录。
- 系统清单中的“功能描述”只进入 `D1.service_scope`。
- 系统清单中的“关联系统”只进入 `integration_interfaces.canonical.extensions.catalog_related_systems`，不得直接改写 D3 canonical。

## 回滚方案

### L1（开关级回滚，优先）
触发条件：
- 画像写入污染
- Memory / execution 写入异常
- 服务治理或系统清单联动阻断主链路

回滚顺序：

```bash
ENABLE_SYSTEM_CATALOG_PROFILE_INIT=false
ENABLE_SERVICE_GOVERNANCE_IMPORT=false
ENABLE_V27_RUNTIME=false
ENABLE_V27_PROFILE_SCHEMA=false
```

然后重新执行：

```bash
bash deploy-backend-internal.sh
```

### L2（版本级回滚）
触发条件：
- L1 无法止损
- v2.7 行为与数据结构已产生系统性回归

回滚步骤：
1. 回退到 `v2.6`
2. 恢复发布前备份的 `data/` 与相关上传目录
3. 重新执行内网 backend / frontend 部署脚本

## 当前状态
- 已完成清理脚本与内网部署脚本自动化回归：`7 passed in 1.46s`
- 主文档已同步到 v2.7 口径：服务治理、系统清单、execution-status、Memory、内网配置源
- 2026-03-14 23:42 已在当前主机完成 STAGING/TEST 运行态发布：`DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 docker-compose build backend && docker-compose up -d backend`；frontend 继续挂载最新 `frontend/build`
- 2026-03-14 23:59 User 已完成 `REQ-003/REQ-004` 人工 E2E 验证并反馈“正常”；当前 `docs/v2.7/status.md` 已收口为 `_phase=Deployment`、`_change_status=done`、`_run_status=completed`

## 验收记录
- 验收时间：2026-03-14 23:59
- 验收人：User
- 验收结论：通过
- 验收说明：User 登录可验收环境验证 `REQ-003/REQ-004` 后反馈“正常”

## 变更记录
| 版本 | 日期 | 说明 | 作者 |
|---|---|---|---|
| v0.1 | 2026-03-14 | 初始化 v2.7 部署指南，固化 `.env.backend.internal`、四开关启用顺序、首次清理步骤、月度系统清单更新约束与回滚路径 | Codex |
| v0.2 | 2026-03-14 | 补记 STAGING/TEST 实际发布与人工验收通过记录，并同步 Deployment 完成态 | Codex |
| v0.3 | 2026-03-15 | 补齐 Deployment 模板要求的目标环境与本次上线 CR 区块，作为 v2.7 发布基线文档 | Codex |
