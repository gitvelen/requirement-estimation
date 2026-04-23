# design.md

## Default Read Layer

**说明**：本章节是设计完成时的快照索引，用于快速浏览核心结构。详细内容以正文各章节为准，索引可能滞后于正文更新。

### Goal / Scope Link
- requirement_refs:
  - REQ-001
  - REQ-002
  - REQ-003
  - REQ-004
- acceptance_refs:
  - ACC-001
  - ACC-002
  - ACC-003
  - ACC-004
- verification_refs:
  - VO-001
  - VO-002
  - VO-003
  - VO-004
- spec_alignment_check:
  - spec_ref: REQ-001
    aligned: true
    notes: 前端仅重写规则管理页的说明与快速设置文案，去掉“直接控制拆分粒度”的误导表达。
  - spec_ref: REQ-002
    aligned: true
    notes: `/tasks/{task_id}/estimate` 在估算前基于管理员当前维护的 COSMIC 配置执行分析、统一构建并注入 rule context，不把 COSMIC 直接焊进估算 Agent。
  - spec_ref: REQ-003
    aligned: true
    notes: COSMIC 作为首个规则会在当前估算动作内生成统一 rule context 结构，并按功能点记录 degraded 证据。
  - spec_ref: REQ-004
    aligned: true
    notes: 估算仍保留完整需求语义和系统画像上下文，rule context 只作补强输入。

### Architecture Boundary
- impacted_capabilities:
  - 规则管理页 COSMIC 使用说明与快速设置文案
  - 任务估算主链路的规则执行、上下文构建与注入
  - COSMIC 管理配置到运行时分析结果的接入与归一化
  - 估算上下文证据落盘
- not_impacted_capabilities:
  - 功能点拆分 Agent 主算法
  - 系统识别链路
  - 评估报告导出结构
  - 规则管理配置存储结构本身
- impacted_shared_surfaces:
  - frontend/src/pages/CosmicConfigPage.js
  - backend/api/routes.py
  - backend/agent/work_estimation_agent.py
  - backend/utils/cosmic_analyzer.py
  - backend/service/system_profile_service.py
- not_impacted_shared_surfaces:
  - backend/agent/feature_breakdown_agent.py
  - backend/prompts/prompt_templates.py 中拆分提示词
  - backend/api/cosmic_routes.py 的独立配置接口
- major_constraints:
  - 不新增管理员可配置的运行时拆分粒度开关。
  - 不重写现有功能点拆分主链路，只在估算入口补入最小必要的规则执行与上下文层。
  - 规则失败处理必须按功能点降级，并留下后台证据；不得整任务静默回退。
  - 估算仍必须保留完整原始需求语义，不能退化为只看短描述或只看规则摘要。
- contract_required: false
- compatibility_constraints:
  - 现有 `/tasks/{task_id}/estimate` 返回结构继续兼容现有字段，可在不破坏旧字段的前提下补充 rule context 证据相关字段。
  - `build_estimation_context()` 继续作为统一上下文入口扩展，不另造平行上下文体系。
  - 后续接入其他估算规则时必须复用统一 `rule_context` 结构，而不是为 COSMIC 写专用旁路协议。

### Work Item Execution Strategy

#### Dependency Analysis
dependency_graph:
  WI-001:
    depends_on: []
    blocks: []
    confidence: high

#### Parallel Recommendation
parallel_groups:
  - group: G1
    work_items: [WI-001]
    can_parallel: false
    rationale: 前端说明纠偏、后端上下文结构、测试与证据落盘都围绕同一条估算链路与同一组共享文件，拆开只会增加冲突面。

#### Branch Strategy Recommendation
recommended_branch_count: 1
rationale: |
  本次改动虽然跨前后端，但都围绕单一目标收敛：纠正规则管理说明，并把 COSMIC 规则接入估算主链路。
  单分支推进更适合保持 `spec -> design -> work-item -> tests -> code` 的一致性，也能避免多 WI 争夺 `backend/api/routes.py`、`backend/agent/work_estimation_agent.py` 和 `frontend/src/pages/CosmicConfigPage.js`。

alternative_if_parallel_needed: |
  若后续要继续扩展到第二套估算规则，可在下一轮把“统一规则上下文层”与“具体规则实现”拆成两个 WI。
  当前不建议预拆。

**Note**: The above three sections (Dependency Analysis, Parallel Recommendation, Branch Strategy Recommendation)
are suggestions only, not enforced by gates. User decides the actual execution strategy.

