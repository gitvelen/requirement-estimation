# 需求评估系统 v2.4 任务计划

## 文档元信息
| 项 | 值 |
|---|---|
| 状态 | Completed |
| 日期 | 2026-03-02 |
| 版本 | v1.3 |
| 基线版本（对比口径） | `v2.3` |
| Active CR（如有） | `-`（已收口） |
| 关联设计 | `docs/v2.4/design.md` |
| 关联需求 | `docs/v2.4/requirements.md` |
| 关联状态 | `docs/v2.4/status.md` |

## 里程碑
| 里程碑 | 交付物 | 截止日期 |
|---|---|---|
| M1 | 后端核心能力（画像模型/提取/估算/权限）完成（T001-T007） | 2026-03-01 |
| M2 | 前端四页面改造与联调完成（T008-T010） | 2026-03-02 |
| M3 | 覆盖验证、回滚演练、文档闭环完成（T011-T012） | 2026-03-03 |

## Definition of Done（DoD）
- [x] 需求可追溯：任务关联 `REQ/SCN/API/TEST` 清晰
- [x] 代码可运行：不破坏主流程，线上行为变化具备回滚路径
- [x] 自测通过：每个任务均有可复现命令与结果
- [x] 安全与合规：权限、输入校验、密钥处理满足要求
- [x] 文档同步：implementation/testing/deployment 产物可追溯

## 禁止项引用索引（来源：requirements.md REQ-C 章节）
| REQ-C ID | 一句话摘要 |
|---|---|
| REQ-C001 | 禁止文档类型切换导致已选文件或导入结果丢失 |
| REQ-C002 | 禁止 AI 建议更新后无法恢复上一版 |
| REQ-C003 | 禁止工作量估算继续沿用静态映射（1.5/2.5/4.0） |
| REQ-C004 | 禁止新增独立页面或菜单路由 |
| REQ-C005 | 禁止 PM 修正数据丢失（快照/diff/画像聚合三位一体） |
| REQ-C006 | 禁止自动覆盖非选中系统画像 |
| REQ-C007 | 禁止画像域重构后语义覆盖缺失 |

## 任务概览
状态标记：`待办` / `进行中` / `已完成`；里程碑标记：`🏁` = 完成后必须向用户展示中间成果
验证命令统一预期：退出码为 0，且关键断言通过

