# spec.md

## Default Read Layer

### Intent Summary
- Problem: 项目经理发起评估任务时缺少“待评估系统”范围控制，只能直接进入自动系统识别与多系统拆分，无法在创建阶段明确锁定单系统评估。
- Goals:
  - [G1] 在任务创建阶段新增必填的“待评估系统”选择，支持“具体系统”与“不限”两种范围。
  - [G2] 选择具体系统时跳过自动系统识别，仅围绕选定系统做功能点拆分与估算。
  - [G3] 选择“不限”时保持现有“系统识别 -> 多系统拆分”逻辑不变。
  - [G4] 让任务后续可追溯创建时的范围选择，并防止单系统任务在编辑期扩成多系统。
- Non-goals:
  - [NG1] 本阶段不调整系统识别算法本身。
  - [NG2] 本阶段不支持任务创建后修改“待评估系统”。
  - [NG3] 本阶段不要求在任务列表展示该字段。
- Must-have Anchors:
  - [A1] “待评估系统”单选框位于“任务名称”之前。
  - [A2] 选项为项目经理相关系统加固定项“不限”，且“不限”排在所有系统之后。
  - [A3] “待评估系统”为必填项，不提供默认值。
  - [A4] 选择具体系统后，不再先做系统识别/系统拆分，只针对该系统相关内容做功能点拆分和估算。
  - [A5] 具体系统模式必须结合全文需求和系统画像，不得仅按系统名或别名命中段落裁剪输入。
  - [A6] 选择“不限”时，沿用原有系统识别逻辑。
  - [A7] 具体系统模式若无法拆出该系统相关功能点，应直接失败并明确提示。
  - [A8] 任务详情页需要展示创建时选择的“待评估系统”结果。
  - [A9] 具体系统模式创建出的任务在编辑期锁定为单系统任务。
  - [A10] 当项目经理没有任何主责/B角系统时，创建页仅保留固定项“不限”，并允许提交。
- Prohibition Anchors:
  - [P1] 不能把“具体系统模式”实现为仅按系统名/别名匹配段落后再拆分。
  - [P2] 不能允许创建后的具体系统任务再修改“待评估系统”选择。
  - [P3] 不能允许具体系统任务通过编辑页扩成多系统任务。
- Success Anchors:
  - [S1] 项目经理可以在发起任务时显式声明评估范围。
  - [S2] 具体系统模式输出单系统评估结果，并保留范围选择的追溯信息。
  - [S3] “不限”模式不改变现有行为路径。
- Boundary Alerts:
  - [B1] “项目经理相关系统”口径复用现有主责+B角归属规则。
  - [B3] 后续展示范围当前只要求任务详情页，不扩展到任务列表。
- Unresolved Decisions:
  - none

### Requirements Quick Index
- Requirements 已冻结 formal REQ/ACC/VO，Proposal Coverage Map 和 Clarification Status 继续保留作为来源闭环。
- Proposal Coverage Map: maintain in `## Requirements`
- Clarification Status: maintain in `## Requirements`
- Requirements Index:
  - REQ-001: 创建页待评估系统输入与候选项规则
  - REQ-002: 任务创建校验、持久化与详情追溯
  - REQ-003: 具体系统模式评估流程
  - REQ-004: “不限”模式兼容现有系统识别流程
  - REQ-005: 具体系统任务的编辑期范围锁定

### Acceptance Index
- ACC-001 -> REQ-001
- ACC-002 -> REQ-002
- ACC-003 -> REQ-003
- ACC-004 -> REQ-004
- ACC-005 -> REQ-005

### Verification Index
- VO-001 -> ACC-001
- VO-002 -> ACC-002
- VO-003 -> ACC-003
- VO-004 -> ACC-004
- VO-005 -> ACC-005

### Appendix Map
- none: 当前 Proposal 无需额外 appendix

<!-- SKELETON-END -->

## Intent

### Problem / Background
当前“项目经理发起评估任务”页面只有任务名称、任务说明和需求文档上传入口。项目经理一旦提交任务，后台就直接进入“系统识别 -> 多系统功能点拆分 -> 工作量估算”的默认链路。这个流程适合范围未知或跨系统的需求，但不适合“项目经理已经明确知道本次只想评估自己负责的某个系统”的场景。

缺少创建阶段的范围声明会带来两个问题。第一，单系统评估场景仍要先走自动系统识别，容易引入不必要的系统拆分与后续人工纠偏。第二，任务在创建后缺少“本次到底是指定系统还是不限”的追溯信息，编辑期也没有边界保护，容易把本应锁定的单系统任务扩成多系统任务。

