# spec.md

## Default Read Layer

### Intent Summary
- Problem: 当前“规则管理”页的 COSMIC 使用说明把计量口径、功能过程颗粒度示意和实际功能点拆分行为混在一起，管理员容易误以为页面配置会直接控制拆分粒度；同时现有功能点拆分与工作量估算主链路未把 COSMIC 等估算规则作为必经上下文，导致规则容易沦为展示信息，无法证明估算 Agent 真正理解并使用了规则。进一步核查发现，管理员在“规则管理”中维护的 COSMIC 配置虽然会影响独立分析器，但尚未稳定成为所有估算任务的前置执行步骤。
- Goals:
  - G1: 优化规则管理页“使用说明”，只保留管理员完成 COSMIC 配置所需的必要说明，帮助其快速理解指标意义并按组织要求配置规则。
  - G2: 澄清产品能力边界，明确规则管理页用于配置 COSMIC 计量口径，而不是直接控制当前功能点拆分粒度。
  - G3: 在估算主链路中引入统一的“估算规则上下文层”，并在点击估算时按管理员当前维护的 COSMIC 配置对待估功能点执行分析，使该规则成为工作量估算前的必经上下文，而不是摆设。
  - G4: 保持估算基于完整需求语义，禁止退化为只依赖功能点短描述或启发式标签。
- Non-goals:
  - NG1: 本轮不引入管理员可直接配置的运行时拆分粒度开关。
  - NG2: 本轮不重写现有功能点拆分算法，也不承诺用 COSMIC 完全接管拆分决策。
  - NG3: 本轮不实现第二套以上估算规则引擎，只为后续接入其他规则预留统一上下文接口。
- Must-have Anchors:
  - A1: “使用说明”必须围绕管理员配置动作展开，重点解释指标含义、适用边界和组织配置含义。
  - A2: 估算前必须按管理员当前维护的 COSMIC 配置主动生成所选规则的结构化上下文，并显式交给估算 Agent 使用。
  - A3: 规则上下文失败时必须按功能点降级并保留后台证据，不能静默回退。
  - A4: 估算仍须保留完整原始需求上下文，规则上下文只能补强，不能替代原始语义。
- Prohibition Anchors:
  - P1: 禁止继续保留会让管理员误认为“修改页面粒度说明 = 直接修改拆分粒度”的文案。
  - P2: 禁止让启发式检测、关键词命中或短描述摘要直接替代工作量估算所需的完整语义上下文。
  - P3: 禁止把 COSMIC 内部结构直接焊死到估算 Agent 中，规则接入必须通过统一上下文层。
- Success Anchors:
  - S1: 管理员能从规则管理页快速理解各 COSMIC 配置项的意义及边界，不再被误导为拆分开关。
  - S2: 工作量估算链路能留下后台证据，证明“管理员配置的规则已在当前估算动作中被应用、降级或跳过”，而不是只消费历史残留结果。
  - S3: COSMIC 作为首个规则接入时，估算仍保持完整上下文，不退化为只看短文本。
- Boundary Alerts:
  - B1: COSMIC 在实践中关注功能过程边界，但不能被简化为一个页面配置项就能决定拆分粒度。
  - B2: 为控制 token 成本增加的局部规则补强必须偏保守，避免大量额外 LLM 调用。
  - B3: 未来可能引入其他估算规则（如 CCEP），因此实现不能与 COSMIC 特有字段深耦合。
- Unresolved Decisions:
  - D1: 是否在未来版本单独引入“可配置拆分粒度”能力，本轮保持 deferred，不纳入交付范围。

### Requirements Quick Index
- Requirements Index:
  - REQ-001: 规则管理页 COSMIC 使用说明纠偏
  - REQ-002: 估算规则上下文层接入估算主链路
  - REQ-003: COSMIC 规则上下文产出与按功能点降级证据
  - REQ-004: 估算完整语义保留与提示词消费约束
- Proposal Coverage Map: maintain in `## Requirements`
- Clarification Status: maintain in `## Requirements`

### Acceptance Index
- ACC-001 -> REQ-001: 使用说明只保留必要配置说明并明确能力边界
- ACC-002 -> REQ-002: 估算前统一构建并注入规则上下文
- ACC-003 -> REQ-003: COSMIC 规则上下文可产出、可降级、可追溯
- ACC-004 -> REQ-004: 估算仍使用完整原始上下文，规则上下文仅作补强

