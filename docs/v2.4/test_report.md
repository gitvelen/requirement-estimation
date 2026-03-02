# 需求评估系统 v2.4 测试报告

## 文档元信息
| 项 | 值 |
|---|---|
| 状态 | Approved |
| 日期 | 2026-03-02 |
| 版本 | v0.9 |
| 基线版本（对比口径） | `v2.3` |
| 关联需求 | `docs/v2.4/requirements.md` |
| 关联计划 | `docs/v2.4/plan.md` |
| 关联状态 | `docs/v2.4/status.md` |
| 包含 CR（如有） | `CR-20260301-001, CR-20260302-001, CR-20260302-002, CR-20260302-003` |

## 测试范围与环境
- 覆盖范围：`REQ-001~REQ-012`、`REQ-101~REQ-106`、`REQ-C001~REQ-C007`
- 测试环境：本地虚拟环境（`.venv`）+ 前端 `react-scripts`（`CI=true`）
- 证据口径：`RUN_OUTPUT`（命令+退出码+摘要）

## 执行命令与结果
| CMD-ID | 命令 | 结果摘要 | 结论 |
|---|---|---|---|
| CMD-01 | `.venv/bin/python -m pytest -q tests/test_system_profile_*.py tests/test_report_download_api.py tests/test_evaluation_contract_api.py tests/test_modification_trace_api.py` | `30 passed in 8.28s` | ✅ |
| CMD-02 | `cd frontend && CI=true npm test -- --watch=false --runInBand src/__tests__/uiComponents.test.js src/__tests__/systemProfileBoardPage.v24.test.js src/__tests__/navigationAndPageTitleRegression.test.js src/__tests__/evaluationReportThreePoint.v24.test.js src/__tests__/dashboardMetrics.test.js` | `18 passed` | ✅ |
| CMD-03 | `.venv/bin/pytest -q tests/test_report_download_api.py tests/test_evaluation_contract_api.py` | `6 passed in 14.84s` | ✅ |
| CMD-04 | `.venv/bin/python -m pytest -q tests/test_task_modification_compat.py` | `2 passed in 8.90s` | ✅ |
| CMD-05 | `.venv/bin/python -m pytest -q tests/test_profile_summary_service.py` | `2 passed in 1.74s` | ✅ |
| CMD-06 | `git rev-parse --verify --quiet v2.3^{commit}` | 返回 commit `9db2c93ee30466879e55425e4f5950028b17795b` | ✅ |
| CMD-07 | `test -x deploy-all.sh` | `DEPLOY_SCRIPT_OK` | ✅ |
| CMD-08 | `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileBoardPage.v24.test.js` | `8 passed in 27.672s` | ✅ |
| CMD-09 | `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileImportPage.render.test.js src/__tests__/codeScanPage.render.test.js src/__tests__/evidenceRuleConfigPage.render.test.js` | `3 passed in 22.254s` | ✅ |
| CMD-10 | `cd frontend && npx eslint src/pages/SystemProfileBoardPage.js src/__tests__/systemProfileBoardPage.v24.test.js --max-warnings=0` | 退出码 0（无 warning） | ✅ |
| CMD-11 | `cd frontend && npm run build` | `Compiled successfully.` | ✅ |
| CMD-12 | `printf '2\n' | bash deploy-all.sh && curl -fsS http://127.0.0.1/api/v1/health` | 部署成功；健康检查返回 `{"status":"healthy",...}` | ✅ |
| CMD-13 | `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileBoardPage.v24.test.js` | `11 passed in 43.921s` | ✅ |
| CMD-14 | `cd frontend && npx eslint src/pages/SystemProfileBoardPage.js src/__tests__/systemProfileBoardPage.v24.test.js --max-warnings=0` | 退出码 0（无 warning） | ✅ |
| CMD-15 | `cd frontend && npm run build` | `Compiled successfully.` | ✅ |
| CMD-16 | `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileBoardPage.v24.test.js -t "prefers current system id from system list when profile carries stale system_id"` | `1 passed (11 skipped)` | ✅ |
| CMD-17 | `cd frontend && npx eslint src/pages/SystemProfileBoardPage.js src/__tests__/systemProfileBoardPage.v24.test.js --max-warnings=0` | 退出码 0（无 warning） | ✅ |
| CMD-18 | `printf '2\n' | bash deploy-all.sh` | STAGING 自动部署成功（BuildKit 失败后自动回退经典构建） | ✅ |
| CMD-19 | `curl -fsS http://127.0.0.1/api/v1/health && curl -fsS http://8.153.194.178/api/v1/health` | 本机/公网健康检查均返回 `healthy` | ✅ |
| CMD-20 | `.venv/bin/pytest -q tests/test_system_profile_publish_rules.py -k "profile_events_returns_empty_when_profile_not_created"` | `1 passed` | ✅ |
| CMD-21 | `printf '2\n' | bash deploy-all.sh` | STAGING 再次自动部署成功（后端容错修复上线） | ✅ |
| CMD-22 | `curl -fsS http://127.0.0.1/api/v1/health && curl -fsS http://8.153.194.178/api/v1/health` | 本机/公网健康检查均返回 `healthy` | ✅ |
| CMD-23 | `.venv/bin/pytest -q tests/test_user_service_internal_bootstrap.py` | `2 passed in 0.08s` | ✅ |
| CMD-24 | `bash -n deploy-backend-internal.sh` | 退出码 0（语法检查通过） | ✅ |
| CMD-25 | `python3 scripts/init_internal_users.py --data-dir $(mktemp -d)` | `created=5, updated=0`（生成默认账号） | ✅ |