| 任务分类 | 任务ID | 任务名称 | 优先级 | 预估工时 | Owner | Reviewer | 关联CR（可选） | 关联需求项 | 关联场景（SCN） | 关联接口（API） | 任务状态 | 依赖任务ID | 验证方式 | 里程碑 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 后端数据模型 | T001 | 画像 5 域 12 子字段模型与迁移兼容 | P0 | 1.5d | Codex | Codex | - | REQ-012, REQ-C007, REQ-106 | SCN-V24-05, SCN-V24-06 | API-007, API-008 | 已完成 | - | `pytest -q tests/test_system_profile_v21_fields.py` | M1 |
| 后端接口 | T002 | 画像 CRUD、时间线、建议采纳/回滚 API 改造 | P0 | 1.5d | Codex | Codex | - | REQ-002, REQ-003, REQ-012, REQ-102, REQ-103, REQ-C002 | SCN-V24-05, SCN-V24-06, SCN-V24-07 | API-004, API-005, API-006, API-007, API-008 | 已完成 | T001 | `pytest -q tests/test_system_profile_publish_rules.py tests/test_system_profile_permissions.py` | M1 |
| 后端接口 | T003 | 导入历史与导入触发异步提取链路 | P0 | 1d | Codex | Codex | - | REQ-001, REQ-004, REQ-101, REQ-C001 | SCN-V24-01, SCN-V24-02, SCN-V24-04 | API-001, API-002, API-003 | 已完成 | T001 | `python -m pytest -q tests/test_system_profile_import_api.py tests/test_system_profile_publish_rules.py tests/test_system_profile_permissions.py tests/test_knowledge_import_api.py` | M1 |
| 后端服务 | T004 | AI 提取异步任务串行化与多系统过滤通知 | P0 | 1.5d | Codex | Codex | - | REQ-004, REQ-005, REQ-C006, REQ-102 | SCN-V24-03, SCN-V24-04 | API-001, API-003 | 已完成 | T003 | `pytest -q tests/test_profile_summary_service.py tests/test_code_scan_api.py tests/test_api_regression.py` | M1🏁 |
| 权限与安全 | T005 | PM-系统写权限绑定与跨系统只读策略 | P0 | 0.5d | Codex | Codex | - | REQ-011, REQ-C004 | SCN-V24-03, SCN-V24-12 | API-001, API-005, API-006, API-008 | 已完成 | T002 | `pytest -q tests/test_system_profile_permissions.py tests/test_system_profile_publish_rules.py tests/test_system_profile_import_api.py` | M1 |
| 估算引擎 | T006 | LLM 三点估计/PERT/降级/三层知识注入 | P0 | 1.5d | Codex | Codex | - | REQ-006, REQ-104, REQ-C003 | SCN-V24-08, SCN-V24-09, SCN-V24-10 | API-011 | 已完成 | T001 | `pytest -q tests/test_task_reevaluate_api.py tests/test_evaluation_contract_api.py` | M1 |
| 经验沉淀 | T007 | AI 快照 + 两阶段 diff + correction history 聚合 | P0 | 1d | Codex | Codex | - | REQ-009, REQ-010, REQ-105, REQ-C005 | SCN-V24-11 | API-009, API-010 | 已完成 | T006 | `pytest -q tests/test_modification_trace_api.py tests/test_task_modification_compat.py` | M1 |
| 前端导入页 | T008 | ImportPage 卡片化、历史折叠、状态轮询、跳转 | P1 | 1d | Codex | Codex | - | REQ-001, REQ-004, REQ-005, REQ-101, REQ-C001 | SCN-V24-01, SCN-V24-02, SCN-V24-03, SCN-V24-04 | API-001, API-002, API-003 | 已完成 | T003,T004 | `pytest -q tests/test_system_profile_import_layout_consistency.py && cd frontend && npm test -- --watch=false --runInBand src/__tests__/uiComponents.test.js` | M2 |
| 前端画像页 | T009 | BoardPage 三区布局、inline diff、时间线、只读模式 | P1 | 1.5d | Codex | Codex | - | REQ-002, REQ-003, REQ-011, REQ-012, REQ-102, REQ-103, REQ-C002, REQ-C004, REQ-C007 | SCN-V24-05, SCN-V24-06, SCN-V24-07, SCN-V24-12 | API-004, API-005, API-006, API-007, API-008 | 已完成 | T002,T005 | `cd frontend && npm test -- --watch=false --runInBand src/__tests__/systemProfileBoardPage.v24.test.js && npm test -- --watch=false --runInBand src/__tests__/navigationAndPageTitleRegression.test.js` | M2🏁 |
| 前端评估/报告 | T010 | Evaluation/Report 三点估计展示与导出联动 | P1 | 1d | Codex | Codex | - | REQ-007, REQ-008, REQ-104 | SCN-V24-09, SCN-V24-10 | API-011, API-012 | 已完成 | T006,T007 | `.venv/bin/pytest -q tests/test_report_download_api.py tests/test_evaluation_contract_api.py && cd frontend && CI=true npm test -- --watch=false --runInBand src/__tests__/evaluationReportThreePoint.v24.test.js src/__tests__/dashboardMetrics.test.js` | M2 |
| 测试与证据 | T011 | REQ/REQ-C 全量回归与覆盖矩阵落盘 | P1 | 1d | Codex | Codex | - | REQ-001~REQ-012, REQ-101~REQ-106, REQ-C001~REQ-C007 | SCN-V24-01~SCN-V24-12 | API-001~API-012 | 已完成 | T001-T010 | `.venv/bin/python -m pytest -q tests/test_system_profile_*.py tests/test_report_download_api.py tests/test_evaluation_contract_api.py tests/test_modification_trace_api.py tests/test_task_modification_compat.py tests/test_profile_summary_service.py && cd frontend && CI=true npm test -- --watch=false --runInBand src/__tests__/uiComponents.test.js src/__tests__/systemProfileBoardPage.v24.test.js src/__tests__/navigationAndPageTitleRegression.test.js src/__tests__/evaluationReportThreePoint.v24.test.js src/__tests__/dashboardMetrics.test.js` | M3🏁 |
| 部署与回滚 | T012 | 部署清单、回滚演练、阶段文档闭环 | P1 | 0.5d | Codex | Codex | - | REQ-106, REQ-102, REQ-105 | SCN-V24-01~SCN-V24-12（抽样回归验收） | API-001~API-012（抽样验收） | 已完成 | T011 | `printf '2\\n' | bash deploy-all.sh && curl -fsS http://127.0.0.1/api/v1/health && git rev-parse --verify --quiet v2.3^{commit} && test -x deploy-all.sh && .venv/bin/python -m pytest -q tests/test_system_profile_publish_rules.py -k rollback && TMP_DIR=\"$(mktemp -d /tmp/v23-l2-drill-XXXX)\"; git worktree add \"$TMP_DIR\" v2.3 && bash -n \"$TMP_DIR/deploy-all.sh\" && git worktree remove \"$TMP_DIR\" --force` | M3 |
| 前端增量CR | T013 | CR-20260301-001 信息展示页展示优先交互一致化修复 | P1 | 0.5d | Codex | Codex | CR-20260301-001 | REQ-011, REQ-012, REQ-101 | SCN-V24-05, SCN-V24-12 | API-004, API-007, API-008 | 已完成 | T009,T011 | `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileBoardPage.v24.test.js && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileImportPage.render.test.js src/__tests__/codeScanPage.render.test.js src/__tests__/evidenceRuleConfigPage.render.test.js && npx eslint src/pages/SystemProfileBoardPage.js src/__tests__/systemProfileBoardPage.v24.test.js --max-warnings=0 && npm run build` | M3 |
| 前端增量CR | T014 | CR-20260302-001 信息展示页域标题去冗余与域导航左对齐 | P1 | 0.25d | Codex | Codex | CR-20260302-001 | REQ-011, REQ-012, REQ-101 | SCN-V24-05, SCN-V24-12 | API-004, API-007, API-008 | 已完成 | T013 | `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileBoardPage.v24.test.js && npx eslint src/pages/SystemProfileBoardPage.js src/__tests__/systemProfileBoardPage.v24.test.js --max-warnings=0 && npm run build` | M3 |
| 前端增量CR | T015 | CR-20260302-002 信息展示页旧 system_id 容错与当前 ID 优先 | P1 | 0.25d | Codex | Codex | CR-20260302-002 | REQ-011, REQ-012 | SCN-V24-05, SCN-V24-12 | API-004, API-007, API-008 | 已完成 | T013,T014 | `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileBoardPage.v24.test.js -t \"prefers current system id from system list when profile carries stale system_id\" && npx eslint src/pages/SystemProfileBoardPage.js src/__tests__/systemProfileBoardPage.v24.test.js --max-warnings=0` | M3 |

