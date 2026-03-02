# v2.4 系统画像增强与评估机制优化 部署指南

## 文档元信息
| 项 | 值 |
|---|---|
| 状态 | Approved |
| 作者 | Codex |
| 评审（通常为 AI 工具） | Codex |
| 日期 | 2026-03-02 |
| 版本 | v0.7 |
| 目标环境 | STAGING |
| 基线版本（对比口径） | `v2.3` |
| 部署版本 | `HEAD`（working tree） |

## 本次上线CR列表（🔴 MUST，Deployment门禁依赖）
| CR-ID | 标题 |
|-------|------|
| CR-20260301-001 | 信息展示页纠错交互一致性与负责系统可见范围修正 |
| CR-20260302-001 | 信息展示页域标题去冗余与域导航左对齐 |
| CR-20260302-002 | 信息展示页旧 system_id 容错与当前 ID 优先 |
| CR-20260302-003 | 内网部署目录属主对齐与默认账号初始化 |

## 环境要求
- 运行环境：Linux + Python venv（`.venv`）+ Node.js/npm
- 服务依赖：FastAPI 服务可访问 `http://127.0.0.1/api/v1/health`
- 权限要求：可执行 pytest、npm build、git worktree、部署脚本

## 配置清单（env/文件）
| 配置项 | 说明 | 默认值 | 是否敏感 | 来源 |
|---|---|---|---|---|
| `DASHSCOPE_API_KEY` | AI 提取与估算服务密钥 | 环境注入 | 是 | `design.md` §0.5 |
| `DASHSCOPE_MODEL` | 估算/提取模型 | `qwen-max` | 否 | `design.md` §0.5 |
| `AI_EXTRACTION_TIMEOUT` | AI 提取超时阈值 | `120s` | 否 | `design.md` §0.5 |
| `EXTRACTION_POLL_INTERVAL` | 前端轮询间隔 | `3000ms` | 否 | `design.md` §0.5 |
| `PROFILE_MIGRATION_ENABLED` | 画像迁移开关 | `true` | 否 | `design.md` §0.5 |

## 部署前检查
- [x] CR-20260302-002 增量回归：`cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileBoardPage.v24.test.js -t "prefers current system id from system list when profile carries stale system_id"`（通过）
- [x] CR-20260302-002 质量门禁：`cd frontend && npx eslint src/pages/SystemProfileBoardPage.js src/__tests__/systemProfileBoardPage.v24.test.js --max-warnings=0`（通过）
- [x] CR-20260302-002 后端容错回归：`.venv/bin/pytest -q tests/test_system_profile_publish_rules.py -k "profile_events_returns_empty_when_profile_not_created"`（通过）
- [x] CR-20260302-003 默认账号初始化回归：`.venv/bin/pytest -q tests/test_user_service_internal_bootstrap.py`（通过）
- [x] CR-20260302-003 内网部署脚本语法检查：`bash -n deploy-backend-internal.sh`（通过）
- [x] CR-20260302-003 默认账号初始化脚本验证：`python3 scripts/init_internal_users.py --data-dir $(mktemp -d)`（通过）
- [x] 关键回归通过：`.venv/bin/python -m pytest -q --tb=short` → `130 passed`
- [x] 构建通过：`cd frontend && npm run build`（成功，含非阻断 warning）
- [x] 类型检查通过：`.venv/bin/python -m compileall -q backend`
- [x] 健康检查通过：`curl -fsS http://127.0.0.1/api/v1/health`
- [x] 回滚路径演练：L1/L2 均有命令证据（见下文）

## 部署步骤（STAGING）
### 1. 准备环境
```bash
cd /home/admin/Claude/requirement-estimation-system
source .venv/bin/activate
```

### 2. 执行发布前门禁
```bash
.venv/bin/python -m pytest -q --tb=short
cd frontend && npm run build
cd ..
.venv/bin/python -m compileall -q backend
```

### 3. 执行部署
```bash
printf '2\n' | bash deploy-all.sh
```

### 4. 验证部署
```bash
curl -fsS http://127.0.0.1/api/v1/health
```
判定标准：HTTP 200 且返回 `{"status":"healthy"...}`。

