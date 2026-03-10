# Review Report：Testing / v2.6

| 项 | 值 |
|---|---|
| 阶段 | Testing |
| 版本号 | v2.6 |
| 日期 | 2026-03-09 |
| 基线版本（对比口径） | `v2.5` |
| 复查口径 | full |
| Active CR | `CR-20260309-001` |
| 审查范围 / 输入材料 | `docs/v2.6/test_report.md`、`docs/v2.6/plan.md`、`docs/v2.6/requirements.md`、`backend/**` 当前 diff、项目级结果门禁输出 |

## §-1 预审结果（🔴 MUST）
| 检查项 | 命令 | 结果 | 通过 |
|---|---|---|---|
| 测试 | `.venv/bin/python -m pytest -q --tb=short` | `210 passed in 63.61s` | ✅ |
| 构建 | `cd frontend && npm run build` | `Compiled successfully.` | ✅ |
| 类型检查 | `.venv/bin/python -m compileall -q backend` | 无输出，退出码 0 | ✅ |
| 测试证据就绪 | 检查 `docs/v2.6/test_report.md` | `test_report.md` v0.2 已包含 GWT 覆盖矩阵、项目级结果门禁与 CR 证据 | ✅ |

## 结论摘要
- 总体结论：✅ 通过
- Blockers（P0）：0 / 高优先级（P1）：0 / 其他建议（P2+）：0
- 说明：Testing 预审曾暴露 4 条 ESB XLSX/CSV 兼容性失败；已在进入本轮 REP 前完成最小兼容修复并复测通过，不计入未收敛项。

## 关键发现（按优先级）
- 无 P0 / P1 Findings。

## §0 审查准备
### A. 事实核实
| # | 声明（出处） | 核实源 | 结论 |
|---|---|---|---|
| 1 | `TEST-BE-REG-001`：v2.6 定向后端回归 `61 passed`（`test_report.md`） | `docs/v2.6/test_report.md` + `tests/test_token_counter.py` / `tests/test_llm_client.py` / `tests/test_profile_summary_service.py` / `tests/test_system_profile_import_api.py` / `tests/test_knowledge_import_api.py` / `tests/test_knowledge_routes_helpers.py` | ✅ |
| 2 | `TEST-BE-COV-001`：覆盖率总计 `92%`（`test_report.md`） | `docs/v2.6/test_report.md` + 覆盖率结果表 | ✅ |
| 3 | `TEST-DEP-001`：无新增运行时依赖（`test_report.md`） | `docs/v2.6/test_report.md` + `git diff --unified=0 v2.5 -- requirements.txt backend/requirements.txt pyproject.toml` 记录 | ✅ |
| 4 | `TEST-GATE-001` / `TEST-BUILD-001` / `TEST-TYPE-001`：项目级 `pytest/build/compileall` 全部通过（`test_report.md` v0.2） | 本轮预审输出 | ✅ |

### B. 关键概念交叉引用
| 概念 | 出现位置 | 口径一致 |
|---|---|---|
| `TEST-BE-COV-001` / 覆盖率 `92%` | `docs/v2.6/test_report.md`、`docs/v2.6/review_implementation.md`、`docs/v2.6/review_testing.md` | ✅ |
| `ENABLE_LLM_CHUNKING` / `LLM_INPUT_MAX_TOKENS=25000` | `docs/v2.6/test_report.md`、`docs/v2.6/deployment.md`、`docs/v2.6/status.md`、`.env.backend*` | ✅ |
| `/api/v1/knowledge/imports` / `/api/v1/system-profiles/{system_id}/profile/import` / `/profile/extraction-status` | `docs/v2.6/test_report.md`、`docs/接口文档.md`、相关 API 测试 | ✅ |
| `210 passed` / `Compiled successfully.` / `compileall` 通过 | `docs/v2.6/test_report.md`、`docs/v2.6/deployment.md`、本文件 §-1 | ✅ |

## Testing 审查清单
- [x] 覆盖完整：20/20 个 GWT 均有 PASS 证据
- [x] 边界/异常覆盖：超长段落、关闭开关、任一块失败、usage 缺失、接口错误包络均已覆盖
- [x] 环境与数据：测试使用本地临时目录、stub、mock 响应，不依赖外部 LLM/Embedding 服务
- [x] 性能（如适用）：`REQ-103` 已通过 chunk 指标与预算路径测试证明“可观测且受控”
- [x] `test_report.md` 交叉校验：覆盖矩阵、覆盖率与结论与本审查一致
- [x] 契约烟测（前端）：不适用，本次无前端页面改造；项目级 build 门禁已通过
- [x] 里程碑展示：`plan.md` 中 `M2🏁` 已在对话中展示并获继续指令