## 任务详情

### T001: 画像 5 域 12 子字段模型与迁移兼容
**分类**：后端数据模型 / **优先级**：P0 / **预估工时**：1.5d / **Owner**：Codex / **Reviewer**：Codex
**关联需求项**：REQ-012, REQ-C007, REQ-106
**关联场景（SCN）**：SCN-V24-05, SCN-V24-06
**关联接口（API）**：API-007, API-008
**任务描述**：
- 在 `system_profiles.json` 引入 `profile_data` 5 域结构和 `_migrated` 标记
- 提供启动迁移：旧 4 字段到新结构的映射，旧字段保留用于回退兼容
- 迁移失败保持可回滚，不破坏 v2.3 读取路径
**影响面/修改范围**：
- `backend/service/system_profile_service.py`
- `tests/test_system_profile_v21_fields.py`（扩展 v2.4 迁移断言）
**验收标准**：
- [ ] 旧数据迁移后新结构完整，旧字段仍可读取
- [ ] `_migrated=true` 仅写一次，重复启动不重复迁移
**验证方式**：
- 命令：`pytest -q tests/test_system_profile_v21_fields.py`

### T002: 画像 CRUD、时间线、建议采纳/回滚 API 改造
**分类**：后端接口 / **优先级**：P0 / **预估工时**：1.5d
**关联需求项**：REQ-002, REQ-003, REQ-012, REQ-102, REQ-103, REQ-C002
**关联场景（SCN）**：SCN-V24-05, SCN-V24-06, SCN-V24-07
**关联接口（API）**：API-004, API-005, API-006, API-007, API-008
**任务描述**：
- 画像读写 API 入参/出参切换到 5 域结构
- 新增/改造时间线、采纳、回滚接口并统一错误码
- 保证回滚无 previous 返回 `ROLLBACK_NO_PREVIOUS(409)`
**影响面/修改范围**：
- `backend/api/system_profile_routes.py`
- `backend/service/system_profile_service.py`
- `tests/test_system_profile_publish_rules.py`
- `tests/test_system_profile_permissions.py`
**验收标准**：
- [ ] 采纳/回滚行为可复现，时间线记录完整
- [ ] 错误码与权限口径与设计一致
**验证方式**：
- 命令：`pytest -q tests/test_system_profile_publish_rules.py tests/test_system_profile_permissions.py`

### T003: 导入历史与导入触发异步提取链路
**分类**：后端接口 / **优先级**：P0 / **预估工时**：1d
**关联需求项**：REQ-001, REQ-004, REQ-101, REQ-C001
**关联场景（SCN）**：SCN-V24-01, SCN-V24-02, SCN-V24-04
**关联接口（API）**：API-001, API-002, API-003
**任务描述**：
- 为文档导入记录 `import_history` 并提供分页查询
- 导入成功返回 `extraction_task_id`
- 保证多文档类型操作互不覆盖后端状态
**影响面/修改范围**：
- `backend/api/system_profile_routes.py`
- `backend/service/system_profile_service.py`
- `tests/test_api_regression.py`
**验收标准**：
- [x] 导入历史字段完整（时间/文件名/类型/状态/操作人）
- [x] 导入接口回包包含任务 ID
**验证方式**：
- 命令：`pytest -q tests/test_api_regression.py -k system_profile`

### T004: AI 提取异步任务串行化与多系统过滤通知
**分类**：后端服务 / **优先级**：P0 / **预估工时**：1.5d
**关联需求项**：REQ-004, REQ-005, REQ-C006, REQ-102
**关联场景（SCN）**：SCN-V24-03, SCN-V24-04
**关联接口（API）**：API-001, API-003
**任务描述**：
- 引入 per-system 串行锁和任务状态机 `pending/processing/completed/failed`
- 两步提取（relevant_domains + domain payload）并按域选择性更新
- 多系统信息仅更新选中系统，其他系统以通知返回
**影响面/修改范围**：
- `backend/service/system_profile_service.py`
- `backend/api/system_profile_routes.py`
- `tests/test_code_scan_api.py`（新增异步任务状态断言）
- `tests/test_api_regression.py`
**验收标准**：
- [x] 同系统并发触发时后触发任务保持 pending
- [x] 非选中系统数据完全不被覆盖
**验证方式**：
- 命令：`pytest -q tests/test_code_scan_api.py tests/test_api_regression.py`

