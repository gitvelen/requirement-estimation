# 需求分析与评估系统 v2.7 测试报告

## 文档元信息
| 项 | 值 |
|---|---|
| 状态 | Review |
| 作者 | Codex |
| 评审/验证 | User |
| 日期 | 2026-03-14 |
| 版本 | v0.5 |
| 关联需求 | `docs/v2.7/requirements.md` |
| 关联计划 | `docs/v2.7/plan.md` |
| 基线版本（对比口径） | `v2.6` |
| 包含 CR（如有） | `CR-20260314-001` |
| 代码版本 | `HEAD` |

## 测试范围与环境
- 覆盖范围：`REQ-001~REQ-012`、`REQ-101~REQ-105`、`REQ-C001~REQ-C008`（共 72 个 GWT）。
- 测试环境：本地 DEV，Linux；后端统一使用 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest` 口径，前端使用 `CI=true npm test` 与 `npm run build`。
- 关键配置：v2.7 开关与内网配置源口径固定为 `.env.backend.internal`；自动化回归使用临时 `REPORT_DIR/UPLOAD_DIR` 与 stub/mock 数据。
- 数据准备与清理：所有集成/回归测试均使用本地临时目录、fixture 与 mock，不依赖外部 LLM/Embedding 服务；API 回归使用临时数据目录启动本地 `uvicorn` 实例。
- 服务治理模板口径：最新样例以 `data/esb-template.xlsx` 为准；`data/接口申请模板.xlsx` 仅保留为兼容输入样例。

## 测试分层概览
| 测试层级 | 用例数 | 通过 | 失败 | 跳过 | 覆盖说明 |
|---|---|---|---|---|---|
| 单元测试 | 4 组 | 4 | 0 | 0 | schema / runtime / memory / skill adapter 纯逻辑验证 |
| 集成测试 | 6 组 | 6 | 0 | 0 | PM 导入、治理导入、系统清单、识别/拆解、code scan、部署脚本 |
| E2E 测试 | 1 组 | 1 | 0 | 0 | 本地 API regression + REQ-003/REQ-004 自动化链路 |
| 回归测试 | 3 组 | 3 | 0 | 0 | full pytest、前端页面 smoke、frontend build |

## 集成测试证据（Integration Required 的 REQ）

### AI 自动化测试（🔴 MUST）

| REQ-ID | 测试场景 | 测试脚本路径 | 验证点 | 执行命令 | 结果 | 日志 |
|---|---|---|---|---|---|---|
| REQ-001 | PM 导入页 3 文档类型、导入成功与 execution-status | `tests/test_system_profile_import_api.py`、`tests/test_system_profile_routes_helpers.py`、`frontend/src/__tests__/systemProfileImportPage.render.test.js` | 1. 页面仅保留 3 类卡片 2. 导入成功记录 history 3. `execution-status` / alias 可查询 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_skill_runtime_service.py tests/test_system_profile_import_api.py tests/test_system_profile_routes_helpers.py` + `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileImportPage.render.test.js` | ✅ 通过 | 本地命令输出 |
| REQ-002 | 5 域 canonical schema 与画像面板 | `tests/test_profile_schema_v27.py`、`tests/test_memory_service_v27.py`、`frontend/src/__tests__/systemProfileBoardPage.v27.test.js` | 1. 5 域字段与 `extensions` 完整 2. D4 子结构固定 3. 前端按 `profile_data` 保存和展示 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_profile_schema_v27.py tests/test_memory_service_v27.py` + `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileBoardPage.v27.test.js` | ✅ 通过 | 本地命令输出 |
| REQ-005 | Skill Runtime 注册、路由与 code scan 接入 | `tests/test_skill_runtime_service.py`、`tests/test_code_scan_skill_v27.py`、`tests/test_code_scan_api.py` | 1. 6 个内置 Skill 注册 2. scene 路由正确 3. code scan 写建议与 Memory | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_skill_runtime_service.py tests/test_code_scan_skill_v27.py tests/test_code_scan_api.py` | ✅ 通过 | 本地命令输出 |
| REQ-006 | 多模板/多格式兼容与 canonical 输出 | `tests/test_system_profile_routes_helpers.py`、`tests/test_esb_service.py`、`tests/test_system_list_import.py`、`tests/test_system_list_unified_source.py` | 1. 文档解析走统一文本链路 2. 治理模板别名/深表头兼容 3. 单一系统清单模板可解析 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_system_profile_routes_helpers.py tests/test_esb_service.py tests/test_system_list_import.py tests/test_system_list_unified_source.py` | ✅ 通过 | 本地命令输出 |
| REQ-007 | Profile update / identification / function adjustment 三类 Memory | `tests/test_memory_service_v27.py`、`tests/test_system_catalog_profile_init_v27.py`、`tests/test_task_feature_update_actor.py`、`tests/test_task_modification_compat.py` | 1. 公共 Memory 模型支持查询与未来类型 2. 成功动作均写 Memory 3. legacy/new modification 共存 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_memory_service_v27.py tests/test_system_catalog_profile_init_v27.py tests/test_task_feature_update_actor.py tests/test_task_modification_compat.py` | ✅ 通过 | 本地命令输出 |
| REQ-008 | Memory 驱动系统识别与直接判定 | `tests/test_system_identification_memory_v27.py` | 1. `matched/ambiguous/unknown` 三态 2. `final_verdict` 强制存在 3. 决策写入 Memory | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_system_identification_memory_v27.py` | ✅ 通过 | 本地命令输出 |
| REQ-009 | 场景化 `auto_apply / suggestion_only / reject` 策略 | `tests/test_service_governance_import_v27.py`、`tests/test_system_catalog_profile_init_v27.py`、`tests/test_code_scan_skill_v27.py` | 1. 治理导入 D3 `auto_apply` 2. 系统清单非空画像 `reject/skip` 3. code scan 只进 suggestions | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_service_governance_import_v27.py tests/test_system_catalog_profile_init_v27.py tests/test_code_scan_skill_v27.py` | ✅ 通过 | 本地命令输出 |
| REQ-010 | 功能点拆解读取/回写 Memory | `tests/test_feature_breakdown_memory_v27.py`、`tests/test_task_feature_update_actor.py`、`tests/test_task_modification_compat.py` | 1. 读取历史调整模式 2. 低风险归一化自动应用 3. 新旧修改记录兼容读写 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_feature_breakdown_memory_v27.py tests/test_task_feature_update_actor.py tests/test_task_modification_compat.py` | ✅ 通过 | 本地命令输出 |
| REQ-011 | Skill / 导入 / Memory 失败态可判定 | `tests/test_system_profile_import_api.py`、`tests/test_memory_service_v27.py`、`tests/test_code_scan_skill_v27.py` | 1. 失败终态可读 2. `partial_success` 补偿态明确 3. 不写半成品正式画像 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_system_profile_import_api.py tests/test_memory_service_v27.py tests/test_code_scan_skill_v27.py` | ✅ 通过 | 本地命令输出 |
| REQ-012 | 旧 schema 与 history_report 清理 | `tests/test_cleanup_v27.py` | 1. 旧 schema / history_report 存量被移除 2. 失败时返回 `failed` 与原因 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_cleanup_v27.py` | ✅ 通过 | 本地命令输出 |

### 人类验证清单（关键流程，🟡 建议）

| REQ-ID | 验证场景 | 操作步骤 | 预期结果 | 验证人 | 验证时间 | 结果 | 问题记录 |
|---|---|---|---|---|---|---|---|
| REQ-001 | PM 导入页 UI 验证 | 1. 进入“知识导入” 2. 查看文档卡片 3. 上传 3 类合法文档 | 页面只展示 3 类卡片；提交后能看到 execution-status | [待填写] | [待填写] | [待验证] | - |
| REQ-002 | 信息展示页保存/回显 | 1. 进入“信息展示” 2. 编辑 D1-D5 字段 3. 保存后刷新页面 | 页面按 v2.7 canonical 结构回显；前端不展示来源、操作人、扩展信息与 Memory 资产 | [待填写] | [待填写] | [待验证] | - |

## 端到端测试证据（E2E Required 的 REQ）

### AI 自动化测试（🔴 MUST）

| REQ-ID | 测试场景 | 测试脚本路径 | 验证点 | 执行命令 | 结果 | 日志 |
|---|---|---|---|---|---|---|
| REQ-003 | admin 服务治理导入 -> 页面统计 -> D3 联动 | `tests/test_service_governance_import_v27.py`、`tests/test_esb_import_api.py`、`frontend/src/__tests__/serviceGovernancePage.render.test.js` | 1. admin 全局导入权限生效 2. 页面展示 matched/unmatched 3. D3 canonical 与汇总统计更新 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_esb_import_api.py tests/test_service_governance_import_v27.py tests/test_esb_service.py` + `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/serviceGovernancePage.render.test.js` | ✅ 通过 | 本地命令输出 |
| REQ-004 | admin 系统清单 preview/confirm -> 空画像初始化 -> 页面结果回显 | `tests/test_system_list_import.py`、`tests/test_system_catalog_profile_init_v27.py`、`tests/test_system_list_unified_source.py`、`tests/test_system_list_cache_reload.py`、`frontend/src/__tests__/systemListConfigPage.v27.test.js` | 1. preview 只做校验不写画像 2. confirm 仅更新空画像 3. 页面展示已更新系统名称、预检错误与用户可读跳过原因 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_system_list_import.py tests/test_system_catalog_profile_init_v27.py tests/test_system_list_unified_source.py tests/test_system_list_cache_reload.py` + `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemListConfigPage.v27.test.js` | ✅ 通过 | 本地命令输出 |

### 人类验证结果（🔴 MUST）

| REQ-ID | 验证场景 | 操作步骤 | 预期结果 | 验证人 | 验证时间 | 结果 | 问题记录 |
|---|---|---|---|---|---|---|---|
| REQ-003 | admin 服务治理导入全链路 | 1. 进入 `/admin/service-governance` 2. 上传最新治理模板（以 `data/esb-template.xlsx` 口径为准） 3. 查看统计、未匹配项与目标系统画像 D3 | 页面统计、未匹配项、D3 画像联动与自动化结果一致 | User | 2026-03-14 23:59 | 通过 | 用户登录可验收环境验证后反馈“正常” |
| REQ-004 | admin 系统清单确认导入全链路 | 1. 进入“系统清单” 2. preview 导入 3. confirm 导入 4. 核对空画像初始化与非空画像跳过 | preview 不写画像；confirm 仅更新空画像；结果区以系统名称和用户可读跳过原因展示结果 | User | 2026-03-14 23:59 | 通过 | 用户登录可验收环境验证后反馈“正常” |

## 自动化测试证据（项目级门禁）
| TEST-ID | 场景 | 执行命令 | 结果 |
|---|---|---|---|
| TEST-FE-001 | PM 导入页 v2.7 smoke | `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileImportPage.render.test.js` | ✅ 通过 |
| TEST-FE-002 | 画像面板 v2.7 smoke | `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileBoardPage.v27.test.js` | ✅ 通过 |
| TEST-FE-003 | admin 服务治理页 smoke | `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/serviceGovernancePage.render.test.js` | ✅ 通过 |
| TEST-FE-004 | 系统清单页 v2.7 smoke | `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemListConfigPage.v27.test.js` | ✅ 通过 |
| TEST-FE-005 | 导航/标题回归 smoke | `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/navigationAndPageTitleRegression.test.js` | ✅ 通过 |
| TEST-FE-006 | 前端用户可读回归（导入状态/导航/系统清单结果） | `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemListConfigPage.v27.test.js src/__tests__/systemProfileImportPage.render.test.js src/__tests__/navigationAndPageTitleRegression.test.js` | ✅ `3 suites, 12 tests passed`（含既有 React Router / AntD warning 输出） |
| TEST-BE-014 | 系统清单 confirm 结果用户可读契约回归 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_system_catalog_profile_init_v27.py::test_catalog_confirm_initializes_blank_profiles_and_writes_memory` | ✅ `1 passed, 1 warning` |
| TEST-DEPLOY-001 | 清理脚本 + 内网部署脚本回归 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_cleanup_v27.py tests/test_deploy_backend_internal_script.py tests/test_deploy_frontend_internal_script.py` | ✅ `7 passed` |
| TEST-GATE-001 | 项目级全量回归 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q --tb=short` | ✅ `237 passed, 1 warning` |
| TEST-BUILD-001 | 前端构建门禁 | `cd frontend && npm run build` | ✅ `Compiled successfully.` |
| TEST-LINT-001 | 前端目标文件 lint | `cd frontend && npx eslint src/pages/SystemListConfigPage.js src/__tests__/systemListConfigPage.v27.test.js src/pages/SystemProfileImportPage.js src/components/MainLayout.js src/__tests__/systemProfileImportPage.render.test.js src/__tests__/navigationAndPageTitleRegression.test.js` | ✅ 无输出，退出码 0 |
| TEST-TYPE-001 | 后端编译检查 | `python -m compileall -q backend` | ✅ 无输出，退出码 0 |
| TEST-DEPS-001 | 无新增运行时依赖 | `git diff --unified=0 v2.6 -- pyproject.toml requirements.txt backend/requirements.txt frontend/package.json` | ✅ 空 diff |
| TEST-CONTRACT-001 | v2.7 契约/配置口径对照 | `rg -n "\\.env\\.backend\\.internal|ENABLE_V27_PROFILE_SCHEMA|ENABLE_V27_RUNTIME|ENABLE_SERVICE_GOVERNANCE_IMPORT|ENABLE_SYSTEM_CATALOG_PROFILE_INIT|profile/execution-status|profile/extraction-status" docs/v2.7/deployment.md docs/技术方案设计.md docs/接口文档.md docs/部署记录.md docs/v2.7/status.md` | ✅ 命中 v2.7 canonical 口径 |
| TEST-API-001 | 本地 API regression | `BASE_URL=http://127.0.0.1:18080 bash scripts/api_regression.sh` | ✅ `health` / `requirement/tasks` / `api regression finished`；知识库接口 `401` 记为可选告警 |