#### Shared Surface Analysis
potentially_conflicting_files:
  - path: frontend/src/pages/CosmicConfigPage.js
    reason: 使用说明、快速设置和现有字段标签集中在同一页，文案边界必须统一。
    recommendation: 所有“粒度”相关描述一次性收口，避免局部改文案后留下残余误导。
  - path: backend/api/routes.py
    reason: `/tasks/{task_id}/estimate` 是规则上下文接入主链路的唯一关键入口。
    recommendation: 在这里集中完成 rule context 构建、注入和证据落盘，不在多处重复拼装。
  - path: backend/agent/work_estimation_agent.py
    reason: 估算 Agent 需要消费统一 rule context，同时保留完整语义上下文。
    recommendation: 只扩展统一入参和提示上下文，不直接依赖 COSMIC 私有对象。
  - path: backend/service/system_profile_service.py
    reason: 当前估算上下文与证据落盘都由这里承载，规则上下文证据应在同一产物层补齐。
    recommendation: 以扩展已有 `build_estimation_context` / `record_estimation_context_artifact` 为主，不另建平行存储。

conflict_risk_assessment:
  high_risk:
    - backend/api/routes.py
    - backend/agent/work_estimation_agent.py
  medium_risk:
    - backend/service/system_profile_service.py
    - frontend/src/pages/CosmicConfigPage.js
  low_risk:
    - frontend/src/__tests__/cosmicConfigPage.render.test.js
    - tests/test_task_reevaluate_api.py
    - tests/test_evaluation_contract_api.py

#### Pre-work for Parent Feature Branch
tasks:
  - task: 清理旧主题设计残留
    content: |
      把 design.md、work-items/WI-001.yaml、testing.md 中上一轮“附件解析”主题内容替换为当前 COSMIC/估算规则主题。
    rationale: 若不先统一权威文档，后续 gate 会因为追溯和 work-item 对齐失败而阻塞。
  - task: 固定统一 rule_context 结构
    content: |
      在 design 中先冻结统一结构：`rule_id`、`rule_name`、`status`、`summary_text`、`structured_payload`、`failure_reason`。
    rationale: 这样后续估算 Agent 与 COSMIC 分析器的边界就不会继续摇摆。

#### Notes
- 当前设计故意不把“可配置拆分粒度”纳入交付范围，避免继续放大误导语义。
- 当前设计只要求后台可追溯规则是否被应用，不要求前台新增规则使用证据展示。

### Design Slice Index
- DS-001:
  - appendix_ref: none
  - scope: 纠正规则管理页说明，并在估算主链路中引入统一规则执行与上下文层，由 COSMIC 作为首个规则在点击估算时接入并产出按功能点可追溯证据。
  - requirement_refs: [REQ-001, REQ-002, REQ-003, REQ-004]
  - acceptance_refs: [ACC-001, ACC-002, ACC-003, ACC-004]
  - verification_refs: [VO-001, VO-002, VO-003, VO-004]

### Work Item Derivation
- wi_id: WI-001
  input_refs:
    - docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
    - docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#clarifications
  requirement_refs:
    - REQ-001
    - REQ-002
    - REQ-003
    - REQ-004
  goal: 在不重写拆分链路的前提下，完成规则管理页说明纠偏，并让 COSMIC 管理配置在点击估算时通过统一 rule context 真正进入估算主链路，保留按功能点可追溯的降级证据。
  covered_acceptance_refs: [ACC-001, ACC-002, ACC-003, ACC-004]
  verification_refs:
    - VO-001
    - VO-002
    - VO-003
    - VO-004
  dependency_refs: []
  contract_needed: false
  notes_on_boundary: 允许修改前端说明页、估算 API/Agent、COSMIC 分析器、系统画像上下文服务及相关测试；不允许扩散到拆分 Agent、系统识别或报告导出。
  work_item_alignment: keep equal to work-items/WI-001.yaml acceptance_refs

### Contract Needs
- no additional contract required; the change stays within existing API shape and internal estimation context artifacts.

### Failure Paths / Reopen Triggers
- 如果实现中发现必须通过前台新增“规则使用证据展示”才能满足验收，需要先回写 spec/design 再扩 scope。
- 如果统一 rule context 无法兼容未来其他估算规则，需要先回写 design 重新定义扩展点。
- 如果要让 COSMIC 直接参与拆分粒度控制，而不是只作为估算前规则上下文，必须重新开启 spec 决策，不在本次实现中追加。