### T005: PM-系统写权限绑定与跨系统只读策略
**分类**：权限与安全 / **优先级**：P0 / **预估工时**：0.5d
**关联需求项**：REQ-011, REQ-C004
**关联场景（SCN）**：SCN-V24-03, SCN-V24-12
**关联接口（API）**：API-001, API-005, API-006, API-008
**任务描述**：
- 固化写操作鉴权：负责人可写、非负责人只读、admin 全局可写
- 跨系统跳转链路加入只读标记
- 明确禁止新增路由（在既有页面内完成交互）
**影响面/修改范围**：
- `backend/api/system_profile_routes.py`
- `frontend/src/pages/SystemProfileBoardPage.js`
- `tests/test_system_profile_permissions.py`
**验收标准**：
- [x] 非负责人写请求统一 403
- [x] 读操作保持开放不回退
**验证方式**：
- 命令：`pytest -q tests/test_system_profile_permissions.py`

### T006: LLM 三点估计/PERT/降级/三层知识注入
**分类**：估算引擎 / **优先级**：P0 / **预估工时**：1.5d
**关联需求项**：REQ-006, REQ-104, REQ-C003
**关联场景（SCN）**：SCN-V24-08, SCN-V24-09, SCN-V24-10
**关联接口（API）**：API-011
**任务描述**：
- 估算返回 `optimistic/most_likely/pessimistic/expected/reasoning`
- `expected` 由系统按 PERT 公式计算并保留 2 位小数
- LLM 失败降级为 `degraded=true` + 回退 `original_estimate`
- 移除静态映射覆写逻辑，接入三层知识注入
**影响面/修改范围**：
- `backend/agent/work_estimation_agent.py`
- `backend/api/routes.py`
- `tests/test_task_reevaluate_api.py`
- `tests/test_evaluation_contract_api.py`
**验收标准**：
- [x] 五字段输出完整且公式正确
- [x] 降级分支返回 200 且标记清晰
**验证方式**：
- 命令：`pytest -q tests/test_task_reevaluate_api.py tests/test_evaluation_contract_api.py`

### T007: AI 快照 + 两阶段 diff + correction history 聚合
**分类**：经验沉淀 / **优先级**：P0 / **预估工时**：1d
**关联需求项**：REQ-009, REQ-010, REQ-105, REQ-C005
**关联场景（SCN）**：SCN-V24-11
**关联接口（API）**：API-009, API-010
**任务描述**：
- 流水线三步保存 `ai_original_output`
- PM 提交时生成 Phase1 diff，评估完成后补 Phase2 估值 diff
- 将 diff 聚合更新到 `ai_correction_history`
**影响面/修改范围**：
- `backend/api/routes.py`
- `backend/service/system_profile_service.py`
- `tests/test_modification_trace_api.py`
- `tests/test_task_modification_compat.py`
**验收标准**：
- [x] 快照/diff/画像聚合三处均可查询
- [x] PM 无修改时 diff 为空且聚合不增长
**验证方式**：
- 命令：`pytest -q tests/test_modification_trace_api.py tests/test_task_modification_compat.py`

### T008: ImportPage 卡片化、历史折叠、状态轮询、跳转
**分类**：前端导入页 / **优先级**：P1 / **预估工时**：1d
**关联需求项**：REQ-001, REQ-004, REQ-005, REQ-101, REQ-C001
**关联场景（SCN）**：SCN-V24-01, SCN-V24-02, SCN-V24-03, SCN-V24-04
**关联接口（API）**：API-001, API-002, API-003
**任务描述**：
- 将单下拉改为 5 行独立 Card
- 增加导入历史折叠与“查看系统画像”跳转
- 导入后轮询提取状态并展示多系统通知
**影响面/修改范围**：
- `frontend/src/pages/SystemProfileImportPage.js`
- `frontend/src/pages/SystemProfilePage.js`
- `tests/test_system_profile_import_layout_consistency.py`
- `frontend/src/__tests__/uiComponents.test.js`
**验收标准**：
- [x] 跨类型操作不丢已选文件和导入结果
- [x] 导入历史默认折叠，支持展开
**验证方式**：
- 命令：`pytest -q tests/test_system_profile_import_layout_consistency.py && cd frontend && npm test -- --watch=false --runInBand src/__tests__/uiComponents.test.js`