## 需求覆盖矩阵（GWT 粒度追溯）
<!-- TEST-COVERAGE-MATRIX-BEGIN -->
| GWT-ID | REQ-ID | 需求摘要 | 对应测试(TEST-ID) | 证据类型 | 证据 | 结果 | 备注 |
| GWT-REQ-001-01 | REQ-001 | Given manager 访问 PM 导入页，When 页面渲染完成，Then 页面仅展示“需求文档”“设计文档”“技术方案”三类卡片，且页面中不出现“历史评估报告”“服务治理文档”字符串。 | TEST-FE-001 / TEST-BE-001 | RUN_OUTPUT | `frontend/src/__tests__/systemProfileImportPage.render.test.js` + `tests/test_system_profile_import_api.py` | ✅ PASS | 前端卡片与导入/execution-status 契约回归 |
| GWT-REQ-001-02 | REQ-001 | Given manager 上传合法 `requirements/design/tech_solution` 文档，When 调用导入接口成功，Then 系统记录成功导入历史，且返回可查询的 Runtime/提取状态。 | TEST-FE-001 / TEST-BE-001 | RUN_OUTPUT | `frontend/src/__tests__/systemProfileImportPage.render.test.js` + `tests/test_system_profile_import_api.py` | ✅ PASS | 前端卡片与导入/execution-status 契约回归 |
| GWT-REQ-001-03 | REQ-001 | Given 请求携带 `doc_type=history_report` 或 `doc_type=esb`，When 调用 PM 文档导入接口，Then 系统返回明确失败结果，且不会生成成功导入历史记录。 | TEST-FE-001 / TEST-BE-001 | RUN_OUTPUT | `frontend/src/__tests__/systemProfileImportPage.render.test.js` + `tests/test_system_profile_import_api.py` | ✅ PASS | 前端卡片与导入/execution-status 契约回归 |
| GWT-REQ-002-01 | REQ-002 | Given 系统首次创建或已清空画像，When 读取画像详情，Then 返回 5 个一级域，且每个域都包含本需求定义的目标字段和 `extensions` 键。 | TEST-BE-002 / TEST-FE-002 | RUN_OUTPUT | `tests/test_profile_schema_v27.py` + `frontend/src/__tests__/systemProfileBoardPage.v27.test.js` | ✅ PASS | canonical 结构、D4 子结构与信息展示页回归 |
| GWT-REQ-002-02 | REQ-002 | Given 读取 D4 技术架构域，When 查看 `tech_stack` 与 `performance_baseline` 结构，Then `tech_stack` 至少包含 `languages/frameworks/databases/middleware/others` 五类键，且 `performance_baseline` 支持“联机/批量 + processing_model”结构。 | TEST-BE-002 / TEST-FE-002 | RUN_OUTPUT | `tests/test_profile_schema_v27.py` + `frontend/src/__tests__/systemProfileBoardPage.v27.test.js` | ✅ PASS | canonical 结构、D4 子结构与信息展示页回归 |
| GWT-REQ-002-03 | REQ-002 | Given manager 在画像面板保存包含 D1-D5 新字段的画像，When 重新读取并渲染页面，Then 页面按新 5 域结构展示并保留已保存值。 | TEST-BE-002 / TEST-FE-002 | RUN_OUTPUT | `tests/test_profile_schema_v27.py` + `frontend/src/__tests__/systemProfileBoardPage.v27.test.js` | ✅ PASS | canonical 结构、D4 子结构与信息展示页回归 |
| GWT-REQ-003-01 | REQ-003 | Given admin 在服务治理页上传包含 3 条可匹配记录和 1 条未匹配记录的治理模板，When 导入完成，Then 页面展示“匹配成功=3、未匹配=1”，且未匹配项清单包含该 1 条记录。 | TEST-BE-003 / TEST-FE-003 | RUN_OUTPUT | `tests/test_service_governance_import_v27.py` + `tests/test_esb_import_api.py` + `frontend/src/__tests__/serviceGovernancePage.render.test.js` | ✅ PASS | 自动化链路已通过；人工 E2E 已补齐 |
| GWT-REQ-003-02 | REQ-003 | Given 治理模板记录的系统名与系统清单标准名称一致，When 导入完成，Then 对应系统画像 D3 至少包含服务名称、服务分类、对端系统、消费方数量、状态字段，并可读取到域级汇总统计。 | TEST-BE-003 / TEST-FE-003 | RUN_OUTPUT | `tests/test_service_governance_import_v27.py` + `tests/test_esb_import_api.py` + `frontend/src/__tests__/serviceGovernancePage.render.test.js` | ✅ PASS | 自动化链路已通过；人工 E2E 已补齐 |
| GWT-REQ-003-03 | REQ-003 | Given 治理模板缺失必填列或文件不可解析，When admin 提交导入，Then 系统返回明确失败结果，且不更新任何系统画像。 | TEST-BE-003 / TEST-FE-003 | RUN_OUTPUT | `tests/test_service_governance_import_v27.py` + `tests/test_esb_import_api.py` + `frontend/src/__tests__/serviceGovernancePage.render.test.js` | ✅ PASS | 自动化链路已通过；人工 E2E 已补齐 |
| GWT-REQ-004-01 | REQ-004 | Given admin 上传包含合法与非法行混合的系统清单模板，When 执行 preview，Then 系统返回行级校验结果与错误行号，且不更新任何系统画像。 | TEST-BE-004 / TEST-FE-004 | RUN_OUTPUT | `tests/test_system_list_import.py` + `tests/test_system_catalog_profile_init_v27.py` + `frontend/src/__tests__/systemListConfigPage.v27.test.js` | ✅ PASS | 自动化链路已通过；人工 E2E 已补齐 |
| GWT-REQ-004-02 | REQ-004 | Given admin 在系统清单首次初始化场景下对 100 条合法记录执行 confirm，且其中命中系统存在空画像与非空画像两类，When Runtime 完成 `system_catalog_skill`，Then 系统仅对空画像直接完成初始化写入、无需 PM 接受建议，并返回可回溯的初始化结果，前端结果区展示系统名称与用户可读状态。 | TEST-BE-004 / TEST-FE-004 | RUN_OUTPUT | `tests/test_system_list_import.py` + `tests/test_system_catalog_profile_init_v27.py` + `frontend/src/__tests__/systemListConfigPage.v27.test.js` | ✅ PASS | 自动化链路已通过；人工 E2E 已补齐 |
| GWT-REQ-004-03 | REQ-004 | Given 系统清单已存在，且某命中系统的 `profile_data` 下 D1-D5 canonical 字段中任一字段非空，When admin 再次执行 confirm 覆盖导入，Then 该系统画像保持不变，并在结果中标记等效的用户可读跳过原因。 | TEST-BE-004 / TEST-FE-004 | RUN_OUTPUT | `tests/test_system_list_import.py` + `tests/test_system_catalog_profile_init_v27.py` + `frontend/src/__tests__/systemListConfigPage.v27.test.js` | ✅ PASS | 自动化链路已通过；人工 E2E 已补齐 |
| GWT-REQ-004-04 | REQ-004 | Given 某空画像命中系统的系统清单记录同时包含 canonical 字段、弱证据字段和 ignore 字段，When admin 执行 confirm，Then 系统仅按本需求定义把字段分别写入 canonical 或 `extensions`，且 ignore 字段不进入画像。 | TEST-BE-004 / TEST-FE-004 | RUN_OUTPUT | `tests/test_system_list_import.py` + `tests/test_system_catalog_profile_init_v27.py` + `frontend/src/__tests__/systemListConfigPage.v27.test.js` | ✅ PASS | 自动化链路已通过；人工 E2E 已补齐 |
| GWT-REQ-004-05 | REQ-004 | Given 系统清单记录包含 `功能描述` 和 `关联系统` 两列，When admin 执行 confirm 初始化空画像，Then `功能描述` 只进入 `D1.service_scope`，`关联系统` 只进入 `D3.extensions.catalog_related_systems`，两者都不触发 D2 或 D3 canonical 写入。 | TEST-BE-004 / TEST-FE-004 | RUN_OUTPUT | `tests/test_system_list_import.py` + `tests/test_system_catalog_profile_init_v27.py` + `frontend/src/__tests__/systemListConfigPage.v27.test.js` | ✅ PASS | 自动化链路已通过；人工 E2E 已补齐 |
| GWT-REQ-005-01 | REQ-005 | Given Runtime 加载 v2.7 注册表，When 查询平台组件与 Scene 配置，Then 可读取到 Registry、Router、Scene Executor、Policy Gate、Memory Reader/Writer 五类能力以及已配置的业务 Scene。 | TEST-BE-005 | RUN_OUTPUT | `tests/test_skill_runtime_service.py` + `tests/test_code_scan_skill_v27.py` | ✅ PASS | Runtime 注册表、Scene 路由与 code_scan 边界 |
| GWT-REQ-005-02 | REQ-005 | Given 查询内置 Skill 注册表，When 检查 Skill 列表，Then 注册表中存在且仅存在 `service_governance_skill`、`system_catalog_skill`、`requirements_skill`、`design_skill`、`tech_solution_skill`、`code_scan_skill` 六项内置 Skill。 | TEST-BE-005 | RUN_OUTPUT | `tests/test_skill_runtime_service.py` + `tests/test_code_scan_skill_v27.py` | ✅ PASS | Runtime 注册表、Scene 路由与 code_scan 边界 |
| GWT-REQ-005-03 | REQ-005 | Given 查询任一 Skill 定义，When 检查配置项，Then 每个 Skill 都明确声明 `skill_id/skill_type/supported_inputs/supported_tasks/target_artifacts/execution_mode/decision_policy/version`。 | TEST-BE-005 | RUN_OUTPUT | `tests/test_skill_runtime_service.py` + `tests/test_code_scan_skill_v27.py` | ✅ PASS | Runtime 注册表、Scene 路由与 code_scan 边界 |
| GWT-REQ-005-04 | REQ-005 | Given `scene_id=admin_service_governance_import` 或 `scene_id=admin_system_catalog_import`，When Runtime 执行场景，Then 系统分别路由到 `service_governance_skill` 或 `system_catalog_skill`，并在 Skill 后执行 Policy Gate 与 Memory Writer，而不是仅执行单个脚本后返回。 | TEST-BE-005 | RUN_OUTPUT | `tests/test_skill_runtime_service.py` + `tests/test_code_scan_skill_v27.py` | ✅ PASS | Runtime 注册表、Scene 路由与 code_scan 边界 |
| GWT-REQ-005-05 | REQ-005 | Given 注册表中存在一个 `enabled=false` 的未来 Skill 定义（如 `requirement_review_skill`），When Runtime 加载注册表，Then 该定义可被识别为合法配置，但不会被纳入可执行内置 Skill 集合。 | TEST-BE-005 | RUN_OUTPUT | `tests/test_skill_runtime_service.py` + `tests/test_code_scan_skill_v27.py` | ✅ PASS | Runtime 注册表、Scene 路由与 code_scan 边界 |
| GWT-REQ-005-06 | REQ-005 | Given 查询 `code_scan_skill` 的注册定义，When 检查其输入源与扫描范围，Then 可读取到 `repo_path`、`repo_archive` 两种输入源，以及“Java / Spring Boot + JS / TS 中度语义扫描”的固定能力边界。 | TEST-BE-005 | RUN_OUTPUT | `tests/test_skill_runtime_service.py` + `tests/test_code_scan_skill_v27.py` | ✅ PASS | Runtime 注册表、Scene 路由与 code_scan 边界 |
| GWT-REQ-006-01 | REQ-006 | Given 两份“需求文档”语义相近但标题层级和章节命名不同，When `requirements_skill` 提取完成，Then 两份结果都输出同一套 D1/D2/D5 目标字段键。 | TEST-BE-001 / TEST-BE-003 / TEST-BE-004 | RUN_OUTPUT | `tests/test_system_profile_routes_helpers.py` + `tests/test_esb_service.py` + `tests/test_system_list_unified_source.py` | ✅ PASS | 多模板/多表头/单系统清单 canonical 化 |
| GWT-REQ-006-02 | REQ-006 | Given 两份列名别名不同但语义一致的治理模板，When `service_governance_skill` 提取完成，Then 两份结果都归一到同一套 D3 canonical 字段键，或对无法识别列返回明确行级错误。 | TEST-BE-001 / TEST-BE-003 / TEST-BE-004 | RUN_OUTPUT | `tests/test_system_profile_routes_helpers.py` + `tests/test_esb_service.py` + `tests/test_system_list_unified_source.py` | ✅ PASS | 多模板/多表头/单系统清单 canonical 化 |
| GWT-REQ-006-03 | REQ-006 | Given 系统清单模板包含额外非核心列，When `system_catalog_skill` 处理 confirm 数据，Then 系统仍按 canonical 字段解析可初始化字段，并对缺失核心字段的记录返回行级错误，而不是中断全部处理。 | TEST-BE-001 / TEST-BE-003 / TEST-BE-004 | RUN_OUTPUT | `tests/test_system_profile_routes_helpers.py` + `tests/test_esb_service.py` + `tests/test_system_list_unified_source.py` | ✅ PASS | 多模板/多表头/单系统清单 canonical 化 |
| GWT-REQ-006-04 | REQ-006 | Given 当前系统清单模板仅包含单一系统清单表，When `system_catalog_skill` 执行 preview 或 confirm，Then 系统可正常解析该模板且不会因为缺少子系统 Sheet 而失败。 | TEST-BE-001 / TEST-BE-003 / TEST-BE-004 | RUN_OUTPUT | `tests/test_system_profile_routes_helpers.py` + `tests/test_esb_service.py` + `tests/test_system_list_unified_source.py` | ✅ PASS | 多模板/多表头/单系统清单 canonical 化 |
| GWT-REQ-006-05 | REQ-006 | Given PM 上传 `docx`、文本型 `pdf` 或 `pptx` 的需求/设计/技术方案文档，When 文档类 skill 执行，Then 系统按统一文本解析链路处理；若上传扫描件 PDF 或纯图片型 PPTX，Then 系统明确返回“超出本期有效性范围”或等效提示，而不是伪造高置信提取结果。 | TEST-BE-001 / TEST-BE-003 / TEST-BE-004 | RUN_OUTPUT | `tests/test_system_profile_routes_helpers.py` + `tests/test_esb_service.py` + `tests/test_system_list_unified_source.py` | ✅ PASS | 多模板/多表头/单系统清单 canonical 化 |
| GWT-REQ-007-01 | REQ-007 | Given 某系统画像完成一次字段更新，When 业务动作成功，Then 系统写入一条 `memory_type=profile_update` 的 Memory，且包含字段变化摘要或等效 diff 信息。 | TEST-BE-002 / TEST-BE-004 / TEST-BE-006 | RUN_OUTPUT | `tests/test_memory_service_v27.py` + `tests/test_system_catalog_profile_init_v27.py` + `tests/test_task_feature_update_actor.py` | ✅ PASS | 三类 Memory 写入与未来类型扩展 |
| GWT-REQ-007-02 | REQ-007 | Given 系统识别完成一次判定，When 结果落库，Then 系统写入一条 `memory_type=identification_decision` 的 Memory，且包含最终判定和理由摘要。 | TEST-BE-002 / TEST-BE-004 / TEST-BE-006 | RUN_OUTPUT | `tests/test_memory_service_v27.py` + `tests/test_system_catalog_profile_init_v27.py` + `tests/test_task_feature_update_actor.py` | ✅ PASS | 三类 Memory 写入与未来类型扩展 |
| GWT-REQ-007-03 | REQ-007 | Given PM 在 AI 首轮功能点结果上执行新增、删除、合并、拆分、改写、复杂度调整或归属调整，When 保存修改，Then 系统写入 `memory_type=function_point_adjustment` 的 Memory，且记录对应调整分类。 | TEST-BE-002 / TEST-BE-004 / TEST-BE-006 | RUN_OUTPUT | `tests/test_memory_service_v27.py` + `tests/test_system_catalog_profile_init_v27.py` + `tests/test_task_feature_update_actor.py` | ✅ PASS | 三类 Memory 写入与未来类型扩展 |
| GWT-REQ-007-04 | REQ-007 | Given 系统尝试写入 `memory_type=review_issue` 的未来类型记录，When 校验公共元数据，Then Memory 模型接受该记录并可被查询，而不要求新增一套专用存储结构。 | TEST-BE-002 / TEST-BE-004 / TEST-BE-006 | RUN_OUTPUT | `tests/test_memory_service_v27.py` + `tests/test_system_catalog_profile_init_v27.py` + `tests/test_task_feature_update_actor.py` | ✅ PASS | 三类 Memory 写入与未来类型扩展 |
| GWT-REQ-008-01 | REQ-008 | Given 需求文本中出现某系统的已确认别名，且该别名已存在于系统清单或 `identification_decision` Memory 的稳定映射中，When 执行系统识别，Then 最终结果直接返回 `matched` 且指向该系统。 | TEST-BE-006 | RUN_OUTPUT | `tests/test_system_identification_memory_v27.py` | ✅ PASS | matched / ambiguous / unknown + `final_verdict` |
| GWT-REQ-008-02 | REQ-008 | Given 需求文本同时命中两个高相似候选系统且证据不足以唯一收敛，When 执行系统识别，Then 最终结果返回 `ambiguous`，并列出候选系统与澄清问题，而不是静默选择其一。 | TEST-BE-006 | RUN_OUTPUT | `tests/test_system_identification_memory_v27.py` | ✅ PASS | matched / ambiguous / unknown + `final_verdict` |
| GWT-REQ-008-03 | REQ-008 | Given 需求文本无法可靠映射到任何标准系统，When 执行系统识别，Then 最终结果返回 `unknown`，且不进入“已选中系统”的后续链路。 | TEST-BE-006 | RUN_OUTPUT | `tests/test_system_identification_memory_v27.py` | ✅ PASS | matched / ambiguous / unknown + `final_verdict` |
| GWT-REQ-008-04 | REQ-008 | Given 任一系统识别响应，When 检查返回载荷，Then 其中必须存在 `final_verdict` 字段，且值只能是 `matched`、`ambiguous`、`unknown` 三者之一。 | TEST-BE-006 | RUN_OUTPUT | `tests/test_system_identification_memory_v27.py` | ✅ PASS | matched / ambiguous / unknown + `final_verdict` |
| GWT-REQ-009-01 | REQ-009 | Given 服务治理导入产生一条结构化 D3 集成记录，且目标字段不存在 `manual` 冲突，When Policy Gate 判定，Then 该记录直接 `auto_apply` 到当前画像草稿的 D3。 | TEST-BE-003 / TEST-BE-004 / TEST-BE-005 | RUN_OUTPUT | `tests/test_service_governance_import_v27.py` + `tests/test_system_catalog_profile_init_v27.py` + `tests/test_code_scan_skill_v27.py` | ✅ PASS | auto_apply / skip / suggestion_only / manual 优先 |
| GWT-REQ-009-02 | REQ-009 | Given 系统清单导入提供一条明确字段映射的标准信息，且目标系统画像满足空画像条件，When Policy Gate 判定，Then 该字段直接 `auto_apply` 到正式 `profile_data`，并记录 `system_catalog` 来源和对应 `profile_update` Memory。 | TEST-BE-003 / TEST-BE-004 / TEST-BE-005 | RUN_OUTPUT | `tests/test_service_governance_import_v27.py` + `tests/test_system_catalog_profile_init_v27.py` + `tests/test_code_scan_skill_v27.py` | ✅ PASS | auto_apply / skip / suggestion_only / manual 优先 |
| GWT-REQ-009-03 | REQ-009 | Given 系统清单导入命中某个已存在非空 canonical 字段的系统画像，When Policy Gate 判定，Then 结果为 `reject/skip`，且系统既不覆盖 `profile_data`，也不生成需 PM 接受的 `ai_suggestions`。 | TEST-BE-003 / TEST-BE-004 / TEST-BE-005 | RUN_OUTPUT | `tests/test_service_governance_import_v27.py` + `tests/test_system_catalog_profile_init_v27.py` + `tests/test_code_scan_skill_v27.py` | ✅ PASS | auto_apply / skip / suggestion_only / manual 优先 |
| GWT-REQ-009-04 | REQ-009 | Given `requirements_skill`、`design_skill`、`tech_solution_skill` 或 `code_scan_skill` 任一输出成功，When 用户重新读取画像详情，Then 结果进入建议区或等效 `ai_suggestions`，且正式 `profile_data` 未被自动覆盖。 | TEST-BE-003 / TEST-BE-004 / TEST-BE-005 | RUN_OUTPUT | `tests/test_service_governance_import_v27.py` + `tests/test_system_catalog_profile_init_v27.py` + `tests/test_code_scan_skill_v27.py` | ✅ PASS | auto_apply / skip / suggestion_only / manual 优先 |
| GWT-REQ-009-05 | REQ-009 | Given 某字段已被 PM 标记为 `manual`，When 任一自动导入链路命中该字段，Then 系统不覆盖该字段，并在结果中标记“manual 优先导致跳过或转建议”。 | TEST-BE-003 / TEST-BE-004 / TEST-BE-005 | RUN_OUTPUT | `tests/test_service_governance_import_v27.py` + `tests/test_system_catalog_profile_init_v27.py` + `tests/test_code_scan_skill_v27.py` | ✅ PASS | auto_apply / skip / suggestion_only / manual 优先 |
| GWT-REQ-010-01 | REQ-010 | Given 某系统已存在与功能点命名和模块归属相关的 `function_point_adjustment` Memory，When 对同一系统执行新一轮功能点拆解，Then 拆解草稿会读取这些 Memory 并在输出中体现同一命名或模块模式，而不是完全忽略历史调整。 | TEST-BE-006 | RUN_OUTPUT | `tests/test_feature_breakdown_memory_v27.py` + `tests/test_task_modification_compat.py` | ✅ PASS | 低风险复用、Memory 回读与兼容修改记录 |
| GWT-REQ-010-02 | REQ-010 | Given 某类低风险局部归一化模式已被确认可复用，When 新一轮拆解命中同类模式，Then 系统可将该调整自动应用到当前拆解草稿，并写入新的 `function_point_adjustment` Memory。 | TEST-BE-006 | RUN_OUTPUT | `tests/test_feature_breakdown_memory_v27.py` + `tests/test_task_modification_compat.py` | ✅ PASS | 低风险复用、Memory 回读与兼容修改记录 |
| GWT-REQ-010-03 | REQ-010 | Given 拆解结果涉及跨系统归属或跨模块结构重排，When 系统完成策略判定，Then 结果仅以建议或待复核草稿形式返回，而不是直接自动定稿。 | TEST-BE-006 | RUN_OUTPUT | `tests/test_feature_breakdown_memory_v27.py` + `tests/test_task_modification_compat.py` | ✅ PASS | 低风险复用、Memory 回读与兼容修改记录 |
| GWT-REQ-011-01 | REQ-011 | Given PM 导入文档后 Skill 执行失败，When 查询导入历史和提取状态，Then 导入历史或任务状态显示失败终态，并包含失败原因。 | TEST-BE-001 / TEST-BE-002 / TEST-BE-005 / TEST-BE-006 | RUN_OUTPUT | `tests/test_system_profile_import_api.py` + `tests/test_memory_service_v27.py` + `tests/test_code_scan_skill_v27.py` | ✅ PASS | 失败态、partial_success 与无半成品写入 |
| GWT-REQ-011-02 | REQ-011 | Given 系统清单 preview 返回行级错误，When 用户未执行 confirm，Then 系统画像不发生任何更新。 | TEST-BE-001 / TEST-BE-002 / TEST-BE-005 / TEST-BE-006 | RUN_OUTPUT | `tests/test_system_profile_import_api.py` + `tests/test_memory_service_v27.py` + `tests/test_code_scan_skill_v27.py` | ✅ PASS | 失败态、partial_success 与无半成品写入 |
| GWT-REQ-011-03 | REQ-011 | Given 画像更新业务动作已成功但 Memory 写入失败，When 接口返回结果，Then 返回状态为 `partial_success` 或等效补偿态，并包含 Memory 失败原因，而不是返回“success”。 | TEST-BE-001 / TEST-BE-002 / TEST-BE-005 / TEST-BE-006 | RUN_OUTPUT | `tests/test_system_profile_import_api.py` + `tests/test_memory_service_v27.py` + `tests/test_code_scan_skill_v27.py` | ✅ PASS | 失败态、partial_success 与无半成品写入 |
| GWT-REQ-011-04 | REQ-011 | Given Runtime 在中途失败，When 用户重新读取画像详情或执行结果，Then 不会看到未标记来源的半成品数据被写入正式画像字段。 | TEST-BE-001 / TEST-BE-002 / TEST-BE-005 / TEST-BE-006 | RUN_OUTPUT | `tests/test_system_profile_import_api.py` + `tests/test_memory_service_v27.py` + `tests/test_code_scan_skill_v27.py` | ✅ PASS | 失败态、partial_success 与无半成品写入 |
| GWT-REQ-012-01 | REQ-012 | Given 环境中存在旧 schema 画像记录与历史评估报告相关存量数据，When 执行 v2.7 清理，Then 旧 schema 数据和历史评估报告数据都被移除。 | TEST-DEPLOY-001 | RUN_OUTPUT | `tests/test_cleanup_v27.py` | ✅ PASS | 旧 schema / history_report 清理与失败回报 |
| GWT-REQ-012-02 | REQ-012 | Given 清理完成，When 执行核验查询，Then 旧 schema 画像数据计数为 0，且历史评估报告类型存量数据计数为 0。 | TEST-DEPLOY-001 | RUN_OUTPUT | `tests/test_cleanup_v27.py` | ✅ PASS | 旧 schema / history_report 清理与失败回报 |
| GWT-REQ-012-03 | REQ-012 | Given 清理过程中发生异常，When 清理任务结束，Then 系统返回失败结果并附带失败原因，不会误报“已清理完成”。 | TEST-DEPLOY-001 | RUN_OUTPUT | `tests/test_cleanup_v27.py` | ✅ PASS | 旧 schema / history_report 清理与失败回报 |
| GWT-REQ-101-01 | REQ-101 | Given v2.7 目标画像结构已落地，When 按 D1-D5 域字段键计数，Then 总字段数不少于 20，且 5 个域均包含 `extensions` 字段。 | TEST-BE-002 / TEST-FE-002 | RUN_OUTPUT | `tests/test_profile_schema_v27.py` + `frontend/src/__tests__/systemProfileBoardPage.v27.test.js` | ✅ PASS | 字段数与前后端 canonical 键对齐 |
| GWT-REQ-101-02 | REQ-101 | Given 前端画像面板和后端空画像结构分别输出字段定义，When 对比两侧字段键，Then 两侧使用同一套 canonical 字段键，不存在仅一侧保留的旧字段名。 | TEST-BE-002 / TEST-FE-002 | RUN_OUTPUT | `tests/test_profile_schema_v27.py` + `frontend/src/__tests__/systemProfileBoardPage.v27.test.js` | ✅ PASS | 字段数与前后端 canonical 键对齐 |
| GWT-REQ-102-01 | REQ-102 | Given 测试样本中有 100 条系统名与系统清单标准名称一致的治理记录，When admin 完成服务治理导入，Then 至少 95 条记录成功匹配并完成画像更新。 | TEST-BE-003 | RUN_OUTPUT | `tests/test_service_governance_import_v27.py` | ✅ PASS | 治理导入匹配成功率与分母口径 |
| GWT-REQ-102-02 | REQ-102 | Given 导入结果同时包含“名称一致可匹配记录”和“名称不一致未匹配记录”，When 统计成功率，Then 仅以名称一致记录作为分母计算，不把未纳入口径的记录混入成功率统计。 | TEST-BE-003 | RUN_OUTPUT | `tests/test_service_governance_import_v27.py` | ✅ PASS | 治理导入匹配成功率与分母口径 |
| GWT-REQ-103-01 | REQ-103 | Given v2.7 Runtime 已加载，When 执行 Skill 功能测试集，Then 6 个内置 Skill 都存在且测试通过。 | TEST-BE-005 | RUN_OUTPUT | `tests/test_skill_runtime_service.py` + `tests/test_code_scan_skill_v27.py` | ✅ PASS | 6 个 Skill 注册与核心场景路由 |
| GWT-REQ-103-02 | REQ-103 | Given 执行核心场景路由矩阵测试，When 检查 `scene_id -> skill_chain` 结果，Then `pm_document_ingest`、`admin_service_governance_import`、`admin_system_catalog_import`、`system_identification`、`feature_breakdown` 五类场景都落到预期链路，不出现错路由或空路由。 | TEST-BE-005 | RUN_OUTPUT | `tests/test_skill_runtime_service.py` + `tests/test_code_scan_skill_v27.py` | ✅ PASS | 6 个 Skill 注册与核心场景路由 |
| GWT-REQ-104-01 | REQ-104 | Given 测试样本中存在画像更新、系统识别结论落库、功能点修改三类成功动作，When 统计 Memory 记录，Then 每个成功动作都能找到对应 Memory 记录，且覆盖率为 100%。 | TEST-BE-004 / TEST-BE-006 | RUN_OUTPUT | `tests/test_system_catalog_profile_init_v27.py` + `tests/test_system_identification_memory_v27.py` + `tests/test_task_feature_update_actor.py` | ✅ PASS | 画像更新/识别/功能点修改三类 Memory 覆盖 |
| GWT-REQ-104-02 | REQ-104 | Given 按 `system_id + memory_type` 查询系统资产，When 查看结果，Then 能分别查到 `profile_update`、`identification_decision`、`function_point_adjustment` 三类 Memory 记录或明确的“当前无记录”结果。 | TEST-BE-004 / TEST-BE-006 | RUN_OUTPUT | `tests/test_system_catalog_profile_init_v27.py` + `tests/test_system_identification_memory_v27.py` + `tests/test_task_feature_update_actor.py` | ✅ PASS | 画像更新/识别/功能点修改三类 Memory 覆盖 |
| GWT-REQ-105-01 | REQ-105 | Given v2.7 清理动作已执行，When 查询画像数据存储，Then 不存在旧 schema 字段记录或旧 schema 结构残留。 | TEST-DEPLOY-001 | RUN_OUTPUT | `tests/test_cleanup_v27.py` | ✅ PASS | 清理后旧 schema 与历史评估数据计数归零 |
| GWT-REQ-105-02 | REQ-105 | Given v2.7 清理动作已执行，When 查询历史评估报告相关导入/知识数据，Then 相关存量数据计数为 0。 | TEST-DEPLOY-001 | RUN_OUTPUT | `tests/test_cleanup_v27.py` | ✅ PASS | 清理后旧 schema 与历史评估数据计数归零 |
| GWT-REQ-C001-01 | REQ-C001 | Given manager 访问 PM 导入页，When 页面加载完成，Then 页面不出现“历史评估报告”“服务治理文档”卡片、上传入口或模板下载按钮。 | TEST-FE-001 / TEST-BE-001 | RUN_OUTPUT | `frontend/src/__tests__/systemProfileImportPage.render.test.js` + `tests/test_system_profile_import_api.py` | ✅ PASS | 前端不展示旧入口，服务端拒绝旧类型/模板 |
| GWT-REQ-C001-02 | REQ-C001 | Given 客户端仍尝试以 `history_report`、`esb` 或治理类旧类型调用 PM 文档导入接口或模板下载接口，When 服务端处理请求，Then 系统返回明确失败结果，且不返回成功结果或模板文件。 | TEST-FE-001 / TEST-BE-001 | RUN_OUTPUT | `frontend/src/__tests__/systemProfileImportPage.render.test.js` + `tests/test_system_profile_import_api.py` | ✅ PASS | 前端不展示旧入口，服务端拒绝旧类型/模板 |
| GWT-REQ-C002-01 | REQ-C002 | Given v2.7 画像结构已启用，When 读取画像详情或空画像结构，Then 返回结果中不包含 `system_description`、`boundaries`、`module_structure`、`integration_points`、`architecture_positioning`、`performance_profile`、`key_constraints` 等旧 schema 字段键。 | TEST-BE-002 / TEST-DEPLOY-001 | RUN_OUTPUT | `tests/test_profile_schema_v27.py` + `tests/test_cleanup_v27.py` | ✅ PASS | 运行态无旧 schema 键，清理后残留为 0 |
| GWT-REQ-C002-02 | REQ-C002 | Given 执行完 v2.7 清理动作，When 查询旧 schema 画像数据和历史评估报告存量数据，Then 两类残留计数都为 0。 | TEST-BE-002 / TEST-DEPLOY-001 | RUN_OUTPUT | `tests/test_profile_schema_v27.py` + `tests/test_cleanup_v27.py` | ✅ PASS | 运行态无旧 schema 键，清理后残留为 0 |
| GWT-REQ-C003-01 | REQ-C003 | Given 某个画像字段已由 PM 手动保存并标记为 `manual`，When 自动导入链路对该字段产生不同值，Then 系统不覆盖该字段，且读取结果仍为人工值。 | TEST-BE-003 / TEST-BE-004 | RUN_OUTPUT | `tests/test_service_governance_import_v27.py` + `tests/test_system_catalog_profile_init_v27.py` | ✅ PASS | manual 字段保持人工值，不被自动链路覆盖 |
| GWT-REQ-C003-02 | REQ-C003 | Given 自动导入命中 `manual` 冲突字段，When 导入完成，Then 结果中明确标记该字段因 `manual` 优先而被跳过或转为建议，而不是无提示覆盖。 | TEST-BE-003 / TEST-BE-004 | RUN_OUTPUT | `tests/test_service_governance_import_v27.py` + `tests/test_system_catalog_profile_init_v27.py` | ✅ PASS | manual 字段保持人工值，不被自动链路覆盖 |
| GWT-REQ-C004-01 | REQ-C004 | Given 注册表新增一个 `enabled=false` 的未来 Skill 定义（如 `architecture_review_skill`），When Runtime 加载注册表，Then 系统识别该定义为合法配置，而不是因硬编码枚举而报错。 | TEST-BE-002 / TEST-BE-005 | RUN_OUTPUT | `tests/test_memory_service_v27.py` + `tests/test_skill_runtime_service.py` | ✅ PASS | disabled future skill 与 future memory_type 均可扩展 |
| GWT-REQ-C004-02 | REQ-C004 | Given Memory 模型写入 `memory_type=review_resolution` 的未来类型记录，When 校验公共元数据，Then 系统接受该记录并可被查询，而不是要求新增一套专用结构。 | TEST-BE-002 / TEST-BE-005 | RUN_OUTPUT | `tests/test_memory_service_v27.py` + `tests/test_skill_runtime_service.py` | ✅ PASS | disabled future skill 与 future memory_type 均可扩展 |
| GWT-REQ-C005-01 | REQ-C005 | Given 任一系统识别结果返回载荷，When 检查结果字段，Then 必须包含 `final_verdict`，且不得只返回候选列表、相似度或澄清问题而缺少直接判定。 | TEST-BE-006 | RUN_OUTPUT | `tests/test_system_identification_memory_v27.py` | ✅ PASS | 识别响应强制 `final_verdict` |
| GWT-REQ-C006-01 | REQ-C006 | Given manager/admin/expert 按现有主链路执行“创建任务 -> 提交给管理员 -> 分配专家 -> 专家评估 -> 查看报告”，When v2.7 变更生效后执行该链路，Then 该链路仍可按原有角色权限和入口完成，不因画像、Runtime 或 Memory 改造被阻断。 | TEST-GATE-001 / TEST-API-001 | RUN_OUTPUT | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q --tb=short` + `scripts/api_regression.sh` | ✅ PASS | 主链路回归与 API 基线未被 v2.7 阻断 |
| GWT-REQ-C006-02 | REQ-C006 | Given 系统画像导入、服务治理导入、系统清单联动或 Memory 写入发生失败，When 用户继续访问评估主链路相关页面和接口，Then 任务评估与报告链路保持可用，且现有报告查询/导出语义不被改变。 | TEST-GATE-001 / TEST-API-001 | RUN_OUTPUT | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q --tb=short` + `scripts/api_regression.sh` | ✅ PASS | 主链路回归与 API 基线未被 v2.7 阻断 |
| GWT-REQ-C007-01 | REQ-C007 | Given 对比 v2.6 与 v2.7 的 `pyproject.toml`、`requirements.txt`、`backend/requirements.txt` 和 `frontend/package.json` 运行时依赖清单，When 检查依赖差异，Then 不新增为实现 v2.7 而引入的外部运行时依赖。 | TEST-DEPS-001 | RUN_OUTPUT | `git diff --unified=0 v2.6 -- pyproject.toml requirements.txt backend/requirements.txt frontend/package.json` | ✅ PASS | 运行时依赖清单无新增 |
| GWT-REQ-C008-01 | REQ-C008 | Given 系统清单已存在，且某命中系统的 `profile_data` 下 D1-D5 canonical 字段中任一字段非空，When admin 执行 confirm 覆盖导入，Then 该系统的 `profile_data` 保持不变，不写入 `ai_suggestions`，并在结果中标记 `profile_not_blank` 或等效跳过原因。 | TEST-BE-004 | RUN_OUTPUT | `tests/test_system_catalog_profile_init_v27.py` | ✅ PASS | 非空画像跳过，空画像仅看 D1-D5 canonical |
| GWT-REQ-C008-02 | REQ-C008 | Given 某命中系统的 `profile_data` 下 D1-D5 canonical 字段全部为空值/空数组/空对象，但 `field_sources`、`ai_suggestions` 或 Memory 已存在元数据，When admin 执行系统清单 confirm，Then 系统仍将该画像判定为空画像，并允许按 REQ-004 / REQ-009 执行初始化写入。 | TEST-BE-004 | RUN_OUTPUT | `tests/test_system_catalog_profile_init_v27.py` | ✅ PASS | 非空画像跳过，空画像仅看 D1-D5 canonical |
<!-- TEST-COVERAGE-MATRIX-END -->

