# design.md

## Default Read Layer

**说明**：本章节是设计完成时的快照索引，用于快速浏览核心结构。详细内容以正文各章节为准，索引可能滞后于正文更新。

### Goal / Scope Link
- requirement_refs:
  - REQ-001
  - REQ-002
  - REQ-003
  - REQ-004
  - REQ-005
- acceptance_refs:
  - ACC-001
  - ACC-002
  - ACC-003
  - ACC-004
  - ACC-005
- verification_refs:
  - VO-001
  - VO-002
  - VO-003
  - VO-004
  - VO-005
- spec_alignment_check:
  - spec_ref: REQ-001
    aligned: true
    notes: 创建页新增必填单选，但不把该字段外溢到任务列表。
  - spec_ref: REQ-003
    aligned: true
    notes: 具体系统模式通过 orchestrator 分支跳过系统识别，仍保留全文需求和系统画像上下文。
  - spec_ref: REQ-005
    aligned: true
    notes: 单系统锁定同时落在编辑页入口和后端系统级接口拒绝逻辑。

### Architecture Boundary
- impacted_capabilities:
  - 任务创建页输入收集与提交校验
  - 任务创建接口校验与任务元数据持久化
  - AI 编排器的具体系统/不限分支
  - 任务详情展示与编辑页单系统锁定
- not_impacted_capabilities:
  - 任务列表展示列与筛选
  - 专家分配、多轮评估与报告导出
  - 系统识别算法本身与主系统配置后台
- impacted_shared_surfaces:
  - backend/api/routes.py
  - backend/agent/agent_orchestrator.py
  - frontend/src/pages/UploadPage.js
  - frontend/src/pages/ReportPage.js
  - frontend/src/pages/EditPage.js
- not_impacted_shared_surfaces:
  - frontend/src/pages/TaskListPage.js
  - backend/api/report_routes.py
  - backend/agent/system_identification_agent.py
- major_constraints:
  - 项目经理相关系统口径复用主责+B角规则，不新增权限模型
  - 具体系统模式禁止做 alias-only 段落裁剪
  - 单系统锁定以后端拒绝为准，前端隐藏仅作辅助
- contract_required: false
- compatibility_constraints:
  - unlimited 模式保持现有系统识别优先顺序
  - 任务列表和专家侧交互不新增字段依赖

### Work Item Execution Strategy

#### Dependency Analysis
dependency_graph:
  WI-001:
    depends_on: []
    blocks: [WI-002, WI-003]
    confidence: high
  WI-002:
    depends_on: [WI-001]
    blocks: [WI-003]
    confidence: high
  WI-003:
    depends_on: [WI-001, WI-002]
    blocks: []
    confidence: high

#### Parallel Recommendation
parallel_groups:
  - group: G1
    work_items: [WI-001, WI-002, WI-003]
    can_parallel: false
    rationale: `backend/api/routes.py` 是创建、详情、编辑和后台处理的共享面，单分支串行能避免协议和字段名漂移。

#### Branch Strategy Recommendation
recommended_branch_count: 1
rationale: |
  当前改动的共享事实来源是 task record 与 routes.py。
  在禁止使用 worktree 的前提下，单分支顺序推进最能避免前后端协议不一致与冲突性回滚。

alternative_if_parallel_needed: |
  如果后续必须并行，只能让 parent feature 分支统一集成 backend/api/routes.py；
  前端执行线仅独占 UploadPage.js / ReportPage.js / EditPage.js，后端执行线独占 agent_orchestrator.py。

**Note**: The above three sections (Dependency Analysis, Parallel Recommendation, Branch Strategy Recommendation)
are suggestions only, not enforced by gates. User decides the actual execution strategy.

#### Shared Surface Analysis
potentially_conflicting_files:
  - path: backend/api/routes.py
    reason: 创建接口、任务详情、编辑接口和后台任务处理流程全部集中在此文件
    recommendation: 所有 WI 顺序执行，routes.py 由当前 feature 分支串行集成
  - path: frontend/src/pages/EditPage.js
    reason: 同时受目标系统元数据和系统级锁定策略影响
    recommendation: 在 WI-003 中一次完成数据消费、入口隐藏和错误反馈
  - path: backend/api/system_routes.py
    reason: 需要补可复用的主责/B角解析 helper，供创建接口服务端校验复用
    recommendation: helper 只处理系统候选解析，不把 task 逻辑回灌到 system_routes

