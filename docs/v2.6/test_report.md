# 需求评估系统 v2.6 测试报告

## 文档元信息
| 项 | 值 |
|---|---|
| 状态 | Review |
| 作者 | Codex |
| 评审/验收 | User |
| 日期 | 2026-03-09 |
| 版本 | v0.3 |
| 关联需求 | `docs/v2.6/requirements.md` |
| 关联计划 | `docs/v2.6/plan.md` |
| 基线版本（对比口径） | `v2.5` |
| 包含 CR | `CR-20260309-001` |
| 代码版本 | `HEAD` |

## 测试范围与环境
- 覆盖范围：`REQ-001~REQ-004`、`REQ-101~REQ-103`、`REQ-C001~REQ-C004`（共 20 个 GWT）。
- 测试环境：本地 DEV，Linux；v2.6 定向回归使用系统 Python 3.10.18（`pytest 7.4.3` / `pytest-cov 7.0.0`），项目级结果门禁使用 `.venv` Python 3.14.2（`pytest 9.0.2`）。
- 关键约束：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`；覆盖率命令显式使用 `-p pytest_cov`。
- 数据准备：全部使用本地临时目录、stub、mock 响应；不依赖外部 LLM/Embedding 服务。

## 自动化测试证据（🔴 MUST）
| TEST-ID | 场景 | 执行命令 | 结果 |
|---|---|---|---|
| TEST-CONF-001 | 环境变量与模型口径校验 | `rg -n "LLM_MODEL=Qwen3-32B|EMBEDDING_MODEL=Qwen3-Embedding-8B|LLM_MAX_CONTEXT_TOKENS=32000|LLM_INPUT_MAX_TOKENS=25000|LLM_CHUNK_OVERLAP_PARAGRAPHS=2|ENABLE_LLM_CHUNKING=true" .env.backend .env.backend.example .env.backend.internal` | ✅ 3 个环境文件均命中目标配置 |
| TEST-BE-REG-001 | v2.6 后端回归（含接口透传） | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_token_counter.py tests/test_llm_client.py tests/test_profile_summary_service.py tests/test_system_profile_import_api.py tests/test_knowledge_import_api.py tests/test_knowledge_routes_helpers.py` | ✅ `61 passed, 1 warning in 20.49s` |
| TEST-BE-COV-001 | 新增代码覆盖率 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p pytest_cov --cov=backend.utils.token_counter --cov=backend.utils.llm_client --cov=backend.service.profile_summary_service --cov-report=term-missing tests/test_token_counter.py tests/test_llm_client.py tests/test_profile_summary_service.py` | ✅ `37 passed in 8.21s`；总覆盖率 `92%` |
| TEST-DEP-001 | 无新增运行时依赖 | `git diff --unified=0 v2.5 -- requirements.txt backend/requirements.txt pyproject.toml` | ✅ 无输出，未引入新增运行时依赖 |
| TEST-GATE-001 | 项目级结果门禁 | `.venv/bin/python -m pytest -q --tb=short` | ✅ `210 passed in 63.61s` |
| TEST-BUILD-001 | 前端构建门禁 | `cd frontend && npm run build` | ✅ `Compiled successfully.` |
| TEST-TYPE-001 | 后端编译检查 | `.venv/bin/python -m compileall -q backend` | ✅ 无输出，退出码 0 |

说明：
- 按 `plan.md` 原文直接执行 `--cov=backend/utils/...` 时，`pytest-cov 7.0.0` 会返回 `No data to report`；本报告使用等价模块路径 `backend.utils...` / `backend.service...` 作为最终统计口径，不改变覆盖对象。
- 当前仅存在 1 条 `environs` 依赖的弃用 warning，不影响退出码与断言结果。

## 覆盖率结果
| 模块 | 覆盖率 | 备注 |
|---|---|---|
| `backend/utils/token_counter.py` | 92% | 覆盖估算、usage 提取、分块、超长段落失败、525 段落量级样本 |
| `backend/utils/llm_client.py` | 90% | 覆盖 raw 调用、重试、JSON 提取、Stage1/Stage2 合并、异常路径 |
| `backend/service/profile_summary_service.py` | 92% | 覆盖上下文选择、单次/分块路径、关闭开关、失败原子性、通知、任务状态 |
| 总体 | 92% | 超过 `REQ-102` 目标 `> 80%` |

## 需求覆盖矩阵（GWT 粒度）
<!-- TEST-COVERAGE-MATRIX-BEGIN -->
| GWT-ID | REQ-ID | 需求摘要 | 对应测试/证据 | 结果 |
|---|---|---|---|---|
| GWT-REQ-001-01 | REQ-001 | 30k 文档自动切成 ≥2 块且每块 ≤25k | `tests/test_profile_summary_service.py::test_call_llm_switches_by_token_budget[30k-chunk]` + `tests/test_token_counter.py::test_chunk_text_handles_525_paragraph_47_table_scale_sample` | ✅ PASS |
| GWT-REQ-001-02 | REQ-001 | 525 段落 + 47 表格量级样本不触发 Token 超限 | `tests/test_token_counter.py::test_chunk_text_handles_525_paragraph_47_table_scale_sample` | ✅ PASS |
| GWT-REQ-001-03 | REQ-001 | 单段超限时固定失败 | `tests/test_token_counter.py::test_chunk_text_rejects_single_paragraph_above_budget` | ✅ PASS |
| GWT-REQ-001-04 | REQ-001 | 任一块失败时整体失败且不写部分结果 | `tests/test_profile_summary_service.py::test_chunking_path_fails_when_any_chunk_processing_fails` | ✅ PASS |
| GWT-REQ-002-01 | REQ-002 | Stage1 `relevant_domains` 去重合并 | `tests/test_llm_client.py::test_merge_stage1_stage2_responses` | ✅ PASS |
| GWT-REQ-002-02 | REQ-002 | Stage2 `module_structure` 按 `module_name` 合并 | `tests/test_llm_client.py::test_merge_stage1_stage2_responses` | ✅ PASS |
| GWT-REQ-002-03 | REQ-002 | Stage2 字符串字段按 `A; B` 拼接 | `tests/test_llm_client.py::test_merge_stage1_stage2_responses` | ✅ PASS |
| GWT-REQ-002-04 | REQ-002 | Stage2 缺失子字段按空值归一化 | `tests/test_profile_summary_service.py::test_calculate_body_budget_and_execute_stage_calls` | ✅ PASS |
| GWT-REQ-003-01 | REQ-003 | 20k 文档只走 1 次 Stage1 + 1 次 Stage2 | `tests/test_profile_summary_service.py::test_call_llm_switches_by_token_budget[20k-single]` | ✅ PASS |
| GWT-REQ-003-02 | REQ-003 | 25k 边界值仍走单次调用 | `tests/test_profile_summary_service.py::test_call_llm_switches_by_token_budget[25k-single]` | ✅ PASS |
| GWT-REQ-004-01 | REQ-004 | 关闭分块后普通文档仍可处理 | `tests/test_profile_summary_service.py::test_chunking_disabled_still_allows_normal_document` | ✅ PASS |
| GWT-REQ-004-02 | REQ-004 | 关闭分块后超长文档显式失败且不截断 | `tests/test_profile_summary_service.py::test_chunking_disabled` | ✅ PASS |
| GWT-REQ-101-01 | REQ-101 | 25k/30k/50k 档位与 525 段落量级样本均无超限错误 | `tests/test_profile_summary_service.py::test_call_llm_switches_by_token_budget[*]` + `tests/test_token_counter.py::test_chunk_text_handles_525_paragraph_47_table_scale_sample` + `TEST-BE-REG-001` | ✅ PASS |
| GWT-REQ-102-01 | REQ-102 | 覆盖率 >80% | `TEST-BE-COV-001`（总覆盖率 `92%`） | ✅ PASS |
| GWT-REQ-103-01 | REQ-103 | 3 块场景总耗时受控并记录 chunk 指标 | `tests/test_profile_summary_service.py::test_calculate_body_budget_and_execute_stage_calls` + `tests/test_profile_summary_service.py::test_chunking_path` | ✅ PASS |
| GWT-REQ-C001-01 | REQ-C001 | 分块后去重叠重建顺序与原文一致 | `tests/test_token_counter.py::test_chunk_text_with_overlap_preserves_reconstruction_order` | ✅ PASS |
| GWT-REQ-C001-02 | REQ-C001 | 关闭分块时超长文档不得静默截断 | `tests/test_profile_summary_service.py::test_chunking_disabled` | ✅ PASS |
| GWT-REQ-C002-01 | REQ-C002 | 不新增外部运行时依赖 | `TEST-DEP-001` | ✅ PASS |
| GWT-REQ-C003-01 | REQ-C003 | 导入接口对外契约不变 | `tests/test_system_profile_import_api.py::test_profile_import_success_returns_task_id_and_records_history` + `tests/test_knowledge_import_api.py::test_knowledge_import_document_updates_completeness` + `tests/test_system_profile_import_api.py::test_profile_import_passes_full_document_text_to_summary_job` + `tests/test_knowledge_import_api.py::test_knowledge_import_passes_full_document_text_to_summary_job` | ✅ PASS |
| GWT-REQ-C004-01 | REQ-C004 | 所有 chunk 估算值 ≤25k | `tests/test_token_counter.py::test_chunk_text_with_overlap_preserves_reconstruction_order` + `tests/test_token_counter.py::test_chunk_text_shrinks_overlap_when_requested_overlap_cannot_fit` + `tests/test_token_counter.py::test_chunk_text_handles_525_paragraph_47_table_scale_sample` | ✅ PASS |
<!-- TEST-COVERAGE-MATRIX-END -->

## CR 验证证据
| CR-ID | 验收标准 | 证据 | 结论 |
|---|---|---|---|
| CR-20260309-001 | Token 感知分块、接口原文透传、回滚开关与无新增依赖 | `TEST-CONF-001` / `TEST-BE-REG-001` / `TEST-BE-COV-001` / `TEST-DEP-001` | ✅ 通过 |

## 缺陷与处理
| BUG-ID | 问题描述 | 状态 | 处理 |
|---|---|---|---|
| BUG-20260309-001 | `pytest-cov` 按计划原命令使用斜杠路径时无覆盖数据 | 已修复 | 改为等价模块路径并显式加载 `pytest_cov` |
| BUG-20260309-002 | 项目级 `pytest` 预审暴露 4 条 ESB XLSX/CSV 兼容性失败，阻断 Testing 阶段结果门禁 | 已修复 | 在 `document_parser.py` 去除 XLSX 固定表头前置假设，并在 `esb_service.py` 补 legacy 模板回退与 `服务方系统标识` 别名，复测恢复到 `210 passed` |

## 测试结论
- 自动化回归：`61 passed, 1 warning in 20.49s`。
- 覆盖率：目标模块总覆盖率 `92%`，满足 `REQ-102`。
- 依赖与配置：无新增运行时依赖；`Qwen3-32B` / `Qwen3-Embedding-8B` 与 token/chunking 配置已在三套环境文件显式声明。
- 项目级门禁：`.venv/bin/python -m pytest -q --tb=short`、`cd frontend && npm run build`、`.venv/bin/python -m compileall -q backend` 全部通过。
- 综合结论：本轮 `REQ/REQ-C` 自动化证据闭环，且项目级结果门禁通过，可进入下一阶段验证/发布准备。

## 变更记录
| 版本 | 日期 | 说明 | 作者 |
|---|---|---|---|
| v0.1 | 2026-03-09 | 初始化 v2.6 测试报告，固化回归、覆盖率、依赖差异与 GWT 证据 | Codex |
| v0.2 | 2026-03-09 | 补记项目级结果门禁与 Testing 预审问题处理记录 | Codex |
| v0.3 | 2026-03-09 | 修正模型命名漂移，统一测试证据中的内网目标模型口径 | Codex |
