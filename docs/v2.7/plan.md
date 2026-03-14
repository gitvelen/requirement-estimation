# v2.7 任务计划：系统画像域重构、Skill Runtime 与 Memory 资产层

## 文档元信息
| 项 | 值 |
|---|---|
| 状态 | Draft |
| 日期 | 2026-03-14 |
| 版本 | v0.3 |
| 基线版本（对比口径） | `v2.6` |
| Active CR（如有） | 无（回溯记录：`CR-20260314-001`） |
| 关联设计 | `docs/v2.7/design.md` |
| 关联需求 | `docs/v2.7/requirements.md` |
| 关联状态 | `docs/v2.7/status.md` |

## 里程碑
| 里程碑 | 交付物 | 截止日期 |
|---|---|---|
| M1 | v2.7 schema / Runtime 基座 / 核心后端场景（T001-T006） | TBD（进入 Implementation 前确认） |
| M2 | PM / Admin 页面与交互改造（T007） | TBD（进入 Implementation 前确认） |
| M3 | 清理、回归、发布与主文档同步（T008-T009） | TBD（进入 Implementation 前确认） |

说明：当前 Planning 先冻结范围、顺序、验证口径与文件落点；具体日程在进入 Implementation 前与 User 确认。

## Definition of Done（DoD）
- [x] 需求可追溯：每个任务均声明 `REQ/SCN/API/TEST`，并补齐反向覆盖矩阵
- [x] 任务可执行：按“可独立提交 + 可独立验证”拆分，依赖关系明确
- [x] 验证可复现：每个任务都给出命令级验证方式与预期结果
- [x] 安全与合规：权限、输入校验、配置源、敏感信息与旧数据清理均有专门任务
- [x] 文档闭环：Implementation / Testing / Deployment 所需主文档同步入口已落到任务

## 禁止项引用索引（来源：requirements.md REQ-C 章节）
| REQ-C ID | 一句话摘要 |
|---|---|
| REQ-C001 | PM 导入页不得保留历史评估报告和服务治理文档入口 |
| REQ-C002 | 不得保留旧 schema 字段和旧数据残留 |
| REQ-C003 | 自动更新不得覆盖 PM 已确认的 `manual` 内容 |
| REQ-C004 | Skill 与 Memory 必须保持可扩展，不得写死 |
| REQ-C005 | 系统识别必须输出 `final_verdict`，不能只给候选列表 |
| REQ-C006 | 不得破坏现有评估主链路和报告语义 |
| REQ-C007 | 不得新增外部运行时依赖 |
| REQ-C008 | 系统清单导入不得覆盖非空画像 |

## 任务概览
状态标记：`待办` / `进行中` / `已完成`；里程碑标记：`🏁` 表示完成后需先向用户展示阶段成果

| 任务分类 | 任务ID | 任务名称 | 优先级 | 预估工时 | Owner | Reviewer | 关联CR | 关联需求项 | 关联场景（SCN） | 关联接口（API） | 关联测试（TEST） | 任务状态 | 依赖任务ID | 验证方式 | 里程碑 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 后端基础 | T001 | v2.7 canonical schema、Memory/Execution 存储与开关基座 | P0 | 1d | Codex | Codex | - | REQ-002, REQ-007, REQ-011, REQ-012, REQ-101, REQ-104, REQ-105, REQ-C002, REQ-C004, REQ-C007 | SCN-001, SCN-003, SCN-008, SCN-009 | API-003, API-004, API-005, API-009 | TEST-002, TEST-007, TEST-011, TEST-012, TEST-013 | 已完成 | - | `pytest + rg` | M1 |
| 后端基础 | T002 | Skill Runtime、Policy Gate 与 PM 文档导入链路 | P0 | 1.5d | Codex | Codex | - | REQ-001, REQ-005, REQ-006, REQ-009, REQ-011, REQ-103, REQ-C001, REQ-C004 | SCN-001, SCN-004, SCN-008 | API-001, API-002, API-003 | TEST-001, TEST-005, TEST-006, TEST-006A, TEST-009, TEST-011 | 已完成 | T001 | `pytest + rg` | M1 |
| 后端场景 | T003 | 服务治理导入改造为 admin 全局画像联动 | P0 | 1d | Codex | Codex | - | REQ-003, REQ-006, REQ-009, REQ-011, REQ-102, REQ-C003, REQ-C006 | SCN-002, SCN-004, SCN-008 | API-006, API-009 | TEST-003, TEST-006, TEST-007, TEST-009, TEST-011 | 已完成 | T001,T002 | `pytest` | M1 |
| 后端场景 | T004 | 单一系统清单解析、空画像初始化与子系统模型退场 | P0 | 1.5d | Codex | Codex | - | REQ-004, REQ-006, REQ-009, REQ-011, REQ-012, REQ-105, REQ-C002, REQ-C008 | SCN-003, SCN-008, SCN-009 | API-007, API-008 | TEST-004, TEST-006, TEST-011, TEST-012 | 已完成 | T001,T002 | `pytest + rg` | M1 |
| 后端能力 | T005 | Memory 驱动的系统识别与功能点拆解联动 | P0 | 1d | Codex | Codex | - | REQ-007, REQ-008, REQ-010, REQ-011, REQ-104, REQ-C005, REQ-C006 | SCN-006, SCN-007, SCN-008 | API-009 | TEST-007, TEST-008, TEST-010, TEST-011 | 已完成 | T001,T002,T004 | `pytest` | M1 |
| 后端能力 | T006 | `code_scan_skill` 适配层与 Runtime 接入 | P1 | 0.5d | Codex | Codex | - | REQ-005, REQ-006, REQ-009, REQ-103, REQ-C004, REQ-C007 | SCN-004 | -（复用现有 `/api/v1/code-scan/jobs*`） | TEST-005, TEST-006, TEST-013 | 已完成 | T001,T002 | `pytest + rg` | M1🏁 |
| 前端 | T007 | PM/Admin 页面、路由与交互收敛到 v2.7 口径 | P0 | 2d | Codex | Codex | `CR-20260314-001` | REQ-001, REQ-002, REQ-003, REQ-004, REQ-007, REQ-009, REQ-011, REQ-C001, REQ-C008 | SCN-001, SCN-002, SCN-003, SCN-005, SCN-008 | API-001, API-003, API-006, API-008, API-009 | TEST-001, TEST-002, TEST-003, TEST-004, TEST-007, TEST-009, TEST-011 | 已完成 | T002,T003,T004,T005,T006 | `npm test + npm build` | M2🏁 |
| 部署与数据 | T008 | v2.7 清理脚本、开关发布顺序与回滚 Runbook | P1 | 0.5d | Codex | Codex | - | REQ-004, REQ-012, REQ-105, REQ-C002, REQ-C006, REQ-C007 | SCN-003, SCN-009 | API-003, API-008 | TEST-012, TEST-013 | 已完成 | T001,T003,T004,T007 | `pytest + rg` | M3 |
| 测试与证据 | T009 | 全量回归、证据闭环与主文档同步 | P0 | 1d | Codex | Codex | `CR-20260314-001` | REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, REQ-010, REQ-011, REQ-012, REQ-101, REQ-102, REQ-103, REQ-104, REQ-105, REQ-C001, REQ-C002, REQ-C003, REQ-C004, REQ-C005, REQ-C006, REQ-C007, REQ-C008 | SCN-001~SCN-009 | API-001~API-009 | TEST-001~TEST-013 | 已完成 | T001-T008 | `pytest + npm build + rg + api_regression` | M3 |