### Goals
- G1. 在任务创建阶段新增必填的“待评估系统”范围选择。
- G2. 为“具体系统”模式提供单系统评估入口，跳过自动系统识别。
- G3. 保留“不限”模式与现有流程兼容，避免影响当前多系统评估场景。
- G4. 让创建时的范围选择在后续详情中可见，并约束具体系统任务的编辑边界。

### Non-goals
- NG1. 本阶段不优化系统识别提示词、算法或画像数据源。
- NG2. 本阶段不支持任务创建后重新选择“待评估系统”。
- NG3. 本阶段不把“待评估系统”展示扩展到任务列表、统计看板等页面。

### Must-have Anchors
- A1. “待评估系统”单选框放在“任务名称”之前，属于创建任务页面的显式输入项。
- A2. 单选项来源于当前项目经理相关的所有系统名称，外加固定项“不限”；“不限”排在最后。
- A3. “待评估系统”为必填，不默认选中任何值。
- A4. 选择具体系统时，评估逻辑不再先做系统识别/系统拆分，只对该系统相关内容作功能点拆分和估算。
- A5. 具体系统模式下，拆分必须结合全文需求和该系统画像理解范围，不能只依赖名称命中段落。
- A6. 选择“不限”时，仍按照现有逻辑，在功能点拆分前先做系统识别。
- A7. 具体系统模式若最终无法拆出该系统相关功能点，应直接失败，不产生误导性的空结果。
- A8. 任务详情页需要展示“待评估系统”的创建时选择结果。
- A9. 具体系统模式任务在编辑期锁定为单系统，不允许通过系统级操作扩展范围。
- A10. 当项目经理没有任何主责/B角系统时，创建页仅保留固定项“不限”，并允许项目经理继续提交任务。

### Prohibition Anchors
- P1. 不能把“具体系统模式”的输入裁剪简化成“只保留系统名/别名命中的段落”。
- P2. 不能允许项目经理在任务创建后修改“待评估系统”。
- P3. 不能允许具体系统任务继续使用新增系统、重命名系统、删除系统、多系统重新拆分等会改变系统范围的操作。

### Success Anchors
- S1. 项目经理创建任务时能明确声明本次评估是“指定系统”还是“不限”。
- S2. 具体系统模式任务产出的结果只对应一个系统，并且该范围选择在后续可追溯。
- S3. “不限”模式继续沿用既有行为，不因为本次变更引入额外限制。

### Boundary Alerts
- B1. “项目经理相关系统”沿用现有主责+B角归属口径，不另起一套系统权限模型。
- B3. 详情展示是本次范围的一部分，但任务列表展示不在当前范围内。

### Unresolved Decisions
- none

### Input Intake Summary
- input_source: 当前会话中的需求口述与逐项澄清
- input_quality: L2
- normalization_effort: 已收敛范围口径、默认值、失败处理、展示范围与编辑期边界

### Input Intake
- input_maturity: L2
- input_refs:
  - docs/inputs/2026-04-19-target-system-scope.md#intent
- input_owner: human
- approval_basis: owner 已确认 Proposal 阶段先只回写 spec，不进入实现
- normalization_status: anchored

### Testing Priority Rules
- P0: must be automated for safety, money, data integrity, or core flow
- P1: prefer automated; otherwise must have manual or equivalent pass evidence
- P2: may use manual or equivalent verification, but still requires a pass result

## Requirements

