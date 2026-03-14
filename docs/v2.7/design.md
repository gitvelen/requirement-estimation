# v2.7 技术方案设计：系统画像域重构、Skill Runtime 与 Memory 资产层

| 项 | 值 |
|---|---|
| 状态 | Draft |
| 作者 | Codex |
| 评审 | Codex |
| 日期 | 2026-03-13 |
| 版本号 | `v2.7` |
| 关联提案 | `docs/v2.7/proposal.md` v0.6 |
| 关联需求 | `docs/v2.7/requirements.md` v0.13 |
| 关联主文档 | `docs/技术方案设计.md` |
| 关联接口 | `docs/接口文档.md` |

---

## 0. 摘要（Executive Summary）

v2.7 采用“单体内模块化 Runtime + 文件存储 Memory + 前后端统一 canonical schema”的方案，在现有 FastAPI + React + 单机 Docker Compose 架构内完成以下收敛：1）PM 导入页收敛为 3 类文档；2）系统画像升级为 5 域 24 个 canonical 字段；3）管理员服务治理导入改为全局批量更新 D3，并按策略处理 D1/D4 语义影响；4）系统清单 confirm 后仅对首次初始化或空画像目标执行初始化写入，非空画像严格跳过；5）系统识别与功能点拆解都改为先读画像与 Memory，再做 Direct Decision / LLM 补强；6）所有范围内成功动作都必须沉淀 Memory。

本设计不新增外部运行时依赖，不拆独立服务，不改现有评估主链路入口。实现上复用现有 `profile_summary_service`、`esb_service`、`system_profile_service`、系统清单导入链路与 `system_identification_agent` / `feature_breakdown_agent`，在其上新增 Runtime 编排层、Policy Gate、MemoryService、空画像判定器与新 schema 适配层。对外接口以最小必要变更为原则，新增 `profile/execution-status` 与 `memory` 查询能力，同时保留 `profile/extraction-status` 兼容别名，保证前端可以逐步切换。

## 0.5 决策记录（Design 前置收集结果）

### 技术决策

| 编号 | 决策项 | 用户选择 | 理由/备注 |
|------|--------|---------|----------|
| D-01 | 后端架构 | 沿用 FastAPI 单体，在进程内新增模块化 Runtime | 满足 REQ-C006 / REQ-C007；复用现有服务，改造成本最低 |
| D-02 | 前端架构 | 沿用 React 管理端，改造现有画像页并新增 admin 服务治理页 | 复用权限、路由和组件体系 |
| D-03 | 存储形态 | 继续使用 JSON 文件 + 文件锁 + 原子写 | 与现有 `system_profiles.json` / `import_history.json` 模式一致 |
| D-04 | 画像 canonical 结构 | `profile_data.<domain>.canonical` 作为唯一正式口径 | 满足“空画像只看 canonical”与前后端单一 schema 要求 |
| D-05 | Memory 资产层 | 新增 `memory_records.json`，按 `system_id -> records[]` 组织 | 满足 REQ-007 / REQ-C004，兼容未来类型 |
| D-06 | Runtime 执行记录 | 新增 `runtime_executions.json`，保留 `extraction_tasks.json` 作为最新状态索引 | 满足 execution-status / 审计 / partial_success 场景 |
| D-07 | PM 文档 Skill 实现 | 复用 `profile_summary_service` 的文档解析与 LLM 提取能力，由 `requirements_skill` / `design_skill` / `tech_solution_skill` 适配输出 | 降低重写成本，保持 v2.6 Token 感知分块方案 |
| D-08 | 服务治理 Skill 实现 | 复用 `esb_service` 的模板识别、列名别名解析和系统匹配能力 | 满足 REQ-006 / REQ-102 |
| D-09 | 系统清单联动策略 | confirm 后仅对空画像执行 deterministic 初始化；非空画像统一 `reject/skip`，不写 `ai_suggestions` | 严格落实用户最新决策与 REQ-C008 |
| D-10 | 系统识别策略 | 新增 DirectDecisionResolver，先做别名/稳定映射判定，再进入 LLM 补强 | 满足 REQ-008 / REQ-C005 |
| D-11 | 发布兼容策略 | 保留现有主链路与旧 `profile/extraction-status` 兼容别名；新增接口以 v2.7 契约为准 | 避免一次性切断现有前端和任务流程 |
| D-12 | `code_scan_skill` 实现 | 复用现有 `code_scan_routes.py` / `code_scan_service.py`，通过 `CodeScanSkillAdapter` 统一 `repo_path` 与压缩包双入口，执行 Java/Spring Boot + JS/TS 中度语义扫描 | 满足 REQ-005 / REQ-006 / REQ-103 |
| D-13 | 系统清单字段映射 | 仅把高确定性字段写入 D1/D4 canonical；弱证据落 `extensions`；责任台账字段不进画像 | 满足 REQ-004 / REQ-009 / REQ-C008 |
| D-14 | 外部依赖 | 不新增外部运行时依赖 | 满足 REQ-C007 |

### 环境配置

| 配置项 | 开发环境 | 验收环境（STAGING/TEST） | 生产环境 | 敏感 | 备注 |
|--------|---------|-------------------------|---------|------|------|
| 部署形态 | Docker Compose 单机 | Docker Compose 单机 | Docker Compose 单机 | 否 | 与主文档一致 |
| 后端配置源 | `.env.backend` / `.env.backend.example` | `.env.backend.internal` | `.env.backend.internal` | 是 | 验收与生产均为内网后端配置源 |
| 前端配置源 | `.env.frontend` / `.env.frontend.example` | 内网前端部署配置（基于 `.env.frontend` 模板） | 内网前端部署配置（基于 `.env.frontend` 模板） | 否 | 前端地址/代理随内网部署覆盖 |
| 后端服务 | `backend:8000` | `backend:8000` | `backend:8000` | 否 | FastAPI |
| 前端服务 | `frontend:80` | `frontend:80` | `frontend:80` | 否 | React + Nginx |
| 画像存储 | `data/system_profiles.json` | `data/system_profiles.json` | `data/system_profiles.json` | 否 | v2.7 schema |
| Memory 存储 | `data/memory_records.json` | `data/memory_records.json` | `data/memory_records.json` | 否 | 新增 |
| Runtime 执行存储 | `data/runtime_executions.json` | `data/runtime_executions.json` | `data/runtime_executions.json` | 否 | 新增 |
| 最新执行状态索引 | `data/extraction_tasks.json` | `data/extraction_tasks.json` | `data/extraction_tasks.json` | 否 | 语义升级为 execution-status |
| LLM/Embedding 模型口径 | `Qwen3-32B` / `Qwen3-Embedding-8B` | 同 DEV | 同 DEV | 否 | 需求目标口径，不等同于配置文件路径 |
| 功能开关 | `.env.backend` | `.env.backend.internal` | `.env.backend.internal` | 否 | 见 §5.6 |

## 1. 背景、目标、非目标与约束

### 1.1 背景与问题

- 当前 PM 导入页仍保留 `history_report`、`esb` 等旧入口，与 v2.7 需求冲突。
- 当前 `system_profile_service` 仍以旧 5 域 12 子字段与 `fields` 派生结构为主，不能满足 v2.7 画像粒度与 canonical 口径。
- 当前 `POST /api/v1/system-list/batch-import/confirm` 只负责写系统清单主台账，没有 Runtime、空画像判定、Memory 写回与 skip reason。
- 当前 `POST /api/v1/esb/imports` 仍是“单系统导入 + 触发画像总结”的旧行为，不是管理员全局服务治理联动。
- 当前系统识别链路只返回 `selected_systems / candidate_systems / maybe_systems / questions`，没有 `final_verdict`，也没有读取 Memory 的 Direct Decision。
- 当前功能点拆解虽然能读 `system_profile` 知识，但没有结构化 Memory 资产输入，也不会沉淀 PM 修改分类。

### 1.2 目标（Goals，可验收）

- G1：输出一套可实现的 v2.7 canonical 画像结构，前后端字段键完全一致，对应 REQ-002 / REQ-101。
- G2：交付 Skill Runtime 基础设施与 6 个内置 Skill，满足场景路由、执行、策略和 Memory 写回，对应 REQ-005 / REQ-103。
- G3：让管理员服务治理导入与系统清单 confirm 都进入受控画像联动链路，对应 REQ-003 / REQ-004 / REQ-009 / REQ-C008。
- G4：让系统识别和功能点拆解都真正使用画像与 Memory，并输出直接判定/分类沉淀，对应 REQ-007 / REQ-008 / REQ-010 / REQ-104。
- G5：在不破坏现有评估主链路、不新增外部依赖的前提下完成上述改造，对应 REQ-C006 / REQ-C007。

### 1.3 非目标（Non-Goals）

- 不拆分独立 Runtime 服务、消息队列或数据库。
- 不引入新的角色模型、资源级 ACL 或手动映射治理界面。
- 不做旧 schema 到新 schema 的兼容迁移层；按需求执行清理与重建。
- 不在 v2.7 实现通用会话式 Codex UI，仅实现后台 Runtime 思路。

### 1.4 关键约束（Constraints）

- C1：模型口径固定为 `Qwen3-32B` / `Qwen3-Embedding-8B`。
- C2：不得新增外部运行时依赖，必须复用现有解析、Embedding、向量与文件存储能力。
- C3：自动更新不能覆盖 `manual` 来源字段。
- C4：系统清单月度更新或覆盖导入时，非空画像必须严格跳过，且不进入 PM 建议流。
- C5：新增 API 必须写清路径、参数、响应、权限和错误码。
- C6：现有任务评估与报告语义保持兼容。

### 1.5 关键假设（Assumptions）

