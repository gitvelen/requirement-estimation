# 需求评估系统 v2.6 任务计划

## 文档元信息
| 项 | 值 |
|---|---|
| 状态 | Review |
| 日期 | 2026-03-09 |
| 版本 | v0.6 |
| 基线版本（对比口径） | `v2.5` |
| Active CR（如有） | `docs/v2.6/cr/CR-20260309-001.md` |
| 关联设计 | `docs/v2.6/design.md` |
| 关联需求 | `docs/v2.6/requirements.md` |
| 关联状态 | `docs/v2.6/status.md` |

## 里程碑
| 里程碑 | 交付物 | 截止日期 |
|---|---|---|
| M1 | Token 预算与分块基座（T001-T002） | 2026-03-10 |
| M2 | 总结链路与导入透传改造（T003-T004） | 2026-03-10 |
| M3 | 回归证据、发布与回滚收口（T005-T006） | 2026-03-11 |

## Definition of Done（DoD）
- [x] 需求可追溯：每个任务均声明 `REQ/SCN/API/TEST`，并补齐反向覆盖矩阵
- [x] 范围可控：以 `CR-20260309-001` 的 backend/config/api/test 范围为主；Testing 预审若暴露项目级结果门禁阻断项，仅允许最小兼容修复并在 `review_testing.md` 留痕
- [x] 自测可复现：每个任务均给出命令级验证方式与预期结果
- [x] 行为可回滚：所有运行时行为变化均收敛到 `ENABLE_LLM_CHUNKING` 开关与版本回退
- [x] 文档闭环：`requirements.md` / `design.md` / `plan.md` / `test_report.md` / `deployment.md` 有明确衔接
- [x] 结果门禁补充：Testing 阶段需额外通过项目级 `pytest` / `build` / `compileall`，如遇现存阻断回归，仅允许最小兼容修复并在 Testing 审查留痕

## 禁止项引用索引（来源：requirements.md REQ-C 章节）
| REQ-C ID | 一句话摘要 |
|---|---|
| REQ-C001 | 禁止文档内容丢失，导入原文必须无静默截断、无重排 |
| REQ-C002 | 禁止引入运行时外部依赖 |
| REQ-C003 | 禁止修改系统画像导入相关 API 契约 |
| REQ-C004 | 禁止生成超限 chunk（估算 token 必须 `<= 25000`） |

## 任务概览
状态标记：`待办` / `进行中` / `已完成`；里程碑标记：`🏁` 表示完成后需向用户展示阶段成果

| 任务分类 | 任务ID | 任务名称 | 优先级 | 预估工时 | Owner | Reviewer | 关联CR | 关联需求项 | 关联场景（SCN） | 关联接口（API） | 任务状态 | 依赖任务ID | 验证方式 | 里程碑 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 后端基础 | T001 | Token 预算、段落分块与环境配置基座 | P0 | 0.5d | Codex | Codex | CR-20260309-001 | REQ-001, REQ-003, REQ-004, REQ-101, REQ-C002, REQ-C004 | SCN-003, SCN-004, SCN-005 | - | 已完成 | - | `pytest + rg` | M1 |
| 后端基础 | T002 | LLM 客户端 raw 调用、usage 提取与分块合并原语 | P0 | 0.5d | Codex | Codex | CR-20260309-001 | REQ-002, REQ-101, REQ-103, REQ-C002 | SCN-004, SCN-006, SCN-007 | - | 已完成 | T001 | `pytest` | M1 |
| 后端服务 | T003 | `profile_summary_service` 双路径执行与失败原子性 | P0 | 1d | Codex | Codex | CR-20260309-001 | REQ-001, REQ-002, REQ-003, REQ-004, REQ-101, REQ-103, REQ-C001, REQ-C004 | SCN-001, SCN-002, SCN-003, SCN-004, SCN-006, SCN-007 | - | 已完成 | T001,T002 | `pytest` | M2🏁 |
| 后端接口 | T004 | 导入接口原文透传与 API 契约回归 | P0 | 0.5d | Codex | Codex | CR-20260309-001 | REQ-001, REQ-003, REQ-C001, REQ-C003 | SCN-001, SCN-002, SCN-003 | API-001, API-002, API-003 | 已完成 | T003 | `pytest` | M2🏁 |
| 测试与证据 | T005 | Token 分档回归、覆盖率与无新增依赖证据 | P1 | 0.5d | Codex | Codex | CR-20260309-001 | REQ-001, REQ-002, REQ-003, REQ-004, REQ-101, REQ-102, REQ-103, REQ-C001, REQ-C002, REQ-C003, REQ-C004 | SCN-001~SCN-007 | API-001~API-003 | 已完成 | T001-T004 | `pytest + pytest-cov + git diff` | M3 |
| 发布与文档 | T006 | 部署 runbook、回滚步骤与主文档同步 | P1 | 0.5d | Codex | Codex | CR-20260309-001 | REQ-004, REQ-101, REQ-103, REQ-C001, REQ-C003 | SCN-003（抽样） | API-001~API-003（抽样） | 已完成 | T005 | `rg + git rev-parse` | M3 |