conflict_risk_assessment:
  high_risk:
    - backend/api/routes.py
  medium_risk:
    - frontend/src/pages/EditPage.js
    - backend/agent/agent_orchestrator.py
  low_risk:
    - frontend/src/pages/UploadPage.js
    - frontend/src/pages/ReportPage.js

#### Pre-work for Parent Feature Branch
tasks:
  - task: 统一任务字段命名
    content: |
      task record 持久化字段采用：
      - target_system_mode: "specific" | "unlimited"
      - target_system_name: 具体系统名或空字符串
      详情接口返回 targetSystemMode / targetSystemName / targetSystemDisplay；
      编辑结果接口返回 target_system_mode / target_system_name。
    rationale: 降低前后端和测试在命名上的额外转换成本
  - task: 明确单系统锁定判定
    content: |
      single_system_locked := target_system_mode == "specific"
    rationale: 让 UI 隐藏、接口拒绝和测试断言共享同一规则
  - task: 保留 ai_system_analysis 的现有数据形状
    content: |
      具体系统模式依然生成 selected_systems / candidate_systems / result_status 等结构，
      仅在 system_recognition 快照中标记 skipped。
    rationale: 避免 EditPage 现有读取逻辑额外分叉

#### Notes
- 当前 feature 分支只做顺序执行，不规划并行执行组。
- Design 阶段不新增 contract 文件。
- `不限` 与 `具体系统` 的差异只允许发生在创建参数校验、编排入口和编辑锁定，不外溢到任务列表。

### Design Slice Index
- DS-001 -> 创建页输入、候选项来源与任务元数据通路
- DS-002 -> 具体系统编排分支与 unlimited 兼容路径
- DS-003 -> 详情展示与编辑期单系统锁定

### Work Item Derivation
- wi_id: WI-001
  input_refs:
    - docs/inputs/2026-04-19-target-system-scope.md#intent
    - docs/inputs/2026-04-19-target-system-scope.md#system-scope-rule
    - docs/inputs/2026-04-19-target-system-scope.md#empty-owned-systems
  requirement_refs:
    - REQ-001
    - REQ-002
  goal: 打通创建页待评估系统输入、候选项来源、后端创建校验与任务详情/结果基础字段
  covered_acceptance_refs: [ACC-001, ACC-002]
  verification_refs:
    - VO-001
    - VO-002
  dependency_refs: []
  contract_needed: false
  notes_on_boundary: 创建入口与基础元数据优先落地，但不进入 AI 编排分支改造
- wi_id: WI-002
  input_refs:
    - docs/inputs/2026-04-19-target-system-scope.md#single-system-scope
    - docs/inputs/2026-04-19-target-system-scope.md#no-match
  requirement_refs:
    - REQ-003
    - REQ-004
  goal: 在后台任务处理与 agent orchestrator 中增加 specific/unlimited 分支，并保证零功能点失败语义
  covered_acceptance_refs: [ACC-003, ACC-004]
  verification_refs:
    - VO-003
    - VO-004
  dependency_refs:
    - WI-001
  contract_needed: false
  notes_on_boundary: 保持 system_identification_agent 和 feature_breakdown_agent 内部算法不改，只在 orchestrator 与 task flow 处分支
- wi_id: WI-003
  input_refs:
    - docs/inputs/2026-04-19-target-system-scope.md#visibility
    - docs/inputs/2026-04-19-target-system-scope.md#edit-constraints
  requirement_refs:
    - REQ-002
    - REQ-005
  goal: 在详情页和编辑页展示待评估系统结果，并对具体系统任务施加前后端双重锁定
  covered_acceptance_refs: [ACC-002, ACC-005]
  verification_refs:
    - VO-002
    - VO-005
  dependency_refs:
    - WI-001
    - WI-002
  contract_needed: false
  notes_on_boundary: 功能点级编辑与任务级重估保留，系统级新增/重命名/删除/重新拆分一律封禁