| 假设 | 可验证方式 | 失效影响 | 兜底策略 |
|---|---|---|---|
| 现有 `profile_summary_service` 可被 Skill 适配层复用 | 代码走查 + 后续集成测试 | PM 文档 Skill 需要重写 LLM 提取链路 | 在 Runtime 中保留适配接口，必要时替换实现，不改 Scene 契约 |
| 文件存储规模可覆盖 v2.7 范围内的导入量 | 压测 `runtime_executions.json` / `memory_records.json` 读写 | 大批量导入耗时升高 | 保留按 `system_id` 分片和后续落库扩展点 |
| 系统清单仍是标准系统名称单一真相源 | preview/confirm 校验 + 名称一致性统计 | 服务治理匹配成功率下降 | 结果中显式输出 unmatched，不做手工映射 |
| 当前评估主链路允许在识别/拆解阶段注入额外上下文 | 代码走查 `agent_orchestrator.py` / 相关 API | 需要更大范围改造任务 API | 先以包装器方式注入，不改任务外部契约 |

## 2. 需求对齐与验收口径（Traceability）

### 2.1 需求-设计追溯矩阵（必须）

<!-- TRACE-MATRIX-BEGIN -->
| REQ-ID | 需求摘要 | 设计落点（章节/模块/API/表） | 验收方式/证据 |
|---|---|---|---|
| REQ-001 | PM 导入页仅保留三类文档 | §5.4 API-001、§5.10 页面设计、`SkillRegistry` | 前端渲染测试 + 接口 allowlist 测试 |
| REQ-002 | 5 域细粒度画像结构 | §5.2.1 `system_profiles.json` schema、§5.10 画像面板 | 空画像读取与保存回读测试 |
| REQ-003 | 服务治理导入联动画像 | §5.1 `ServiceGovernanceProfileUpdater`、§5.3.2、API-006 | E2E 导入结果与 D3 回读 |
| REQ-004 | 系统清单 confirm 后仅初始化/补空 | §5.1 `SystemCatalogProfileInitializer`、§5.2.4 空画像算法、§5.3.3、API-008 | preview/confirm E2E + skip reason 校验 |
| REQ-005 | Skill Runtime 平台 | §4.2 架构、§5.1 运行时模块、§5.5 场景执行模式 | 路由矩阵测试 + Registry 查询测试 |
| REQ-006 | 多格式输入兼容与 canonical 化 | §5.1 Skill 适配层、§5.2 canonical schema、§5.3 流程 | 多模板输入对比测试 |
| REQ-007 | Per-System Memory 资产层 | §5.1 `MemoryService`、§5.2.2 `memory_records.json`、API-009 | Memory 写入/查询测试 |
| REQ-008 | 系统识别直接判定 | §5.1 `DirectDecisionResolver`、§5.3.4、§5.4 API-010（内部链路契约） | verdict 测试 + Memory 回写测试 |
| REQ-009 | 场景化更新策略 | §5.1 `PolicyGate`、§5.3.1~§5.3.5、§5.6 Feature Flags | policy matrix 测试 |
| REQ-010 | 功能点拆解读写 Memory | §5.1 `FeatureAdjustmentMemoryAdapter`、§5.3.5 | 拆解上下文与调整 Memory 测试 |
| REQ-011 | 失败结果可判定 | §5.3 异常路径、§5.4 错误码、§5.7 可观测性 | partial_success / failed 测试 |
| REQ-012 | 旧 schema 与历史评估数据清理 | §6.1.2 部署步骤、§6.1.3 回滚、§7.1 TEST-012 | 清理脚本与核验命令 |
| REQ-101 | 画像字段总数 ≥ 20 | §5.2.1 canonical 字段定义 | schema 键计数与前后端一致性比对 |
| REQ-102 | 服务治理匹配成功率 ≥ 95% | §5.3.2 匹配策略、§5.7 指标 | 样本导入统计 |
| REQ-103 | 6 个 Skill 与场景路由全部通过 | §5.1 Scene/Skill 矩阵、§7.1 TEST-103 | Skill 与 Scene 测试 |
| REQ-104 | 三类 Memory 写入覆盖率 100% | §5.2.2 Memory 模型、§5.3.1~§5.3.5 | Memory 覆盖率统计 |
| REQ-105 | 旧数据清理结果可核验 | §6.1.2/§6.1.3、§7.1 TEST-105 | 文件/知识数据清理核验 |
| REQ-C001 | PM 导入页不得保留旧入口 | §5.4 API-001 allowlist、§5.10 页面设计 | UI/接口双向校验 |
| REQ-C002 | 禁止残留旧 schema 与旧数据 | §5.2.1 新 schema、§6.1.2 清理 | schema 搜索 + 数据清理核验 |
| REQ-C003 | `manual` 优先 | §5.1 `PolicyGate`、§5.2.3 `field_sources`、§5.3 流程 | 冲突字段跳过/建议化测试 |
| REQ-C004 | Skill / Memory 必须可扩展 | §5.1 `SkillRegistry` / `MemoryService`、§5.2.2 通用元模型 | disabled Skill / future memory type 测试 |
| REQ-C005 | 系统识别不能只有候选列表 | §5.3.4 verdict 算法、内部识别结果契约 | `final_verdict` 强校验 |
| REQ-C006 | 不破坏现有评估主链路 | §4.3 影响面、§6.1.1 兼容策略、§7.1 回归测试 | 主链路回归测试 |
| REQ-C007 | 不新增外部依赖 | §3.3 依赖评估、§5.6 配置 | 依赖 diff 检查 |
| REQ-C008 | 系统清单不得覆盖非空画像 | §5.2.4 空画像算法、§5.3.3、API-008 | 非空画像 skip 测试 |
<!-- TRACE-MATRIX-END -->

### 2.2 质量属性与典型场景（Quality Scenarios）

| Q-ID | 质量属性 | 场景描述 | 目标/阈值 | 验证方式 |
|---|---|---|---|---|
| Q-01 | 正确性 | 系统清单 confirm 命中已有内容画像 | 非空 canonical 画像 100% 跳过，且不写 `ai_suggestions` | E2E confirm 测试 |
| Q-02 | 可追溯性 | 任一成功画像更新动作 | 必须生成 1 条 `profile_update` Memory 与 1 条 execution 记录 | API 查询 + 文件核验 |
| Q-03 | 鲁棒性 | Runtime 成功但 Memory 写入失败 | 返回 `partial_success`，禁止返回纯 `success` | 集成测试 |
| Q-04 | 兼容性 | 现有任务创建到报告导出主链路 | 全链路可完成，入口与角色不变 | 回归测试 |
| Q-05 | 性能 | 100 条系统清单 confirm 批量初始化 | 单次 confirm 在 STAGING 内可在 10 秒内返回结果摘要 | 压测样本 |
| Q-06 | 安全性 | manager 尝试访问 admin 服务治理或系统清单接口 | 100% 返回 403 / `AUTH_001` | 权限测试 |

## 3. 现状分析与方案选型（Options & Trade-offs）

### 3.1 现状与问题定位

- `frontend/src/pages/SystemProfileImportPage.js` 仍保留 `history_report` 与 `esb` 常量，页面职责与 v2.7 不一致。
- `frontend/src/pages/SystemProfileBoardPage.js` 仍基于 v2.4/v2.5 的 12 子字段结构，不能展示 24 个 canonical 字段。
- `backend/service/system_profile_service.py` 目前空结构仍是旧字段：`system_description`、`module_structure`、`integration_points`、`architecture_positioning` 等。
- `system_profile_routes.py` 现有导入链路本质是“文档入知识库 -> 触发 summary”，没有 Runtime 概念，没有 `profile/execution-status`，也没有系统 Memory API。
- `esb_routes.py` 当前要求 `system_id` 且允许 manager/admin 调用，不符合管理员全局治理场景。
- `system_list_routes.py` 的 confirm 目前只写系统清单，不区分首次初始化/后续补空，也不返回画像联动详情。
- `backend/agent/system_identification_agent.py` 当前缺少 `final_verdict` 直接判定逻辑。
- `backend/agent/feature_breakdown_agent.py` 当前只读 `system_profile` 知识，不读 Memory，也不回写分类经验。

### 3.2 方案候选与对比（至少 2 个）

| 方案 | 核心思路 | 优点 | 缺点/风险 | 成本 | 结论 |
|---|---|---|---|---|---|
| A | 在现有 FastAPI 单体内新增 `Runtime + Policy + Memory` 模块，继续使用 JSON 文件存储；复用现有解析/LLM/系统画像服务 | 改造面可控；不新增依赖；满足当前部署约束；可逐步接入现有 agent/service | 文件存储查询效率一般；需要清理旧 schema；需要补 execution/memory 索引 | 中 | 采用 |
| B | 拆出独立 Runtime 服务，引入任务队列与数据库存储 Memory/执行记录 | 运行时解耦，长远扩展更强 | 违反“不新增外部依赖/部署复杂度上升”；当前阶段返工过大；发布/回滚成本高 | 高 | 不采用 |

### 3.3 关键技术选型与新增依赖评估

| 组件/依赖 | 选型 | 理由 | 替代方案 | 维护状态 | 安全评估 | 移除/替换成本 | 风险/备注 |
|---|---|---|---|---|---|---|---|
| Runtime 编排 | 仓内 Python 模块 | 无外部依赖，满足 REQ-C007 | 独立服务/队列 | 自研 | 低 | 中 | 需要补充分层测试 |
| Skill Registry | Python 常量 + dataclass/Pydantic 模型 | 无配置中心依赖，易于追溯 | JSON/YAML 文件 | 自研 | 低 | 低 | 先不做动态热加载 |
| Memory 存储 | `memory_records.json` + 文件锁 | 与现有风格一致 | SQLite/DB | 自研 | 低 | 中 | 规模上限要在 §5.9 说明 |
| Execution 存储 | `runtime_executions.json` + `extraction_tasks.json` 索引 | 能满足 execution-status / 历史查询 | 队列表/DB | 自研 | 低 | 中 | 按 `system_id` 分片读取 |
| 文档 Skill 引擎 | 复用 `profile_summary_service` | 继承 v2.6 chunking 能力 | 重写提取器 | 已有 | 低 | 中 | 需要输出适配到新 canonical schema |
| 服务治理解析 | 复用 `esb_service` | 已支持 Excel/CSV/列名别名 | 重写解析器 | 已有 | 低 | 中 | 需改为 admin 全局导入语义 |
| 系统清单解析 | 复用 `system_list_routes.py` 解析逻辑 | 现有模板、preview 逻辑成熟 | 新 parser | 已有 | 低 | 低 | 需增加 confirm 后 Runtime 联动 |