## 任务详情

### T001: Token 预算、段落分块与环境配置基座
**分类**：后端基础 / **优先级**：P0 / **预估工时**：0.5d / **Owner**：Codex / **Reviewer**：Codex
**关联CR**：CR-20260309-001
**关联需求项**：REQ-001, REQ-003, REQ-004, REQ-101, REQ-C002, REQ-C004
**关联场景（SCN）**：SCN-003, SCN-004, SCN-005
**关联测试（TEST）**：TEST-001, TEST-002
**任务描述**：
- 新增 `backend/utils/token_counter.py`，提供 `estimate_tokens()`、`extract_usage_from_response()`、`chunk_text()` 与重叠收缩能力。
- 在 `backend/config/config.py` 暴露 `LLM_MAX_CONTEXT_TOKENS`、`LLM_INPUT_MAX_TOKENS`、`LLM_CHUNK_OVERLAP_PARAGRAPHS`、`ENABLE_LLM_CHUNKING`。
- 更新 `.env.backend`、`.env.backend.example`、`.env.backend.internal`，显式声明 `LLM_MODEL=Qwen3-32B`、`EMBEDDING_MODEL=Qwen3-Embedding-8B` 与 token/chunking 配置。
**影响面/修改范围**：
- `backend/utils/token_counter.py`
- `backend/config/config.py`
- `.env.backend`
- `.env.backend.example`
- `.env.backend.internal`
- `tests/test_token_counter.py`
**验收标准**：
- [ ] 30k 样本可切成 `>=2` 个 chunk，且每块估算 token `<= 25000`。
- [ ] 单段超限触发固定错误，不允许静默截断。
- [ ] 无新增运行时外部依赖，环境示例文件与内网口径一致。
**验证方式**（🔴 MUST）：
- 命令：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_token_counter.py`
- 预期：退出码 0，覆盖分块上限、单段超限、重叠收缩与重建顺序断言。
- 命令：`rg -n "LLM_MODEL=Qwen3-32B|EMBEDDING_MODEL=Qwen3-Embedding-8B|LLM_MAX_CONTEXT_TOKENS=32000|LLM_INPUT_MAX_TOKENS=25000|LLM_CHUNK_OVERLAP_PARAGRAPHS=2|ENABLE_LLM_CHUNKING=true" .env.backend .env.backend.example .env.backend.internal`
- 预期：退出码 0，三个环境文件均含显式配置。
**回滚/开关策略**：
- 回滚条件：Token 估算/分块基座导致正常文档路径异常。
- 回滚步骤：回退 `token_counter.py` 与新增 settings 字段；运行时兜底开关为 `ENABLE_LLM_CHUNKING=false`。
**依赖**：-

### T002: LLM 客户端 raw 调用、usage 提取与分块合并原语
**分类**：后端基础 / **优先级**：P0 / **预估工时**：0.5d / **Owner**：Codex / **Reviewer**：Codex
**关联CR**：CR-20260309-001
**关联需求项**：REQ-002, REQ-101, REQ-103, REQ-C002
**关联场景（SCN）**：SCN-004, SCN-006, SCN-007
**关联测试（TEST）**：TEST-003, TEST-004
**任务描述**：
- 扩展 `backend/utils/llm_client.py`，保留兼容 `chat()` 入口，同时新增可返回原始响应/usage 的调用路径。
- 落地 Stage1 列表去重合并、Stage2 深度合并与 chunk 级执行度量，供总结服务复用。
- 保持重试、超时与错误抛出语义不变，不引入并发执行复杂度。
**影响面/修改范围**：
- `backend/utils/llm_client.py`
- `tests/test_llm_client.py`
**验收标准**：
- [ ] Stage1 `relevant_domains` / `related_systems` 合并去重且保持顺序。
- [ ] Stage2 对 `module_structure`、`integration_points`、`key_constraints` 等字段可深度合并。
- [ ] usage 缺失时可安全回落，不阻断主流程。
**验证方式**（🔴 MUST）：
- 命令：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_llm_client.py`
- 预期：退出码 0，覆盖 usage 提取、Stage1 合并、Stage2 深度合并与异常路径。
**回滚/开关策略**：
- 回滚条件：LLM 客户端兼容入口被破坏或合并逻辑产生结构漂移。
- 回滚步骤：保留 `chat()` / `chat_with_system_prompt()` 原行为，撤回新增 chunk 合并辅助。
**依赖**：T001