## 任务完成度
| 任务ID | 任务名称 | 状态 | 备注 |
|---|---|---|---|
| T001 | Token 预算、段落分块与环境配置基座 | ✅完成 | v2.6 定向回归通过 |
| T002 | LLM 客户端 raw 调用、usage 提取与分块合并原语 | ✅完成 | 覆盖率 90%，回归通过 |
| T003 | `profile_summary_service` 双路径执行与失败原子性 | ✅完成 | 单次/分块/降级路径闭环 |
| T004 | 导入接口原文透传与 API 契约回归 | ✅完成 | system profile / knowledge 两条链路兼容 |
| T005 | Token 分档回归、覆盖率与无新增依赖证据 | ✅完成 | `61 passed`，覆盖率 `92%` |
| T006 | 部署 runbook、回滚步骤与主文档同步 | ✅完成 | `deployment.md` 与主文档同步完成 |

- 总任务数：6 / 完成：6 / 跳过：0 / 变更：0

## 需求符合性审查（REQ 模式）
### 逐条 GWT 判定表（🔴 MUST）
| GWT-ID | REQ-ID | 判定 | 证据类型 | 证据（可复现） | 备注 |
|---|---|---|---|---|---|
| GWT-REQ-001-01 | REQ-001 | ✅ | RUN_OUTPUT | `docs/v2.6/test_report.md` 中 `TEST-BE-REG-001` + `tests/test_profile_summary_service.py::test_call_llm_switches_by_token_budget[30k-chunk]` | 超长文档自动分块 |
| GWT-REQ-001-02 | REQ-001 | ✅ | RUN_OUTPUT | `tests/test_token_counter.py::test_chunk_text_handles_525_paragraph_47_table_scale_sample` | 525 段落量级样本通过 |
| GWT-REQ-001-03 | REQ-001 | ✅ | RUN_OUTPUT | `tests/test_token_counter.py::test_chunk_text_rejects_single_paragraph_above_budget` | 单段超限固定失败 |
| GWT-REQ-001-04 | REQ-001 | ✅ | RUN_OUTPUT | `tests/test_profile_summary_service.py::test_chunking_path_fails_when_any_chunk_processing_fails` | 任一块失败整体失败 |
| GWT-REQ-002-01 | REQ-002 | ✅ | RUN_OUTPUT | `tests/test_llm_client.py::test_merge_stage1_stage2_responses` | Stage1 去重合并 |
| GWT-REQ-002-02 | REQ-002 | ✅ | RUN_OUTPUT | `tests/test_llm_client.py::test_merge_stage1_stage2_responses` | `module_structure` 深度合并 |
| GWT-REQ-002-03 | REQ-002 | ✅ | RUN_OUTPUT | `tests/test_llm_client.py::test_merge_stage1_stage2_responses` | 字符串字段拼接 |
| GWT-REQ-002-04 | REQ-002 | ✅ | RUN_OUTPUT | `tests/test_profile_summary_service.py::test_calculate_body_budget_and_execute_stage_calls` | 缺失字段归一化 |
| GWT-REQ-003-01 | REQ-003 | ✅ | RUN_OUTPUT | `tests/test_profile_summary_service.py::test_call_llm_switches_by_token_budget[20k-single]` | 20k 单次路径 |
| GWT-REQ-003-02 | REQ-003 | ✅ | RUN_OUTPUT | `tests/test_profile_summary_service.py::test_call_llm_switches_by_token_budget[25k-single]` | 25k 边界单次路径 |
| GWT-REQ-004-01 | REQ-004 | ✅ | RUN_OUTPUT | `tests/test_profile_summary_service.py::test_chunking_disabled_still_allows_normal_document` | 开关关闭后的普通文档 |
| GWT-REQ-004-02 | REQ-004 | ✅ | RUN_OUTPUT | `tests/test_profile_summary_service.py::test_chunking_disabled` | 超长文档显式失败 |
| GWT-REQ-101-01 | REQ-101 | ✅ | RUN_OUTPUT | `docs/v2.6/test_report.md` 中 `TEST-BE-REG-001` | 25k/30k/50k 档位均无超限错误 |
| GWT-REQ-102-01 | REQ-102 | ✅ | RUN_OUTPUT | `docs/v2.6/test_report.md` 中 `TEST-BE-COV-001` | 总覆盖率 `92%` |
| GWT-REQ-103-01 | REQ-103 | ✅ | RUN_OUTPUT | `tests/test_profile_summary_service.py::test_calculate_body_budget_and_execute_stage_calls` | chunk 指标与预算路径 |
| GWT-REQ-C001-01 | REQ-C001 | ✅ | RUN_OUTPUT | `tests/test_token_counter.py::test_chunk_text_with_overlap_preserves_reconstruction_order` | 去重叠后顺序一致 |
| GWT-REQ-C001-02 | REQ-C001 | ✅ | RUN_OUTPUT | `tests/test_profile_summary_service.py::test_chunking_disabled` | 关闭分块不截断 |
| GWT-REQ-C002-01 | REQ-C002 | ✅ | RUN_OUTPUT | `docs/v2.6/test_report.md` 中 `TEST-DEP-001` | 依赖 diff 为空 |
| GWT-REQ-C003-01 | REQ-C003 | ✅ | RUN_OUTPUT | `tests/test_system_profile_import_api.py::test_profile_import_success_returns_task_id_and_records_history` + `tests/test_knowledge_import_api.py::test_knowledge_import_document_updates_completeness` | 对外契约兼容 |
| GWT-REQ-C004-01 | REQ-C004 | ✅ | RUN_OUTPUT | `tests/test_token_counter.py::test_chunk_text_handles_525_paragraph_47_table_scale_sample` | 所有 chunk ≤25k |