结论：v2.7 不新增外部运行时依赖；新增的都是仓内模块与数据文件。

## 4. 总体设计（High-level Design）

### 4.1 系统上下文与边界

| 依赖方/系统 | 用途 | 协议 | SLA/SLO | 失败模式 | 降级/兜底 | Owner |
|---|---|---|---|---|---|---|
| React 前端 | PM/Admin/Expert 交互 | HTTP / WebSocket | 页面可访问 | 接口失败、状态轮询超时 | 显式错误提示 + 重试 | 项目前端 |
| FastAPI 后端 | Runtime、画像、导入、任务主链路 | HTTP / 内部调用 | 单机可用 | 解析失败、LLM失败、Memory失败 | `failed/partial_success` | 项目后端 |
| DashScope LLM/Embedding | 文档 Skill、系统识别、功能点拆解 | HTTPS SDK | 外部依赖 | 超时、配额、不可用 | 失败终态 + 主链路继续可用 | 外部服务 |
| 文件存储（`data/*.json`） | 画像、导入历史、Memory、执行记录 | 本地文件 | 单机 IO | 文件损坏、写失败 | 原子写 + 备份 + 回滚脚本 | 运维 |
| 系统清单数据 | 标准系统名称/别名/归属单一真相源 | 本地 JSON/XLSX | 按月更新 | 模板错误、名称不一致 | preview 拦截 + unmatched 清单 | Admin |

### 4.2 架构概述（建议按 C4）

```text
PM/Admin/Expert
    |
    v
React Pages
  - SystemProfileImportPage (PM)
  - SystemProfileBoardPage  (PM/Admin/Expert)
  - ServiceGovernancePage   (Admin)
  - SystemListImportPage    (Admin)
    |
    v
FastAPI Routers
  - system_profile_routes
  - esb_routes
  - system_list_routes
  - task/evaluation routes
    |
    v
Runtime Facade
  - SkillRegistry
  - SceneRouter
  - SceneExecutor
  - PolicyGate
  - MemoryService
  - RuntimeExecutionService
    |
    +--> Built-in Skills
    |     - requirements_skill / design_skill / tech_solution_skill
    |     - service_governance_skill
    |     - system_catalog_skill
    |     - code_scan_skill
    |
    +--> Domain Services
    |     - SystemProfileService (v2.7 schema)
    |     - ServiceGovernanceProfileUpdater
    |     - SystemCatalogProfileInitializer
    |     - DirectDecisionResolver
    |     - FeatureAdjustmentMemoryAdapter
    |
    +--> Existing Engines
          - profile_summary_service
          - esb_service
          - system_identification_agent
          - feature_breakdown_agent

Storage
  - system_profiles.json
  - import_history.json
  - extraction_tasks.json
  - runtime_executions.json
  - memory_records.json
```

核心设计原则：

- 所有业务入口先归一到 `scene_id`，再由 Runtime 统一执行。
- 正式画像只有一份 canonical 数据源：`profile_data.<domain>.canonical`。
- `field_sources` 决定是否允许自动写入；`manual` 永远最高优先级。
- `MemoryService` 负责沉淀成功动作与高价值判定，不把 Memory 当 debug 日志。
- `RuntimeExecutionService` 负责把“执行状态”和“结果状态”区分开：`queued/running/completed/failed/partial_success`。

### 4.3 变更影响面（Impact Analysis）

| 影响面 | 是否影响 | 说明 | 需要迁移/兼容 | Owner |
|---|---|---|---|---|
| API 契约 | 是 | 新增 `profile/execution-status`、`memory`；`esb/imports` 与 `system-list/confirm` 响应扩展；保留 `profile/extraction-status` 兼容别名 | 是，见 §5.4 / §6.1.1 | 后端 |
| 数据库/存储 | 是 | `system_profiles.json` schema 重构；新增 `memory_records.json`、`runtime_executions.json` | 是，先备份再清理 | 后端 |
| 权限与审计 | 是 | PM 移除治理入口；admin 独占服务治理/系统清单联动；所有成功动作写 Memory / execution | 是 | 前后端 |
| 性能与容量 | 是 | 批量导入会增加文件写入次数 | 需要压测与批量写优化 | 后端 |
| 运维与监控 | 是 | 新增 Runtime / Memory 日志与指标 | 需要日志字段与告警规则 | 运维 |
| 前端交互 | 是 | PM 导入页卡片收敛；画像页 schema 变更；新增 admin 服务治理页；系统清单 confirm 结果页扩展 | 是 | 前端 |
| 任务评估主链路 | 是 | 系统识别与功能点拆解会读画像/Memory，但入口、角色和报告语义不变 | 必须回归验证 | 后端 |

## 5. 详细设计（Low-level Design）

### 5.1 模块分解与职责（Components）

| 模块 | 职责 | 关键接口 | 关键数据 | 依赖 |
|---|---|---|---|---|
| `SkillRegistry` | 注册 6 个内置 Skill 与未来 disabled Skill；声明输入/任务/产物/执行模式/策略 | `load()`, `get(skill_id)` | `skill_definition` | 无 |
| `SceneRouter` | 根据 `scene_id + input_type + actor_role` 选择 `skill_chain` | `resolve(scene_id, context)` | `scene_plan` | `SkillRegistry` |
| `SceneExecutor` | 执行 `skill_chain`，串联 pre-read / skill / policy / apply / memory / status | `execute(scene_id, payload)` | `execution_context` | 各 Skill、`PolicyGate` |
| `PolicyGate` | 统一输出 `auto_apply / draft_apply / suggestion_only / reject` | `decide(scene_id, field_result, context)` | `policy_result` | `field_sources`, blank evaluator |
| `RuntimeExecutionService` | 写 execution history、最新状态索引、partial_success | `start()`, `finish()`, `fail()`, `get_latest()` | `runtime_executions.json`, `extraction_tasks.json` | 文件存储 |
| `MemoryService` | 写/查系统级 Memory，支持未来类型 | `append(record)`, `query(filter)` | `memory_records.json` | 文件存储 |
| `ProfileWriter` | 根据 policy 将 `auto_apply/draft_apply` 结果写入画像与 `field_sources` | `apply_updates(system_id, updates)` | `profile_update_result` | `system_profile_service`, `ProfileSchemaService` |
| `SuggestionWriter` | 将 `suggestion_only` 结果写入 `ai_suggestions` 并生成建议摘要 | `write(system_id, suggestions)` | `suggestion_result` | `system_profile_service` |
| `ProfileSchemaService` | 统一构造 v2.7 空画像、canonical 校验、diff 与字段路径工具 | `build_empty()`, `normalize()`, `diff()` | schema definition | 无 |
| `DocumentSkillAdapter` | 将 `profile_summary_service` 输出适配为 v2.7 canonical suggestions | `run(doc_type, text, context)` | D1/D2/D4/D5 suggestions | `profile_summary_service` |
| `ServiceGovernanceProfileUpdater` | 把治理导入结果归一到 D3 canonical，并按 D1/D4 生成语义影响项 | `apply(batch_result)` | D3 updates, summary | `esb_service`, `PolicyGate` |
| `SystemCatalogProfileInitializer` | 根据系统清单 confirm 结果映射 deterministic 初始化字段，并做空画像判定 | `initialize(confirm_payload)` | init updates, skipped_items | `ProfileSchemaService`, `system_list_routes` |
| `CodeScanSkillAdapter` | 复用现有代码扫描 API/Service，统一 `repo_path` 与源码压缩包输入，合并 Java 与 JS/TS 中度扫描结果 | `run(payload, context)` | D4 suggestions, breakdown context | `code_scan_routes`, `code_scan_service` |
| `DirectDecisionResolver` | 先基于系统清单/Memory 做系统识别直接判定，再决定是否调用 LLM | `resolve(requirement_text)` | `identification_result` | system list, Memory, agent |
| `FeatureAdjustmentMemoryAdapter` | 读取历史 adjustment pattern，写回新的功能点调整 Memory | `build_context()`, `record_adjustments()` | `function_point_adjustment` | `MemoryService`, feature agent |

#### 5.1.1 Scene 与 Skill 链矩阵

| `scene_id` | 输入 | `skill_chain` | 执行模式 | 默认策略 |
|---|---|---|---|---|
| `pm_document_ingest` + `requirements` | PM 文档 | `requirements_skill -> PolicyGate -> SuggestionWriter -> MemoryWriter` | async | `suggestion_only` |
| `pm_document_ingest` + `design` | PM 文档 | `design_skill -> PolicyGate -> SuggestionWriter -> MemoryWriter` | async | `suggestion_only` |
| `pm_document_ingest` + `tech_solution` | PM 文档 | `tech_solution_skill -> PolicyGate -> SuggestionWriter -> MemoryWriter` | async | `suggestion_only` |
| `admin_service_governance_import` | 治理模板 | `service_governance_skill -> PolicyGate -> ProfileWriter -> MemoryWriter` | sync | D3=`auto_apply`，D1/D4=`draft_apply/suggestion_only` |
| `admin_system_catalog_import` | 系统清单 confirm | `system_catalog_skill -> BlankProfileEvaluator -> PolicyGate -> ProfileWriter -> MemoryWriter` | sync | 空画像=`auto_apply`，非空=`reject/skip` |
| `code_scan_ingest` | `repo_path` / `repo_archive` / 现有扫描作业结果 | `code_scan_skill -> PolicyGate -> SuggestionWriter -> MemoryWriter` | async | `suggestion_only` |
| `system_identification` | 需求文本 | `DirectDecisionResolver -> LLMResolver(必要时) -> MemoryWriter` | sync | 直接输出 `final_verdict` |
| `feature_breakdown` | 需求文本 + system context | `MemoryContextBuilder -> FeatureBreakdownAgent -> AdjustmentPolicy -> MemoryWriter` | sync | 低风险草稿内自动应用，高风险建议化 |