## 需求覆盖矩阵（REQ / REQ-C）
| 需求ID | 主要覆盖测试 | 证据 | 结果 |
|---|---|---|---|
| REQ-001 | `test_system_profile_import_api.py`, `test_system_profile_import_layout_consistency.py`, `uiComponents.test.js` | CMD-01, CMD-02 | ✅ |
| REQ-002 | `test_system_profile_publish_rules.py`, `systemProfileBoardPage.v24.test.js` | CMD-01, CMD-02 | ✅ |
| REQ-003 | `test_system_profile_publish_rules.py`, `systemProfileBoardPage.v24.test.js` | CMD-01, CMD-02 | ✅ |
| REQ-004 | `test_system_profile_import_api.py`, `test_system_profile_publish_rules.py`, `uiComponents.test.js` | CMD-01, CMD-02 | ✅ |
| REQ-005 | `test_profile_summary_service.py`, `uiComponents.test.js` | CMD-05, CMD-02 | ✅ |
| REQ-006 | `test_evaluation_contract_api.py` | CMD-01, CMD-03 | ✅ |
| REQ-007 | `test_report_download_api.py`, `evaluationReportThreePoint.v24.test.js` | CMD-01, CMD-02, CMD-03 | ✅ |
| REQ-008 | `evaluationReportThreePoint.v24.test.js` | CMD-02 | ✅ |
| REQ-009 | `test_modification_trace_api.py` | CMD-01 | ✅ |
| REQ-010 | `test_modification_trace_api.py`, `test_task_modification_compat.py` | CMD-01, CMD-04 | ✅ |
| REQ-011 | `test_system_profile_permissions.py`, `systemProfileBoardPage.v24.test.js` | CMD-01, CMD-02 | ✅ |
| REQ-012 | `test_system_profile_v21_fields.py`, `systemProfileBoardPage.v24.test.js` | CMD-01, CMD-02 | ✅ |
| REQ-101 | `test_system_profile_import_layout_consistency.py`, `uiComponents.test.js` | CMD-01, CMD-02 | ✅ |
| REQ-102 | `test_system_profile_publish_rules.py`, `systemProfileBoardPage.v24.test.js` | CMD-01, CMD-02 | ✅ |
| REQ-103 | `test_system_profile_publish_rules.py`, `systemProfileBoardPage.v24.test.js` | CMD-01, CMD-02 | ✅ |
| REQ-104 | `test_evaluation_contract_api.py`, `test_report_download_api.py`, `evaluationReportThreePoint.v24.test.js` | CMD-01, CMD-02, CMD-03 | ✅ |
| REQ-105 | `test_modification_trace_api.py`, `test_task_modification_compat.py` | CMD-01, CMD-04 | ✅ |
| REQ-106 | 回滚前置检查（`v2.3` tag、部署脚本可执行） | CMD-06, CMD-07 | ✅（回滚实演待 T012） |
| REQ-C001 | `test_system_profile_import_layout_consistency.py`, `uiComponents.test.js` | CMD-01, CMD-02 | ✅ |
| REQ-C002 | `test_system_profile_publish_rules.py`, `systemProfileBoardPage.v24.test.js` | CMD-01, CMD-02 | ✅ |
| REQ-C003 | `test_evaluation_contract_api.py` | CMD-01, CMD-03 | ✅ |
| REQ-C004 | `test_system_profile_permissions.py`, `navigationAndPageTitleRegression.test.js` | CMD-01, CMD-02 | ✅ |
| REQ-C005 | `test_modification_trace_api.py`, `test_task_modification_compat.py` | CMD-01, CMD-04 | ✅ |
| REQ-C006 | `test_profile_summary_service.py`, `test_system_profile_publish_rules.py` | CMD-05, CMD-01 | ✅ |
| REQ-C007 | `test_system_profile_v21_fields.py`, `systemProfileBoardPage.v24.test.js` | CMD-01, CMD-02 | ✅ |