### T003: `profile_summary_service` 双路径执行与失败原子性
**分类**：后端服务 / **优先级**：P0 / **预估工时**：1d / **Owner**：Codex / **Reviewer**：Codex
**关联CR**：CR-20260309-001
**关联需求项**：REQ-001, REQ-002, REQ-003, REQ-004, REQ-101, REQ-103, REQ-C001, REQ-C004
**关联场景（SCN）**：SCN-001, SCN-002, SCN-003, SCN-004, SCN-006, SCN-007
**关联测试（TEST）**：TEST-005, TEST-006, TEST-008
**任务描述**：
- 在 `backend/service/profile_summary_service.py` 引入 `context_override` / `SummaryContextBundle`，把静态前缀与可分块正文分离。
- 将 `_call_llm()` 改为 token-aware 决策：预算内走单次调用，超预算且开关打开走段落分块，超预算且开关关闭时显式失败。
- 保证任一块失败时整次任务失败，不写入部分 `ai_suggestions`；日志仅记录 token/chunk/latency/失败块索引，不落正文。
**影响面/修改范围**：
- `backend/service/profile_summary_service.py`
- `tests/test_profile_summary_service.py`
**验收标准**：
- [ ] 20k/25k 文档仅执行 1 次 Stage1 + 1 次 Stage2，不触发分块。
- [ ] 30k/50k 文档进入分块路径后无 Token 超限错误，且任一块失败时整体失败。
- [ ] `ENABLE_LLM_CHUNKING=false` 时普通文档可继续处理，超长文档返回固定错误提示且不截断。
**验证方式**（🔴 MUST）：
- 命令：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_profile_summary_service.py`
- 预期：退出码 0，覆盖单次路径、分块路径、关闭开关、失败原子性与日志指标断言。
**里程碑展示**：
- 展示内容：展示 20k/30k/50k 样本在 `profile_summary_service` 中分别走单次/分块/失败原子性路径的关键输入输出与日志指标。
- 确认要点：用户确认 token-aware 分流、失败整单回滚和错误语义符合预期后，继续接口集成任务。
**回滚/开关策略**：
- 回滚条件：分块编排导致总结任务失败率显著上升或异步任务耗时不可接受。
- 回滚步骤：将 `ENABLE_LLM_CHUNKING=false`，保留单次路径；必要时回退 `profile_summary_service.py` 到 v2.5 逻辑。
**依赖**：T001, T002

### T004: 导入接口原文透传与 API 契约回归
**分类**：后端接口 / **优先级**：P0 / **预估工时**：0.5d / **Owner**：Codex / **Reviewer**：Codex
**关联CR**：CR-20260309-001
**关联需求项**：REQ-001, REQ-003, REQ-C001, REQ-C003
**关联场景（SCN）**：SCN-001, SCN-002, SCN-003
**关联接口（API）**：API-001, API-002, API-003
**关联测试（TEST）**：TEST-007, TEST-010
**任务描述**：
- 在 `backend/api/system_profile_routes.py` 与 `backend/api/knowledge_routes.py` 的导入成功路径中，把完整 `text_content` 以内存参数透传给 `trigger_summary(...)`。
- 保持对外成功载荷、错误包络、权限与异步任务状态接口不变，不新增强制字段。
- 为系统画像导入与知识导入回归测试补充 stub 断言，证明透传的是完整原文而非知识库切片采样。
**影响面/修改范围**：
- `backend/api/system_profile_routes.py`
- `backend/api/knowledge_routes.py`
- `tests/test_system_profile_import_api.py`
- `tests/test_knowledge_import_api.py`
- `tests/test_knowledge_routes_helpers.py`
**验收标准**：
- [ ] 绑定系统的知识导入与系统画像导入都会把完整原文传给总结任务。
- [ ] `/api/v1/knowledge/imports`、`/api/v1/system-profiles/{system_id}/profile/import`、`/profile/extraction-status` 成功/失败包络保持兼容。
- [ ] 权限、空文件、格式错误等既有错误码不回归。
**验证方式**（🔴 MUST）：
- 命令：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_system_profile_import_api.py tests/test_knowledge_import_api.py tests/test_knowledge_routes_helpers.py`
- 预期：退出码 0，覆盖原文透传、任务状态、错误码与 API 包络回归。
**里程碑展示**：
- 展示内容：展示系统画像导入与知识导入两条链路的端到端调用结果，证明传入总结任务的是完整原文且对外 API 包络未变化。
- 确认要点：用户确认导入链路的集成行为、权限口径和兼容性回归结果后，进入测试证据收口。
**回滚/开关策略**：
- 回滚条件：导入接口契约或异步任务状态接口出现兼容性回归。
- 回滚步骤：回退接口内部透传改动，保留对外 API 契约与权限逻辑。
**依赖**：T003