### 对抗性审查（REQ-C 强制）
- `REQ-C001`：
  - 泄漏路径 1：分块重叠导致原文重建错序。排除证据：`test_chunk_text_with_overlap_preserves_reconstruction_order`
  - 泄漏路径 2：关闭 chunking 时再次出现静默截断。排除证据：`test_chunking_disabled`
- `REQ-C002`：
  - 泄漏路径 1：运行时依赖文件新增第三方包。排除证据：`TEST-DEP-001`
  - 泄漏路径 2：为 token 计数引入额外库。排除证据：`backend/utils/token_counter.py` + 依赖 diff 为空
- `REQ-C003`：
  - 泄漏路径 1：导入成功载荷结构变化。排除证据：system profile / knowledge API 回归测试
  - 泄漏路径 2：新增必填请求字段或错误包络漂移。排除证据：`tests/test_system_profile_import_api.py`、`tests/test_knowledge_import_api.py`
- `REQ-C004`：
  - 泄漏路径 1：重叠段加入后 chunk 超出预算。排除证据：`test_chunk_text_shrinks_overlap_when_requested_overlap_cannot_fit`
  - 泄漏路径 2：大样本仍产生 >25k chunk。排除证据：`test_chunk_text_handles_525_paragraph_47_table_scale_sample`

## §3 覆盖率证明
| 维度 | 应检项数 | 已检 | 未检 | 未检说明 |
|---|---|---|---|---|
| 事实核实（步骤A） | 4 | 4 | 0 | - |
| 概念交叉引用（步骤B） | 4 | 4 | 0 | - |
| 审查清单项 | 7 | 7 | 0 | - |
| GWT 判定项 | 20 | 20 | 0 | - |

### 对抗性自检
- [x] 是否存在“我知道意思但文本没写清”的地方？否
- [x] 所有新增 API 是否都有完整契约（路径/参数/返回/权限/错误码）？是，本次未新增外部 API
- [x] 所有“可选/或者/暂不”表述是否已收敛为单一口径？是
- [x] 是否有验收用例无法仅凭文档文本判定 pass/fail？否
- [x] 高风险项（兼容/回滚/权限/REQ-C）是否已在本阶段收敛？是

## 建议验证清单（命令级别）
- [x] `.venv/bin/python -m pytest -q --tb=short`
- [x] `cd frontend && npm run build`
- [x] `.venv/bin/python -m compileall -q backend`
- [x] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_token_counter.py tests/test_llm_client.py tests/test_profile_summary_service.py tests/test_system_profile_import_api.py tests/test_knowledge_import_api.py tests/test_knowledge_routes_helpers.py`
- [x] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p pytest_cov --cov=backend.utils.token_counter --cov=backend.utils.llm_client --cov=backend.service.profile_summary_service --cov-report=term-missing tests/test_token_counter.py tests/test_llm_client.py tests/test_profile_summary_service.py`

## 处理记录
| RVW-ID | 严重度 | 处理决策 | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-PRE-001 | P0 | Fix | Codex | 项目级 `pytest` 预审暴露 4 条 ESB 导入兼容性失败，已在正式审查前完成最小兼容修复 | `.venv/bin/python -m pytest -q --tb=short` -> `210 passed in 63.61s` |

## 机器可读摘要块
<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: testing
REVIEW_SCOPE: full
REVIEW_MODES: REQ,TRACE
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
SPOT_CHECK_GWTS: GWT-REQ-001-01,GWT-REQ-102-01,GWT-REQ-C003-01
SPOTCHECK_FILE: docs/v2.6/spotcheck_testing_cr-20260309-001.md
GWT_CHANGE_CLASS: structural
CLARIFICATION_CONFIRMED_BY: N/A
CLARIFICATION_CONFIRMED_AT: N/A
VERIFICATION_COMMANDS: .venv/bin/python -m pytest -q --tb=short,cd frontend && npm run build,.venv/bin/python -m compileall -q backend,PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_token_counter.py tests/test_llm_client.py tests/test_profile_summary_service.py tests/test_system_profile_import_api.py tests/test_knowledge_import_api.py tests/test_knowledge_routes_helpers.py,PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p pytest_cov --cov=backend.utils.token_counter --cov=backend.utils.llm_client --cov=backend.service.profile_summary_service --cov-report=term-missing tests/test_token_counter.py tests/test_llm_client.py tests/test_profile_summary_service.py
REVIEW_RESULT: pass
<!-- REVIEW-SUMMARY-END -->