### Appendix Map
- none

## Goal / Scope Link

### Scope Summary
- 前端只做说明纠偏：保留管理员理解 COSMIC 配置所需的必要说明，去掉会让人理解为“页面直接控制当前拆分粒度”的表述。
- 后端在估算入口先按管理员当前维护的 COSMIC 配置对待估功能点执行分析，再统一构建 `rule_context`，将“规则是否被执行、是否应用成功、规则摘要与结构化载荷”显式注入估算 Agent。
- COSMIC 作为首个规则实现运行时分析与 `rule_context` 归一化，并在单个功能点规则失败时输出 `degraded` 证据，而不是整任务静默退回。
- 估算提示继续以完整需求语义和系统画像为主，`rule_context` 只作为补强信息，禁止替代原始文本。

### spec_alignment_check
- spec_ref: REQ-001
  aligned: true
  notes: 设计只改文案和帮助信息，不把当前历史“细/中/粗”教学示例继续表达为现网拆分控制能力。
- spec_ref: REQ-002
  aligned: true
  notes: 规则上下文层在 `/tasks/{task_id}/estimate` 统一构建，且构建前会按管理员当前维护的 COSMIC 配置触发分析，再通过通用入参扩展到估算 Agent。
- spec_ref: REQ-003
  aligned: true
  notes: COSMIC 分析器负责在当前估算动作内生成分析结果、归一成统一 rule context，并在失败时留下 `failure_reason` 与功能点级降级状态。
- spec_ref: REQ-004
  aligned: true
  notes: 估算 Agent 继续消费完整原始描述、系统画像上下文和功能点信息，rule context 仅作为补充块拼入提示词。

## Architecture Boundary
- system_context: 当前估算链路以 `/tasks/{task_id}/estimate -> COSMIC analyze -> build rule_context -> build_estimation_context -> work_estimation_agent.estimate_three_point_for_feature` 为主线；本次在这条链路中补入统一规则执行与上下文消费。
- impacted_capabilities:
  - COSMIC 说明文案纠偏
  - 估算规则运行时执行与上下文构建
  - COSMIC 管理配置到运行时分析结果的归一化
  - 估算证据落盘扩展
- not_impacted_capabilities:
  - 功能点拆分 prompt 和拆分实现
  - 系统识别编排
  - 报告生成和下载
  - COSMIC 配置持久化接口
- impacted_shared_surfaces:
  - frontend/src/pages/CosmicConfigPage.js
  - backend/api/routes.py
  - backend/agent/work_estimation_agent.py
  - backend/utils/cosmic_analyzer.py
  - backend/service/system_profile_service.py
- not_impacted_shared_surfaces:
  - backend/agent/feature_breakdown_agent.py
  - backend/agent/agent_orchestrator.py
  - backend/api/cosmic_routes.py
- major_constraints:
  - 统一 `rule_context` 必须对未来其他规则可复用，因此字段名和语义必须通用。
  - COSMIC 分析必须在点击估算时执行，避免消费过期的历史中间结果。
  - COSMIC 分析失败时仅允许功能点级降级，不能使整次估算失败。
  - 规则证据只要求后台可追溯，不新增前台证据展示义务。
  - 所有新增测试必须围绕当前 acceptance 设计，避免“顺手重构”无关实现。
- contract_required: false
- compatibility_constraints:
  - `/tasks/{task_id}/estimate` 现有 `features` 列表返回必须继续可用。
  - `record_estimation_context_artifact()` 继续写 output artifact，但 payload 可补 rule context 相关字段。
  - 不修改任务存储的根结构，只在 feature 明细和 artifact 中增加兼容字段。

## Work Item Execution Strategy

### Dependency Analysis
dependency_graph:
  WI-001:
    depends_on: []
    blocks: []
    confidence: high

### Parallel Recommendation
parallel_groups:
  - group: G1
    work_items: [WI-001]
    can_parallel: false
    rationale: 单个 WI 已覆盖前端文案、后端估算上下文和相关测试，拆开会在共享文件上产生无谓冲突。

### Branch Strategy Recommendation
recommended_branch_count: 1
rationale: |
  本轮是一次小而集中的行为纠偏和链路补强，单 WI 单分支最容易保持追溯清晰。
  尤其 `backend/api/routes.py`、`backend/agent/work_estimation_agent.py` 和 `frontend/src/pages/CosmicConfigPage.js` 都是共享面，串行推进更稳妥。