### T005: Token 分档回归、覆盖率与无新增依赖证据
**分类**：测试与证据 / **优先级**：P1 / **预估工时**：0.5d / **Owner**：Codex / **Reviewer**：Codex
**关联CR**：CR-20260309-001
**关联需求项**：REQ-001, REQ-002, REQ-003, REQ-004, REQ-101, REQ-102, REQ-103, REQ-C001, REQ-C002, REQ-C003, REQ-C004
**关联场景（SCN）**：SCN-001~SCN-007
**关联接口（API）**：API-001~API-003
**关联测试（TEST）**：TEST-001~TEST-010
**任务描述**：
- 执行 v2.6 目标测试集，覆盖 20k / 25k / 30k / 50k 档位、单段超限、关闭 chunking、API 契约与失败原子性。
- 使用 `pytest-cov` 统计 `backend/utils/token_counter.py`、`backend/utils/llm_client.py`、`backend/service/profile_summary_service.py` 新增代码覆盖率。
- 用基线对比命令证明 `requirements.txt`、`backend/requirements.txt`、`pyproject.toml` 相对 `v2.5` 未引入新增运行时依赖，并产出 `docs/v2.6/test_report.md`。
**影响面/修改范围**：
- `tests/test_token_counter.py`
- `tests/test_llm_client.py`
- `tests/test_profile_summary_service.py`
- `tests/test_system_profile_import_api.py`
- `tests/test_knowledge_import_api.py`
- `tests/test_knowledge_routes_helpers.py`
- `docs/v2.6/test_report.md`
**验收标准**：
- [ ] REQ-001~REQ-004、REQ-101~REQ-103、REQ-C001~REQ-C004 均有可复现证据。
- [ ] 覆盖率命令结果 `> 80%`。
- [ ] 无新增运行时依赖，测试报告中的结论与命令输出一致。
**验证方式**（🔴 MUST）：
- 命令：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_token_counter.py tests/test_llm_client.py tests/test_profile_summary_service.py tests/test_system_profile_import_api.py tests/test_knowledge_import_api.py tests/test_knowledge_routes_helpers.py`
- 预期：退出码 0，关键功能与失败路径全部通过。
- 命令：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p pytest_cov --cov=backend.utils.token_counter --cov=backend.utils.llm_client --cov=backend.service.profile_summary_service --cov-report=term-missing tests/test_token_counter.py tests/test_llm_client.py tests/test_profile_summary_service.py`
- 预期：退出码 0，终端报告总覆盖率大于 80%。
- 命令：`.venv/bin/python -m pytest -q --tb=short`
- 预期：退出码 0，全项目结果门禁通过。
- 命令：`git diff --unified=0 v2.5 -- requirements.txt backend/requirements.txt pyproject.toml`
- 预期：对比基线 `v2.5` 时不得出现新增运行时依赖条目；若存在差异，只能是测试/覆盖率工具说明且需在 `test_report.md` 明确解释。
**回滚/开关策略**：
- 回滚条件：测试阶段发现超限回归、契约漂移或覆盖率无法支撑上线判断。
- 回滚步骤：冻结进入 Deployment，按 RVW 问题回修后重新执行 T005。
**依赖**：T001-T004