### 引用自检（🔴 MUST，R6）
```bash
VERSION="v2.7"

# plan 引用的 REQ / REQ-C
rg -o "REQ-C?[0-9]{3}" docs/${VERSION}/plan.md | LC_ALL=C sort -u > /tmp/plan_refs_${VERSION}.txt

# requirements 中定义的 REQ / REQ-C
rg "^#### REQ-C?[0-9]{3}[：:]" docs/${VERSION}/requirements.md | sed 's/^#### //;s/[：:].*$//' | tr -d '\r' | LC_ALL=C sort -u > /tmp/req_defs_${VERSION}.txt

# plan 引用了但 requirements 未定义（期望为空）
LC_ALL=C comm -23 /tmp/plan_refs_${VERSION}.txt /tmp/req_defs_${VERSION}.txt

# requirements 定义了但 plan 未覆盖（期望为空）
LC_ALL=C comm -23 /tmp/req_defs_${VERSION}.txt /tmp/plan_refs_${VERSION}.txt
```

### 阶段反向覆盖门禁（Planning Exit）
```bash
bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_plan_reverse_coverage requirements docs/v2.7/requirements.md plan docs/v2.7/plan.md'
```

## 任务详情

### T001: v2.7 canonical schema、Memory/Execution 存储与开关基座
**分类**：后端基础 / **优先级**：P0 / **预估工时**：1d / **Owner**：Codex / **Reviewer**：Codex
**关联CR**：`CR-20260314-001`
**关联需求项**：REQ-002, REQ-007, REQ-011, REQ-012, REQ-101, REQ-104, REQ-105, REQ-C002, REQ-C004, REQ-C007
**关联场景（SCN）**：SCN-001, SCN-003, SCN-008, SCN-009
**关联接口（API）**：API-003, API-004, API-005, API-009
**关联测试（TEST）**：TEST-002, TEST-007, TEST-011, TEST-012, TEST-013
**任务描述**：
- 将 `backend/service/system_profile_service.py` 从旧 12 子字段/`fields` 结构升级为 `profile_data.<domain>.canonical` 单一口径，并补齐 `field_sources`、`ai_suggestions`。
- 新增 `backend/service/profile_schema_service.py`、`backend/service/memory_service.py`、`backend/service/runtime_execution_service.py`，负责空结构、Memory、execution 索引与 `partial_success`。
- 在 `backend/config/config.py` 与 `.env.backend*` 中补齐 `ENABLE_V27_PROFILE_SCHEMA`、`ENABLE_V27_RUNTIME`、`ENABLE_SERVICE_GOVERNANCE_IMPORT`、`ENABLE_SYSTEM_CATALOG_PROFILE_INIT`，并固定 `.env.backend.internal` 为验收/生产后端配置源。
**影响面/修改范围**：
- `backend/service/system_profile_service.py`
- `backend/service/profile_schema_service.py`
- `backend/service/memory_service.py`
- `backend/service/runtime_execution_service.py`
- `backend/config/config.py`
- `.env.backend`
- `.env.backend.example`
- `.env.backend.internal`
- `tests/test_profile_schema_v27.py`
- `tests/test_memory_service_v27.py`
**验收标准**：
- [ ] 新空画像结构与 design §5.2.1 一致，D1-D5 均带 `canonical.extensions`
- [ ] `memory_records.json`、`runtime_executions.json`、`extraction_tasks.json` 的写入/查询/最新状态索引可独立工作
- [ ] 旧 schema 键不会再被新建或回写
**验证方式**（🔴 MUST，必须可复现）：
- 命令：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_profile_schema_v27.py tests/test_memory_service_v27.py`
- 预期：退出码 0，覆盖空结构、Memory 元模型、execution 状态与 `partial_success`
- 命令：`bash -lc 'if rg -n "\"fields\"|system_scope|module_structure|integration_points|architecture_positioning|key_constraints" backend/service/system_profile_service.py | rg -v "现状|旧 schema|兼容"; then exit 1; fi'`
- 预期：退出码 0，正式实现不再依赖旧 schema 键
**回滚/开关策略（如涉及线上行为变化）**：
- 回滚条件：v2.7 schema 导致画像读写失败或 execution 状态不稳定
- 回滚步骤：关闭 `ENABLE_V27_PROFILE_SCHEMA` / `ENABLE_V27_RUNTIME`，恢复上线前 `system_profiles.json`、`memory_records.json`、`runtime_executions.json` 备份
**依赖**：-

### T002: Skill Runtime、Policy Gate 与 PM 文档导入链路
**分类**：后端基础 / **优先级**：P0 / **预估工时**：1.5d / **Owner**：Codex / **Reviewer**：Codex
**关联CR**：`CR-20260314-001`
**关联需求项**：REQ-001, REQ-005, REQ-006, REQ-009, REQ-011, REQ-103, REQ-C001, REQ-C004
**关联场景（SCN）**：SCN-001, SCN-004, SCN-008
**关联接口（API）**：API-001, API-002, API-003
**关联测试（TEST）**：TEST-001, TEST-005, TEST-006, TEST-006A, TEST-009, TEST-011
**任务描述**：
- 新增 `backend/service/skill_runtime_service.py` 与 `backend/service/document_skill_adapter.py`，落地 Registry、SceneRouter、SceneExecutor、PolicyGate 以及 3 个 PM 文档 skill。
- 修改 `backend/service/profile_summary_service.py` 与 `backend/service/document_parser.py`，统一 `docx` / 文本型 `pdf` / `pptx` 输入边界，并让 `design_skill` 保持保守 `suggestion_only`。
- 修改 `backend/api/system_profile_routes.py`，把 PM 导入允许的 `doc_type` 收敛到 `requirements/design/tech_solution`，并将状态轮询语义迁移到 execution-status。
**影响面/修改范围**：
- `backend/service/skill_runtime_service.py`
- `backend/service/document_skill_adapter.py`
- `backend/service/profile_summary_service.py`
- `backend/service/document_parser.py`
- `backend/api/system_profile_routes.py`
- `tests/test_skill_runtime_service.py`
- `tests/test_system_profile_import_api.py`
- `tests/test_system_profile_routes_helpers.py`
**验收标准**：
- [ ] Runtime 可读取 6 个内置 Skill 的注册定义，且未知/disabled Skill 不会被误执行
- [ ] PM 导入接口只接受三类文档，`history_report` / `esb` / 旧治理类入口全部拒绝
- [ ] 文档类 skill 超出有效性边界时返回显式失败或降级，不伪造高置信 suggestions
**验证方式**（🔴 MUST，必须可复现）：
- 命令：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_skill_runtime_service.py tests/test_system_profile_import_api.py tests/test_system_profile_routes_helpers.py`
- 预期：退出码 0，覆盖注册表、路由、导入 allowlist、execution-status 与失败结果
- 命令：`bash -lc 'if rg -n "history_report|esb_document|knowledge_doc" backend/api/system_profile_routes.py; then exit 1; fi'`
- 预期：退出码 0，PM 导入实现中不再放行旧类型
**回滚/开关策略（如涉及线上行为变化）**：
- 回滚条件：PM 导入链路或 execution-status 兼容性回归
- 回滚步骤：关闭 `ENABLE_V27_RUNTIME`，保留旧 `profile/extraction-status` alias；必要时回退路由改动
**依赖**：T001