### Contract Needs
- none: 当前变更不新增 shared contract；任务元数据与接口字段可直接在现有 FastAPI 响应中扩展

### Failure Paths / Reopen Triggers
- 如果发现“项目经理相关系统”并不能稳定复用当前主责+B角解析结果，需要 reopen spec 与 design 对齐数据来源。
- 如果单系统模式必须修改系统识别算法或系统画像算法本身，需 reopen design 评估是否越过 NG1。
- 如果编辑阶段后续还要支持“改选另一个具体系统”，需 reopen spec，因为这直接冲突 REQ-002 / P2。
- 如果 `backend/api/routes.py` 的共享改动导致当前 WI 切分无法顺序落地，需要 reopen design 重新拆分 work item。

### Appendix Map
- No appendices.

## Goal / Scope Link

### Scope Summary
- 本次设计只覆盖项目经理发起任务、AI 处理编排、任务详情展示与编辑期边界控制四段链路。
- 设计目标是把“待评估系统”从创建期显式输入一路传到任务记录、编排分支和后续页面，而不是在前端临时态上做一次性分流。
- `不限` 作为兼容模式保持原链路不变；具体系统作为新链路在 orchestrator 入口处分叉，并保持全文需求 + 系统画像的拆分上下文。

### spec_alignment_check
- spec_ref: REQ-001
  aligned: true
  notes: 创建页以单选方式承载必填选择，无相关系统时仅保留“不限”。
- spec_ref: REQ-002
  aligned: true
  notes: 任务记录持久化 mode/name，详情页与编辑结果接口都返回该元数据。
- spec_ref: REQ-003
  aligned: true
  notes: 单系统模式在 orchestrator 层跳过系统识别，直接进入指定系统拆分与估算。
- spec_ref: REQ-004
  aligned: true
  notes: unlimited 模式继续复用现有 process_requirement 主链路，不改系统识别顺序。
- spec_ref: REQ-005
  aligned: true
  notes: 锁定同时体现在系统级接口拒绝和编辑页不暴露系统操作入口。

## Architecture Boundary
- system_context: FastAPI + in-memory/json task storage + React 单页前端；任务创建、处理和编辑都围绕 `backend/api/routes.py` 维护的 task 记录展开。
- impacted_capabilities:
  - UploadPage 创建表单与 multipart 提交协议
  - 主系统清单按主责/B角过滤后的候选项生成
  - create_task_v2 的表单校验、任务元数据持久化与详情返回
  - process_task_sync / AgentOrchestrator 的 single-system 分支
  - ReportPage / EditPage 的目标系统展示和锁定判定
  - requirement 系统级编辑接口的锁定保护
- not_impacted_capabilities:
  - TaskListPage 列定义与列表筛选
  - 专家分配、邀请、专家评估提交、偏差计算与报告导出
  - 系统识别 agent 的识别算法、系统画像摘要算法、主系统配置 CRUD
- impacted_shared_surfaces:
  - backend/api/routes.py
  - backend/agent/agent_orchestrator.py
  - frontend/src/pages/UploadPage.js
  - frontend/src/pages/ReportPage.js
  - frontend/src/pages/EditPage.js
  - frontend/src/utils/systemOwnership.js
  - backend/api/system_routes.py
- not_impacted_shared_surfaces:
  - frontend/src/pages/TaskListPage.js
  - backend/api/report_routes.py
  - backend/agent/system_identification_agent.py
  - backend/agent/work_estimation_agent.py
- major_constraints:
  - 候选项口径必须与系统清单里的主责/B角解析一致，前端展示不能成为权限真相。
  - 具体系统模式必须把全文 requirement_content 直接交给功能点拆分 agent，不允许先做名称命中裁剪。
  - 无功能点场景必须失败，不能以空 `systems_data` 成功落盘。
  - 编辑期锁定必须以服务端接口拒绝为准，前端隐藏仅作为辅助手段。