### Verification Index
- VO-001 -> ACC-001: 前端渲染测试或等效验证
- VO-002 -> ACC-002: API / 服务层自动化测试
- VO-003 -> ACC-003: 规则上下文与降级证据自动化测试
- VO-004 -> ACC-004: 估算提示词与上下文注入自动化测试

### Appendix Map
- none: 当前无正式 appendix；补充输入沉淀见 `docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md`

<!-- SKELETON-END -->

## Intent

### Problem / Background
当前评估链路存在两个相互耦合的问题。

第一，规则管理页的 COSMIC 使用说明混合了计量口径说明、功能过程颗粒度示意和类似“粗粒度 / 中等粒度 / 细粒度”的教学式示例，管理员容易误解为该页面配置会直接控制当前功能点拆分粒度。这与实际实现不一致，也会让页面文案对外形成错误能力承诺。

第二，当前功能点拆分和工作量估算链路并没有把 COSMIC 等估算规则作为必经上下文来消费。现状更接近“LLM 基于文本语义做拆分和估算，COSMIC 分析器作为旁路能力存在”。这会带来两个风险：其一，复杂改造项容易被粗粒度合并；其二，即使管理员配置了 COSMIC 规则，也缺乏后台证据证明估算 Agent 真实理解并运用了这些规则。

因此，本轮 Requirements 的核心不是把 COSMIC 直接改造成唯一拆分引擎，而是落实两个最小必要动作：先纠正规则管理页“使用说明”的产品语义，再把 COSMIC 管理配置真正接到估算主链路中，确保点击估算时会基于当前管理员规则对待估功能点执行分析、生成统一 `rule_context`、注入估算、可追溯降级，并且不牺牲完整需求语义。

### Goals
- G1: 优化规则管理页“使用说明”，只保留管理员完成 COSMIC 配置所需的必要说明，帮助其快速理解指标意义并按组织要求配置规则。
- G2: 澄清产品能力边界，明确规则管理页配置的是 COSMIC 计量口径，而不是当前拆分粒度控制。
- G3: 在估算主链路中引入统一的“估算规则上下文层”，并在点击估算时按管理员当前维护的 COSMIC 配置对待估功能点执行分析，让该规则成为估算前的必经上下文。
- G4: 保持估算基于完整需求语义，禁止退化为只依赖功能点短描述或只言片语。

### Non-goals
- NG1: 本轮不引入管理员可直接配置的运行时拆分粒度开关。
- NG2: 本轮不重写现有功能点拆分算法，也不承诺用 COSMIC 完全接管拆分决策。
- NG3: 本轮不实现第二套以上估算规则引擎，只为后续接入其他规则预留统一上下文接口。
- NG4: 本轮不把 COSMIC 计数结果直接映射为固定人天公式。

### Must-have Anchors
- A1: “使用说明”必须围绕管理员配置动作展开，重点解释指标含义、适用边界和组织配置含义。
- A2: 估算前必须按管理员当前维护的 COSMIC 配置构建规则分析结果和结构化上下文，并显式交给估算 Agent 使用。
- A3: 规则上下文失败时必须按功能点降级并保留后台证据，不能静默回退。
- A4: 估算仍须保留完整原始需求上下文，规则上下文只能补强，不能替代原始语义。

### Prohibition Anchors
- P1: 禁止继续保留会让管理员误认为“修改页面粒度说明 = 直接修改拆分粒度”的文案。
- P2: 禁止让启发式检测、关键词命中或短描述摘要直接替代工作量估算所需的完整语义上下文。
- P3: 禁止把 COSMIC 内部结构直接焊死到估算 Agent 中，规则接入必须通过统一上下文层。

### Success Anchors
- S1: 管理员能从规则管理页快速理解各 COSMIC 配置项的意义及边界，不再被误导为拆分开关。
- S2: 工作量估算链路能留下后台证据，证明“管理员配置的规则已在当前估算动作中被应用、降级或跳过”。
- S3: COSMIC 作为首个规则接入时，估算仍保持完整上下文，不退化为只看短文本。

### Boundary Alerts
- B1: COSMIC 在实践中关注功能过程边界，但不能被简化为一个页面配置项就能决定拆分粒度。
- B2: 为控制 token 成本增加的局部规则补强必须偏保守，避免大量额外 LLM 调用。
- B3: 未来可能引入其他估算规则（如 CCEP），因此实现不能与 COSMIC 特有字段深耦合。