### T003: 服务治理导入改造为 admin 全局画像联动
**分类**：后端场景 / **优先级**：P0 / **预估工时**：1d / **Owner**：Codex / **Reviewer**：Codex
**关联CR**：-
**关联需求项**：REQ-003, REQ-006, REQ-009, REQ-011, REQ-102, REQ-C003, REQ-C006
**关联场景（SCN）**：SCN-002, SCN-004, SCN-008
**关联接口（API）**：API-006, API-009
**关联测试（TEST）**：TEST-003, TEST-006, TEST-007, TEST-009, TEST-011
**任务描述**：
- 将 `backend/api/esb_routes.py` 从“单系统 owner/import”语义改为 admin 全局治理导入。
- 新增 `backend/service/service_governance_profile_updater.py`，复用 `backend/service/esb_service.py` 做 exact-name 匹配、D3 canonical 更新、D1/D4 语义提示与 Memory 写回。
- 明确 `manual` 冲突时只跳过冲突字段或建议化，不阻断同系统其他低风险更新。
**影响面/修改范围**：
- `backend/api/esb_routes.py`
- `backend/service/esb_service.py`
- `backend/service/service_governance_profile_updater.py`
- `backend/service/skill_runtime_service.py`
- `tests/test_esb_import_api.py`
- `tests/test_service_governance_import_v27.py`
- `tests/test_esb_service.py`
**验收标准**：
- [ ] `POST /api/v1/esb/imports` 仅 admin 可调用，响应返回 `matched_count/unmatched_count/updated_system_ids`
- [ ] D3 结构化事实默认 `auto_apply`，D1/D4 只进入 `draft_apply` 或 `suggestion_only`
- [ ] 100 条 exact-name 样本的自动匹配成功率可统计且目标为 `>= 95%`
**验证方式**（🔴 MUST，必须可复现）：
- 命令：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_esb_import_api.py tests/test_service_governance_import_v27.py tests/test_esb_service.py`
- 预期：退出码 0，覆盖 admin 权限、匹配统计、D3 更新、manual 冲突与失败态
**回滚/开关策略（如涉及线上行为变化）**：
- 回滚条件：治理导入误更新画像、匹配成功率显著低于目标或阻断主链路
- 回滚步骤：关闭 `ENABLE_SERVICE_GOVERNANCE_IMPORT`，回退 D3 更新与新增 Memory 记录
**依赖**：T001, T002

### T004: 单一系统清单解析、空画像初始化与子系统模型退场
**分类**：后端场景 / **优先级**：P0 / **预估工时**：1.5d / **Owner**：Codex / **Reviewer**：Codex
**关联CR**：-
**关联需求项**：REQ-004, REQ-006, REQ-009, REQ-011, REQ-012, REQ-105, REQ-C002, REQ-C008
**关联场景（SCN）**：SCN-003, SCN-008, SCN-009
**关联接口（API）**：API-007, API-008
**关联测试（TEST）**：TEST-004, TEST-006, TEST-011, TEST-012
**任务描述**：
- 修改 `backend/api/system_list_routes.py` 使 preview/confirm 仅解析单一系统清单，不再要求子系统 sheet 或 `mappings`。
- 新增 `backend/service/system_catalog_profile_initializer.py` 与 `BlankProfileEvaluator`，只在 D1-D5 canonical 全空时按确定性字段写入；`功能描述` 只进 `D1.service_scope`，`关联系统` 只进 `D3.extensions.catalog_related_systems`。
- 移除 `backend/api/subsystem_routes.py` 与 `backend/app.py` 中对子系统模型的继续维护，并让 `backend/agent/system_identification_agent.py` 不再依赖 `subsystem_list.csv`。
**影响面/修改范围**：
- `backend/api/system_list_routes.py`
- `backend/api/subsystem_routes.py`
- `backend/app.py`
- `backend/agent/system_identification_agent.py`
- `backend/service/system_catalog_profile_initializer.py`
- `tests/test_system_list_import.py`
- `tests/test_system_catalog_profile_init_v27.py`
- `tests/test_system_list_unified_source.py`
- `tests/test_system_list_cache_reload.py`
**验收标准**：
- [ ] preview 只校验，不联动画像；confirm 才触发 `scene_id=admin_system_catalog_import`
- [ ] 非空画像统一 `profile_not_blank` 跳过，且不写 `ai_suggestions`
- [ ] 实现与测试中不再存在“主系统/子系统双清单”“子系统映射”作为有效模型
**验证方式**（🔴 MUST，必须可复现）：
- 命令：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_system_list_import.py tests/test_system_catalog_profile_init_v27.py tests/test_system_list_unified_source.py tests/test_system_list_cache_reload.py`
- 预期：退出码 0，覆盖单 sheet 解析、blank evaluator、字段映射、skip reason 与清理后的缓存行为
- 命令：`bash -lc 'if rg -n "子系统清单|子系统映射|mappings_total|mappings_error|subsystem_list.csv" backend tests | rg -v "历史|review|docs/v2.7"; then exit 1; fi'`
- 预期：退出码 0，后端与后端测试中不再保留子系统模型
**回滚/开关策略（如涉及线上行为变化）**：
- 回滚条件：confirm 误更新非空画像或单 sheet 模板解析异常
- 回滚步骤：关闭 `ENABLE_SYSTEM_CATALOG_PROFILE_INIT`，恢复上线前系统清单与画像备份；必要时回退至 v2.6 代码版本
**依赖**：T001, T002