## CR 验证证据（🔴 MUST，Deployment 门禁依赖）
| CR-ID | 验收标准 | 证据类型 | 证据链接/说明 | 验证结论 |
|---|---|---|---|---|
| `CR-20260314-001` | 前端不直接渲染内部执行元数据、对象结构、原始 ID 与 reason code；既有交互边界保持不变 | RUN_OUTPUT | `frontend/src/__tests__/systemProfileImportPage.render.test.js`、`frontend/src/__tests__/navigationAndPageTitleRegression.test.js`、`frontend/src/__tests__/systemListConfigPage.v27.test.js`、`tests/test_system_catalog_profile_init_v27.py` | ✅ 通过 |

## 回滚验证
| CR-ID | 回滚条件/步骤 | 证据类型 | 证据链接/说明 | 回滚可执行性 |
|---|---|---|---|---|
| `CR-20260314-001` | 回退相关前端页面与 `system_catalog_profile_initializer/system_list_routes` 的展示适配；版本级仍遵循 `docs/v2.7/deployment.md` L1/L2 | RUN_OUTPUT | `tests/test_cleanup_v27.py` + `tests/test_deploy_backend_internal_script.py` + `tests/test_deploy_frontend_internal_script.py` | ✅ 可执行 |

## 缺陷与处理
| BUG-ID | 问题描述 | 严重程度 | 状态 | 关联REQ | 修复版本 |
|---|---|---|---|---|---|
| BUG-20260314-001 | full pytest 下 `DocumentParser` 单例被测试污染，导致治理导入和 v2.7 画像导入在全量回归中失败 | 高 | 已修复 | REQ-001, REQ-003, REQ-006, REQ-011 | v2.7 |
| BUG-20260314-002 | `SystemProfileImportPage` 缺失 `renderDocTypeCard` helper，布局一致性测试失败；`SystemProfileService` 缺失 `_normalize_module_structure` 兼容入口 | 中 | 已修复 | REQ-001, REQ-002 | v2.7 |
| BUG-20260314-003 | `ServiceGovernanceProfileUpdater` 未兼容最新 `data/esb-template.xlsx` 的 `服务方系统名称` 表头，导致按最新治理模板导入时 `matched_count=0` | 中 | 已修复 | REQ-003, REQ-006 | v2.7 |
| BUG-20260314-004 | PM 导入页、信息展示页与左侧布局把后台执行信息/对象结构直接带到前端，且状态卡片/滚动交互不符合已确认页面边界 | 中 | 已修复 | REQ-001, REQ-002, REQ-007, REQ-011 | v2.7 |
| BUG-20260314-005 | 服务治理与系统清单结果区直接渲染 `updated_system_ids`、`profile_not_blank` 等后台字段，用户无法直接理解结果 | 中 | 已修复 | REQ-003, REQ-004, REQ-C008 | v2.7 |