#### 5.1.2 内置 Skill 定义与适配层

Skill 在 v2.7 中不是仓外独立脚本包，而是后端 Runtime 内的内置执行单元。注册表记录能力定义，适配层把现有 service / route / parser 统一包装成可被 SceneExecutor 调度的 skill。

| `skill_id` | 输入源 | 主要输出 | 复用实现 | 新增适配层/脚本 | 默认策略 |
|---|---|---|---|---|---|
| `requirements_skill` | PM 需求文档 | D1/D2/D5 suggestions | `profile_summary_service` | `DocumentSkillAdapter(doc_type=requirements)` | `suggestion_only` |
| `design_skill` | PM 设计文档 | D2/D4/D5 suggestions | `profile_summary_service` | `DocumentSkillAdapter(doc_type=design)` | `suggestion_only` |
| `tech_solution_skill` | PM 技术方案 | D4/D5 suggestions | `profile_summary_service` | `DocumentSkillAdapter(doc_type=tech_solution)` | `suggestion_only` |
| `service_governance_skill` | 治理模板（最新样例为 `data/esb-template.xlsx`；兼容 `data/接口申请模板.xlsx`） | D3 canonical updates + D1/D4 semantic hints | `esb_service` | `ServiceGovernanceProfileUpdater` | D3=`auto_apply`；D1/D4=`draft_apply/suggestion_only` |
| `system_catalog_skill` | 单一系统清单 confirm 数据 | D1/D4 deterministic init package + D3/D5 extensions | 现有 `system_list_routes.py` preview/confirm 解析链路 | `SystemCatalogProfileInitializer` | 空画像=`auto_apply`；非空=`reject/skip` |
| `code_scan_skill` | `repo_path` / `repo_archive` / 既有 scan job | D4 suggestions + 功能点拆解辅助上下文 | `code_scan_routes.py`、`code_scan_service.py` | `CodeScanSkillAdapter`、`CodeScanResultNormalizer` | `suggestion_only` |

补充约束：

- 文档类 skill 的本期输入格式边界固定为可直接抽文本的 `docx`、文本型 `pdf`、`pptx`。扫描件 PDF、纯图片型 PPTX/OCR 场景不作为 v2.7 有效性目标，命中时只允许返回显式降级/失败，不得伪造高置信结果。
- `code_scan_skill` 不重写底层扫描引擎，复用现有仓库路径 allowlist、安全解压、作业状态和结果持久化能力。
- `code_scan_skill` 的固定扫描边界是 Java / Spring Boot 与前端 JS / TS，中度语义扫描只产出 D4 现状、模块线索、接口线索和功能点拆解上下文。
- `system_catalog_skill` 只消费单一系统清单表，不再设计子系统清单解析器或主子系统映射写入器。

#### 5.1.3 文档类 Skill 的有效性边界

基于本轮样本文档分析，三类 PM 文档 skill 在 v2.7 的设计目标应区分为“有效提取”与“保守提取”，不能统一承诺。

| `skill_id` | 样本依据 | 本期目标字段 | 有效性判断 | 说明 |
|---|---|---|---|---|
| `requirements_skill` | `req-temp1.docx`、`req-temp2.docx`、`req-temp3.docx` | D1 / D2 / D5 为主；少量 D3 / D4 弱证据 | 有效设计 | 三份样本虽格式不同，但都稳定提供概述、范围、流程、功能、角色、约束类信息 |
| `tech_solution_skill` | `arch-temp.docx` | D4 / D5 为主；补充 D2 / D3 | 有效设计 | 技术方案样本稳定包含架构、部署、接口、技术栈、风险与实施约束，且大量证据在表格中 |
| `design_skill` | 暂无真实样本 | D2 / D4 / D5 | 保守设计 | v2.7 先接入统一解析链路，但不承诺高质量字段提取；默认只输出 `suggestion_only` |

字段级边界：

- `requirements_skill`
  - 高置信：`D1.service_scope`、`D1.target_users`、`D1.system_boundary`、`D2.functional_modules`、`D2.business_processes`、`D5.technical_constraints`、`D5.business_constraints`
  - 中低置信：`D2.data_assets`、`D3.other_integrations`、`D4.performance_baseline`
- `tech_solution_skill`
  - 高置信：`D3.provided_services`、`D3.consumed_services`、`D3.other_integrations`、`D4.architecture_style`、`D4.tech_stack`、`D4.network_zone`、`D5.technical_constraints`、`D5.known_risks`
  - 中低置信：`D2.functional_modules`、`D2.data_assets`、`D4.performance_baseline`
- `design_skill`
  - 无真实样本前只允许做保守 suggestions，不承诺字段覆盖率或准确率

实现约束：

- 文档类 skill 必须采用“章节语义 + 表格语义”双通道提取，而不能只依赖段落标题。
- `tech_solution_skill` 必须优先解析表格，因为高价值技术信息主要存在于架构、接口、运行平台和部署表中。
- 当输入超出本期有效性边界时，Runtime 应显式返回 `failed` 或 `partial_success + degraded_reason`，而不是伪造完整 suggestions。

### 5.2 数据模型与存储（Data Model）

### 5.2.1 `system_profiles.json` v2.7 canonical 结构

单条记录示意：

```json
{
  "system_id": "SYS-001",
  "system_name": "统一支付平台",
  "status": "draft",
  "created_at": "2026-03-13T10:00:00",
  "updated_at": "2026-03-13T10:10:00",
  "published_at": null,
  "profile_data": {
    "system_positioning": {
      "canonical": {
        "system_type": "",
        "business_domain": [],
        "architecture_layer": "",
        "target_users": [],
        "service_scope": "",
        "system_boundary": [],
        "extensions": {}
      }
    },
    "business_capabilities": {
      "canonical": {
        "functional_modules": [],
        "business_processes": [],
        "data_assets": [],
        "extensions": {}
      }
    },
    "integration_interfaces": {
      "canonical": {
        "provided_services": [],
        "consumed_services": [],
        "other_integrations": [],
        "extensions": {}
      }
    },
    "technical_architecture": {
      "canonical": {
        "architecture_style": "",
        "tech_stack": {
          "languages": [],
          "frameworks": [],
          "databases": [],
          "middleware": [],
          "others": []
        },
        "network_zone": "",
        "performance_baseline": {
          "online": {
            "peak_tps": "",
            "p95_latency_ms": "",
            "availability_target": ""
          },
          "batch": {
            "window": "",
            "data_volume": "",
            "peak_duration": ""
          },
          "processing_model": ""
        },
        "extensions": {}
      }
    },
    "constraints_risks": {
      "canonical": {
        "technical_constraints": [],
        "business_constraints": [],
        "known_risks": [],
        "extensions": {}
      }
    }
  },
  "field_sources": {},
  "ai_suggestions": {},
  "evidence_refs": []
}
```

字段数统计：

- D1：7
- D2：4
- D3：4
- D4：5
- D5：4
- 合计：24 个 canonical 字段，满足 REQ-101

关键规则：

- `profile_data.<domain>.canonical` 是正式画像唯一写入目标。
- `fields`、旧 12 子字段、旧 `performance_profile` / `integration_points` 等 legacy 键全部移除，不再出现在读写结果中。
- `ai_suggestions` 不写入系统清单非空画像 skip 场景。

### 5.2.2 `field_sources`、`ai_suggestions`、`memory_records.json` 与 `runtime_executions.json`

`field_sources` 采用“字段路径 -> 元数据”结构：

```json
{
  "technical_architecture.canonical.tech_stack.frameworks": {
    "source": "manual",
    "scene_id": "profile_manual_edit",
    "source_id": "profile_save_20260313_001",
    "updated_at": "2026-03-13T10:10:00",
    "actor": "pm_zhangsan"
  }
}
```

规则：

- `source` 枚举：`manual`、`ai`、`governance`、`system_catalog`、`code_scan`
- `manual` 最高优先级；`PolicyGate` 遇到冲突时必须 skip 或 suggestion 化
- 系统清单空画像初始化是特例：blank 判定明确忽略既有 `field_sources`，初始化成功后对应字段的 source 元数据统一重写为 `system_catalog`

`ai_suggestions` 采用“字段路径 -> suggestion payload”结构：

```json
{
  "system_positioning.canonical.system_type": {
    "value": "渠道支撑系统",
    "scene_id": "pm_document_ingest",
    "skill_id": "requirements_skill",
    "decision_policy": "suggestion_only",
    "confidence": 0.76,
    "reason": "从需求文档摘要中提取"
  }
}
```

`memory_records.json` 采用 `system_id -> records[]`：

```json
{
  "SYS-001": [
    {
      "memory_id": "mem_xxx",
      "system_id": "SYS-001",
      "memory_type": "profile_update",
      "memory_subtype": "system_catalog_init",
      "scene_id": "admin_system_catalog_import",
      "source_type": "system_catalog",
      "source_id": "exec_xxx",
      "decision_policy": "auto_apply",
      "confidence": 1.0,
      "summary": "初始化 D1/D5 基础字段",
      "payload": {
        "changed_fields": [
          "system_positioning.canonical.system_type"
        ]
      },
      "evidence_refs": [
        {
          "source_type": "system_catalog_file",
          "source_id": "catalog_20260313.xlsx"
        }
      ],
      "created_at": "2026-03-13T10:10:00"
    }
  ]
}
```

`runtime_executions.json` 采用 append-only list：

```json
[
  {
    "execution_id": "exec_xxx",
    "scene_id": "admin_system_catalog_import",
    "system_id": "SYS-001",
    "source_type": "system_catalog",
    "source_file": "catalog_20260313.xlsx",
    "skill_chain": ["system_catalog_skill"],
    "status": "partial_success",
    "policy_results": [],
    "errors": [],
    "result_summary": {
      "updated_system_ids": ["SYS-001"],
      "skipped_items": []
    },
    "created_at": "2026-03-13T10:10:00",
    "completed_at": "2026-03-13T10:10:05"
  }
]
```