### Unresolved Decisions
- D1: 是否在未来版本单独引入“可配置拆分粒度”能力，本轮保持 deferred，不纳入交付范围。

### Input Intake Summary
- input_source: 用户多轮对话澄清 + 本地代码/历史文档核查
- input_quality: L2
- normalization_effort: 将“说明误导”“估算 Agent 需要真正消费 COSMIC 规则”“估算不能退化为只看短文本”的要求归并为单一需求主题，并补充本地实现现状作为背景证据。

### Input Intake
- input_maturity: L2
- input_refs:
  - docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
  - docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#clarifications
- input_owner: human
- approval_basis: 用户确认本轮应先修正规则管理页“使用说明”的误导，并把 COSMIC 等估算规则接入为估算主链路的必经上下文，同时要求策略偏保守且不能让估算退化为只看短描述。
- normalization_status: anchored

### Testing Priority Rules
- P0: must be automated for rule-context injection, degradation evidence, and core estimate flow correctness
- P1: prefer automated for UI copy rendering and prompt/context composition correctness
- P2: manual or equivalent verification may supplement wording sanity checks but does not replace automated core-flow coverage

## Requirements

### Proposal Coverage Map
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
  anchor_ref: G1: 优化规则管理页“使用说明”，只保留管理员完成 COSMIC 配置所需的必要说明，帮助其快速理解指标意义并按组织要求配置规则。
  target_ref: REQ-001
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
  anchor_ref: G2: 澄清产品能力边界，明确规则管理页配置的是 COSMIC 计量口径，而不是当前拆分粒度控制。
  target_ref: REQ-001
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
  anchor_ref: G3: 在估算主链路中引入统一的“估算规则上下文层”，让被选中的估算规则成为估算前的必经上下文。
  target_ref: REQ-002
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
  anchor_ref: G4: 保持估算基于完整需求语义，禁止退化为只依赖功能点短描述或只言片语。
  target_ref: REQ-004
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#clarifications
  anchor_ref: scope-priority: 本轮优先处理 COSMIC 使用说明的纠偏与能力边界澄清；拆分链路的 COSMIC 边界补强作为后续 Requirements / Design direction，不在 Proposal 阶段直接实现。
  target_ref: REQ-001
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#clarifications
  anchor_ref: estimation-context: 工作量估算不能退化为只根据功能点短描述或只言片语估算；若未来引入局部 refine，估算仍须保留完整原始需求上下文。
  target_ref: REQ-004
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#clarifications
  anchor_ref: conservative-policy: 后续若增加粗粒度检测，应采取偏保守策略，优先减少误伤和无意义的额外 LLM 调用。
  target_ref: REQ-003
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#clarifications
  anchor_ref: capability-boundary: 当前 COSMIC 规则管理页用于解释和配置计量口径，不应继续暗示其直接控制当前功能点拆分行为。
  target_ref: REQ-001
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#clarifications
  anchor_ref: future-scope: 是否要在未来单独引入“可配置拆分粒度”能力，可后续单独评估，不默认纳入 `v3.1` 当前范围。
  target_ref: CLR-001
  status: deferred
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
  anchor_ref: A1: “使用说明”必须围绕管理员配置动作展开，重点解释指标含义、适用边界和组织配置含义。
  target_ref: REQ-001
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
  anchor_ref: A2: 估算前必须构建所选规则的结构化上下文，并显式交给估算 Agent 使用。
  target_ref: REQ-002
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
  anchor_ref: A3: 规则上下文失败时必须按功能点降级并保留后台证据，不能静默回退。
  target_ref: REQ-003
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
  anchor_ref: A4: 估算仍须保留完整原始需求上下文，规则上下文只能补强，不能替代原始语义。
  target_ref: REQ-004
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
  anchor_ref: P1: 禁止继续保留会让管理员误认为“修改页面粒度说明 = 直接修改拆分粒度”的文案。
  target_ref: REQ-001
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
  anchor_ref: P2: 禁止让启发式检测、关键词命中或短描述摘要直接替代工作量估算所需的完整语义上下文。
  target_ref: REQ-004
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
  anchor_ref: P3: 禁止把 COSMIC 内部结构直接焊死到估算 Agent 中，规则接入必须通过统一上下文层。
  target_ref: REQ-002
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
  anchor_ref: S1: 管理员能从规则管理页快速理解各 COSMIC 配置项的意义及边界，不再被误导为拆分开关。
  target_ref: REQ-001
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
  anchor_ref: S2: 工作量估算链路能留下后台证据，证明“选中的估算规则已被应用、降级或跳过”。
  target_ref: REQ-003
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
  anchor_ref: S3: COSMIC 作为首个规则接入时，估算仍保持完整上下文，不退化为只看短文本。
  target_ref: REQ-004
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
  anchor_ref: B1: COSMIC 在实践中关注功能过程边界，但不能被简化为一个页面配置项就能决定拆分粒度。
  target_ref: REQ-001
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
  anchor_ref: B2: 为控制 token 成本增加的局部规则补强必须偏保守，避免大量额外 LLM 调用。
  target_ref: REQ-003
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
  anchor_ref: B3: 未来可能引入其他估算规则（如 CCEP），因此实现不能与 COSMIC 特有字段深耦合。
  target_ref: REQ-002
  status: covered