alternative_if_parallel_needed: |
  后续若引入第二套估算规则，可把“统一规则框架”和“具体规则实现”分开，但当前不需要。

**Note**: The above three sections (Dependency Analysis, Parallel Recommendation, Branch Strategy Recommendation)
are suggestions only, not enforced by gates. User decides the actual execution strategy.

### Shared Surface Analysis
potentially_conflicting_files:
  - path: frontend/src/pages/CosmicConfigPage.js
    reason: 说明文案和快速设置入口集中在同一组件内。
    recommendation: 一次性替换所有误导性表述，避免局部遗漏。
  - path: backend/api/routes.py
    reason: 估算入口在这里触发 COSMIC 分析、拼装上下文并写回 feature 字段。
    recommendation: 所有 COSMIC 分析触发、rule context 的构建、调用与落盘都集中在该入口完成。
  - path: backend/agent/work_estimation_agent.py
    reason: 这里控制估算提示词与降级逻辑。
    recommendation: 新增通用参数，避免对 COSMIC 结构形成硬编码依赖。
  - path: backend/service/system_profile_service.py
    reason: 现有估算上下文与 artifact 写入都在这里。
    recommendation: 沿用现有上下文载体，扩展而不平行复制。

conflict_risk_assessment:
  high_risk:
    - backend/api/routes.py
    - backend/agent/work_estimation_agent.py
  medium_risk:
    - frontend/src/pages/CosmicConfigPage.js
    - backend/service/system_profile_service.py
  low_risk:
    - backend/utils/cosmic_analyzer.py
    - frontend/src/__tests__/cosmicConfigPage.render.test.js
    - tests/test_task_reevaluate_api.py
    - tests/test_evaluation_contract_api.py

### Pre-work for Parent Feature Branch
tasks:
  - task: 冻结设计中的统一 rule_context 字段与执行时机
    content: |
      `rule_id`、`rule_name`、`status`、`summary_text`、`structured_payload`、`failure_reason`，并明确 COSMIC 在点击估算时执行，而不是只消费历史 `cosmic_analysis`。
    rationale: 防止后续实现时把 COSMIC 私有字段直接扩散进多个层级，也防止规则配置的生效时机继续摇摆。
  - task: 限定单 WI 允许改动路径
    content: |
      只允许修改前端说明页、估算 API/Agent、COSMIC 分析器、系统画像服务与对应测试。
    rationale: 防止本轮演变成“顺手改拆分算法”或“顺手加前台证据展示”。

### Notes
- 本次不要求 COSMIC 一定“正确估值”，要求的是“被选择的规则确实被结构化消费，并能证明是否成功应用”。
- `fine / medium / coarse` 字段本身暂不移除，但其文案语义要回到组织内部计量口径配置，不再暗示现网拆分控制能力。
- 当前设计明确把 COSMIC 的执行时机收敛到点击估算，避免“配置只影响旁路分析器、不影响真实估算任务”的半闭环状态。

## Design Slice Index
- DS-001:
  - appendix_ref: none
  - scope: 前端说明纠偏 + 后端点击估算时执行 COSMIC 分析并构建统一规则上下文层 + 按功能点降级证据。
  - requirement_refs: [REQ-001, REQ-002, REQ-003, REQ-004]
  - acceptance_refs: [ACC-001, ACC-002, ACC-003, ACC-004]
  - verification_refs: [VO-001, VO-002, VO-003, VO-004]

## Work Item Derivation
- wi_id: WI-001
  input_refs:
    - docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
    - docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#clarifications
  requirement_refs:
    - REQ-001
    - REQ-002
    - REQ-003
    - REQ-004
  goal: 在估算入口引入统一 rule context，并让点击估算时主动执行 COSMIC 分析，完成 COSMIC 使用说明纠偏与后台证据闭环。
  covered_acceptance_refs: [ACC-001, ACC-002, ACC-003, ACC-004]
  verification_refs:
    - VO-001
    - VO-002
    - VO-003
    - VO-004
  dependency_refs: []
  contract_needed: false
  notes_on_boundary: 允许修改前端文案页、估算 API/Agent、COSMIC 分析器、系统画像服务和相关测试；不允许修改拆分 Agent、系统识别、报告导出或其他无关前端页面。
  work_item_alignment: keep equal to work-items/WI-001.yaml acceptance_refs