### T005: Memory 驱动的系统识别与功能点拆解联动
**分类**：后端能力 / **优先级**：P0 / **预估工时**：1d / **Owner**：Codex / **Reviewer**：Codex
**关联CR**：-
**关联需求项**：REQ-007, REQ-008, REQ-010, REQ-011, REQ-104, REQ-C005, REQ-C006
**关联场景（SCN）**：SCN-006, SCN-007, SCN-008
**关联接口（API）**：API-009
**关联测试（TEST）**：TEST-007, TEST-008, TEST-010, TEST-011
**任务描述**：
- 为 `backend/agent/system_identification_agent.py` 引入 `DirectDecisionResolver` 与 Memory 上下文读取，强制输出 `final_verdict=matched/ambiguous/unknown`。
- 为 `backend/agent/feature_breakdown_agent.py` 引入 adjustment Memory 读取与写回，并在 `backend/agent/agent_orchestrator.py` / `backend/api/routes.py` 中接入上下文降级与 `partial_success`。
- 保持现有任务评估、报告导出与主链路入口不变。
**影响面/修改范围**：
- `backend/agent/system_identification_agent.py`
- `backend/agent/feature_breakdown_agent.py`
- `backend/agent/agent_orchestrator.py`
- `backend/api/routes.py`
- `backend/service/memory_service.py`
- `tests/test_system_identification_memory_v27.py`
- `tests/test_feature_breakdown_memory_v27.py`
- `tests/test_task_feature_update_actor.py`
- `tests/test_task_modification_compat.py`
**验收标准**：
- [ ] 任一识别结果都包含 `final_verdict`
- [ ] 功能点拆解会读取历史 adjustment Memory，并仅对低风险模式自动应用到当前草稿
- [ ] Memory 读取/写入失败时主链路可降级，但不得伪装为完整成功
**验证方式**（🔴 MUST，必须可复现）：
- 命令：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_system_identification_memory_v27.py tests/test_feature_breakdown_memory_v27.py tests/test_task_feature_update_actor.py tests/test_task_modification_compat.py`
- 预期：退出码 0，覆盖 matched/ambiguous/unknown、adjustment 复用、context_degraded 与 Memory 失败补偿
**回滚/开关策略（如涉及线上行为变化）**：
- 回滚条件：系统识别错误率升高或功能点拆解被新上下文阻断
- 回滚步骤：关闭 `ENABLE_V27_RUNTIME`，保留旧识别/拆解逻辑，恢复仅知识库增强模式
**依赖**：T001, T002, T004

### T006: `code_scan_skill` 适配层与 Runtime 接入
**分类**：后端能力 / **优先级**：P1 / **预估工时**：0.5d / **Owner**：Codex / **Reviewer**：Codex
**关联CR**：-
**关联需求项**：REQ-005, REQ-006, REQ-009, REQ-103, REQ-C004, REQ-C007
**关联场景（SCN）**：SCN-004
**关联接口（API）**：-（复用现有 `/api/v1/code-scan/jobs*`）
**关联测试（TEST）**：TEST-005, TEST-006, TEST-013
**任务描述**：
- 新增 `backend/service/code_scan_skill_adapter.py`，把 `repo_path` / `repo_archive` / 既有作业结果统一转成 Runtime skill 输出。
- 调整 `backend/api/code_scan_routes.py` 与 `backend/service/code_scan_service.py`，让 code scan execution 能被 Runtime 跟踪并写入 `profile_update` Memory（`memory_subtype=code_scan_suggestion`）。
- 保持 Java / Spring Boot + JS / TS 中度语义扫描边界，不新增外部扫描依赖。
**影响面/修改范围**：
- `backend/api/code_scan_routes.py`
- `backend/service/code_scan_service.py`
- `backend/service/code_scan_skill_adapter.py`
- `backend/service/skill_runtime_service.py`
- `tests/test_code_scan_api.py`
- `tests/test_code_scan_skill_v27.py`
**验收标准**：
- [ ] Registry 中 `code_scan_skill` 暴露 `repo_path` / `repo_archive` 双入口
- [ ] code scan 结果只进入 suggestions / breakdown context，不直接覆盖正式画像
- [ ] 运行时依赖清单无新增第三方运行时库
**验证方式**（🔴 MUST，必须可复现）：
- 命令：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_code_scan_api.py tests/test_code_scan_skill_v27.py`
- 预期：退出码 0，覆盖双入口、allowlist、安全解压、suggestion_only 与 execution 跟踪
- 命令：`git diff --unified=0 v2.6 -- pyproject.toml requirements.txt backend/requirements.txt frontend/package.json`
- 预期：不出现新的运行时依赖条目
**里程碑展示（如标注 🏁）**：
- 展示内容：后端 Runtime 的 6 个 Skill 注册定义、5 个核心 Scene 路由结果，以及 code scan 双入口定义
- 确认要点：用户确认 Runtime/Skill 边界、`code_scan_skill` 双入口与 `suggestion_only` 口径后，再进入前端整合
**回滚/开关策略（如涉及线上行为变化）**：
- 回滚条件：code scan runtime 接入影响现有扫描 API 或引入额外依赖
- 回滚步骤：关闭 `ENABLE_V27_RUNTIME` 中 code scan scene 注册，保留原 `/api/v1/code-scan/jobs*` 流程
**依赖**：T001, T002