### T009: BoardPage 三区布局、inline diff、时间线、只读模式
**分类**：前端画像页 / **优先级**：P1 / **预估工时**：1.5d
**关联需求项**：REQ-002, REQ-003, REQ-011, REQ-012, REQ-102, REQ-103, REQ-C002, REQ-C004, REQ-C007
**关联场景（SCN）**：SCN-V24-05, SCN-V24-06, SCN-V24-07, SCN-V24-12
**关联接口（API）**：API-004, API-005, API-006, API-007, API-008
**任务描述**：
- 左域导航 + 中央内容 + 右时间线侧栏
- 子字段级 inline diff、采纳/忽略/回滚按钮
- 跨系统链接进入只读模式并提示
**影响面/修改范围**：
- `frontend/src/pages/SystemProfileBoardPage.js`
- `frontend/src/utils/systemProfileV21.js`
- `frontend/src/__tests__/navigationAndPageTitleRegression.test.js`
**验收标准**：
- [x] 时间线支持分页和空态
- [x] 回滚按钮在无 previous 时禁用
**验证方式**：
- 命令：`cd frontend && npm test -- --watch=false --runInBand src/__tests__/systemProfileBoardPage.v24.test.js && npm test -- --watch=false --runInBand src/__tests__/navigationAndPageTitleRegression.test.js`

### T010: Evaluation/Report 三点估计展示与导出联动
**分类**：前端评估/报告 / **优先级**：P1 / **预估工时**：1d
**关联需求项**：REQ-007, REQ-008, REQ-104
**关联场景（SCN）**：SCN-V24-09, SCN-V24-10
**关联接口（API）**：API-011, API-012
**任务描述**：
- EvaluationPage 主列展示 expected，行内展开 O/M/P/reasoning
- ReportPage 同步展开视图与导出按钮对接
- 降级场景展示 N/A 与提示文案
**影响面/修改范围**：
- `frontend/src/pages/EvaluationPage.js`
- `frontend/src/pages/ReportPage.js`
- `backend/api/report_routes.py`
- `tests/test_report_download_api.py`
**验收标准**：
- [x] 三渠道（评估页/报告页/导出）expected 一致
- [x] 降级场景展示符合要求
**验证方式**：
- 命令：`.venv/bin/pytest -q tests/test_report_download_api.py tests/test_evaluation_contract_api.py && cd frontend && CI=true npm test -- --watch=false --runInBand src/__tests__/evaluationReportThreePoint.v24.test.js src/__tests__/dashboardMetrics.test.js`

### T011: REQ/REQ-C 全量回归与覆盖矩阵落盘
**分类**：测试与证据 / **优先级**：P1 / **预估工时**：1d
**关联需求项**：REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, REQ-010, REQ-011, REQ-012, REQ-101, REQ-102, REQ-103, REQ-104, REQ-105, REQ-106, REQ-C001, REQ-C002, REQ-C003, REQ-C004, REQ-C005, REQ-C006, REQ-C007
**关联场景（SCN）**：SCN-V24-01~SCN-V24-12
**关联接口（API）**：API-001~API-012
**任务描述**：
- 构建 GWT 粒度测试覆盖矩阵并补齐缺失用例
- 输出 `test_report.md` 证据（命令、结果、截图/日志）
- 对 REQ-C 项强制使用 `UI_PROOF` 或 `RUN_OUTPUT`
**影响面/修改范围**：
- `docs/v2.4/test_report.md`
- `tests/` 下新增/更新 v2.4 相关用例
**验收标准**：
- [x] 需求覆盖矩阵无缺项、无伪证据
- [x] 关键失败路径（权限/降级/回滚）全部覆盖
**验证方式**：
- 命令：`.venv/bin/python -m pytest -q tests/test_system_profile_*.py tests/test_report_download_api.py tests/test_evaluation_contract_api.py tests/test_modification_trace_api.py tests/test_task_modification_compat.py tests/test_profile_summary_service.py && cd frontend && CI=true npm test -- --watch=false --runInBand src/__tests__/uiComponents.test.js src/__tests__/systemProfileBoardPage.v24.test.js src/__tests__/navigationAndPageTitleRegression.test.js src/__tests__/evaluationReportThreePoint.v24.test.js src/__tests__/dashboardMetrics.test.js`

### T012: 部署清单、回滚演练、阶段文档闭环
**分类**：部署与回滚 / **优先级**：P1 / **预估工时**：0.5d
**关联需求项**：REQ-106, REQ-102, REQ-105
**关联场景（SCN）**：SCN-V24-01~SCN-V24-12（抽样回归验收）
**关联接口（API）**：API-001~API-012（抽样验收）
**任务描述**：
- 完成 deployment 前检查项和回滚 SOP 预演记录
- 在 `review_implementation.md` / `review_testing.md` / `deployment.md` 回写证据
- 验证 L1/L2 回滚路径可执行
**影响面/修改范围**：
- `docs/v2.4/review_implementation.md`
- `docs/v2.4/review_testing.md`
- `docs/v2.4/deployment.md`
**验收标准**：
- [x] 回滚命令有执行证据和恢复验证
- [x] 阶段文档与 status 状态一致
**验证方式**：
- 命令：`printf '2\n' | bash deploy-all.sh && curl -fsS http://127.0.0.1/api/v1/health && git rev-parse --verify --quiet v2.3^{commit} && test -x deploy-all.sh && .venv/bin/python -m pytest -q tests/test_system_profile_publish_rules.py -k rollback && TMP_DIR="$(mktemp -d /tmp/v23-l2-drill-XXXX)"; git worktree add "$TMP_DIR" v2.3 && bash -n "$TMP_DIR/deploy-all.sh" && git worktree remove "$TMP_DIR" --force`