## Contract Needs
- contract_id: none
  required: false
  reason: 现有改动不引入新的外部接口契约，只在内部上下文和兼容字段上扩展。
  consumers: []

## Implementation Readiness Baseline

### Environment Configuration Matrix
- 前端测试继续使用现有 Jest 环境，验证 `CosmicConfigPage` 文案渲染与 payload merge 行为。
- 后端测试继续使用 pytest + FastAPI TestClient，不引入新的外部服务依赖。
- 若环境已启用 `ENABLE_V27_PROFILE_SCHEMA`，估算上下文扩展必须兼容当前 `build_estimation_context()` 返回形状。

### Security Baseline
- 规则上下文只在已有任务所有者可触发的 `/tasks/{task_id}/estimate` 链路中使用，不新增越权入口。
- COSMIC 分析执行也只在已有任务所有者可触发的 `/tasks/{task_id}/estimate` 链路中发生，不新增越权入口。
- 估算证据 artifact 继续沿用现有 output artifact 写入路径，不新增公开读接口。
- 前端说明纠偏不改变权限模型，规则管理页仍仅管理员可写。

### Data / Migration Strategy
- 不做数据库或持久化结构迁移。
- 任务内 feature 明细允许在估算时即时生成或覆盖 `cosmic_analysis` / `rule_context` 兼容字段；历史任务缺失这些字段时，应在当前估算动作内即时补齐，而不是直接判定为缺失。
- 估算 artifact payload 扩展为向后兼容追加字段，不要求回填历史产物。

### Operability / Health Checks
- COSMIC 分析或规则上下文生成失败时必须记录 `degraded` / `failure_reason`，便于后台排查“规则是否真的在当前估算动作中被用到”。
- 估算主链路仍应返回结果，即使部分功能点的规则上下文降级。
- 日志中需要能区分 LLM 估算失败与规则上下文生成失败两类降级来源。

### Backup / Restore
- 本轮不引入新的持久化根目录或新文件类型，沿用现有 artifact 目录与任务存储备份策略。
- 如需回滚，只需回退代码和新增 artifact 字段消费逻辑，不涉及数据迁移回滚。

### UX / Experience Readiness
- “使用说明”需让管理员一眼理解哪些字段是计量口径配置，哪些不是现网拆分控制。
- 快速设置的命名和说明必须避免再出现“每个按钮/操作=1个功能点”这类能力承诺式表述。

## Verification Design
- ACC-001:
  - approach: 更新前端渲染测试，验证 Modal 说明和快速设置文案已去除“直接控制拆分粒度”的误导，并保留必要配置说明。
  - evidence: `frontend/src/__tests__/cosmicConfigPage.render.test.js` 通过。
- ACC-002:
  - approach: 更新任务估算 API 测试，验证估算前会按管理员当前维护的 COSMIC 配置触发分析、构建统一 rule context，并显式传入估算 Agent；规则禁用或显式跳过时状态为 degraded/skipped。
  - evidence: `tests/test_task_reevaluate_api.py` 或等效测试通过。
- ACC-003:
  - approach: 为 COSMIC 分析器 / 估算入口补测试，验证点击估算时确实按管理员配置触发分析、统一 rule context 结构、功能点级 degraded 状态与后台 artifact 证据。
  - evidence: 后端新增或更新测试通过，且 artifact payload 包含规则状态、失败原因和当前估算动作内生成的规则结果。
- ACC-004:
  - approach: 为估算 Agent 增加测试，验证其入参同时保留完整需求语义、系统画像上下文与 rule context，提示输入不退化为短描述摘要。
  - evidence: 后端新增或更新测试通过，并能断言提示中包含完整上下文块。

## Failure Paths / Reopen Triggers
- 如果实现必须修改功能点拆分 prompt 或拆分主链路，需回到 spec/design 重新界定范围。
- 如果现有 `functional_process_rules.granularity` 字段被证明无法保留其现有存储语义，需要先做产品决策，再回写 spec。
- 如果要把规则使用证据暴露到前台页面，而不仅是后台 artifact，需要重新开边界。
- 如果发现点击估算时执行 COSMIC 分析会引入不可接受的额外时延或 LLM 成本，需要先回到 design 重新决策是否引入缓存或预分析机制。

## Appendix Map
- none