`extraction_tasks.json` 保留为 `system_id -> latest execution summary`，语义从“提取任务”升级为“最新 Runtime 状态”，以兼容现有轮询 / WebSocket 逻辑。

### 5.2.3 关键对象字段定义

| 对象 | 字段 | 类型 | 约束 | 索引 | 说明 |
|---|---|---|---|---|---|
| `memory_record` | `memory_id` | string | 必填，唯一 | 内存去重键 | 支持未来类型 |
| `memory_record` | `memory_type` | string | 必填 | `system_id + memory_type` 查询 | 至少支持 3 类，未来可扩展 |
| `runtime_execution` | `execution_id` | string | 必填，唯一 | `execution_id` | 场景执行主键 |
| `runtime_execution` | `status` | enum | `queued/running/completed/failed/partial_success` | `system_id + completed_at` | 与 HTTP 成功语义分离 |
| `catalog_import_result` | `skipped_items[].reason` | enum | 至少支持 `profile_not_blank`、`profile_not_found`、`mapping_incomplete` | - | 满足 REQ-004 / REQ-C008 |
| `identification_result` | `final_verdict` | enum | `matched/ambiguous/unknown` | - | 必填 |

### 5.2.4 空画像判定算法

空画像判定器 `BlankProfileEvaluator` 只看 `profile_data.<domain>.canonical`，忽略 `field_sources`、`ai_suggestions`、Memory：

```python
def is_blank_profile(profile: dict) -> bool:
    profile_data = profile.get("profile_data") or {}
    for domain in DOMAIN_KEYS:
        canonical = ((profile_data.get(domain) or {}).get("canonical")) or {}
        if has_non_empty_value(canonical):
            return False
    return True

def has_non_empty_value(value) -> bool:
    if value in (None, ""):
        return False
    if isinstance(value, list):
        return any(has_non_empty_value(item) for item in value)
    if isinstance(value, dict):
        return any(has_non_empty_value(item) for item in value.values())
    return True
```

规则：

- `[]`、`{}`、`""`、`null` 视为空。
- `tech_stack`、`performance_baseline`、`extensions` 等对象只有在内部任一子值非空时才视为非空。
- 任一 domain 的 canonical 只要存在非空内容，整份画像即视为非空。

迁移方案：

- 向后兼容策略：不对旧画像做字段级迁移，部署时先备份旧数据，再清理旧 schema 记录。
- 回滚步骤：回滚代码同时恢复部署前备份的 `system_profiles.json`、知识数据与导入历史。
- 双写/回填/灰度策略：不采用双写；v2.7 直接切换到新 schema。

数据迁移 SOP 检查清单：

- [x] 迁移策略以“备份 + 清理 + 新 schema 重建”为单一口径
- [x] 有回滚恢复步骤
- [x] 无大表迁移，不涉及锁表
- [x] 上线顺序已在 §6.1.2 明确

### 5.3 核心流程（Flow）

### 5.3.1 场景一：PM 三类文档导入

接口与权限：

- 路径：`POST /api/v1/system-profiles/{system_id}/profile/import`
- 权限：仅 `manager`（主责/B角）或 `admin`
- 请求参数：path `system_id`，form `doc_type`、`file`

1. 接口校验角色、系统归属、`doc_type` allowlist 与文件格式。
2. Router 将 `doc_type=requirements|design|tech_solution` 映射为 `pm_document_ingest` + 对应 Skill。
3. RuntimeExecutionService 创建 execution 记录，`status=queued`，并把 `execution_id` 写入最新状态索引。
4. DocumentSkillAdapter 复用 `profile_summary_service` 完成文档解析、分块、LLM 提取，并产出 v2.7 canonical suggestions。
5. PolicyGate 对文档 Skill 输出统一判定为 `suggestion_only`；不得直接覆盖 `profile_data`。
6. SuggestionWriter 把结果写入 `ai_suggestions`，MemoryService 写 `profile_update` Memory（`memory_subtype=document_suggestion`）。
7. execution 终态写入 `completed`；若提取失败则写 `failed` 并同步导入历史。

失败路径：

- 文件非法 / `doc_type` 非法：接口直接 `400`，记录 failed import history。
- Skill/LLM 失败：execution 终态为 `failed`，导入历史保留成功入库与失败提取原因的分层信息。
- Memory 写失败：`status=partial_success`，suggestions 已保存但响应不得宣称完全成功。

### 5.3.2 场景二：管理员服务治理导入

1. admin 调用 `POST /api/v1/esb/imports` 上传治理模板。
2. `service_governance_skill` 复用 `esb_service` 解析模板、列名别名和系统匹配逻辑，生成以系统名聚合的 canonical D3 更新包。
3. 对每个命中系统：
   - D3 结构化事实更新交给 PolicyGate，若目标字段非 `manual`，则 `auto_apply` 到当前画像草稿。
   - D1/D4 的语义影响项只允许 `draft_apply` 或 `suggestion_only`，不得无条件覆盖。
4. 未命中项进入 `unmatched_items`，不得写入任何画像。
5. 每个成功画像更新写 1 条 `profile_update` Memory，`memory_subtype=service_governance`。
6. 顶层返回 `matched_count/unmatched_count/unmatched_items/updated_system_ids/errors`。

失败路径：

- 模板解析失败：整批 `failed`，不写画像。
- 部分系统写失败：顶层返回 `partial_success`，成功和失败项分开统计。
- Memory 写失败：对应系统更新结果标记 `partial_success`，并回填 `memory_error`。

### 5.3.3 场景三：系统清单 preview / confirm 联动画像

接口与权限：

- preview 路径：`POST /api/v1/system-list/batch-import/preview`
- confirm 路径：`POST /api/v1/system-list/batch-import/confirm`
- 权限：仅 `admin`
- 请求参数：preview=form `file`；confirm=json `mode/systems`

1. preview 只做模板校验与行级错误，不触发 Runtime。
2. confirm 先写系统清单主台账，再触发 `admin_system_catalog_import`。
3. `system_catalog_skill` 按固定映射把单表系统清单字段转换为初始化包：
   - 写入 canonical：
     - `系统类型` -> `system_positioning.canonical.system_type`
     - `应用主题域` -> `system_positioning.canonical.business_domain`
     - `应用分层` -> `system_positioning.canonical.architecture_layer`
     - `服务对象` -> `system_positioning.canonical.target_users`
     - `功能描述` -> `system_positioning.canonical.service_scope`
     - `开发语言` -> `technical_architecture.canonical.tech_stack.languages`
     - `RDBMS` -> `technical_architecture.canonical.tech_stack.databases`
     - `应用中间件` -> `technical_architecture.canonical.tech_stack.middleware`
     - `操作系统` / `芯片` / `新技术特征` -> `technical_architecture.canonical.tech_stack.others`
   - 写入 `extensions`：
     - `英文简称` -> `system_positioning.canonical.extensions.aliases`
     - `业务领域` -> `system_positioning.canonical.extensions.business_lines`
     - `状态` / `应用等级` -> `system_positioning.canonical.extensions.*`
     - `是否云部署` / `是否有互联网出口` / `是否双活` / `集群分类` / `虚拟化分布` -> `technical_architecture.canonical.extensions.*`
     - `全栈信创` / `等保定级` / `是否是重要信息系统` -> `constraints_risks.canonical.extensions.*`
     - `系统RTO` / `系统RPO` / `灾备情况` / `灾备部署地` / `应急预案更新日期` -> `constraints_risks.canonical.extensions.*`
     - `知识产权` / `产品授权证书情况` -> `constraints_risks.canonical.extensions.*`
     - `关联系统` -> `integration_interfaces.canonical.extensions.catalog_related_systems`
   - 不入画像：`系统编号`、`上线日期`、`下线时间`、`主管部门`、`产品经理`、`系统负责人`、`需求分析师`、`架构师`、`归属中心`、`实施厂商`、`厂商属地`、`开发模式`、`运维模式`、`备注`
4. `BlankProfileEvaluator` 对命中系统逐个判断：
   - 画像不存在：创建空画像后继续初始化。
   - 画像存在且 blank：允许 `auto_apply`。
   - 画像存在且 non-blank：返回 `skipped_items.reason=profile_not_blank`，不写 `profile_data`，不写 `ai_suggestions`。
5. PolicyGate 对本场景只有两种输出：
   - 空画像：`auto_apply`
   - 非空画像：`reject/skip`
6. 成功初始化系统写 `profile_update` Memory；skip 项不写 `profile_update`，但保留 execution 结果。
7. confirm 响应返回 `updated_system_ids/skipped_items/errors`。

关键约束：

- preview 失败不得进入 confirm。
- 首次初始化不需要 PM 接受建议。
- 后续月度更新或覆盖导入只允许补空，不允许“部分字段覆盖非空画像”。
- `功能描述` 只写 `D1.service_scope`，不拆分生成 D2 模块或流程。
- `关联系统` 只写 `D3.extensions.catalog_related_systems`，不直接生成 D3 canonical 集成关系。

### 5.3.4 场景四：系统识别直接判定

1. 任务主链路进入系统识别阶段时，调用 Runtime 的 `system_identification` scene。
2. DirectDecisionResolver 先读取：
   - 系统清单标准名 / 简称 / 额外别名
   - 最近成功的 `identification_decision` Memory
   - 已发布或当前草稿画像中的稳定描述
3. 判定顺序：
   - 精确别名命中 1 个系统：`matched`
   - 精确命中多个系统：`ambiguous`
   - 无精确命中：构造 candidate context，调用现有 `system_identification_agent`
   - LLM 返回后由 resolver 统一映射到 `matched / ambiguous / unknown`
4. 输出统一结构：
   - `final_verdict`
   - `selected_systems`
   - `candidate_systems`
   - `questions`
   - `reason_summary`
5. 将最终结果写入 `identification_decision` Memory。

保护规则：

- `candidate_systems` 与 `questions` 永远是解释信息，不是最终判定。
- `ambiguous` / `unknown` 不得静默进入“已选中系统”的后续链路。