### Proposal Coverage Map
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#intent
  anchor_ref: G1. 在任务创建阶段新增必填的“待评估系统”范围选择。
  target_ref: REQ-001
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#intent
  anchor_ref: G2. 为“具体系统”模式提供单系统评估入口，跳过自动系统识别。
  target_ref: REQ-003
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#intent
  anchor_ref: G3. 保留“不限”模式与现有流程兼容，避免影响当前多系统评估场景。
  target_ref: REQ-004
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#visibility
  anchor_ref: G4. 让创建时的范围选择在后续详情中可见，并约束具体系统任务的编辑边界。
  target_ref: REQ-002
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#intent
  anchor_ref: A1. “待评估系统”单选框放在“任务名称”之前，属于创建任务页面的显式输入项。
  target_ref: REQ-001
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#intent
  anchor_ref: A2. 单选项来源于当前项目经理相关的所有系统名称，外加固定项“不限”；“不限”排在最后。
  target_ref: REQ-001
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#required
  anchor_ref: A3. “待评估系统”为必填，不默认选中任何值。
  target_ref: REQ-001
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#intent
  anchor_ref: A4. 选择具体系统时，评估逻辑不再先做系统识别/系统拆分，只对该系统相关内容作功能点拆分和估算。
  target_ref: REQ-003
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#single-system-scope
  anchor_ref: A5. 具体系统模式下，拆分必须结合全文需求和该系统画像理解范围，不能只依赖名称命中段落。
  target_ref: REQ-003
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#intent
  anchor_ref: A6. 选择“不限”时，仍按照现有逻辑，在功能点拆分前先做系统识别。
  target_ref: REQ-004
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#no-match
  anchor_ref: A7. 具体系统模式若最终无法拆出该系统相关功能点，应直接失败，不产生误导性的空结果。
  target_ref: REQ-003
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#visibility
  anchor_ref: A8. 任务详情页需要展示“待评估系统”的创建时选择结果。
  target_ref: REQ-002
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#edit-constraints
  anchor_ref: A9. 具体系统模式任务在编辑期锁定为单系统，不允许通过系统级操作扩展范围。
  target_ref: REQ-005
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#empty-owned-systems
  anchor_ref: A10. 当项目经理没有任何主责/B角系统时，创建页仅保留固定项“不限”，并允许项目经理继续提交任务。
  target_ref: REQ-001
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#single-system-scope
  anchor_ref: P1. 不能把“具体系统模式”的输入裁剪简化成“只保留系统名/别名命中的段落”。
  target_ref: REQ-003
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#mutability
  anchor_ref: P2. 不能允许项目经理在任务创建后修改“待评估系统”。
  target_ref: REQ-002
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#edit-constraints
  anchor_ref: P3. 不能允许具体系统任务继续使用新增系统、重命名系统、删除系统、多系统重新拆分等会改变系统范围的操作。
  target_ref: REQ-005
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#intent
  anchor_ref: S1. 项目经理创建任务时能明确声明本次评估是“指定系统”还是“不限”。
  target_ref: REQ-001
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#visibility
  anchor_ref: S2. 具体系统模式任务产出的结果只对应一个系统，并且该范围选择在后续可追溯。
  target_ref: REQ-002
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#intent
  anchor_ref: S3. “不限”模式继续沿用既有行为，不因为本次变更引入额外限制。
  target_ref: REQ-004
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#system-scope-rule
  anchor_ref: B1. “项目经理相关系统”沿用现有主责+B角归属口径，不另起一套系统权限模型。
  target_ref: REQ-001
  status: covered
- source_ref: docs/inputs/2026-04-19-target-system-scope.md#visibility
  anchor_ref: B3. 详情展示是本次范围的一部分，但任务列表展示不在当前范围内。
  target_ref: REQ-002
  status: covered

### Clarification Status
- clr_id: CLR-001
  source_ref: docs/inputs/2026-04-19-target-system-scope.md#system-scope-rule
  status: resolved
  impact: high
  owner: human
  next_action: 已由 REQ-001 正式化
  deferred_exit_phase: none
- clr_id: CLR-002
  source_ref: docs/inputs/2026-04-19-target-system-scope.md#single-system-scope
  status: resolved
  impact: high
  owner: human
  next_action: 已由 REQ-003 正式化
  deferred_exit_phase: none
- clr_id: CLR-003
  source_ref: docs/inputs/2026-04-19-target-system-scope.md#required
  status: resolved
  impact: high
  owner: human
  next_action: 已由 REQ-001 正式化
  deferred_exit_phase: none
- clr_id: CLR-004
  source_ref: docs/inputs/2026-04-19-target-system-scope.md#no-match
  status: resolved
  impact: medium
  owner: human
  next_action: 已由 REQ-003 正式化
  deferred_exit_phase: none
- clr_id: CLR-005
  source_ref: docs/inputs/2026-04-19-target-system-scope.md#mutability
  status: resolved
  impact: medium
  owner: human
  next_action: 已由 REQ-002 正式化
  deferred_exit_phase: none
- clr_id: CLR-006
  source_ref: docs/inputs/2026-04-19-target-system-scope.md#visibility
  status: resolved
  impact: medium
  owner: human
  next_action: 已由 REQ-002 正式化
  deferred_exit_phase: none
- clr_id: CLR-007
  source_ref: docs/inputs/2026-04-19-target-system-scope.md#edit-constraints
  status: resolved
  impact: high
  owner: human
  next_action: 已由 REQ-005 正式化
  deferred_exit_phase: none
- clr_id: CLR-008
  source_ref: docs/inputs/2026-04-19-target-system-scope.md#empty-owned-systems
  status: resolved
  impact: medium
  owner: human
  next_action: 已由 REQ-001 正式化
  deferred_exit_phase: none