### T013: CR-20260301-001 信息展示页展示优先交互一致化修复
**分类**：前端增量CR / **优先级**：P1 / **预估工时**：0.5d
**关联需求项**：REQ-011, REQ-012, REQ-101
**关联场景（SCN）**：SCN-V24-05, SCN-V24-12
**关联接口（API）**：API-004, API-007, API-008
**任务描述**：
- 信息展示页系统范围收敛为“当前 PM 作为 A角/B角负责的系统”。
- 五域字段统一展示+轻量修正输入，不保留新增/删除按钮的编辑器化交互。
- 空画像场景下保持全部要素可见（空输入态），避免“无输入控件”的不一致体验。
**影响面/修改范围**：
- `frontend/src/pages/SystemProfileBoardPage.js`
- `frontend/src/__tests__/systemProfileBoardPage.v24.test.js`
- `docs/v2.4/status.md`
- `docs/v2.4/plan.md`
- `docs/v2.4/test_report.md`
- `docs/v2.4/cr/CR-20260301-001.md`
**验收标准**：
- [x] 信息展示页仅显示当前 PM 主责/B角系统。
- [x] 五域要素交互一致，不出现新增/删除按钮混用。
- [x] 页面首屏渲染稳定，不出现空白或崩溃。
**验证方式**：
- 命令：`cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileBoardPage.v24.test.js`
- 命令：`cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileImportPage.render.test.js src/__tests__/codeScanPage.render.test.js src/__tests__/evidenceRuleConfigPage.render.test.js`
- 命令：`cd frontend && npx eslint src/pages/SystemProfileBoardPage.js src/__tests__/systemProfileBoardPage.v24.test.js --max-warnings=0`
- 命令：`cd frontend && npm run build`

### T014: CR-20260302-001 信息展示页域标题去冗余与域导航左对齐
**分类**：前端增量CR / **优先级**：P1 / **预估工时**：0.25d
**关联需求项**：REQ-011, REQ-012, REQ-101
**关联场景（SCN）**：SCN-V24-05, SCN-V24-12
**关联接口（API）**：API-004, API-007, API-008
**任务描述**：
- 去掉内容区随域变化的重复导航标题，避免与左侧域导航语义重复。
- 左侧五域导航按钮统一左对齐，减少视觉跳动和认知负担。
- 增加断言：`D1...D5` 域标题不重复、导航按钮左对齐。
**影响面/修改范围**：
- `frontend/src/pages/SystemProfileBoardPage.js`
- `frontend/src/__tests__/systemProfileBoardPage.v24.test.js`
- `docs/v2.4/cr/CR-20260302-001.md`
- `docs/v2.4/status.md`
- `docs/v2.4/plan.md`
- `docs/v2.4/test_report.md`
**验收标准**：
- [x] 内容区不再重复出现 `D1...D5` 作为二次导航标题。
- [x] 五域导航按钮左对齐。
- [x] 页面主流程不受影响（域切换、保存草稿、发布按钮仍可用）。
**验证方式**：
- 命令：`cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileBoardPage.v24.test.js`
- 命令：`cd frontend && npx eslint src/pages/SystemProfileBoardPage.js src/__tests__/systemProfileBoardPage.v24.test.js --max-warnings=0`
- 命令：`cd frontend && npm run build`

### T015: CR-20260302-002 信息展示页旧 system_id 容错与当前 ID 优先
**分类**：前端增量CR / **优先级**：P1 / **预估工时**：0.25d
**关联需求项**：REQ-011, REQ-012
**关联场景（SCN）**：SCN-V24-05, SCN-V24-12
**关联接口（API）**：API-004, API-007, API-008
**任务描述**：
- 针对信息展示页新增 `effectiveSystemId` 解析逻辑：优先系统清单当前 ID，回退画像 `system_id`。
- 将时间线、保存、发布、建议采纳/回滚、加载更多时间线统一收敛到同一 ID 选择策略。
- 增加 stale id 回归断言，防止再次请求旧 ID 导致 404。
- 修复后端事件查询容错：系统存在但画像未创建时返回空事件列表，避免页面弹“系统不存在”。
**影响面/修改范围**：
- `frontend/src/pages/SystemProfileBoardPage.js`
- `frontend/src/__tests__/systemProfileBoardPage.v24.test.js`
- `backend/service/system_profile_service.py`
- `tests/test_system_profile_publish_rules.py`
- `docs/v2.4/cr/CR-20260302-002.md`
- `docs/v2.4/status.md`
- `docs/v2.4/plan.md`
- `docs/v2.4/test_report.md`
**验收标准**：
- [x] 画像携带旧 `system_id` 时，时间线请求仍命中系统清单当前 ID。
- [x] 保存/发布/采纳建议/回滚建议请求均使用当前系统清单 ID。
- [x] 页面不再因旧 ID 触发“系统不存在”。
**验证方式**：
- 命令：`cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileBoardPage.v24.test.js -t "prefers current system id from system list when profile carries stale system_id"`
- 命令：`cd frontend && npx eslint src/pages/SystemProfileBoardPage.js src/__tests__/systemProfileBoardPage.v24.test.js --max-warnings=0`
- 命令：`.venv/bin/pytest -q tests/test_system_profile_publish_rules.py -k "profile_events_returns_empty_when_profile_not_created"`