- contract_required: false
- compatibility_constraints:
  - `POST /api/v1/tasks` 继续使用 multipart/form-data，只新增两个 form 字段，不改文件上传方式。
  - `GET /api/v1/tasks/{task_id}` 与 `GET /api/v1/requirement/result/{task_id}` 在原 payload 上增字段，不移除既有字段。
  - `不限` 模式继续产出 `systems` / `systems_data` 多系统结构，确保 ReportPage、EditPage、专家侧无额外适配成本。

## Work Item Execution Strategy

### Dependency Analysis
dependency_graph:
  WI-001:
    depends_on: []
    blocks: [WI-002, WI-003]
    confidence: high
  WI-002:
    depends_on: [WI-001]
    blocks: [WI-003]
    confidence: high
  WI-003:
    depends_on: [WI-001, WI-002]
    blocks: []
    confidence: high

### Parallel Recommendation
parallel_groups:
  - group: G1
    work_items: [WI-001, WI-002, WI-003]
    can_parallel: false
    rationale: task 元数据、详情响应和系统级锁定都依赖 `backend/api/routes.py` 的同一批字段，串行更安全。

### Branch Strategy Recommendation
recommended_branch_count: 1
rationale: |
  该变更虽然同时涉及前后端，但真正的共享事实来源是 task record 和 routes.py。
  在不使用 worktree 的约束下，单分支顺序推进最能避免字段名漂移、前后端协议不一致和冲突性回滚。

alternative_if_parallel_needed: |
  如果后续必须并行，只能让 parent feature 分支统一集成 backend/api/routes.py；
  前端执行线仅独占 UploadPage.js / ReportPage.js / EditPage.js，后端执行线独占 agent_orchestrator.py。

**Note**: The above three sections (Dependency Analysis, Parallel Recommendation, Branch Strategy Recommendation)
are suggestions only, not enforced by gates. User decides the actual execution strategy.

### Shared Surface Analysis
potentially_conflicting_files:
  - path: backend/api/routes.py
    reason: 创建接口、任务详情、编辑接口和后台任务处理流程全部集中在此文件
    recommendation: 作为单分支串行集成文件，禁止把它拆成并行 WI 的共享写面
  - path: frontend/src/pages/EditPage.js
    reason: 既要消费新的 target system 元数据，又要调整系统操作入口
    recommendation: 在 WI-003 中一次完成结果加载、操作入口隐藏和错误反馈
  - path: backend/api/system_routes.py
    reason: 需要补可复用的主责/B角解析 helper，供创建接口复用
    recommendation: helper 只做候选解析，不把 task 逻辑反向塞回 system_routes

conflict_risk_assessment:
  high_risk:
    - backend/api/routes.py
  medium_risk:
    - frontend/src/pages/EditPage.js
    - backend/agent/agent_orchestrator.py
  low_risk:
    - frontend/src/pages/UploadPage.js
    - frontend/src/pages/ReportPage.js
    - frontend/src/utils/systemOwnership.js

### Pre-work for Parent Feature Branch
tasks:
  - task: 统一任务字段命名
    content: |
      task record 持久化字段采用：
      - target_system_mode: "specific" | "unlimited"
      - target_system_name: 具体系统名或空字符串
      详情接口返回 targetSystemMode / targetSystemName / targetSystemDisplay；
      编辑结果接口返回 target_system_mode / target_system_name。
    rationale: 降低前后端和测试在命名上的额外转换成本
  - task: 明确单系统锁定判定
    content: |
      single_system_locked := target_system_mode == "specific"
    rationale: 让 UI 隐藏、接口拒绝和测试断言共享同一规则
  - task: 保留 ai_system_analysis 的现有数据形状
    content: |
      具体系统模式依然生成 selected_systems / candidate_systems / result_status 等结构，
      仅在 system_recognition 快照中标记 skipped。
    rationale: 避免 EditPage 现有读取逻辑额外分叉