### Functional Requirements
- REQ-001
  - summary: 发起评估任务页面必须提供“待评估系统”必填输入，并按主责+B角口径提供候选项与空集合降级行为。
  - rationale: 让项目经理在创建时显式声明评估范围，并把“无相关系统”场景收敛到唯一允许的“不限”入口。
- REQ-002
  - summary: 任务创建接口必须校验并持久化“待评估系统”选择，详情页必须展示该结果，且创建后不可修改。
  - rationale: 保证范围选择具备后端约束与任务级追溯，不依赖前端临时状态。
- REQ-003
  - summary: 具体系统模式必须跳过自动系统识别，基于全文需求和所选系统画像完成单系统拆分与估算，并在无有效功能点时直接失败。
  - rationale: 用单系统流程替代多系统预处理，同时避免名称命中裁剪带来的误判和空结果误导。
- REQ-004
  - summary: “不限”模式必须保留现有“系统识别 -> 功能点拆分 -> 估算”行为，不因本次变更改变多系统评估路径。
  - rationale: 保持对既有跨系统需求场景的兼容性，降低回归风险。
- REQ-005
  - summary: 具体系统模式创建出的任务必须在编辑期锁定为单系统任务，禁止任何会改变系统范围的系统级操作。
  - rationale: 防止创建期已确认的单系统范围在后续编辑中被人为扩张，破坏追溯边界。

### Requirements Detail

- req_id: REQ-001
  description: 创建页在“任务名称”之前展示“待评估系统”单选输入；当项目经理存在主责/B角系统时，候选项为这些系统名称加固定项“不限”，且“不限”始终位于最后；当项目经理不存在主责/B角系统时，候选项仅保留“不限”；该字段为必填，创建时不得默认选中任何值。
  acceptance_refs:
    - ACC-001
  verification_refs:
    - VO-001
  priority: P0
  status: approved
- req_id: REQ-002
  description: 创建任务请求必须区分“具体系统”与“不限”两种模式，并在后端校验“具体系统”只能取自当前项目经理可选系统集合；任务对象必须持久化范围模式与系统名称；任务详情必须返回并展示该结果；创建后不得提供修改“待评估系统”的入口或接口语义。
  acceptance_refs:
    - ACC-002
  verification_refs:
    - VO-002
  priority: P0
  status: approved
- req_id: REQ-003
  description: 当项目经理选择具体系统时，评估流程不得先做自动系统识别；功能点拆分必须以全文需求和所选系统画像为输入，只输出该系统结果；如果最终没有识别出该系统相关功能点，任务必须直接失败并给出明确提示，而不是生成空结果草稿。
  acceptance_refs:
    - ACC-003
  verification_refs:
    - VO-003
  priority: P0
  status: approved
- req_id: REQ-004
  description: 当项目经理选择“不限”时，系统必须继续沿用现有流程，在功能点拆分前先做系统识别，并允许输出多系统拆分结果；本次变更不得改变该路径的行为顺序和能力边界。
  acceptance_refs:
    - ACC-004
  verification_refs:
    - VO-004
  priority: P0
  status: approved
- req_id: REQ-005
  description: 对于以具体系统模式创建的任务，编辑页和对应后端接口必须禁止新增系统、重命名系统、删除系统、重新拆分系统等会改变系统范围的操作；功能点级增删改与重估仍可在该单一系统内继续使用。
  acceptance_refs:
    - ACC-005
  verification_refs:
    - VO-005
  priority: P0
  status: approved

### Constraints / Prohibitions
- C1. Proposal 阶段不得在主文档之外定义正式 REQ/ACC/VO。
- C2. “具体系统模式”的范围收敛必须依赖全文语义和系统画像，不得退化为简单段落命中筛选。
- C3. 任何后续实现都需要保持“不限”模式与现有行为兼容。

### Non-functional Requirements
- 本次 Requirements 不新增独立的可量化 NFR；兼容性与回归约束由 REQ-004、VO-004 体现。

## Acceptance

- acc_id: ACC-001
  source_ref: REQ-001
  requirement_refs:
    - REQ-001
  expected_outcome: 项目经理创建任务时能看到位于“任务名称”之前的“待评估系统”必填输入；有主责/B角系统时显示“相关系统 + 不限（最后一项）”，无主责/B角系统时仅显示“不限”，且仍可正常提交。
  description: 创建页输入规则与候选项来源闭环。
  priority: P0
  priority_rationale: 这是任务创建主流程的入口约束，错误候选项会直接导致范围选择失真。
  status: approved
