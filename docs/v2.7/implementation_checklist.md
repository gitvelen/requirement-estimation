# v2.7 实现检查清单

| 项 | 值 |
|---|---|
| 版本号 | v2.7 |
| 当前阶段 | Deployment（Implementation / Testing 已收口） |
| 日期 | 2026-03-14 |
| 当前执行批次 | M3（T008-T009） |
| 首个强制展示点 | T006（M1🏁）或更早跑通的后端核心流程里程碑 |
| 关联计划 | `docs/v2.7/plan.md` |

## 实现前检查
- [x] 已阅读相关现有代码/文档（`requirements.md` / `design.md` / `plan.md` / `status.md` / `.aicoding/phases/05-implementation.md`）
- [x] 已对齐范围与“不做什么”
- [x] 已明确验收标准（以 T001-T006 对应 REQ/API/TEST 与命令级验证为准）
- [x] 已明确影响面：先聚焦 schema / Runtime / Memory 基座、PM 文档导入 Runtime、服务治理导入、系统清单联动、Memory 驱动识别/拆解、code scan Runtime 接入六条后端主线
- [x] 如涉及线上行为变化：已明确四个开关与回滚思路（`ENABLE_V27_PROFILE_SCHEMA` / `ENABLE_V27_RUNTIME` / `ENABLE_SERVICE_GOVERNANCE_IMPORT` / `ENABLE_SYSTEM_CATALOG_PROFILE_INIT`）
- [x] 开发环境就绪：依赖安装、测试数据与必要配置已实际验证可运行
- [x] 基线测试已记录：进入 TDD 前先确认当前相关测试基线

## 当前批次任务
- [x] T001：v2.7 canonical schema、Memory/Execution 存储与开关基座
- [x] T002：Skill Runtime、Policy Gate 与 PM 文档导入链路
- [x] T003：服务治理导入改造为 admin 全局画像联动
- [x] T004：单一系统清单解析、空画像初始化与子系统模型退场
- [x] T005：Memory 驱动的系统识别与功能点拆解联动
- [x] T006：`code_scan_skill` 适配层与 Runtime 接入
- [x] T007：PM/Admin 页面、路由与交互收敛到 v2.7 口径
- [x] T008：v2.7 清理脚本、开关发布顺序与回滚 Runbook
- [x] T009：全量回归、证据闭环与主文档同步（自动化回归、回溯 CR `CR-20260314-001`、主文档同步与 `REQ-003/REQ-004` 人工 E2E 回填均已完成；服务治理最新模板口径已收敛到 `data/esb-template.xlsx`）
- [x] `backend/service/system_profile_service.py` 已移除 legacy schema 字面量依赖；发布画像与最小画像判定改为直接基于 canonical `profile_data`

## 实现中检查
- [x] 按 TDD 执行：核心行为均以失败测试或回归重现先行，含 Runtime、治理导入、系统清单初始化、前端 smoke 与全量回归修复
- [x] 不跨任务隐式扩 scope；T001~T009 之外的改动仅限兼容性修复、测试隔离与文档同步
- [x] 未引入非必要依赖；依赖变更持续对照 `REQ-C007`
- [x] 关键路径校验：鉴权、输入校验、错误码、`failed/partial_success`、`manual` 冲突处理口径一致
- [x] 安全检查：`repo_path`、文件上传、admin 权限与系统名匹配逻辑不降级
- [x] 数据变更可回滚：旧 schema 不再新写入，但保留回滚开关与备份恢复路径
- [x] 里程碑纪律：T006（🏁）与 T007（M2🏁）完成后均已先向 User 展示阶段成果再继续

## 实现后检查
- [x] 当前批次代码可正常运行
- [x] 当前批次对应测试通过并记录命令输出
- [x] 对照验收标准自测并留证据（命令、日志、必要时截图）
- [x] 文档同步更新：`docs/v2.7/*` 与主文档已同步到 v2.7 口径，未改验收标准
- [x] 敏感信息检查：未新增 secret、生产数据、个人信息

## 契约与集成验证（进入 Testing 前）

