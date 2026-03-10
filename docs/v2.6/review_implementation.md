# Review Report：Implementation / v2.6

| 项 | 值 |
|---|---|
| 阶段 | Implementation |
| 版本号 | v2.6 |
| 日期 | 2026-03-09 |
| 基线版本（对比口径） | `v2.5` |
| 复查口径 | diff-only |
| Active CR | `CR-20260309-001` |
| 审查范围 / 输入材料 | `backend/config/config.py`、`backend/utils/token_counter.py`、`backend/utils/llm_client.py`、`backend/service/profile_summary_service.py`、`backend/api/system_profile_routes.py`、`backend/api/knowledge_routes.py`、测试与 v2.6 文档 |

## §-1 预审结果（🔴 MUST）
| 检查项 | 命令 | 结果 | 通过 |
|---|---|---|---|
| 测试 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_token_counter.py tests/test_llm_client.py tests/test_profile_summary_service.py tests/test_system_profile_import_api.py tests/test_knowledge_import_api.py tests/test_knowledge_routes_helpers.py` | `61 passed, 1 warning in 20.49s` | ✅ |
| 构建 | `python -m compileall -q backend` | 无输出，退出码 0 | ✅ |
| 类型检查 | `rg -n "tool\\.mypy|mypy" pyproject.toml` | 仅检出依赖声明，无统一 typecheck 配置/命令 | ✅（N/A） |
| 产出物就绪 | 检查代码改动 + `docs/v2.6/test_report.md` + `docs/v2.6/deployment.md` + `docs/v2.6/implementation_checklist.md` | 实现、测试证据与 runbook 已产出 | ✅ |

## 结论摘要
- 总体结论：✅ 通过
- Blockers（P0）：0 / 高优先级（P1）：0 / 其他建议（P2+）：0
- 说明：未发现阻断实现阶段收口的问题；剩余工作转入后续 Testing / Deployment 使用。

## 关键发现（按优先级）
- 无 P0 / P1 Findings。

## §0 审查准备
### A. 事实核实
| # | 声明 | 核实源 | 结论 |
|---|---|---|---|
| 1 | 新增 Token/chunking 配置并同步环境文件 | `backend/config/config.py` + `TEST-CONF-001` | ✅ |
| 2 | `llm_client.py` 支持 raw 调用、重试、usage 与合并原语 | `tests/test_llm_client.py` + `TEST-BE-COV-001` | ✅ |
| 3 | `profile_summary_service.py` 支持单次/分块双路径与失败原子性 | `tests/test_profile_summary_service.py` + `TEST-BE-COV-001` | ✅ |
| 4 | 导入接口以内存参数透传完整原文，HTTP 契约不变 | `tests/test_system_profile_import_api.py`、`tests/test_knowledge_import_api.py` + 契约检索 | ✅ |

### B. 关键概念交叉引用
| 概念 | 出现位置 | 口径一致 |
|---|---|---|
| `ENABLE_LLM_CHUNKING` | `backend/config/config.py`、`.env.backend*`、`docs/v2.6/design.md`、`docs/v2.6/deployment.md` | ✅ |
| `LLM_MAX_CONTEXT_TOKENS` / `LLM_INPUT_MAX_TOKENS` | `backend/config/config.py`、`.env.backend*`、`docs/v2.6/design.md`、`docs/v2.6/deployment.md` | ✅ |
| `context_override.document_text` | `backend/service/profile_summary_service.py`、`backend/api/system_profile_routes.py`、`backend/api/knowledge_routes.py`、相关 API 测试 | ✅ |
| `/api/v1/knowledge/imports` / `/api/v1/system-profiles/{system_id}/profile/import` / `/profile/extraction-status` | `backend/api/*.py`、`docs/v2.6/design.md`、`docs/接口文档.md` | ✅ |

## Implementation 审查清单
- [x] 安全：未新增密钥落盘、未放宽权限校验、未引入越权路径
- [x] 边界与错误：超长段落、关闭开关、块失败、usage 缺失、解析失败均有固定语义
- [x] 可维护性：新增逻辑集中在 `token_counter` / `llm_client` / `profile_summary_service` / 2 条导入路由
- [x] 内容完整性：T001~T006 均有实现与证据
- [x] 测试与证据：关键路径、异常路径、覆盖率与依赖差异均可复现
- [x] 里程碑展示：M2 已在对话中展示并获继续指令

## 任务完成度
| 任务ID | 任务名称 | 状态 | 备注 |
|---|---|---|---|
| T001 | Token 预算、段落分块与环境配置基座 | ✅完成 | 配置/env/test 已落地 |
| T002 | LLM 客户端 raw 调用、usage 提取与分块合并原语 | ✅完成 | merge/retry/json/raw 覆盖到位 |
| T003 | `profile_summary_service` 双路径执行与失败原子性 | ✅完成 | 单次/分块/关闭开关/失败原子性通过 |
| T004 | 导入接口原文透传与 API 契约回归 | ✅完成 | system profile / knowledge 两条链路透传原文 |
| T005 | Token 分档回归、覆盖率与无新增依赖证据 | ✅完成 | 回归 61 passed，覆盖率 92%，依赖 diff 为空 |
| T006 | 部署 runbook、回滚步骤与主文档同步 | ✅完成 | `deployment.md` 与主文档同步完成 |

- 总任务数：6 / 完成：6 / 跳过：0 / 变更：0

## 需求符合性审查（REQ 模式）
### 逐条 GWT 判定表（🔴 MUST）
| GWT-ID | REQ-ID | 判定 | 证据类型 | 证据（可复现） | 备注 |
|---|---|---|---|---|---|
| GWT-REQ-001-01 | REQ-001 | ✅ | RUN_OUTPUT | `tests/test_profile_summary_service.py::test_call_llm_switches_by_token_budget[30k-chunk]` | 30k 样本进入分块 |
| GWT-REQ-001-02 | REQ-001 | ✅ | RUN_OUTPUT | `tests/test_token_counter.py::test_chunk_text_handles_525_paragraph_47_table_scale_sample` | 525 段落 + 47 表格量级 |
| GWT-REQ-001-03 | REQ-001 | ✅ | RUN_OUTPUT | `tests/test_token_counter.py::test_chunk_text_rejects_single_paragraph_above_budget` | 单段超限固定失败 |
| GWT-REQ-001-04 | REQ-001 | ✅ | RUN_OUTPUT | `tests/test_profile_summary_service.py::test_chunking_path_fails_when_any_chunk_processing_fails` | 任一块失败整单失败 |
| GWT-REQ-002-01 | REQ-002 | ✅ | RUN_OUTPUT | `tests/test_llm_client.py::test_merge_stage1_stage2_responses` | Stage1 去重合并 |
| GWT-REQ-002-02 | REQ-002 | ✅ | RUN_OUTPUT | `tests/test_llm_client.py::test_merge_stage1_stage2_responses` | `module_structure` 合并 |
| GWT-REQ-002-03 | REQ-002 | ✅ | RUN_OUTPUT | `tests/test_llm_client.py::test_merge_stage1_stage2_responses` | 字符串拼接 |
| GWT-REQ-002-04 | REQ-002 | ✅ | RUN_OUTPUT | `tests/test_profile_summary_service.py::test_calculate_body_budget_and_execute_stage_calls` | 缺失字段归一化 |
| GWT-REQ-003-01 | REQ-003 | ✅ | RUN_OUTPUT | `tests/test_profile_summary_service.py::test_call_llm_switches_by_token_budget[20k-single]` | 20k 单次路径 |
| GWT-REQ-003-02 | REQ-003 | ✅ | RUN_OUTPUT | `tests/test_profile_summary_service.py::test_call_llm_switches_by_token_budget[25k-single]` | 25k 边界单次路径 |
| GWT-REQ-004-01 | REQ-004 | ✅ | RUN_OUTPUT | `tests/test_profile_summary_service.py::test_chunking_disabled_still_allows_normal_document` | 关闭分块但普通文档可处理 |
| GWT-REQ-004-02 | REQ-004 | ✅ | RUN_OUTPUT | `tests/test_profile_summary_service.py::test_chunking_disabled` | 关闭分块后超长文档显式失败 |
| GWT-REQ-101-01 | REQ-101 | ✅ | RUN_OUTPUT | `docs/v2.6/test_report.md` 中 `TEST-BE-REG-001` + `test_call_llm_switches_by_token_budget[*]` | 无 Token 超限错误 |
| GWT-REQ-102-01 | REQ-102 | ✅ | RUN_OUTPUT | `docs/v2.6/test_report.md` 中 `TEST-BE-COV-001` | 总覆盖率 92% |
| GWT-REQ-103-01 | REQ-103 | ✅ | RUN_OUTPUT | `tests/test_profile_summary_service.py::test_calculate_body_budget_and_execute_stage_calls` | chunk 指标与预算路径 |
| GWT-REQ-C001-01 | REQ-C001 | ✅ | RUN_OUTPUT | `tests/test_token_counter.py::test_chunk_text_with_overlap_preserves_reconstruction_order` | 重建顺序一致 |
| GWT-REQ-C001-02 | REQ-C001 | ✅ | RUN_OUTPUT | `tests/test_profile_summary_service.py::test_chunking_disabled` | 不截断 |
| GWT-REQ-C002-01 | REQ-C002 | ✅ | RUN_OUTPUT | `git diff --unified=0 v2.5 -- requirements.txt backend/requirements.txt pyproject.toml` | 无新增依赖 |
| GWT-REQ-C003-01 | REQ-C003 | ✅ | RUN_OUTPUT | `tests/test_system_profile_import_api.py::test_profile_import_success_returns_task_id_and_records_history` + `tests/test_knowledge_import_api.py::test_knowledge_import_document_updates_completeness` | 成功/失败包络兼容 |
| GWT-REQ-C004-01 | REQ-C004 | ✅ | RUN_OUTPUT | `tests/test_token_counter.py::test_chunk_text_handles_525_paragraph_47_table_scale_sample` | 所有块 ≤25k |

### 对抗性审查（REQ-C）
- `REQ-C001`：
  - 泄漏路径 1：分块重叠导致重建错序。排除证据：`test_chunk_text_with_overlap_preserves_reconstruction_order`
  - 泄漏路径 2：导入接口未透传完整原文。排除证据：`test_profile_import_passes_full_document_text_to_summary_job`、`test_knowledge_import_passes_full_document_text_to_summary_job`
- `REQ-C002`：
  - 泄漏路径 1：新增 `requirements.txt` 运行时依赖。排除证据：`git diff --unified=0 v2.5 -- requirements.txt backend/requirements.txt pyproject.toml`
  - 泄漏路径 2：为 token 计数引入三方库。排除证据：实现仅使用启发式计数与标准库，无新增依赖 diff
- `REQ-C003`：
  - 泄漏路径 1：导入成功载荷结构变化。排除证据：system profile / knowledge API 回归测试
  - 泄漏路径 2：新增强制请求字段。排除证据：接口契约检索与回归测试均未发现变化
- `REQ-C004`：
  - 泄漏路径 1：重叠段加入后 chunk 超限。排除证据：`test_chunk_text_shrinks_overlap_when_requested_overlap_cannot_fit`
  - 泄漏路径 2：大样本切块仍出现 >25k。排除证据：`test_chunk_text_handles_525_paragraph_47_table_scale_sample`

## §3 覆盖率证明
| 维度 | 应检项数 | 已检 | 未检 | 未检说明 |
|---|---|---|---|---|
| 事实核实（步骤A） | 4 | 4 | 0 | - |
| 概念交叉引用（步骤B） | 4 | 4 | 0 | - |
| 审查清单项 | 6 | 6 | 0 | - |
| GWT 判定项 | 20 | 20 | 0 | - |

### 对抗性自检
- [x] 不存在“我知道意思但文本没写清”的地方
- [x] 受影响 API 已在 design / interface 文档中补齐契约说明
- [x] 无“可选/或者/暂不”型实现歧义残留在本次实现范围内
- [x] 所有 GWT 均可仅凭命令与测试结果判定 pass/fail
- [x] 高风险项（兼容/回滚/权限/REQ-C）已在本阶段收敛

## 建议验证清单（命令级别）
- [x] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_token_counter.py tests/test_llm_client.py tests/test_profile_summary_service.py tests/test_system_profile_import_api.py tests/test_knowledge_import_api.py tests/test_knowledge_routes_helpers.py`
- [x] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p pytest_cov --cov=backend.utils.token_counter --cov=backend.utils.llm_client --cov=backend.service.profile_summary_service --cov-report=term-missing tests/test_token_counter.py tests/test_llm_client.py tests/test_profile_summary_service.py`
- [x] `git diff --unified=0 v2.5 -- requirements.txt backend/requirements.txt pyproject.toml`

## 处理记录
| RVW-ID | 严重度 | 处理决策 | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| - | - | - | Codex | 本轮未发现 P0/P1/P2 问题 | `review_result=pass` |

## 机器可读摘要块
<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: implementation
REVIEW_SCOPE: diff-only
REVIEW_MODES: TECH,REQ,TRACE
CODE_BASELINE: HEAD
REQ_BASELINE_HASH: v2.6-requirements-gwt-20260309
GWT_TOTAL: 20
GWT_CHECKED: 20
GWT_CARRIED: 0
CARRIED_FROM_COMMIT: N/A
CARRIED_GWTS: N/A
GWT_DEFERRED: 0
GWT_FAIL: 0
GWT_WARN: 0
SPOT_CHECK_GWTS: GWT-REQ-001-02,GWT-REQ-C001-01,GWT-REQ-C003-01
SPOTCHECK_FILE: docs/v2.6/spotcheck_implementation_cr-20260309-001.md
GWT_CHANGE_CLASS: structural
CLARIFICATION_CONFIRMED_BY: User
CLARIFICATION_CONFIRMED_AT: 2026-03-09
VERIFICATION_COMMANDS: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_token_counter.py tests/test_llm_client.py tests/test_profile_summary_service.py tests/test_system_profile_import_api.py tests/test_knowledge_import_api.py tests/test_knowledge_routes_helpers.py,PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p pytest_cov --cov=backend.utils.token_counter --cov=backend.utils.llm_client --cov=backend.service.profile_summary_service --cov-report=term-missing tests/test_token_counter.py tests/test_llm_client.py tests/test_profile_summary_service.py,python -m compileall -q backend,git diff --unified=0 v2.5 -- requirements.txt backend/requirements.txt pyproject.toml
REVIEW_RESULT: pass
<!-- REVIEW-SUMMARY-END -->