### 5.3.5 场景五：功能点拆解与 Memory 反哺

1. 进入功能点拆解前，`FeatureAdjustmentMemoryAdapter` 读取：
   - 当前系统画像 canonical 数据
   - 最近 N 条 `function_point_adjustment` Memory
   - 最近 N 条 `profile_update` / `identification_decision` Memory
2. 将上述上下文注入现有 `feature_breakdown_agent`。
3. Agent 输出草稿后，AdjustmentPolicy 仅对低风险模式自动应用到“当前拆解草稿”：
   - 命名归一化
   - 重复项去重
   - 已确认稳定模块映射
4. 高风险模式仅输出建议或待复核草稿：
   - 跨系统归属
   - 模块拆分/合并
   - 范围增删
5. PM 保存 AI 首轮修改后，系统按分类写入 `function_point_adjustment` Memory。

失败路径：

- Memory 读取失败：继续拆解，但执行结果标记 `context_degraded=true`。
- Memory 写失败：保存结果返回 `partial_success`。

### 5.3.6 场景六：代码扫描 Skill 接入 Runtime

1. manager/admin 通过现有 `POST /api/v1/code-scan/jobs` 入口提交 `repo_path` 或源码压缩包，Runtime 以 `scene_id=code_scan_ingest` 跟踪执行。
2. `CodeScanSkillAdapter` 复用现有 `code_scan_routes.py` / `code_scan_service.py`：
   - `repo_path` 模式沿用 allowlist、绝对路径和权限校验。
   - `repo_archive` 模式沿用安全解压、大小和文件数限制。
3. 扫描阶段固定为 Java / Spring Boot 与前端 JS / TS 双通道中度语义扫描，输出：
   - D4 技术栈、工程结构、模块/接口线索 suggestions
   - 面向功能点拆解的上下文摘要
4. PolicyGate 对 `code_scan_skill` 统一判定为 `suggestion_only`；结果写入 `ai_suggestions`，并沉淀 `profile_update` Memory（`memory_subtype=code_scan_suggestion`）。
5. FeatureBreakdownAgent 后续读取该上下文，但不得把代码扫描结果直接覆盖正式画像。

失败路径：

- `repo_path` 越界或无权限：返回 `SCAN_004`
- 压缩包格式、大小或链接文件非法：返回 `SCAN_005` / `SCAN_006`
- 扫描作业失败：execution 终态为 `failed`
- suggestion 已生成但 Memory 写失败：execution 终态为 `partial_success`

### 5.4 API 设计（Contracts）

| API-ID | 方法 | 路径 | 请求体结构 | 响应体结构 | 错误码 | 兼容性 | 备注 |
|---|---|---|---|---|---|---|---|
| API-001 | POST | `/api/v1/system-profiles/{system_id}/profile/import` | `multipart/form-data` | `ProfileImportResponse` | `AUTH_001` / `PROFILE_IMPORT_FAILED` / `SKILL_002` / `MEMORY_001` | 保持现有路径；收紧 `doc_type` allowlist | PM 三类文档导入 |
| API-002 | GET | `/api/v1/system-profiles/{system_id}/profile/import-history` | query: `limit`, `offset` | `ProfileImportHistoryResponse` | `AUTH_001` / `PROFILE_002` | 保持现有路径 | 历史查询 |
| API-003 | GET | `/api/v1/system-profiles/{system_id}/profile/execution-status` | query: 无 | `ProfileExecutionStatusResponse` | `AUTH_001` / `PROFILE_002` | 新增；保留 `/profile/extraction-status` alias | Runtime 状态查询 |
| API-004 | PUT | `/api/v1/system-profiles/{system_name}` | `UpdateProfileRequest` | `UpdateProfileResponse` | `AUTH_001` / `PROFILE_001` / `MEMORY_001` | 保持现有路径，切换新 schema | 手动保存画像 |
| API-005 | POST | `/api/v1/system-profiles/{system_name}/publish` | 无 | `PublishProfileResponse` | `AUTH_001` / `PROFILE_001` / `PROFILE_003` | 保持现有路径 | 发布画像 |
| API-006 | POST | `/api/v1/esb/imports` | `multipart/form-data` | `GovernanceImportResponse` | `AUTH_001` / `ESB_001` / `ESB_002` / `MEMORY_001` | 路径不变，语义改为 admin 全局治理 | 服务治理导入 |
| API-007 | POST | `/api/v1/system-list/batch-import/preview` | `multipart/form-data` | `CatalogPreviewResponse` | `AUTH_001` / `CATALOG_001` / `CATALOG_002` | 保持现有路径与 `code/data` 包络 | 只校验不联动画像 |
| API-008 | POST | `/api/v1/system-list/batch-import/confirm` | `CatalogConfirmRequest` | `CatalogConfirmResponse` | `AUTH_001` / `CATALOG_001` / `CATALOG_002` / `MEMORY_001` | 保持现有路径；扩展响应字段 | confirm + Runtime 联动 |
| API-009 | GET | `/api/v1/system-profiles/{system_id}/memory` | query: `memory_type`, `scene_id`, `start_at`, `end_at`, `limit`, `offset` | `MemoryQueryResponse` | `AUTH_001` / `PROFILE_002` | 新增 | 系统 Memory 查询 |

#### API-001 `POST /api/v1/system-profiles/{system_id}/profile/import`

权限：

- 仅 `manager`（主责/B角）或 `admin` 可调用

请求参数：

```typescript
type AllowedDocType = 'requirements' | 'design' | 'tech_solution';

interface ProfileImportRequest {
  system_id: string;           // path param
  doc_type: AllowedDocType;    // form field
  file: File;                  // form field
}
```

响应：

```typescript
interface ProfileImportResponse {
  result_status: 'queued' | 'partial_success' | 'failed';
  execution_id: string | null;
  scene_id: 'pm_document_ingest';
  import_result: {
    status: 'success' | 'failed';
    file_name: string;
    imported_at: string | null;
    failure_reason: string | null;
  };
  execution_status: {
    status: 'queued' | 'running' | 'completed' | 'failed' | 'partial_success';
    error: string | null;
  };
}
```

错误码：

- `AUTH_001`：无权限
- `PROFILE_IMPORT_FAILED`：`doc_type` 非法、文件为空、格式不支持、Runtime 初始化失败
- `SKILL_002`：Skill 执行失败
- `MEMORY_001`：suggestion 已生成但 Memory 写失败，响应需降级为 `partial_success`

#### API-002 `GET /api/v1/system-profiles/{system_id}/profile/import-history`

权限：

- `manager/admin/expert` 按读权限访问

请求参数：

```typescript
interface ProfileImportHistoryQuery {
  system_id: string; // path param
  limit?: number;
  offset?: number;
}
```

响应：

```typescript
interface ProfileImportHistoryItem {
  id: string;
  doc_type: 'requirements' | 'design' | 'tech_solution';
  file_name: string;
  imported_at: string;
  status: 'success' | 'failed';
  failure_reason: string | null;
  operator_id: string;
  execution_id?: string;
}

interface ProfileImportHistoryResponse {
  total: number;
  items: ProfileImportHistoryItem[];
}
```

错误码：

- `AUTH_001`
- `PROFILE_002`

#### API-003 `GET /api/v1/system-profiles/{system_id}/profile/execution-status`

权限：

- `manager/admin/expert` 按读权限访问

请求参数：

```typescript
interface ProfileExecutionStatusQuery {
  system_id: string; // path param
}
```

响应：

```typescript
interface PolicyResultSummary {
  field_path: string;
  decision: 'auto_apply' | 'draft_apply' | 'suggestion_only' | 'reject';
  reason: string;
}

interface ProfileExecutionStatusResponse {
  execution_id: string | null;
  scene_id: string | null;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'partial_success';
  created_at: string | null;
  completed_at: string | null;
  skill_chain: string[];
  policy_results: PolicyResultSummary[];
  error: string | null;
  notifications: string[];
}
```

错误码：

- `AUTH_001`
- `PROFILE_002`

兼容性：

- `GET /api/v1/system-profiles/{system_id}/profile/extraction-status` 作为兼容别名返回相同结构，至少保留到 v2.8。

#### API-004 `PUT /api/v1/system-profiles/{system_name}`

权限：

- 仅 `manager`（主责/B角）可调用

请求参数：

```typescript
interface UpdateProfileRequest {
  system_id: string;
  profile_data: Record<string, { canonical: Record<string, unknown> }>;
  evidence_refs?: Array<{ source_type: string; source_id: string; source_file?: string }>;
}
```

响应：

```typescript
interface UpdateProfileResponse {
  result_status: 'success' | 'partial_success' | 'failed';
  profile: {
    system_id: string;
    system_name: string;
    status: 'draft' | 'published';
    profile_data: Record<string, { canonical: Record<string, unknown> }>;
    field_sources: Record<string, unknown>;
    ai_suggestions: Record<string, unknown>;
    updated_at: string;
  };
  memory_result: {
    status: 'success' | 'failed';
    memory_id: string | null;
    reason: string | null;
  };
}
```

错误码：

- `AUTH_001`
- `PROFILE_001`
- `MEMORY_001`

#### API-005 `POST /api/v1/system-profiles/{system_name}/publish`

权限：

- 仅系统主责 `manager` 可调用

请求参数：

- path param：`system_name`

响应：

```typescript
interface PublishProfileResponse {
  result_status: 'success' | 'failed';
  system_name: string;
  published_at: string;
  status: 'published';
  pending_fields: string[];
}
```

错误码：

- `AUTH_001`
- `PROFILE_001`
- `PROFILE_003`

#### API-006 `POST /api/v1/esb/imports`

权限：

- 仅 `admin` 可调用

请求参数：

```typescript
interface GovernanceImportRequest {
  file: File;
  mapping_json?: string; // form field, optional
}
```

响应：

```typescript
interface GovernanceImportResponse {
  result_status: 'success' | 'partial_success' | 'failed';
  execution_id: string;
  matched_count: number;
  unmatched_count: number;
  updated_system_ids: string[];
  unmatched_items: Array<{ raw_system_name: string; reason: string }>;
  errors: Array<{ row_no?: number; reason: string }>;
}
```

