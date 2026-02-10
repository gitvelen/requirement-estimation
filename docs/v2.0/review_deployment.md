# Review Report：Deployment / v2.0

| 项 | 值 |
|---|---|
| 阶段 | Deployment |
| 版本号 | v2.0 |
| 日期 | 2026-02-07 |
| 检查点 | 部署阶段代码健康度、运行时兼容性、回归可复现性、遗留风险收敛 |
| 审查范围 | 后端：`backend/app.py`、`backend/api/auth.py`；验证：`tests/`、`frontend/src/__tests__/`、部署脚本语法检查 |
| 输入材料 | `docs/v2.0/status.md`、`.claude/templates/review_template.md`、命令：`.venv/bin/pytest -q`、`cd frontend && npm run build && CI=true npm test -- --watchAll=false`、`bash -n deploy-*.sh` |

## 结论摘要
- 总体结论：✅ 通过（本轮发现 2 个 P2 已完成修复）
- Blockers（P0）：0
- 高优先级（P1）：0
- 其他建议（P2+）：1（第三方依赖告警治理）

## 审查证据快照
- 后端全量回归：`.venv/bin/pytest -q` → `60 passed, 604 warnings in 13.87s`
- 前端构建与单测：`cd frontend && npm run build && CI=true npm test -- --watchAll=false` → `Compiled successfully`，`1 suite / 4 tests passed`
- 部署脚本语法：`bash -n deploy-*.sh` → 通过
- 兼容性关键字检查：`rg -n "on_event\(|utcnow\(" backend` → 无命中

## 关键发现（按优先级）

### RVW-DEP-001（P2）FastAPI 生命周期事件仍使用 `@app.on_event`，存在升级兼容风险
- 证据：审查前 `backend/app.py` 使用 `@app.on_event("startup")` 与 `@app.on_event("shutdown")`，在 FastAPI 当前版本触发弃用告警。
- 风险：后续 FastAPI 主版本升级时行为可能变化或移除，影响服务启动/关闭钩子稳定性。
- 建议修改：迁移为 `lifespan` 管理器统一承接启动与关闭逻辑。
- 验证方式（可复现）：`rg -n "lifespan|on_event\(" backend/app.py`

### RVW-DEP-002（P2）JWT 过期时间基于 `datetime.utcnow()`，存在未来 Python 版本兼容风险
- 证据：审查前 `backend/api/auth.py` 使用 `datetime.utcnow()` 构造 `exp`。
- 风险：`utcnow` 已被标记弃用路径，长期会增加运行时告警与维护成本。
- 建议修改：改为时区显式写法 `datetime.now(timezone.utc)`。
- 验证方式（可复现）：`rg -n "utcnow\(|timezone\.utc" backend/api/auth.py`

### RVW-DEP-101（P2）第三方依赖告警噪声仍高，建议持续治理
- 证据：`.venv/bin/pytest -q` 仍有 604 条告警，主要来自 `pymilvus` 与 `langchain_core` 在 Python 3.14 下的兼容提示。
- 风险：告警噪声会掩盖新问题，升级窗口期风险提升。
- 建议修改：建立“warning 基线+分批治理”计划，优先跟踪依赖升级窗口（`pymilvus`、`langchain`）。
- 验证方式（可复现）：`.venv/bin/pytest -q -W default`

## 建议验证清单（命令级别）
- [x] 后端全量回归：`.venv/bin/pytest -q`
- [x] 前端构建与单测：`cd frontend && npm run build && CI=true npm test -- --watchAll=false`
- [x] 部署脚本语法：`bash -n deploy-*.sh`
- [x] 兼容性关键字检查：`rg -n "on_event\(|utcnow\(" backend`

## 开放问题
- [ ] 是否将 Python 运行时从 `3.14` 固定回 `3.12/3.13`，以降低当前第三方兼容告警噪声？
- [ ] 是否将 `pytest -W error::DeprecationWarning` 纳入 CI（先对白名单依赖做排除）？

## 处理记录（建议由开发/人工填写）
| RVW-ID | 严重度 | 处理决策（Fix/Defer/Accept） | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-DEP-001 | P2 | Fix | AI | 已迁移到 FastAPI `lifespan`，移除 `on_event` 钩子 | `backend/app.py` |
| RVW-DEP-002 | P2 | Fix | AI | `exp` 计算改为 `datetime.now(timezone.utc)` | `backend/api/auth.py` |
| RVW-DEP-101 | P2 | Defer | AI | 属第三方依赖告警，纳入后续治理计划 | 本报告“关键发现” |

---

## 追加记录：告警收口（2026-02-07）

| 项 | 值 |
|---|---|
| 复查输入 | 告警治理增量（依赖升级 + `pytest` 告警白名单） |
| 复查结论 | ✅ 通过（本轮测试输出已无告警噪声） |
| 复查说明 | 已先升级 `pymilvus/langchain/langchain-core/langgraph` 到当前可用最新补丁版，再对剩余第三方已知告警做最小范围白名单，不屏蔽项目自有代码告警。 |

### 处理记录（本轮更新）
| RVW-ID | 严重度 | 处理决策（Fix/Defer/Accept） | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-DEP-101 | P2 | Fix | AI | 增加 `pytest` 定向 `filterwarnings`（仅 `langchain_core._api.deprecation` 与 `pymilvus.decorators`） | `pyproject.toml` |

### 复查证据
- 后端全量回归：`.venv/bin/pytest -q` → `60 passed in 12.00s`（无 warning 输出）
- 前端构建与单测：`cd frontend && npm run build && CI=true npm test -- --watchAll=false` → `Compiled successfully`，`4 passed`
- 部署脚本语法：`bash -n deploy-*.sh` → 通过