## 本轮问题与修复
| ID | 问题 | 根因 | 处理 | 结果 |
|---|---|---|---|---|
| BUG-T011-001 | `test_system_profile_import_layout_consistency.py` 失败 | 用例仍断言 v2.3 的 `Select+Upload` 单工具条，与 v2.4 卡片化设计冲突 | 将用例改为断言 `renderDocTypeCard` + `DOC_TYPE_CONFIGS` + 无 `Select` 依赖 | 修复后单测通过，已纳入 CMD-01 |
| BUG-T010-001 | `evaluationReportThreePoint.v24.test.js` 首个断言失败 | 文本断言使用全等，页面实际为“估算理由：xxx” | 改为正则子串断言 | 修复后套件通过，已纳入 CMD-02 |

## CR 验证证据（增量）
| CR-ID | 验收标准 | 验证命令 | 证据 | 结论 |
|---|---|---|---|---|
| CR-20260301-001 | 仅展示主责/B角系统 | CMD-08 | `shows only systems where current user is owner or backup owner` 断言通过 | ✅ |
| CR-20260301-001 | 五域要素交互一致（无新增/删除） | CMD-08 | `uses human-readable editors instead of raw json textarea` 断言通过；页面无“新增/删除”按钮文案 | ✅ |
| CR-20260301-001 | 空画像首屏可见且可编辑 | CMD-08 | `renders empty editors for all domain fields when profile is not imported` 断言通过 | ✅ |
| CR-20260301-001 | 相邻页面首屏不崩溃回归 | CMD-09 | import/code-scan/evidence-rule 三页面 render smoke 通过 | ✅ |
| CR-20260301-001 | 前端质量门禁与构建产物 | CMD-10, CMD-11, CMD-12 | ESLint 零 warning；构建成功；部署后健康检查通过 | ✅ |
| CR-20260302-001 | 内容区不重复域导航标题 | CMD-13 | `does not duplicate active domain title in content area` 断言通过 | ✅ |
| CR-20260302-001 | 五域导航按钮左对齐 | CMD-13 | `left-aligns domain navigation buttons` 断言通过 | ✅ |
| CR-20260302-001 | 前端质量门禁与构建产物 | CMD-14, CMD-15 | ESLint 零 warning；构建成功 | ✅ |
| CR-20260302-002 | 画像携带旧 `system_id` 时仍使用系统清单当前 ID 请求 | CMD-16 | `prefers current system id from system list when profile carries stale system_id` 断言通过 | ✅ |
| CR-20260302-002 | 前端质量门禁（增量） | CMD-17 | ESLint 零 warning | ✅ |
| CR-20260302-002 | STAGING 发布与双链路健康检查 | CMD-18, CMD-19 | 发布成功；本机/公网健康检查均通过 | ✅ |
| CR-20260302-002 | 系统存在但画像为空时事件查询不再返回404 | CMD-20 | `profile_events_returns_empty_when_profile_not_created` 断言通过 | ✅ |
| CR-20260302-002 | 后端容错修复再次发布与双链路健康检查 | CMD-21, CMD-22 | 发布成功；本机/公网健康检查均通过 | ✅ |
| CR-20260302-003 | 默认账号初始化单测通过 | CMD-23 | `ensure_internal_default_users` 新建/更新场景均通过 | ✅ |
| CR-20260302-003 | 内网部署脚本语法检查通过 | CMD-24 | `deploy-backend-internal.sh` 无语法错误 | ✅ |
| CR-20260302-003 | 默认账号初始化脚本可生成 5 个同名口令账号 | CMD-25 | `admin/manager/expert1/expert2/expert3` 创建成功 | ✅ |