### API 契约一致性
- [x] 前端 API 调用、后端路由与 `design.md` 5.4 契约已逐项对齐
- [x] 所有新增 API 已在 `design.md` 中定义
- [x] 当前仓库未发现 `scripts/validate_api_contracts.sh`；已改用 `rg` + 路由对照 + `scripts/api_regression.sh` 作为等价可复现校验

### 集成测试准备
- [x] T001-T006 对应测试已具备独立执行命令并完成本轮复跑
- [x] 测试脚本覆盖 API 调用、数据副作用与存储校验
- [x] 测试脚本已验证通过并记录日志

### 人类验证准备（关键流程）
- [x] 已准备后端核心流程里程碑展示材料（关键输入 -> 输出）
- [x] 已准备 T006（🏁）展示项：6 个 Skill 注册定义、Scene 路由、服务治理导入与 execution 跟踪结果

## M1（T006🏁）验证留痕

### T001
- [x] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_profile_schema_v27.py tests/test_memory_service_v27.py` → `6 passed, 1 warning`
- [x] `python - <<'PY' ... backend/service/system_profile_service.py legacy schema gate ... PY` → 退出码 0，无违规命中

### T002
- [x] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_skill_runtime_service.py tests/test_system_profile_import_api.py tests/test_system_profile_routes_helpers.py` → `18 passed, 1 warning`
- [x] `bash -lc 'if rg -n "history_report|esb_document|knowledge_doc" backend/api/system_profile_routes.py; then exit 1; fi'` → 退出码 0

### T003
- [x] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_esb_import_api.py tests/test_service_governance_import_v27.py tests/test_esb_service.py` → `17 passed, 1 warning`

### T004
- [x] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_system_list_import.py tests/test_system_catalog_profile_init_v27.py tests/test_system_list_unified_source.py tests/test_system_list_cache_reload.py` → `10 passed, 1 warning`
- [x] `bash -lc 'if rg -n "子系统清单|子系统映射|mappings_total|mappings_error|subsystem_list.csv" backend tests | rg -v "历史|review|docs/v2.7"; then exit 1; fi'` → 退出码 0

### T005
- [x] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_system_identification_memory_v27.py tests/test_feature_breakdown_memory_v27.py tests/test_task_feature_update_actor.py tests/test_task_modification_compat.py` → `10 passed, 1 warning`

### T006
- [x] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_code_scan_skill_v27.py tests/test_code_scan_api.py` → `14 passed, 1 warning`
- [x] `git diff --unified=0 v2.6 -- pyproject.toml requirements.txt backend/requirements.txt frontend/package.json` → 空 diff，未新增运行时依赖
- [x] `python -m compileall -q backend/service/system_profile_service.py backend/service/system_profile_legacy_helper.py` → 退出码 0

### 里程碑展示样例
- [x] Runtime 注册快照：6 个内置 Skill 全部启用；`pm_document_ingest(requirements)` → `requirements_skill`；`admin_service_governance_import` → `service_governance_skill`；`admin_system_catalog_import` → `system_catalog_skill`；`code_scan_ingest` → `code_scan_skill`
- [x] `code_scan_skill.supported_inputs` = `['repo_path', 'repo_archive']`
- [x] 服务治理导入隔离样例：`status=completed`、`matched_count=3`、`unmatched_count=1`、`updated_systems=['统一支付平台', '信贷核心']`
- [x] 服务治理导入隔离样例未匹配项：`{'system_name': '未知系统', 'service_name': '孤立服务', 'reason': 'system_not_found'}`
- [x] 服务治理导入后 `统一支付平台` D3：`provided_services=2`、`consumed_services=1`
- [x] execution 跟踪：`scene_id=admin_service_governance_import`、`skill_chain=['service_governance_skill']`

## M2（T007🏁）验证留痕

### T007
- [x] `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileImportPage.render.test.js src/__tests__/systemProfileBoardPage.v27.test.js src/__tests__/serviceGovernancePage.render.test.js src/__tests__/systemListConfigPage.v27.test.js src/__tests__/navigationAndPageTitleRegression.test.js` → `5 passed, 13 passed`
- [x] `cd frontend && npm run build` → `Compiled successfully.`