### T007: PM/Admin 页面、路由与交互收敛到 v2.7 口径
**分类**：前端 / **优先级**：P0 / **预估工时**：2d / **Owner**：Codex / **Reviewer**：Codex
**关联CR**：-
**关联需求项**：REQ-001, REQ-002, REQ-003, REQ-004, REQ-007, REQ-009, REQ-011, REQ-C001, REQ-C008
**关联场景（SCN）**：SCN-001, SCN-002, SCN-003, SCN-005, SCN-008
**关联接口（API）**：API-001, API-003, API-006, API-008, API-009
**关联测试（TEST）**：TEST-001, TEST-002, TEST-003, TEST-004, TEST-007, TEST-009, TEST-011
**任务描述**：
- 修改 `frontend/src/pages/SystemProfileImportPage.js`，只保留三类 PM 文档卡片，删除 `history_report` / `esb` 常量与模板映射，并把轮询切到 `profile/execution-status`。
- 修改 `frontend/src/pages/SystemProfileBoardPage.js` 读取 `profile_data.<domain>.canonical`，保持既有系统TAB/域TAB交互，并收敛前端禁展示项；新增 `frontend/src/pages/ServiceGovernancePage.js` 承载 admin 服务治理页。
- 修改 `frontend/src/pages/SystemListConfigPage.js` / `frontend/src/pages/MainSystemConfigPage.js` / `frontend/src/App.js` / `frontend/src/components/MainLayout.js`，使系统清单页仅保留单一导入视图，不再展示子系统 tab，并新增 `/admin/service-governance` 路由。
**影响面/修改范围**：
- `frontend/src/App.js`
- `frontend/src/components/MainLayout.js`
- `frontend/src/pages/SystemProfileImportPage.js`
- `frontend/src/pages/SystemProfileBoardPage.js`
- `frontend/src/pages/SystemListConfigPage.js`
- `frontend/src/pages/MainSystemConfigPage.js`
- `frontend/src/pages/ServiceGovernancePage.js`
- `frontend/src/__tests__/systemProfileImportPage.render.test.js`
- `frontend/src/__tests__/systemProfileBoardPage.v27.test.js`
- `frontend/src/__tests__/serviceGovernancePage.render.test.js`
- `frontend/src/__tests__/systemListConfigPage.v27.test.js`
- `frontend/src/__tests__/navigationAndPageTitleRegression.test.js`
**验收标准**：
- [ ] PM 导入页只显示 3 类文档，旧类型入口不可见且服务端拒绝
- [ ] 系统画像面板保持既有“系统TAB + 5域TAB”交互，只展示 D1-D5 canonical 与 AI 建议，前端不展示来源/操作人/扩展信息/Memory
- [ ] 系统清单页不再出现主/子系统双 tab，confirm 结果区展示已更新系统名称、预检错误与用户可读跳过原因
- [ ] 页面级改动都具备首屏渲染 smoke 证据
**验证方式**（🔴 MUST，必须可复现）：
- 命令：`cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileImportPage.render.test.js src/__tests__/systemProfileBoardPage.v27.test.js src/__tests__/serviceGovernancePage.render.test.js src/__tests__/systemListConfigPage.v27.test.js src/__tests__/navigationAndPageTitleRegression.test.js`
- 预期：退出码 0，覆盖首屏渲染、角色路由、单 tab 系统清单、PM 三类导入、结果区用户可读化与导航回归
- 命令：`cd frontend && npm run build`
- 预期：退出码 0，前端可构建，无首屏渲染阻断项
**里程碑展示（如标注 🏁）**：
- 展示内容：PM 导入页、系统画像面板、admin 服务治理页、单 tab 系统清单页的真实界面与关键交互
- 确认要点：用户确认页面信息架构、文案、结果区字段与禁展示项均保持收敛后，再进入清理与全量回归
**回滚/开关策略（如涉及线上行为变化）**：
- 回滚条件：页面首屏崩溃、权限路由错误或系统清单页面信息架构不符合 v2.7
- 回滚步骤：前端回退至 v2.6 构建；后端保留 alias 和关闭相关开关
**依赖**：T002, T003, T004, T005, T006