### Notes
- 当前 feature 分支只做顺序执行，不规划并行执行组。
- Design 阶段不新增 contract 文件。
- `不限` 与 `具体系统` 的差异只允许发生在创建参数校验、编排入口和编辑锁定，不外溢到任务列表。

## Design Slice Index
- DS-001:
  - appendix_ref: none
  - scope: 创建页待评估系统单选、候选项来源和任务元数据持久化
  - requirement_refs: [REQ-001, REQ-002]
  - acceptance_refs: [ACC-001, ACC-002]
  - verification_refs: [VO-001, VO-002]
- DS-002:
  - appendix_ref: none
  - scope: AI 编排器 specific/unlimited 分支与单系统失败语义
  - requirement_refs: [REQ-003, REQ-004]
  - acceptance_refs: [ACC-003, ACC-004]
  - verification_refs: [VO-003, VO-004]
- DS-003:
  - appendix_ref: none
  - scope: 详情展示与编辑期单系统锁定
  - requirement_refs: [REQ-002, REQ-005]
  - acceptance_refs: [ACC-002, ACC-005]
  - verification_refs: [VO-002, VO-005]

## Work Item Derivation
- wi_id: WI-001
  input_refs:
    - docs/inputs/2026-04-19-target-system-scope.md#intent
    - docs/inputs/2026-04-19-target-system-scope.md#system-scope-rule
    - docs/inputs/2026-04-19-target-system-scope.md#empty-owned-systems
  requirement_refs:
    - REQ-001
    - REQ-002
  goal: 打通创建页待评估系统输入、候选项来源、后端创建校验与任务详情/结果基础字段
  covered_acceptance_refs: [ACC-001, ACC-002]
  verification_refs:
    - VO-001
    - VO-002
  dependency_refs: []
  contract_needed: false
  notes_on_boundary: 创建入口与基础元数据优先落地，但不进入 AI 编排分支改造
- wi_id: WI-002
  input_refs:
    - docs/inputs/2026-04-19-target-system-scope.md#single-system-scope
    - docs/inputs/2026-04-19-target-system-scope.md#no-match
  requirement_refs:
    - REQ-003
    - REQ-004
  goal: 在后台任务处理与 agent orchestrator 中增加 specific/unlimited 分支，并保证零功能点失败语义
  covered_acceptance_refs: [ACC-003, ACC-004]
  verification_refs:
    - VO-003
    - VO-004
  dependency_refs:
    - WI-001
  contract_needed: false
  notes_on_boundary: 保持 system_identification_agent 和 feature_breakdown_agent 内部算法不改，只在 orchestrator 与 task flow 处分支
- wi_id: WI-003
  input_refs:
    - docs/inputs/2026-04-19-target-system-scope.md#visibility
    - docs/inputs/2026-04-19-target-system-scope.md#edit-constraints
  requirement_refs:
    - REQ-002
    - REQ-005
  goal: 在详情页和编辑页展示待评估系统结果，并对具体系统任务施加前后端双重锁定
  covered_acceptance_refs: [ACC-002, ACC-005]
  verification_refs:
    - VO-002
    - VO-005
  dependency_refs:
    - WI-001
    - WI-002
  contract_needed: false
  notes_on_boundary: 功能点级编辑与任务级重估保留，系统级新增/重命名/删除/重新拆分一律封禁

## Contract Needs
- contract_id: none
  required: false
  reason: 当前变更只扩展现有 task payload 和接口字段，不引入跨 WI 独立冻结合约
  consumers: []

## Implementation Readiness Baseline

### Environment Configuration Matrix
- 前端继续使用现有 `axios` 和登录态；无需新增环境变量或新路由前缀。
- 后端继续沿用当前 FastAPI 应用、任务线程池和 `settings.UPLOAD_DIR` / `settings.REPORT_DIR`，本次不新增部署配置。
- `POST /api/v1/tasks` 仍由 manager 角色调用，新增 form 字段不会影响现有 multipart 解析链路。