## 任务级回滚/开关策略
| 任务ID | 回滚触发条件 | 回滚/开关策略 |
|---|---|---|
| T001 | 启动迁移后读取异常或字段语义错位 | 保留旧 4 字段双读；关闭 `PROFILE_MIGRATION_ENABLED` 并恢复迁移前 JSON 备份 |
| T002 | 新 API 契约导致读写/时间线异常 | 回退 `system_profile_routes.py` 到基线；保留 API-007 只读兜底 |
| T003 | 导入链路引发状态覆盖或回包不兼容 | 临时关闭 `extraction_task_id` 展示路径，导入仅保留 v2.3 主流程 |
| T004 | 异步任务串行化或过滤逻辑异常 | 关闭异步触发开关并回退到手动触发；保留 `ai_suggestions_previous` 作为恢复锚点 |
| T005 | 权限策略误拦截/越权 | 回退到 v2.3 权限判定；只读模式保留前端提示不做写入 |
| T006 | LLM 估算失败率高或数值异常 | 强制 `degraded=true` 回退 `original_estimate`；禁用新注入层仅保留基础上下文 |
| T007 | 快照/diff/聚合落盘异常 | 暂停聚合写入，仅保留快照；开启只读校验避免污染历史数据 |
| T008 | 导入页交互回归（状态丢失/轮询抖动） | 关闭新卡片态管理分支，回退到基线交互并保留导入能力 |
| T009 | 三区布局或只读模式影响操作 | 关闭时间线侧栏与 inline diff 展示开关，保留基础画像编辑能力 |
| T010 | 三点估计展示/导出不一致 | 前端回退显示 `original_estimate`；导出接口降级为无三点估计列 |
| T011 | 回归套件不稳定或证据不完整 | 按任务批次回退新增用例并保留已通过证据，阻断上线 |
| T012 | 部署后关键链路异常 | 执行 L2 版本回滚：`git checkout v2.3 && bash deploy-all.sh`，并按验证清单复测 |
| T013 | 信息展示页交互回归为编辑器体验或系统范围越权显示 | 回退 `SystemProfileBoardPage.js` 与 `systemProfileBoardPage.v24.test.js` 到 CR 前版本并重建前端 |
| T014 | 信息展示页再出现重复域导航标题或域按钮非左对齐 | 回退 `SystemProfileBoardPage.js` 到 CR 前版本并重建前端，恢复原布局后重新评审 |
| T015 | 信息展示页再次出现旧 system_id 请求导致 404 | 回退 `SystemProfileBoardPage.js` 到 T015 前版本并重建前端；恢复后优先排查系统清单 ID 与画像 ID 一致性 |

## 需求反向覆盖矩阵（REQ ↔ Task）
| REQ-ID | 关联任务 |
|---|---|
| REQ-001 | T003, T008 |
| REQ-002 | T002, T009 |
| REQ-003 | T002, T009 |
| REQ-004 | T003, T004, T008, T009 |
| REQ-005 | T004, T008 |
| REQ-006 | T006 |
| REQ-007 | T010 |
| REQ-008 | T010 |
| REQ-009 | T007 |
| REQ-010 | T007 |
| REQ-011 | T005, T009, T013, T014, T015 |
| REQ-012 | T001, T002, T009, T013, T014, T015 |
| REQ-101 | T003, T008, T013, T014 |
| REQ-102 | T002, T004, T009, T012 |
| REQ-103 | T002, T009 |
| REQ-104 | T006, T010 |
| REQ-105 | T007, T012 |
| REQ-106 | T001, T012 |
| REQ-C001 | T003, T008 |
| REQ-C002 | T002, T009 |
| REQ-C003 | T006 |
| REQ-C004 | T005, T009 |
| REQ-C005 | T007 |
| REQ-C006 | T004 |
| REQ-C007 | T001, T009 |

## 场景反向覆盖矩阵（SCN ↔ Task）
| SCN-ID | 关联任务 |
|---|---|
| SCN-V24-01 | T003, T008, T011 |
| SCN-V24-02 | T003, T008, T011 |
| SCN-V24-03 | T004, T005, T008, T011 |
| SCN-V24-04 | T003, T004, T008, T011 |
| SCN-V24-05 | T001, T002, T009, T011, T013, T014, T015 |
| SCN-V24-06 | T001, T002, T009, T011 |
| SCN-V24-07 | T002, T009, T011 |
| SCN-V24-08 | T006, T010, T011 |
| SCN-V24-09 | T006, T010, T011 |
| SCN-V24-10 | T006, T010, T011 |
| SCN-V24-11 | T007, T011, T012 |
| SCN-V24-12 | T005, T009, T011, T013, T014, T015 |