### T008: v2.7 清理脚本、开关发布顺序与回滚 Runbook
**分类**：部署与数据 / **优先级**：P1 / **预估工时**：0.5d / **Owner**：Codex / **Reviewer**：Codex
**关联CR**：`CR-20260314-001`
**关联需求项**：REQ-004, REQ-012, REQ-105, REQ-C002, REQ-C006, REQ-C007
**关联场景（SCN）**：SCN-003, SCN-009
**关联接口（API）**：API-003, API-008
**关联测试（TEST）**：TEST-012, TEST-013
**任务描述**：
- 新增 `scripts/cleanup_v27_profile_assets.py`，清理旧 schema 画像、历史评估报告相关知识/导入数据，并输出可核验结果。
- 编写 `docs/v2.7/deployment.md`，固定开关打开顺序：`ENABLE_V27_PROFILE_SCHEMA` → `ENABLE_V27_RUNTIME` → `ENABLE_SERVICE_GOVERNANCE_IMPORT` → `ENABLE_SYSTEM_CATALOG_PROFILE_INIT`。
- 同步 `docs/技术方案设计.md`、`docs/接口文档.md`、`docs/部署记录.md` 的 v2.7 口径，尤其 `.env.backend.internal`、兼容 alias 与回滚步骤。
- 评估并同步 `docs/系统功能说明书.md`、`docs/用户手册.md`；若判定本期不适用，需在 `docs/v2.7/status.md` 留下明确结论，而不是保持悬空勾选。
**影响面/修改范围**：
- `scripts/cleanup_v27_profile_assets.py`
- `docs/v2.7/deployment.md`
- `docs/v2.7/status.md`
- `docs/系统功能说明书.md`
- `docs/用户手册.md`
- `docs/技术方案设计.md`
- `docs/接口文档.md`
- `docs/部署记录.md`
- `tests/test_cleanup_v27.py`
- `tests/test_deploy_backend_internal_script.py`
- `tests/test_deploy_frontend_internal_script.py`
**验收标准**：
- [ ] 清理脚本可证明旧 schema 与历史评估报告残留为 0
- [ ] Runbook 明确开关顺序、备份路径、回滚路径与 `.env.backend.internal` 配置源
- [ ] 主文档同步范围与 status 清单一致
**验证方式**（🔴 MUST，必须可复现）：
- 命令：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_cleanup_v27.py tests/test_deploy_backend_internal_script.py tests/test_deploy_frontend_internal_script.py`
- 预期：退出码 0，覆盖清理、内部环境部署脚本与回滚要点
- 命令：`rg -n "\\.env\\.backend\\.internal|ENABLE_V27_PROFILE_SCHEMA|ENABLE_V27_RUNTIME|ENABLE_SERVICE_GOVERNANCE_IMPORT|ENABLE_SYSTEM_CATALOG_PROFILE_INIT|profile/execution-status|profile/extraction-status" docs/v2.7/deployment.md docs/技术方案设计.md docs/接口文档.md docs/部署记录.md docs/v2.7/status.md`
- 预期：退出码 0，关键配置、接口、回滚说明和文档同步结论都已落盘
**回滚/开关策略（如涉及线上行为变化）**：
- 回滚条件：STAGING/TEST 中出现画像污染、Memory 写失败或主链路阻断
- 回滚步骤：按 Runbook 顺序关闭四个开关并恢复上线前数据备份；必要时回退到 `v2.6`
**依赖**：T001, T003, T004, T007

### T009: 全量回归、证据闭环与主文档同步
**分类**：测试与证据 / **优先级**：P0 / **预估工时**：1d / **Owner**：Codex / **Reviewer**：Codex
**关联CR**：-
**关联需求项**：REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, REQ-010, REQ-011, REQ-012, REQ-101, REQ-102, REQ-103, REQ-104, REQ-105, REQ-C001, REQ-C002, REQ-C003, REQ-C004, REQ-C005, REQ-C006, REQ-C007, REQ-C008
**关联场景（SCN）**：SCN-001~SCN-009
**关联接口（API）**：API-001~API-009
**关联测试（TEST）**：TEST-001~TEST-013
**任务描述**：
- 汇总并执行 v2.7 的后端、前端、静态检查、接口回归与部署 smoke，产出 `docs/v2.7/test_report.md`。
- 在 `docs/v2.7/review_implementation.md`、`docs/v2.7/review_testing.md`、`docs/v2.7/status.md` 中沉淀结论与证据链，补齐回溯 CR `CR-20260314-001`，确保后续阶段门禁可复现。
- 追加 `docs/v2.7/implementation_checklist.md`，显式列出 T001-T009 的执行顺序与里程碑暂停点。
**影响面/修改范围**：
- `docs/v2.7/test_report.md`
- `docs/v2.7/review_implementation.md`
- `docs/v2.7/review_testing.md`
- `docs/v2.7/implementation_checklist.md`
- `docs/v2.7/status.md`
- `scripts/api_regression.sh`
**验收标准**：
- [ ] TEST-001~TEST-013 均有对应命令与证据
- [ ] 项目级 `pytest`、前端 build、关键 API 回归和依赖 diff 均通过
- [ ] review / test_report / deployment / status 之间不存在口径漂移
**验证方式**（🔴 MUST，必须可复现）：
- 命令：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q --tb=short`
- 预期：退出码 0，全项目 Python 回归通过
- 命令：`cd frontend && npm run build`
- 预期：退出码 0，前端构建通过
- 命令：`bash scripts/api_regression.sh`
- 预期：退出码 0，关键 API 回归通过
- 命令：`git diff --unified=0 v2.6 -- pyproject.toml requirements.txt backend/requirements.txt frontend/package.json`
- 预期：不出现新增运行时依赖条目
**回滚/开关策略（如涉及线上行为变化）**：
- 回滚条件：任一 P0/P1 阻断未收敛、证据链断裂或部署 smoke 失败
- 回滚步骤：冻结进入 Deployment，按 review 结论回修后重新执行 T009
**依赖**：T001-T008