- acc_id: ACC-002
  source_ref: REQ-002
  requirement_refs:
    - REQ-002
  expected_outcome: 创建请求会校验“具体系统”是否属于当前项目经理可选系统集合，并把范围模式与系统名称写入任务；任务详情可展示该结果；创建后不存在修改该字段的合法路径。
  description: 后端约束、持久化和详情追溯闭环。
  priority: P0
  priority_rationale: 如果后端不校验或不持久化，前端显示无法代表真实任务边界。
  status: approved
- acc_id: ACC-003
  source_ref: REQ-003
  requirement_refs:
    - REQ-003
  expected_outcome: 具体系统模式下不会执行自动系统识别，而是直接对所选系统进行单系统拆分与估算；拆分输入仍依赖全文需求和系统画像；若无有效功能点则任务失败并返回明确错误。
  description: 具体系统模式核心评估流程。
  priority: P0
  priority_rationale: 这是本次变更的核心行为变化，错误实现会直接导致估算路径偏离。
  status: approved
- acc_id: ACC-004
  source_ref: REQ-004
  requirement_refs:
    - REQ-004
  expected_outcome: “不限”模式仍在功能点拆分前执行系统识别，并保留既有多系统评估能力，不因为新增字段改变原有流程顺序或结果形态。
  description: 既有多系统路径兼容性。
  priority: P0
  priority_rationale: 旧路径回归会影响当前主要使用场景，属于高风险核心流程。
  status: approved
- acc_id: ACC-005
  source_ref: REQ-005
  requirement_refs:
    - REQ-005
  expected_outcome: 具体系统模式任务在编辑期不能执行任何系统范围变更操作，但仍保留该单一系统内的功能点编辑和重估能力。
  description: 单系统任务编辑边界约束。
  priority: P0
  priority_rationale: 若编辑期能扩范围，将破坏创建时已确认的任务边界与追溯链。
  status: approved

## Verification

- vo_id: VO-001
  acceptance_ref: ACC-001
  acceptance_refs:
    - ACC-001
  verification_type: automated
  verification_profile: focused
  obligations:
    - 验证创建页字段顺序、必填约束和无默认值行为。
    - 验证候选项来源遵循主责+B角口径，且“不限”始终位于最后。
    - 验证无主责/B角系统时仅展示“不限”且提交不被阻断。
  artifact_expectation: 前端渲染测试 + 候选项生成逻辑测试，能明确断言字段顺序、候选项列表和空集合降级行为。
- vo_id: VO-002
  acceptance_ref: ACC-002
  acceptance_refs:
    - ACC-002
  verification_type: automated
  verification_profile: focused
  obligations:
    - 验证创建接口对具体系统选择做合法性校验，并拒绝越权或非法系统值。
    - 验证任务持久化字段包含范围模式与系统名称。
    - 验证任务详情接口返回用于展示的待评估系统结果，且创建后不存在修改语义。
  artifact_expectation: 后端 API 测试，覆盖创建成功、创建拒绝、详情返回和不可修改约束。
- vo_id: VO-003
  acceptance_ref: ACC-003
  acceptance_refs:
    - ACC-003
  verification_type: automated
  verification_profile: focused
  obligations:
    - 验证具体系统模式不会调用自动系统识别分支。
    - 验证拆分输入使用全文需求和所选系统上下文，结果只产出单系统数据。
    - 验证零功能点场景返回明确失败，而不是空结果成功。
  artifact_expectation: 编排层/任务处理测试，使用桩或可观测日志断言分支选择、单系统输出和失败语义。
- vo_id: VO-004
  acceptance_ref: ACC-004
  acceptance_refs:
    - ACC-004
  verification_type: automated
  verification_profile: regression
  obligations:
    - 验证“不限”模式仍在功能点拆分前执行系统识别。
    - 验证该模式仍允许多系统输出，且不被新增字段改变默认流程。
  artifact_expectation: 回归测试，覆盖“不限”路径的系统识别调用顺序和多系统结果形态。
- vo_id: VO-005
  acceptance_ref: ACC-005
  acceptance_refs:
    - ACC-005
  verification_type: automated
  verification_profile: focused
  obligations:
    - 验证具体系统模式任务的系统级变更接口全部被阻断。
    - 验证功能点级编辑和重估在锁定单系统任务中仍然可用。
    - 验证编辑页不再暴露会改变系统范围的操作入口。
  artifact_expectation: 后端接口测试 + 前端页面行为测试，分别证明系统级操作被禁用且功能点级操作保留。