## 结论
- 当前 `T011` 所需回归命令已执行并通过，REQ/REQ-C 覆盖矩阵已落盘。
- `CR-20260301-001` 增量验证命令已执行通过，信息展示页“展示优先+轻量修正”交互一致性达成。
- `CR-20260302-001` 增量验证命令已执行通过，域标题去冗余与五域导航左对齐已达成。
- `CR-20260302-002` 增量验证命令已执行通过，信息展示页旧 `system_id` 容错已生效。
- `CR-20260302-002` 后端容错（无画像事件查询空返回）已执行并通过，线上不再因该场景返回 404。
- `CR-20260302-003` 增量验证命令已执行通过，内网部署目录属主对齐与默认账号初始化能力已就绪。
- CR-20260301-001/002 已完成增量发布并通过本机/公网健康检查；CR-20260302-003 已纳入本次 v2.4 收口基线并标记 Implemented。

## 变更记录
| 版本 | 日期 | 说明 |
|---|---|---|
| v0.9 | 2026-03-02 | `CR-20260302-003` 验证结论收口：状态更新为 Approved，并与 `status.md` 完成态对齐 |
| v0.8 | 2026-03-02 | 追加 `CR-20260302-003` 增量验证证据（默认账号初始化单测、内网部署脚本语法检查、初始化脚本执行结果） |
| v0.7 | 2026-03-02 | 追加后端容错修复证据（CMD-20）与二次部署健康检查（CMD-21/CMD-22） |
| v0.6 | 2026-03-02 | 追加 STAGING 增量发布证据（CMD-18/CMD-19）与双链路健康检查结果 |
| v0.5 | 2026-03-02 | 追加 `CR-20260302-002` 增量验证证据（旧 `system_id` 容错定向回归 + ESLint） |
| v0.4 | 2026-03-02 | 追加 `CR-20260302-001` 增量验证证据（域标题去冗余、导航左对齐、board回归11通过、eslint、build） |
| v0.3 | 2026-03-01 | 追加 `CR-20260301-001` 增量验证证据（board/render smoke/eslint/build/deploy+health） |
| v0.2 | 2026-03-01 | 测试阶段收口：与 `review_testing.md` 审查结论对齐，状态更新为 Approved |
| v0.1 | 2026-03-01 | 初始化 v2.4 `test_report.md`，补齐 REQ/REQ-C 覆盖矩阵与命令证据 |