### Security Baseline
- 创建接口必须以当前登录 manager 身份在服务端重新计算可选系统集合，不能信任前端提交的 system name。
- 任务详情和编辑系统级接口必须继续走现有任务访问控制，只在此基础上叠加 single-system lock。
- 文件上传白名单、大小校验、路径校验和报告下载的现有安全逻辑保持不变。

### Data / Migration Strategy
- 旧任务缺少 `target_system_mode` 时按兼容默认值 `unlimited` 解释，避免历史任务无法打开详情/编辑页。
- `_ensure_task_schema()` 负责为历史 task 补齐 `target_system_mode=unlimited` 与 `target_system_name=""`。
- 不做数据迁移脚本；兼容逻辑在读路径和 task 创建路径内完成。

### Operability / Health Checks
- 具体系统模式失败时直接复用 task failure 状态，`message` 必须可定位为“未拆出该系统相关功能点”而不是泛化异常。
- 编排日志需能区分 `selection_mode=specific` 与 `selection_mode=unlimited`，便于排查是否误走旧分支。
- 如果后端返回 `targetSystemMode/Name` 缺失，ReportPage 和 EditPage 应按 unlimited 兼容显示，而不是白屏。

### Backup / Restore
- 任务数据仍使用现有 task storage 与 report 文件路径；本次不新增持久化副本或额外恢复步骤。
- 若上线后需要快速回滚，只需忽略新字段并恢复创建页旧交互即可，不影响旧任务读取。

### UX / Experience Readiness
- 创建页在系统列表尚未加载完成时需要禁用提交或给出加载态，避免无候选项时误提交。
- 当候选项只有“不限”时，页面仍需允许直接提交，且不把“暂无主责/B角系统”解释为错误。
- 具体系统锁定任务在 EditPage 需要给出清晰说明，只保留功能点级编辑和重估能力。

## Verification Design
- ACC-001:
  - approach: 为 UploadPage 增加渲染测试，并通过 mock `/api/v1/system/systems` + AuthContext 覆盖“有主责/B角系统”和“无主责/B角系统”两种候选项来源。
  - evidence: `frontend/src/__tests__/uploadPage.targetSystem.test.js` 断言字段顺序、必填、候选项顺序以及 only-不限 场景。
- ACC-002:
  - approach: 为 `POST /api/v1/tasks`、`GET /api/v1/tasks/{task_id}` 和 `GET /api/v1/requirement/result/{task_id}` 增加后端测试，覆盖合法 specific、非法 specific、详情回传和创建后不可修改语义。
  - evidence: 后端 API 测试证明任务记录持久化 `target_system_mode/name`，并对外返回一致字段。
- ACC-003:
  - approach: 对 orchestrator 或 `process_task_sync` 做分支测试，使用 stub 断言 specific 模式不会调用系统识别，且零功能点直接失败。
  - evidence: 后端编排测试能观察 specific 分支、单系统输出以及 clear failure message。
- ACC-004:
  - approach: 保留 unlimited 路径回归测试，断言系统识别仍先于拆分执行，且多系统输出结构不变。
  - evidence: 回归测试可观测系统识别调用顺序和多系统 `systems_data` 形态。
- ACC-005:
  - approach: 后端测试覆盖 add/rename/delete/rebreakdown 在锁定任务上的拒绝；前端 EditPage 测试覆盖系统操作入口隐藏或禁用，同时保留功能点级编辑。
  - evidence: `frontend/src/__tests__/editPage.targetSystemLock.test.js` 与后端锁定测试共同证明“前端不暴露 + 后端强拒绝”。

## Failure Paths / Reopen Triggers
- 如果发现具体系统模式必须依赖 prompt/template 级识别改造才能可用，需要 reopen design，并确认是否触碰 NG1。
- 如果创建页无法通过现有系统清单稳定推导主责+B角候选，需要 reopen spec，确认是否要新增专用后端候选接口。
- 如果旧 task 的兼容默认值 `unlimited` 会误导历史详情展示，需要 reopen design，决定是否补一次数据修复。
- 如果 EditPage 还存在其他未枚举的系统级 scope-change 操作，需要 reopen design 补完整锁定矩阵。

## Appendix Map
- No appendices.