### T006: 部署 runbook、回滚步骤与主文档同步
**分类**：发布与文档 / **优先级**：P1 / **预估工时**：0.5d / **Owner**：Codex / **Reviewer**：Codex
**关联CR**：CR-20260309-001
**关联需求项**：REQ-004, REQ-101, REQ-103, REQ-C001, REQ-C003
**关联场景（SCN）**：SCN-003（抽样）
**关联接口（API）**：API-001~API-003（抽样）
**关联测试（TEST）**：TEST-006, TEST-008, TEST-010
**任务描述**：
- 产出 `docs/v2.6/deployment.md`，记录环境变量核对、上线步骤、`ENABLE_LLM_CHUNKING=false` 回滚步骤与验证命令。
- 同步主文档中与配置/API/部署相关的适用部分，至少覆盖 `docs/技术方案设计.md`、`docs/接口文档.md`、`docs/部署记录.md`；如 `docs/系统功能说明书.md` / `docs/用户手册.md` 判定不适用，需在 `status.md` 中保留勾选结论。
- 记录基线回滚点 `v2.5` 与配置核对项，保证部署后可复核。
**影响面/修改范围**：
- `docs/v2.6/deployment.md`
- `docs/v2.6/status.md`
- `docs/技术方案设计.md`
- `docs/接口文档.md`
- `docs/部署记录.md`
**验收标准**：
- [ ] Runbook 明确列出上线、验证、回滚步骤与配置键。
- [ ] 主文档同步范围与 `status.md` 清单一致。
- [ ] 回滚到 `ENABLE_LLM_CHUNKING=false` 的验证方法可执行。
**验证方式**（🔴 MUST）：
- 命令：`rg -n "ENABLE_LLM_CHUNKING|LLM_MAX_CONTEXT_TOKENS|LLM_INPUT_MAX_TOKENS|Qwen3-32B|Qwen3-Embedding-8B|/api/v1/knowledge/imports|/api/v1/system-profiles/.*/profile/import" docs/v2.6/deployment.md docs/技术方案设计.md docs/接口文档.md docs/部署记录.md`
- 预期：退出码 0，关键配置、接口与回滚要点均已同步。
- 命令：`git rev-parse --verify --quiet v2.5^{commit}`
- 预期：成功定位基线回滚点。
**回滚/开关策略**：
- 回滚条件：STAGING/PROD 观察到 chunking 触发失败率或耗时异常。
- 回滚步骤：先切 `ENABLE_LLM_CHUNKING=false`，必要时按基线 `v2.5` 做版本级回退。
**依赖**：T005