## 任务关联 REQ/覆盖矩阵
| REQ-ID | 关联任务 | 关联场景（SCN） | 关联接口（API） | 关联测试（TEST） | 计划验证 |
|---|---|---|---|---|---|
| REQ-001 | T002, T007, T009 | SCN-001, SCN-004, SCN-008 | API-001, API-002, API-003 | TEST-001, TEST-005, TEST-011 | `tests/test_skill_runtime_service.py`, `tests/test_system_profile_import_api.py`, 前端渲染测试 |
| REQ-002 | T001, T007, T009 | SCN-001, SCN-005 | API-004, API-005, API-009 | TEST-002 | `tests/test_profile_schema_v27.py`, `frontend/src/__tests__/systemProfileBoardPage.v27.test.js` |
| REQ-003 | T003, T007, T009 | SCN-002, SCN-004 | API-006, API-009 | TEST-003, TEST-007, TEST-009 | `tests/test_service_governance_import_v27.py`, 服务治理页渲染/回读 |
| REQ-004 | T004, T007, T008, T009 | SCN-003, SCN-009 | API-007, API-008 | TEST-004, TEST-012 | `tests/test_system_catalog_profile_init_v27.py`, `scripts/cleanup_v27_profile_assets.py` |
| REQ-005 | T002, T006, T009 | SCN-004 | API-001, API-003 | TEST-005 | `tests/test_skill_runtime_service.py`, `tests/test_code_scan_skill_v27.py` |
| REQ-006 | T002, T003, T004, T006, T009 | SCN-001, SCN-002, SCN-003, SCN-004 | API-001, API-006, API-007, API-008 | TEST-006, TEST-006A | 文档/治理/系统清单 canonical 化测试 |
| REQ-007 | T001, T005, T007, T009 | SCN-001, SCN-002, SCN-003, SCN-006, SCN-007 | API-009 | TEST-007 | `tests/test_memory_service_v27.py`, `tests/test_system_identification_memory_v27.py` |
| REQ-008 | T005, T009 | SCN-006 | API-009 | TEST-008 | `tests/test_system_identification_memory_v27.py` |
| REQ-009 | T002, T003, T004, T006, T007, T009 | SCN-002, SCN-003, SCN-005 | API-001, API-006, API-008 | TEST-009 | PolicyGate / 页面建议区 / skip 逻辑测试 |
| REQ-010 | T005, T009 | SCN-007 | API-009 | TEST-010 | `tests/test_feature_breakdown_memory_v27.py` |
| REQ-011 | T001, T002, T003, T004, T005, T006, T007, T009 | SCN-001, SCN-002, SCN-003, SCN-006, SCN-007, SCN-008 | API-001, API-003, API-006, API-008, API-009 | TEST-011 | 失败注入与 `partial_success` 测试 |
| REQ-012 | T001, T004, T008, T009 | SCN-003, SCN-009 | API-008 | TEST-012 | 清理脚本、备份恢复与旧字段残留检查 |
| REQ-101 | T001, T007, T009 | SCN-001, SCN-005 | API-004, API-005 | TEST-002 | schema 键对比、前端字段常量与回读一致性 |
| REQ-102 | T003, T009 | SCN-002 | API-006 | TEST-003 | 100 条治理样本导入统计 |
| REQ-103 | T002, T006, T009 | SCN-004 | API-001, API-003 | TEST-005 | Skill 注册表与 Scene 路由矩阵 |
| REQ-104 | T001, T005, T009 | SCN-006, SCN-007 | API-009 | TEST-007, TEST-010 | Memory 覆盖率统计 |
| REQ-105 | T001, T004, T008, T009 | SCN-009 | API-008 | TEST-012 | 清理结果核验与备份恢复演练 |
| REQ-C001 | T002, T007, T009 | SCN-001 | API-001 | TEST-001 | PM 导入页旧类型入口删除 + API 负向校验 |
| REQ-C002 | T001, T004, T008, T009 | SCN-003, SCN-009 | API-008 | TEST-012 | 旧 schema / 子系统模型 / 历史报告残留清理 |
| REQ-C003 | T003, T004, T007, T009 | SCN-002, SCN-003, SCN-005 | API-004, API-006, API-008 | TEST-009 | `manual` 冲突跳过或建议化 |
| REQ-C004 | T001, T002, T006, T009 | SCN-004 | API-001, API-003 | TEST-005 | Registry 支持 disabled future skill，Memory 元模型支持 future type |
| REQ-C005 | T005, T009 | SCN-006 | API-009 | TEST-008 | `final_verdict` 强校验 |
| REQ-C006 | T003, T005, T008, T009 | SCN-002, SCN-006, SCN-009 | API-003, API-006, API-008 | TEST-011, TEST-012 | 评估主链路回归 + 发布/回滚 runbook |
| REQ-C007 | T001, T006, T008, T009 | SCN-004, SCN-009 | - | TEST-013 | 依赖 diff 与配置口径检查 |
| REQ-C008 | T004, T007, T009 | SCN-003 | API-008 | TEST-004 | 非空画像 skip + 页面结果区核验 |