## 测试结论
- 自动化覆盖：72/72 个 GWT 已具备自动化或命令级 PASS 证据。
- 项目级门禁：full pytest（`237 passed, 1 warning`）、前端页面 smoke、frontend build、backend compileall、依赖 diff、API regression 全部通过。
- 主文档与契约：`.env.backend.internal`、四个 v2.7 开关、`profile/execution-status` / alias 与 Memory 契约已同步到主文档。
- 模板口径补充：服务治理最新模板已固定为 `data/esb-template.xlsx`，并保留 `data/接口申请模板.xlsx` 作为兼容输入；两条链路均已有自动化覆盖。
- 回溯 CR：`CR-20260314-001` 已补记入 Testing 文档链，覆盖前端可读性/交互回归修复及其自动化证据。
- 人工 E2E：`REQ-003`、`REQ-004` 已于 2026-03-14 23:59 由 User 在可验收环境完成验证并反馈“正常”。
- 说明：`REQ-001`、`REQ-002` 的人类验证清单属于建议项，当前未补充独立人工记录，但不构成 Testing 阶段阻断。
- 整体结论：自动化证据、人工 E2E 与部署留痕已闭环，Testing 阶段通过，可进入并完成 Deployment 收口。

## 测试确认记录
- 确认人：User
- 确认日期：2026-03-14 23:59
- 说明：User 已在可验收环境完成 `REQ-003/REQ-004` 人工 E2E，并反馈“正常”。

## 开放问题
- 无阻断项；`REQ-001/REQ-002` 的人工抽检仍可在后续日常回归中按需补充。

## 变更记录
| 版本 | 日期 | 说明 | 作者 |
|---|---|---|---|
| v0.1 | 2026-03-14 | 初始化 v2.7 测试报告，固化自动化回归、契约/依赖/部署 smoke 证据，并显式标记 `REQ-003/REQ-004` 人工 E2E 验证待补 | Codex |
| v0.2 | 2026-03-14 | 补记服务治理最新模板口径为 `data/esb-template.xlsx`，并记录其表头兼容缺陷修复 | Codex |
| v0.3 | 2026-03-14 | 同步最新项目级回归结果（`237 passed, 1 warning`），并将 REQ-003 人工验证步骤固定到最新治理模板口径 | Codex |
| v0.4 | 2026-03-14 | 回填 `CR-20260314-001`，同步前端可读性/交互回归、系统清单结果用户可读化与相关缺陷记录 | Codex |
| v0.5 | 2026-03-14 | 回填 `REQ-003/REQ-004` 人工 E2E 验证结果，关闭 Testing 阶段阻断项并同步通过结论 | Codex |