- source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#intent
  anchor_ref: D1: 是否在未来版本单独引入“可配置拆分粒度”能力，本轮保持 deferred，不纳入交付范围。
  target_ref: CLR-001
  status: deferred

### Clarification Status
- clr_id: CLR-001
  source_ref: docs/inputs/2026-04-22-cosmic-guidance-and-splitting-boundary.md#clarifications
  status: deferred
  impact: medium
  owner: human
  next_action: 若后续希望把“可配置拆分粒度”纳入正式范围，需要独立立项并重新定义产品语义、规则入口与验收方式，而不是继续借用当前 COSMIC 规则管理页说明。
  deferred_exit_phase: Design

### Functional Requirements
- REQ-001
  - summary: 重写规则管理页 COSMIC 使用说明，只保留管理员配置 COSMIC 规则所需的必要说明，并明确该页面用于配置计量口径，不直接控制当前功能点拆分粒度。
  - rationale: 当前“粗粒度 / 中等粒度 / 细粒度”等教学式表述会误导管理员对系统能力形成错误预期，必须纠偏为最小必要说明。

- REQ-002
  - summary: 在工作量估算主链路引入统一的估算规则上下文层；当任务触发工作量估算时，系统必须基于管理员当前维护的 COSMIC 配置对待估功能点执行分析，生成对应 rule context，并将其作为显式上下文注入估算 Agent。
  - rationale: 当前规则分析与估算主链路脱节，配置页影响不到真实估算动作；只有把规则分析执行点收敛到点击估算时，才能证明估算 Agent 真实使用了管理员配置的规则，同时避免依赖过期的历史中间结果。

- REQ-003
  - summary: COSMIC 作为首个接入的估算规则，必须在点击估算时基于当前管理员配置为每个待估功能点产出结构化 rule context，至少包含规则身份、状态、摘要、结构化载荷、失败原因；规则失败时按功能点降级并记录后台证据。
  - rationale: 只有在当前估算动作中实时生成可追溯的结构化上下文和降级证据，才能证明规则不是摆设，并避免历史分析结果与当前功能点不一致。

- REQ-004
  - summary: 估算 Agent 在消费 rule context 时，仍必须保留并使用完整原始需求上下文、系统画像和功能点描述；规则上下文只能作为补强输入，不能替代完整语义。
  - rationale: 工作量估算主要依赖完整语义理解，若退化为只看短描述或只看规则摘要，会显著降低估算质量并违反用户明确要求。

### Constraints / Prohibitions
- 不新增管理员可配置的运行时拆分粒度开关。
- 不重写现有功能点拆分主链路，只补充最小必要的估算前规则上下文注入。
- 规则失败处理必须按功能点降级，不得整任务静默回退。
- 后台证据至少能区分 `applied`、`degraded`、`skipped` 三类状态，并可追溯失败原因；`applied/degraded` 必须对应当前估算动作内执行得到的规则结果，而不是只消费历史残留字段。
- 估算 Agent 对规则的消费必须通过统一 `rule_context` 接口完成，不能直接依赖 COSMIC 私有对象结构。