## 任务关联 REQ/覆盖矩阵
| REQ-ID | 关联任务 | 关联场景（SCN） | 关联接口（API） | 关联测试（TEST） | 计划验证 |
|---|---|---|---|---|---|
| REQ-001 | T001, T003, T004, T005 | SCN-001, SCN-004, SCN-005 | API-001, API-002 | TEST-001, TEST-002, TEST-006, TEST-007 | `tests/test_token_counter.py`, `tests/test_profile_summary_service.py`, `tests/test_system_profile_import_api.py`, `tests/test_knowledge_import_api.py` |
| REQ-002 | T002, T003, T005 | SCN-006, SCN-007 | - | TEST-004, TEST-006 | `tests/test_llm_client.py`, `tests/test_profile_summary_service.py` |
| REQ-003 | T001, T003, T004, T005 | SCN-002, SCN-004 | API-001, API-002 | TEST-001, TEST-005 | `tests/test_profile_summary_service.py`, API 回归测试 |
| REQ-004 | T001, T003, T005, T006 | SCN-003 | API-001, API-002 | TEST-008 | `tests/test_profile_summary_service.py`, `docs/v2.6/deployment.md` |
| REQ-101 | T001, T002, T003, T005, T006 | SCN-001, SCN-004 | API-001, API-002 | TEST-003, TEST-006 | token/latency 日志断言、`test_report.md` |
| REQ-102 | T005 | SCN-001~SCN-007 | - | TEST-001~TEST-010 | `pytest --cov` |
| REQ-103 | T002, T003, T005, T006 | SCN-001, SCN-003 | API-001, API-002 | TEST-006 | `tests/test_profile_summary_service.py`, `test_report.md`, `deployment.md` |
| REQ-C001 | T001, T003, T004, T005, T006 | SCN-001, SCN-003 | API-001, API-002 | TEST-002, TEST-004, TEST-007, TEST-008 | 原文透传、重建顺序与关闭开关失败测试 |
| REQ-C002 | T001, T002, T005 | SCN-004, SCN-005 | - | - | env/config diff、依赖 diff |
| REQ-C003 | T004, T005, T006 | SCN-001, SCN-002, SCN-003 | API-001, API-002, API-003 | TEST-007, TEST-010 | API 回归测试、接口文档同步 |
| REQ-C004 | T001, T003, T005 | SCN-005 | - | TEST-002, TEST-009 | chunk 上限测试、预算断言 |

## 执行顺序
1. T001 → T002 → T003 → T004 → T005 → T006

## 风险与缓解
| 风险 | 影响 | 概率 | 缓解措施 |
|---|---|---|---|
| Token 估算偏保守不足 | 仍可能触发上限错误 | 中 | `prompt_overhead + safety reserve`，并对 usage 缺失场景保留 warning |
| 深度合并规则误判 | Stage2 结果重复或丢失 | 中 | 在 T002/T003 明确 canonical normalize 与字段级测试 |
| 导入接口透传改动破坏契约 | 前端或调用方回归 | 低 | T004 固定做 API 包络与错误码回归 |
| 测试样本不足导致证据薄弱 | 无法支撑上线判断 | 中 | T005 明确按 20k/25k/30k/50k 四档补齐证据 |

## 开放问题
- [x] 无待确认项；Design 阶段已收敛为单一口径，本计划不保留“可选/二选一”实现路线。

## 变更记录
| 版本 | 日期 | 说明 |
|---|---|---|
| v0.1 | 2026-03-09 | 初始化 v2.6 Planning 阶段任务拆解、REQ 覆盖矩阵与验证命令 |
| v0.2 | 2026-03-09 | 修复覆盖矩阵：补充 REQ-C001~REQ-C004、新增 TEST 列、修正 REQ-C001 关联任务包含 T001 |
| v0.3 | 2026-03-09 | 补充 T003/T004 里程碑展示锚点，修正 T005 依赖证明命令为基线对比 |
| v0.4 | 2026-03-09 | 将基线口径从不可达别名 `v2.5` 解析为可验证 commit `7a0c6befb88ad848459264ba2456543bea5f9b44`，修正 T005/T006 验证命令 |
| v0.5 | 2026-03-09 | 补建正式 `v2.5` tag 后，将基线验证口径从临时 commit 回切到 tag |
| v0.6 | 2026-03-09 | 修正模型命名漂移，统一为 `Qwen3-32B` / `Qwen3-Embedding-8B`，并保持部署事实与需求口径分离 |