错误码：

- `AUTH_001`
- `ESB_001`
- `ESB_002`
- `MEMORY_001`

#### API-007 `POST /api/v1/system-list/batch-import/preview`

权限：

- 仅 `admin` 可调用

请求参数：

```typescript
interface CatalogPreviewRequest {
  file: File;
}
```

响应：

```typescript
interface CatalogPreviewResponse {
  code: 200;
  data: {
    systems: Array<Record<string, unknown>>;
    summary: {
      systems_total: number;
      systems_error: number;
    };
  };
}
```

错误码：

- `AUTH_001`
- `CATALOG_001`
- `CATALOG_002`

#### API-008 `POST /api/v1/system-list/batch-import/confirm`

权限：

- 仅 `admin` 可调用

请求参数：

```typescript
interface CatalogConfirmRequest {
  mode: 'replace' | 'upsert';
  systems: Array<Record<string, unknown>>;
}
```

响应：

```typescript
interface CatalogConfirmResponse {
  code: 200;
  message: 'success';
  result_status: 'success' | 'partial_success';
  execution_id: string;
  catalog_import_result: {
    updated_system_ids: string[];
    skipped_items: Array<{
      system_id: string;
      system_name: string;
      reason: 'profile_not_blank' | 'profile_not_found' | 'mapping_incomplete';
    }>;
    errors: Array<{ row_no?: number; reason: string }>;
  };
}
```

错误码：

- `AUTH_001`
- `CATALOG_001`
- `CATALOG_002`
- `MEMORY_001`

#### API-009 `GET /api/v1/system-profiles/{system_id}/memory`

权限：

- `manager/admin/expert` 按读权限访问

请求参数：

```typescript
interface MemoryQuery {
  system_id: string; // path param
  memory_type?: string;
  scene_id?: string;
  start_at?: string;
  end_at?: string;
  limit?: number;
  offset?: number;
}
```

响应：

```typescript
interface MemoryRecordResponse {
  memory_id: string;
  memory_type: string;
  memory_subtype: string;
  scene_id: string;
  source_type: string;
  source_id: string;
  decision_policy: string;
  confidence: number;
  summary: string;
  payload: Record<string, unknown>;
  evidence_refs: Array<{ source_type: string; source_id: string; source_file?: string }>;
  created_at: string;
}

interface MemoryQueryResponse {
  total: number;
  items: MemoryRecordResponse[];
}
```

错误码：

- `AUTH_001`
- `PROFILE_002`

### 5.5 异步/消息/作业（如适用）

| EVT-ID | Topic/Queue | 生产者 | 消费者 | 投递语义 | 幂等/去重 | DLQ | 备注 |
|---|---|---|---|---|---|---|---|
| EVT-001 | 进程内后台任务 | `pm_document_ingest` | `DocumentSkillAdapter` | at-most-once（同进程） | 以 `execution_id` 去重，更新最新状态 | 无 | 复用现有 WebSocket/轮询 |
| EVT-002 | 同步批处理 | `admin_service_governance_import` | `ServiceGovernanceProfileUpdater` | request scoped | 按 `execution_id + system_id` 去重 | 无 | 不引入外部队列 |
| EVT-003 | 同步批处理 | `admin_system_catalog_import` | `SystemCatalogProfileInitializer` | request scoped | 按 `execution_id + system_id` 去重 | 无 | deterministic 初始化 |

### 5.6 配置、密钥与开关（Config/Secrets/Flags）

配置项清单：

| 配置项 | 默认值 | 取值范围 | 作用 | 敏感 | 备注 |
|---|---|---|---|---|---|
| `ENABLE_V27_PROFILE_SCHEMA` | `false` | `true/false` | 控制新 schema 读写与前端展示切换 | 否 | 上线时与清理步骤联动 |
| `ENABLE_V27_RUNTIME` | `false` | `true/false` | 控制 SceneRouter / Memory / PolicyGate 启用 | 否 | 回滚主开关 |
| `ENABLE_SERVICE_GOVERNANCE_IMPORT` | `false` | `true/false` | 控制 admin 服务治理页与接口 | 否 | 灰度到 STAGING |
| `ENABLE_SYSTEM_CATALOG_PROFILE_INIT` | `false` | `true/false` | 控制 confirm 后画像联动 | 否 | 回滚时可单独关闭 |
| `RUNTIME_MEMORY_QUERY_LIMIT` | `200` | `1-500` | Memory 查询分页上限 | 否 | 防止大查询 |
| `RUNTIME_EXECUTION_RETENTION_DAYS` | `180` | `1-3650` | execution 历史保留期 | 否 | 采用写入时顺带清理 |
| `MEMORY_RETENTION_DAYS` | `3650` | `30-3650` | Memory 留存期 | 否 | 默认长期保留 |

Feature Flag 策略：

- STAGING/TEST 先开启 `ENABLE_V27_PROFILE_SCHEMA` 与 `ENABLE_V27_RUNTIME`。
- `ENABLE_SYSTEM_CATALOG_PROFILE_INIT` 单独灰度，先验证空画像判定。
- 回滚时优先关闭 `ENABLE_SYSTEM_CATALOG_PROFILE_INIT` 与 `ENABLE_SERVICE_GOVERNANCE_IMPORT`，再关闭总开关。

### 5.7 可靠性与可观测性（Reliability/Observability）

| 指标 | 维度 | 阈值 | 告警级别 | 处理指引 |
|---|---|---|---|---|
| `runtime_execution_total` | `scene_id,status` | `failed > 0` 按场景告警 | P1 | 先看 execution 结果与错误详情 |
| `runtime_execution_latency_ms_p95` | `scene_id` | `> 5000ms` | P2 | 排查 LLM、文件 IO、批量大小 |
| `policy_decision_total` | `scene_id,decision` | `reject` 异常升高 | P2 | 检查 blank 判定和 manual 冲突 |
| `memory_write_fail_total` | `memory_type` | `> 0` | P1 | 检查 `memory_records.json` 写权限与锁 |
| `catalog_profile_skip_total` | `reason` | `profile_not_blank` 异常升高 | P2 | 检查是否误判非空画像 |
| `identification_final_verdict_total` | `final_verdict` | `unknown/ambiguous` 突增 | P2 | 排查别名数据和 Direct Decision |

日志要求：

- 每次 Runtime 执行必须输出 `execution_id`、`scene_id`、`skill_chain`、`status`、`duration_ms`。
- Memory 写入必须输出 `memory_id`、`memory_type`、`system_id`，禁止打印原始大段文档正文。
- 系统清单 skip 必须记录 `system_id/system_name/reason`。
- 服务治理 unmatched 必须记录原始系统名与失败原因。

### 5.8 安全设计（Security）

| 威胁/攻击面 | 风险 | 缓解措施 | 验证方式 |
|---|---|---|---|
| manager 访问 admin 接口 | 越权修改全局画像 | `require_roles/require_admin_api_key` 收紧到 admin | 权限集成测试 |
| 非法 `doc_type` / 模板类型 | 绕过前端旧缓存直调接口 | 服务端 allowlist 严格校验 | 接口负向测试 |
| 导入文件中包含无关敏感列 | PII 落入画像或 Memory | Skill/Parser 只提取白名单字段，其余忽略或拒绝 | 导入样本测试 |
| Memory / execution 文件损坏 | 状态错乱、审计失真 | 文件锁 + 原子写 + 备份 + 写失败显式返回 | 故障注入 |
| 系统清单覆盖非空画像 | 画像污染 | BlankProfileEvaluator 只看 canonical；非空统一 skip | E2E 测试 |
| LLM 输出幻觉覆盖正式画像 | 正式画像被污染 | 文档/代码扫描 Skill 默认 `suggestion_only` | policy 测试 |

### 5.9 性能与容量（Performance/Capacity）

- 指标与口径：
  - 单次治理导入目标样本：100 条 exact-name 命中记录
  - 单次系统清单 confirm 目标样本：100 条系统记录
  - Memory 单系统保留：最近 2000 条查询窗口内分页读取
- 主要瓶颈：
  - `runtime_executions.json` / `memory_records.json` 文件增长
  - PM 文档 Skill 的 LLM 调用时延
- 优化策略：
  - `memory_records.json` 按 `system_id` 分桶
  - execution 和 Memory 采用 append + 最新状态索引双层存储
  - 长列表查询强制分页，限制 `limit`
  - 写入时顺带清理超保留期 execution 记录，不引入新调度器
- 扩展方案：
  - 当 `memory_records.json` 或 `runtime_executions.json` 超过单文件可接受上限时，可平滑切换到 SQLite/DB，但不在 v2.7 范围内

### 5.10 前端设计（有前端界面时必填，否则删除本段）

#### 页面结构与路由

| 页面/路由 | 路径 | 布局 | 权限 | 对应 REQ |
|---|---|---|---|---|
| PM 系统画像导入页 | `/system-profiles/import` | 现有页面改造 | manager | REQ-001 / REQ-005 |
| 系统画像面板 | `/system-profiles/board` | 现有页面改造 | manager/admin/expert | REQ-002 / REQ-007 |
| 服务治理页 | `/admin/service-governance` | 新增 admin 页面 | admin | REQ-003 / REQ-009 |
| 系统清单导入页 | 现有 admin 入口 | 结果区扩展 | admin | REQ-004 / REQ-C008 |

#### 核心页面说明

- PM 导入页：
  - 仅展示“需求文档 / 设计文档 / 技术方案”三张卡片
  - 上传成功后仅展示用户可读的执行状态、时间与结果摘要，不直接展示 `execution_id` / `scene` / 原始状态码
  - 轮询接口从 `profile/extraction-status` 迁移到 `profile/execution-status`
- 系统画像面板：
  - D1-D5 改为读取 `profile_data.<domain>.canonical`
  - 保持既有“系统TAB + 5域TAB”交互，不改页面主交互形式
  - 前端不展示 `extensions`、`field_sources`、Memory、来源、操作人；相关信息仅在后台存储/查询