## 执行顺序
1. T001 → T002
2. T003 与 T004 可并行，均依赖 T001/T002
3. T005 依赖 T001/T002/T004；T006 依赖 T001/T002
4. T007 依赖 T002~T006
5. T008 依赖 T001/T003/T004/T007
6. T009 依赖 T001~T008

## 风险与缓解
| 风险 | 影响 | 概率 | 缓解措施 |
|---|---|---|---|
| 旧 `system_profile_service` 与前端面板同时切 schema，容易出现字段漂移 | 页面渲染错误、保存回读不一致 | 中 | T001/T007 以前后端共享 canonical 常量、schema 回读测试与首屏 smoke 联动兜底 |
| 单一系统清单模型退场不彻底 | 代码仍残留子系统路径，导致模板解析或系统识别口径分裂 | 中 | T004 强制删除子系统实现路径，并用 `rg` 做残留搜索 |
| `design_skill` 缺少真实样本 | 设计文档 suggestions 质量不稳定 | 中 | T002 保持 `suggestion_only`，并在测试中验证超边界时显式降级 |
| Memory 与 execution 文件增长过快 | 查询变慢、失败恢复复杂 | 中 | T001 设计分页与 latest index，T009 再用覆盖率和 smoke 校验 |
| 服务治理 / 系统清单自动更新误触 `manual` 或非空画像 | 画像污染 | 低 | T003/T004 用 PolicyGate、BlankProfileEvaluator 和 E2E 证据双重兜底 |

## 开放问题
- [ ] 里程碑日期待进入 Implementation 前与 User 最终确认；不影响当前任务拆分、依赖和验证口径

## 变更记录
| 版本 | 日期 | 说明 |
|---|---|---|
| v0.1 | 2026-03-13 | 初始化 v2.7 Planning 首版任务拆解，覆盖 Runtime、schema、服务治理、系统清单、Memory、前端改造、清理发布与全量回归 |
| v0.2 | 2026-03-14 | 回填 Testing 阶段前端可读性/交互回归收敛的回溯 CR `CR-20260314-001`，并修正 T007/T009 的验收口径为用户可读展示边界 |
| v0.3 | 2026-03-14 | 回填 `REQ-003/REQ-004` 人工 E2E 通过结果，并将 T009 同步为已完成 |