### Non-functional Requirements
- 可追溯性：每个参与估算的功能点都能在后台证据中看到规则应用状态、规则摘要和失败原因（如有）。
- 向后兼容：未选择估算规则或规则不可用时，现有估算主链路仍可继续执行，但必须有明确状态标识。
- 成本约束：规则补强策略应偏保守，不引入明显不必要的额外 LLM 调用。

## Acceptance

- acc_id: ACC-001
  source_ref: REQ-001
  expected_outcome: 规则管理页的 COSMIC 使用说明仅保留管理员理解和配置规则所需的必要说明，不再出现会让管理员理解为“当前可直接配置拆分粒度”的误导性表述，并明确该页面配置的是计量口径而非现网拆分控制。
  priority: P1
  priority_rationale: 这是当前用户最直接指出的误导问题，若不纠偏会持续传递错误产品语义。
  status: pending

- acc_id: ACC-002
  source_ref: REQ-002
  expected_outcome: 当任务进入工作量估算时，系统会基于管理员当前维护的 COSMIC 配置先对当前待估功能点执行分析，生成统一 rule context，并把该上下文显式注入估算 Agent；若规则未启用或被显式跳过，则状态被明确标记为 skipped/degraded。
  priority: P0
  priority_rationale: 这是保证“规则不是摆设”的主链路要求，缺失则无法证明估算真正使用了规则。
  status: pending

- acc_id: ACC-003
  source_ref: REQ-003
  expected_outcome: COSMIC 规则能够在当前估算动作中基于管理员配置产出包含规则身份、状态、摘要、结构化载荷和失败原因的统一 rule context；当规则生成失败时，仅受影响的功能点会被标记为 degraded，并在后台证据中可追溯失败原因。
  priority: P0
  priority_rationale: 没有统一结构和降级证据，就无法稳定扩展到其他规则，也无法区分“已使用”与“已跳过”。
  status: pending

- acc_id: ACC-004
  source_ref: REQ-004
  expected_outcome: 估算 Agent 接收到的上下文同时包含完整原始需求语义、系统画像上下文、功能点信息和 rule context，估算提示不退化为只依赖功能点短描述或规则摘要。
  priority: P0
  priority_rationale: 用户已明确指出“只靠只言片语估算”是大忌，这一约束必须成为核心验收项。
  status: pending

## Verification

- vo_id: VO-001
  acceptance_ref: ACC-001
  verification_type: automated
  verification_profile: focused
  obligations:
    - 前端渲染测试覆盖规则管理页“使用说明”文案，验证保留必要配置说明并去除误导性粒度表述。
    - 如存在快速设置或辅助提示，同步验证其措辞不再暗示页面直接控制当前拆分粒度。
  artifact_expectation: `frontend/src/__tests__/cosmicConfigPage.render.test.js` 或等效测试用例通过，并能证明文案边界已纠正。

- vo_id: VO-002
  acceptance_ref: ACC-002
  verification_type: automated
  verification_profile: focused
  obligations:
    - API / 服务层测试验证 `/tasks/{task_id}/estimate` 在估算前会基于当前管理员配置触发 COSMIC 分析并构建统一 rule context。
    - 验证 rule context 被纳入估算 Agent 入参，规则未启用或显式跳过时状态为 skipped/degraded。
  artifact_expectation: `tests/test_task_reevaluate_api.py`、`tests/test_evaluation_contract_api.py` 或等效自动化测试通过，并覆盖规则上下文注入主链路。

- vo_id: VO-003
  acceptance_ref: ACC-003
  verification_type: automated
  verification_profile: focused
  obligations:
    - 后端测试验证 COSMIC 规则上下文的统一结构输出，包括 `rule_id`、`rule_name`、`status`、`summary_text`、`structured_payload`、`failure_reason`。
    - 验证点击估算时确实调用基于管理员配置的 COSMIC 分析，规则失败时按功能点降级且后台证据可追溯失败原因。
  artifact_expectation: 新增或更新后端测试通过，并覆盖 COSMIC rule context 生成与 degradation evidence。

- vo_id: VO-004
  acceptance_ref: ACC-004
  verification_type: automated
  verification_profile: focused
  obligations:
    - 测试验证估算 Agent 构造的上下文同时保留完整原始需求文本、系统画像上下文、功能点信息与 rule context。
    - 验证估算提示词或等效输入不会退化为只依赖功能点短描述或规则摘要。
  artifact_expectation: 新增或更新后端测试通过，并覆盖提示词 / 估算上下文组合行为。