## 部署执行结果（本轮）
| 项 | 命令 | 结果 |
|---|---|---|
| STAGING 部署 | `printf '2\\n' | bash deploy-all.sh` | 成功；BuildKit 检测失败后自动回退经典构建，`backend/frontend` 保持运行 |
| 健康检查（本机） | `curl -fsS http://127.0.0.1/api/v1/health` | `{\"status\":\"healthy\",\"service\":\"业务需求工作量评估系统\",\"version\":\"1.0.0\"}` |
| 健康检查（公网） | `curl -fsS http://8.153.194.178/api/v1/health` | `{\"status\":\"healthy\",\"service\":\"业务需求工作量评估系统\",\"version\":\"1.0.0\"}` |
| 容器状态 | `docker-compose ps` | `backend` 为 `Up (healthy)`，`frontend` 为 `Up` |
| CR-20260302-002 后端验证 | `.venv/bin/pytest -q tests/test_system_profile_publish_rules.py -k "profile_events_returns_empty_when_profile_not_created"` | `1 passed in 5.70s` |
| CR-20260302-003 默认账号回归 | `.venv/bin/pytest -q tests/test_user_service_internal_bootstrap.py` | `2 passed in 0.10s` |
| CR-20260302-003 脚本验证 | `bash -n deploy-backend-internal.sh` + `python3 scripts/init_internal_users.py --data-dir $(mktemp -d)` | 语法检查通过；默认账号初始化输出 `created=5, updated=0` |

## 回滚方案

### L1（功能级回滚）
- 触发条件：画像建议采纳/回滚链路异常、三点估计显示/导出异常。
- 执行策略：优先走应用内回滚能力（AI 建议回滚 + 手动字段回滚）。
- 本轮演练证据：
```bash
.venv/bin/python -m pytest -q tests/test_system_profile_publish_rules.py -k rollback
```
结果：`2 passed, 4 deselected in 8.78s`。

### L2（版本级回滚）
- 触发条件：功能级回滚无法止损，或出现跨模块系统性异常。
- 目标命令：`git checkout v2.3 && bash deploy-all.sh`
- 本轮安全演练（不污染当前工作树）：
```bash
TMP_DIR="$(mktemp -d /tmp/v23-l2-drill-XXXX)"
git worktree add "$TMP_DIR" v2.3
bash -n "$TMP_DIR/deploy-all.sh"
```
结果：`L2_DRILL_OK:9db2c93:/tmp/v23-l2-drill-VOyd/deploy-all.sh`。

## 健康检查与监控
- 健康检查：`curl -fsS http://127.0.0.1/api/v1/health`。
- 关键观察项：
  - 导入后异步提取任务状态（pending/processing/completed/failed）
  - 画像时间线写入成功率
  - 估算接口 `degraded` 比例
  - 报告导出成功率

## 上线后观察窗口（🔴 MUST）
| 项 | 值 |
|---|---|
| 观察窗口时长 | 30 分钟 |
| 观察开始/结束时间 | 2026-03-02 10:02 ~ 10:15 |
| 观察结论 | 正常（人工验收通过） |

## 常见问题
| 问题 | 原因 | 解决方法 |
|------|------|----------|
| 估算接口返回 `degraded=true` 占比异常升高 | LLM 依赖异常或提示词输入质量下降 | 检查 DashScope 可用性并回退到 L1 兜底路径 |
| 导入成功但画像未更新 | 异步提取任务失败/轮询未命中 | 检查 extraction-status 与任务事件日志，必要时重触发导入 |

## 部署记录
- 本轮 STAGING 已自动部署完成，已同步到 `docs/部署记录.md`。

## 变更记录
| 版本 | 日期 | 说明 | 作者 |
|---|---|---|---|
| v0.7 | 2026-03-02 | 纳入 `CR-20260302-003`（内网部署目录属主对齐与默认账号初始化）验证证据，完成 v2.4 收口对齐 | Codex |
| v0.6 | 2026-03-02 | 人工验收通过，观察窗口收口，文档状态更新为 Approved | Codex |
| v0.5 | 2026-03-02 | 补充后端容错修复（无画像事件查询空返回）验证证据并执行二次发布，健康检查通过 | Codex |
| v0.4 | 2026-03-02 | 执行 CR 增量发布（含 CR-20260302-002）；自动部署到 STAGING 并完成本机/公网健康检查；状态置为待人工验收 | Codex |
| v0.3 | 2026-03-01 | 观察窗口收口：状态更新为 Approved，记录观察结束时间与通过结论 | Codex |
| v0.2 | 2026-03-01 | 执行 STAGING 自动部署（非交互模式），补充部署结果与健康检查证据，状态置为 Wait Confirm | Codex |
| v0.1 | 2026-03-01 | 初始化 v2.4 部署指南，补齐门禁结果与 L1/L2 回滚演练证据 | Codex |