## 接口反向覆盖矩阵（API ↔ Task）
| API-ID | 关联任务 |
|---|---|
| API-001 | T003, T004, T005, T008, T011 |
| API-002 | T003, T008, T011 |
| API-003 | T003, T004, T008, T011 |
| API-004 | T002, T009, T011, T013, T014, T015 |
| API-005 | T002, T005, T009, T011 |
| API-006 | T002, T005, T009, T011 |
| API-007 | T001, T002, T009, T011, T013, T014, T015 |
| API-008 | T001, T002, T005, T009, T011, T013, T014, T015 |
| API-009 | T007, T011 |
| API-010 | T007, T011 |
| API-011 | T006, T010, T011 |
| API-012 | T010, T011 |

## 执行顺序
1. T001 → T002 → T003 → T004（🏁里程碑展示）→ T005
2. T006 → T007
3. T008 → T009（🏁里程碑展示）→ T010
4. T011 → T012
5. T013（CR-20260301-001，diff-only 增量验证）
6. T014（CR-20260302-001，UI 去冗余与左对齐）
7. T015（CR-20260302-002，旧 system_id 容错与当前 ID 优先）

## 里程碑展示点（🏁）
| 任务ID | 展示内容 | 用户确认要点 |
|---|---|---|
| T004 | 异步提取任务串行化 + 多系统过滤通知（后端输出与状态流转） | 同系统并发是否严格串行、非选中系统是否零覆盖 |
| T009 | 画像页三区布局 + inline diff + 回滚按钮 + 只读模式 | 布局方向、交互路径、权限提示是否符合预期 |
| T011 | REQ/REQ-C 覆盖矩阵与关键回归结果 | 证据完整性、失败路径覆盖是否可进入部署准备 |

## 风险与缓解
| 风险 | 影响 | 概率 | 缓解措施 |
|---|---|---|---|
| 旧画像迁移语义偏移 | 画像信息错位、评估上下文失真 | 中 | 迁移映射 + 双读兼容 + 回退演练 |
| DashScope 不稳定 | 估算/提取抖动，联调阻塞 | 中 | 明确降级分支与重试策略，测试覆盖失败路径 |
| 前后端契约再漂移 | 联调反复、验收争议 | 中 | 以 API 契约章节为单一真相，PR 前执行契约一致性检查 |
| REQ-C 回归破坏 | 上线风险高 | 低 | REQ-C 单独覆盖矩阵与强证据门禁 |

## 开放问题
- [x] 已收敛：按后端优先（T001-T007）→ 前端联调（T008-T010）→ 测试与部署收口（T011-T012）执行。

## 变更记录
| 版本 | 日期 | 说明 |
|---|---|---|
| v1.3 | 2026-03-02 | 人工验收通过后收口：计划状态切换为 Completed，Active CR 标记为无 |
| v1.2 | 2026-03-02 | 新增 `CR-20260302-002` 增量任务（T015），补充“旧 system_id 容错 + 当前 ID 优先”实现与验证追溯 |
| v1.1 | 2026-03-02 | 新增 `CR-20260302-001` 增量任务（T014），补充“域标题去冗余 + 导航左对齐”实现与验证追溯 |
| v1.0 | 2026-03-01 | 新增 `CR-20260301-001` 增量任务（T013），回填信息展示页交互一致性修复的验证命令与追溯链路；文档状态切换为 In Progress |
| v0.9 | 2026-03-01 | 计划文档收口：状态更新为 Completed，DoD 全项勾选；与 `status.md` 完成态对齐 |
| v0.8 | 2026-03-01 | 补充 T012 的 STAGING 自动部署执行证据（`printf '2\\n' | bash deploy-all.sh`）与健康检查结果；与 `status.md` 的 `wait_confirm` 状态对齐 |
| v0.7 | 2026-03-01 | T012 状态更新为已完成；新增 `review_implementation.md`/`review_testing.md`/`deployment.md`；补齐 L1 回滚测试与 L2 worktree 演练证据 |
| v0.6 | 2026-03-01 | T010/T011 状态更新为已完成；补齐 T010 三点估计前后端联动验证命令；新增 `docs/v2.4/test_report.md` 并回写 REQ/REQ-C 覆盖矩阵与回归证据 |
| v0.5 | 2026-03-01 | T009 状态更新为已完成；补齐验收勾选（时间线分页/空态、无 previous 禁用回滚）；验证命令补充 `systemProfileBoardPage.v24` + 导航回归双用例证据 |
| v0.2 | 2026-02-28 | 深度走查修复：补齐任务级 `SCN/API` 追溯链与反向覆盖矩阵；新增任务级回滚/开关策略；显式标注 `🏁` 里程碑展示点；修复 T012 非法验证命令（`git checkout --dry-run`） |
| v0.1 | 2026-02-28 | 初始化 v2.4 计划：任务拆解、REQ/REQ-C 反向覆盖矩阵、验证命令与执行顺序 |