- 服务治理页：
  - 上传治理模板
  - 展示匹配成功数、未匹配数、已更新系统名称与未匹配项
  - 不直接展示内部 ID 或原始 reason code
- 系统清单导入页：
  - 仅保留单一系统清单导入视图，不再展示“主系统清单 / 子系统清单”双 tab
  - preview 区保持现有校验结果
  - confirm 后新增画像联动结果区，展示已更新系统名称、预检错误与用户可读跳过原因

#### 组件与状态设计（如适用）

- `SystemProfileImportPage`：
  - 删除 `history_report`、`esb` 常量和模板映射
  - `executionStatus` 替代 `extractionStatus`
- `SystemProfileBoardPage`：
  - 新增 canonical schema 常量，作为前后端共享字段键单一真相源
  - 只消费前端展示所需的 canonical / ai_suggestions 字段，不直接渲染 `extensions`、`field_sources`、Memory
- 新增 `ServiceGovernancePage`：
  - 复用 Ant Design Upload / Table / Alert 组件
- 前后端数据流：
  - 前端所有页面只消费 API 契约中的 canonical 结构，不自行拼旧字段

## 6. 环境与部署（Environments & Deployment）

### 6.0 环境一致性矩阵（推荐）

| 维度 | DEV | STAGING | TEST | PROD |
|------|-----|---------|------|------|
| 数据 / 外部依赖 | 本地样本 / DashScope 测试 key | 脱敏副本 / 内网模型 | 脱敏副本 / 近生产模型 | 真实数据 / 真实模型 |
| 配置来源 / 密钥管理 | `.env.backend` + `.env.frontend` | `.env.backend.internal` + 内网前端部署配置 | `.env.backend.internal` + 内网前端部署配置 | `.env.backend.internal` + 内网前端部署配置 |
| 画像/Memory 文件 | 本地 data 卷 | 挂载卷 | 挂载卷 | 挂载卷 |
| 监控告警 | 开发日志 | 开启结构化日志 | 开启结构化日志 | 开启结构化日志 |

### 6.1 发布、迁移与回滚（Release/Migration/Rollback）

### 6.1.1 向后兼容策略

- API 兼容：
  - `profile/import-history`、`PUT /{system_name}`、`POST /{system_name}/publish` 路径不变
  - 新增 `profile/execution-status`
  - 保留 `profile/extraction-status` 兼容别名
- 数据兼容：
  - 不兼容旧 schema；通过备份 + 清理切换到 v2.7 新结构
- 配置兼容：
  - 通过 Feature Flag 控制切换；默认关闭，逐环境开启

### 6.1.2 上线步骤（Runbook 级别）

1. 备份 `data/system_profiles.json`、`data/import_history.json`、知识存储与相关旧数据文件。
2. 部署包含 v2.7 Runtime 与 schema 的后端/前端代码，保持所有 v2.7 开关关闭。
3. 在 STAGING/TEST 执行旧数据清理：
   - 清空旧 schema 系统画像数据
   - 清理历史评估报告相关导入/知识数据
4. 开启 `ENABLE_V27_PROFILE_SCHEMA=true`，验证空画像读取结构。
5. 开启 `ENABLE_V27_RUNTIME=true`，验证 PM 文档导入 execution-status。
6. 开启 `ENABLE_SERVICE_GOVERNANCE_IMPORT=true`，验证服务治理导入统计与 D3 更新。
7. 开启 `ENABLE_SYSTEM_CATALOG_PROFILE_INIT=true`，验证空画像初始化与非空 skip。
8. 运行 §7.1 关键测试与 §7.2 验收清单。

### 6.1.3 回滚策略（必须可执行）

- 触发条件：
  - 批量出现 `memory_write_fail_total > 0`
  - 系统清单 confirm 误更新非空画像
  - 现有评估主链路被阻断
- 回滚步骤：
  1. 关闭 `ENABLE_SYSTEM_CATALOG_PROFILE_INIT`
  2. 关闭 `ENABLE_SERVICE_GOVERNANCE_IMPORT`
  3. 关闭 `ENABLE_V27_RUNTIME`
  4. 如需完整回退，关闭 `ENABLE_V27_PROFILE_SCHEMA` 并恢复备份文件
  5. 回退到 `v2.6` 代码版本
- 数据处理：
  - 若已执行清理，回滚必须恢复上线前备份
  - 若 only runtime 开启未清理，可仅关闭开关并保留文件

## 7. 测试与验收计划（Test Plan）

### 7.1 测试用例清单（建议按 REQ-ID）

| TEST-ID | 对应 REQ-ID | 用例说明 | 类型 | 负责人 | 证据 |
|---|---|---|---|---|---|
| TEST-001 | REQ-001 / REQ-C001 | PM 导入页仅显示 3 类文档，旧类型接口被拒绝 | frontend + integration | AI | 页面渲染测试 / API 负向测试 |
| TEST-002 | REQ-002 / REQ-101 | 新 5 域 canonical 空结构、保存回读、前后端字段键一致 | integration | AI | schema 对比 + 接口回读 |
| TEST-003 | REQ-003 / REQ-102 | admin 服务治理导入 100 条 exact-name 样本成功率统计 | e2e | AI | 导入日志与回读 |
| TEST-004 | REQ-004 / REQ-C008 | 系统清单 confirm 空画像初始化、非空画像跳过，以及 canonical/extensions/ignore 映射正确 | e2e | AI | confirm 返回体 + 数据核验 |
| TEST-005 | REQ-005 / REQ-103 | 6 个 Skill 注册与 5 个核心 Scene 路由矩阵，含 `code_scan_skill` 双入口定义 | integration | AI | Registry / Router 测试 |
| TEST-006 | REQ-006 | 多格式文档 / 治理模板 / 单表系统清单额外列 canonical 化 | integration | AI | 输入样本对比 |
| TEST-006A | REQ-006 | 文档类 skill 仅支持 `docx` / 文本型 `pdf` / `pptx`，扫描件/OCR 明确降级 | integration | AI | 负向样本与错误提示 |
| TEST-007 | REQ-007 / REQ-104 | `profile_update` / `identification_decision` / `function_point_adjustment` Memory 覆盖率 | integration | AI | Memory 查询与统计 |
| TEST-008 | REQ-008 / REQ-C005 | 系统识别 `final_verdict=matched/ambiguous/unknown` | integration | AI | 识别结果断言 |
| TEST-009 | REQ-009 / REQ-C003 | `manual` 冲突字段跳过或建议化 | integration | AI | PolicyGate 测试 |
| TEST-010 | REQ-010 | 功能点拆解读取历史 adjustment Memory 并回写新 Memory | integration | AI | 任务链路测试 |
| TEST-011 | REQ-011 / REQ-C006 | Skill/Memory 失败返回 `failed/partial_success`，主链路不受阻断 | integration + regression | AI | 错误注入测试 |
| TEST-012 | REQ-012 / REQ-105 / REQ-C002 | 旧 schema 与历史评估数据清理核验 | deployment smoke | AI | 清理脚本输出 |
| TEST-013 | REQ-C007 | `pyproject.toml` / `requirements.txt` / `backend/requirements.txt` / `frontend/package.json` 运行时依赖 diff | static check | AI | 依赖 diff 命令 |

### 7.2 验收清单（可勾选）

- [ ] 所有 REQ-xxx / REQ-Cxxx 均有对应验证证据
- [ ] PM 导入页、系统画像页、服务治理页、系统清单导入页首屏都可正常渲染
- [ ] `profile/execution-status` 与 `profile/extraction-status` 兼容返回一致
- [ ] 系统清单非空画像 skip 已被 E2E 证据证明
- [ ] 三类 Memory 写入覆盖率达到 100%
- [ ] 现有评估主链路已完成回归
- [ ] 清理与回滚步骤已演练或具备演练计划

## 8. 风险与开放问题

### 8.1 风险清单

| 风险 | 影响 | 概率 | 应对措施 | Owner |
|---|---|---|---|---|
| 旧 `SystemProfileBoardPage` 与新 canonical schema 改造不完整 | 页面渲染错误或字段丢失 | 中 | 以前后端共享字段常量和渲染 smoke test 兜底 | 前端 |
| `profile_summary_service` 适配到新 schema 时输出不稳定 | PM suggestions 质量下降 | 中 | 通过 Skill adapter 做字段映射与空值归一 | 后端 |
| `memory_records.json` 增长过快 | 查询延迟上升 | 中 | 按 `system_id` 分桶 + 分页 + retention | 后端 |
| 系统清单 blank 判定实现错误 | 非空画像被误初始化 | 低 | 独立单元测试 + E2E + 开关灰度 | 后端 |
| 服务治理 exact-name 匹配不足 95% | 指标不达标 | 中 | 复用 `esb_service` 别名与 header mapping；把 unmatched 显式暴露 | 后端 |

### 8.2 开放问题（必须收敛）

- [ ] 无阻塞性开放问题；当前方案已按用户最新口径收敛，可进入 Planning。

## 10. 变更记录

| 版本 | 日期 | 修改章节 | 说明 | 作者 |
|---|---|---|---|---|
| v0.1 | 2026-03-13 | 初始化 | 完成 v2.7 Design 首版，覆盖 Runtime、schema、Memory、系统清单补空规则与 API 契约 | Codex |
| v0.2 | 2026-03-13 | 环境/Skill/系统清单收敛 | 删除子系统清单设计，补齐 `code_scan_skill` 适配方案与系统清单字段映射，并改为内网生产配置口径 | Codex |
| v0.3 | 2026-03-13 | 文档 skill 有效性边界 | 基于需求/技术方案样本文档补充 `requirements_skill`、`tech_solution_skill`、`design_skill` 的有效性范围与格式边界 | Codex |
| v0.4 | 2026-03-14 | 服务治理模板口径 | 明确 `service_governance_skill` 的最新模板样例以 `data/esb-template.xlsx` 为准，并要求兼容历史 `data/接口申请模板.xlsx` 输入 | Codex |