### 里程碑展示样例
- [x] PM 导入页仅保留 `需求文档 / 设计文档 / 技术方案` 三张导入卡片，执行态读取 `profile/execution-status`，并保留代码扫描入口
- [x] 系统画像面板按 `profile_data.<domain>.canonical` 展示 D1-D5，保持既有系统TAB/域TAB交互，并将 `extensions`、Memory、来源/操作人收敛为后台留存
- [x] admin 侧已新增 `/admin/service-governance` 路由与菜单入口，导入结果展示匹配/未匹配数量、已更新系统名称与未匹配项
- [x] 系统清单页仅保留单一导入视图，confirm 后结果区展示已更新系统名称、预检错误、跳过项与用户可读原因
- [x] 导航回归：管理员菜单包含“服务治理”且不再出现“子系统”；项目经理画像菜单仅保留“知识导入 / 信息展示”

## M3（T008-T009）验证留痕

### T008
- [x] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_cleanup_v27.py tests/test_deploy_backend_internal_script.py tests/test_deploy_frontend_internal_script.py` → `7 passed`
- [x] `docs/v2.7/deployment.md` 已固化 `.env.backend.internal`、四开关启用顺序、首次清理、月度系统清单“仅空画像初始化”规则与回滚路径
- [x] `docs/部署记录.md` / `docs/技术方案设计.md` / `docs/接口文档.md` / `docs/系统功能说明书.md` / `docs/用户手册.md` 已同步 v2.7 主文档口径

### T009
- [x] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q --tb=short` → `237 passed, 1 warning`
- [x] `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileImportPage.render.test.js src/__tests__/systemProfileBoardPage.v27.test.js src/__tests__/serviceGovernancePage.render.test.js src/__tests__/systemListConfigPage.v27.test.js src/__tests__/navigationAndPageTitleRegression.test.js` → `5 suites / 13 tests passed`
- [x] `cd frontend && npm run build` → `Compiled successfully.`
- [x] `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemListConfigPage.v27.test.js src/__tests__/systemProfileImportPage.render.test.js src/__tests__/navigationAndPageTitleRegression.test.js` → `3 suites / 12 tests passed`（含既有 React Router / AntD warning 输出）
- [x] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_system_catalog_profile_init_v27.py::test_catalog_confirm_initializes_blank_profiles_and_writes_memory` → `1 passed, 1 warning`
- [x] `cd frontend && npx eslint src/pages/SystemListConfigPage.js src/__tests__/systemListConfigPage.v27.test.js src/pages/SystemProfileImportPage.js src/components/MainLayout.js src/__tests__/systemProfileImportPage.render.test.js src/__tests__/navigationAndPageTitleRegression.test.js` → 无输出，退出码 0
- [x] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_service_governance_import_v27.py tests/test_esb_import_api.py tests/test_esb_service.py tests/test_system_list_import.py tests/test_system_catalog_profile_init_v27.py --tb=short` → `25 passed, 1 warning`
- [x] `git diff --unified=0 v2.6 -- pyproject.toml requirements.txt backend/requirements.txt frontend/package.json` → 空 diff，未新增运行时依赖
- [x] `BASE_URL=http://127.0.0.1:18080 bash scripts/api_regression.sh` → `[PASS] health`、`[PASS] requirement/tasks`、`[PASS] api regression finished`；知识库未配置接口返回 `401` 已记为可选告警
- [x] 文档/契约对照：`rg -n "\\.env\\.backend\\.internal|ENABLE_V27_PROFILE_SCHEMA|ENABLE_V27_RUNTIME|ENABLE_SERVICE_GOVERNANCE_IMPORT|ENABLE_SYSTEM_CATALOG_PROFILE_INIT|profile/execution-status|profile/extraction-status" docs/v2.7/deployment.md docs/技术方案设计.md docs/接口文档.md docs/部署记录.md docs/v2.7/status.md` → 命中 v2.7 canonical 口径，无旧配置源漂移
- [x] User 人工 E2E：`REQ-003/REQ-004` 已于 2026-03-14 23:59 在可验收环境验证通过，反馈“正常”

## 收口结论
- [x] Implementation 出口文件已具备：`implementation_checklist.md`、`review_implementation.md`
- [x] Testing 入口文件已具备：`test_report.md`、`review_testing.md`
- [x] `REQ-003/REQ-004` 属于 `[E2E Required]`，人工验证记录已在 Testing 阶段补齐；当前已完成 Deployment 收口
