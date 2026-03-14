# v2.7 需求说明书：系统画像域重构、Skill Runtime 与 Memory 资产层

| 项 | 值 |
|---|---|
| 状态 | Review |
| 作者 | Codex |
| 评审 | Codex |
| 日期 | 2026-03-13 |
| 版本 | v0.13 |
| 关联提案 | `docs/v2.7/proposal.md` v0.6 |

## 1. 概述

### 1.1 目的与范围

**目的**：将 v2.7 提案中“系统画像 5 域细粒度重构、PM 知识导入页收敛、管理员服务治理导入、管理员系统清单导入画像联动、Skill Runtime、Per-System Memory 资产层”六项能力，转化为范围明确、可验收、可追溯的需求规格，为后续 Design / Planning / Implementation 提供唯一需求口径。

**范围**：
- 收敛 PM 知识导入页文档类型，仅保留需求文档、设计文档、技术方案三类入口，并清理历史评估报告相关存量数据。
- 将系统画像从当前 5 域 12 子字段升级为细粒度 5 域结构，统一后端空画像结构、前端展示配置、导入结果结构和后续验收口径。
- 新增管理员“服务治理”页，支持导入治理文档/模板，批量更新系统画像，且以 D3 为主、允许按策略形成 D1/D4 语义更新。
- 在系统清单批量导入 confirm 后，自动触发 `system_catalog_skill`，仅对系统首次初始化或画像全空的命中系统执行画像初始化/补空。
- 建立 Skill Runtime，明确 Registry、Router、Scene Executor、Policy Gate、Memory Reader/Writer 的职责，而不是只实现若干独立脚本。
- 实现 6 个内置 Skill，并保证可扩展到后续需求评审、架构评审等新 Skill。
- 为每个系统建立 Memory 资产层，记录画像更新、系统识别结论、AI 评估后功能点修改，并要求其实际用于系统画像完善、系统识别和功能点拆解。
- 收敛系统识别必须给出直接判定、画像更新与功能点拆解必须按场景区分落地方式、不得破坏现有评估主链路等关键边界。

### 1.2 背景、约束与关键假设

**现状与痛点**：
- 当前系统画像虽已升级为 5 域 12 子字段，但 D1/D3/D4 粒度不足，无法稳定支撑系统识别、功能点拆解和跨来源画像融合。
- 当前 PM 导入页同时承载 5 类文档导入，其中历史评估报告和 ESB/服务治理文档不适合继续由 PM 逐系统操作。
- 管理员在服务治理页导入的治理文档、以及系统清单批量导入的数据，都包含大量高价值字段，但当前系统没有形成统一画像联动能力。
- 当前“Skill”更像散落在服务中的提取逻辑，而不是类似 Codex 的目标驱动式调用能力；系统无法按场景自动选择、组合和执行 Skill。
- 当前没有 per-system memory 资产层，系统画像更新、系统识别结论、AI 评估后的功能点修改没有被结构化沉淀，也无法反哺后续工作。

**约束**：
- **技术约束**：
  - 内网模型口径固定为 `Qwen3-32B` 和 `Qwen3-Embedding-8B`，不得在 v2.7 范围内变更模型。
  - 复用 v2.6 已实现的 Token 感知分块机制，不新增外部运行时依赖。
  - 复用现有 admin / manager / expert 权限模型，不在 v2.7 引入新角色或资源级权限体系改造。
  - 现有评估算法、评估报告生成链路、任务评估主流程保持兼容，不得因画像、导入、Runtime、Memory 改造而改变评估主链路语义。
- **业务约束**：
  - 存量画像数据直接清理，不做旧 schema 到新 schema 的迁移兼容。
  - 服务治理和系统清单未匹配/校验失败项通过修正模板后重导处理，不提供手动映射界面。
  - PM 手动编辑内容优先于自动更新结果，必须能通过 `field_sources` 或等效元数据判断来源优先级。
  - 系统识别必须给出直接判定，候选列表和澄清问题只能作为辅助解释，不能替代最终结论。
- **交付约束**：
  - v2.7 只学习 Codex 的运行思路，不照搬 Codex/Claude 的产品形态。
  - 本次必须交付 Runtime 能力，而不是只交付若干 Skill 脚本。
  - Memory 必须按可扩展资产层设计，后续可承载需求评审、架构评审等新用途。

**关键假设**：
- Runtime 作为系统内部服务存在，通过已有业务入口触发，不要求对外暴露一个“仿 Codex 会话 UI”。
- 场景化落地策略按以下单一口径收敛：
  - 结构化、字段级、低歧义事实：允许 `auto_apply` 或 `draft_apply`
  - 语义推断、综合判断、冲突场景：默认 `suggestion_only`
  - 高风险或不满足前置条件：`reject`
- 系统清单导入场景按以下特殊口径收敛：
  - 仅当目标系统 `profile_data` 下 D1-D5 canonical 字段全部为空值/空数组/空对象时，允许 `auto_apply`
  - `field_sources`、`ai_suggestions` 和 Memory 记录不参与“空画像”判定
  - 目标画像存在任一 canonical 内容时统一 `reject/skip`，且不生成 PM 需接受的建议
- 系统识别保留 `candidates/questions` 作为解释信息，但必须同时返回 `matched / ambiguous / unknown` 之一。
- 功能点拆解场景继续复用现有系统识别/功能点拆解链路，但在 v2.7 中必须接入系统画像与 Memory 作为约束。

### 1.3 术语与口径

**ID 前缀规则**：详见 `.aicoding/STRUCTURE.md` 统一定义。

**核心术语**：
- **系统画像（System Profile）**：用于表达系统定位、业务能力、集成关系、技术架构、约束与风险的结构化数据对象。
- **D1-D5 五域模型**：`system_positioning`、`business_capabilities`、`integration_interfaces`、`technical_architecture`、`constraints_risks` 五个一级域。
- **Skill Runtime**：负责按场景读取上下文、选择 Skill、串联执行、做策略判断并写回 Memory 的内部运行能力。
- **Skill Registry**：管理 Skill 元数据的注册表，不仅保存 Skill 名称，还保存输入契约、任务类型、目标工件、执行模式和策略信息。
- **Scene Executor**：按业务场景执行一个或多个 Skill 的编排单元，例如 `admin_service_governance_import`、`admin_system_catalog_import`。
- **Policy Gate**：在 Skill 输出后决定 `auto_apply / draft_apply / suggestion_only / reject` 的策略门。
- **Memory Record**：系统级资产记录，至少包含 `profile_update`、`identification_decision`、`function_point_adjustment` 三类。
- **Direct Decision**：基于系统清单、系统画像、Memory 中的稳定事实直接做出判定，而不是完全交给 LLM 自由生成。
- **Retrieval Context**：在复杂语义场景中，为 LLM 提供来自系统画像和 Memory 的增强上下文。
- **系统识别直接判定**：最终返回 `matched / ambiguous / unknown` 之一，允许附带候选系统和澄清问题，但不得只有候选列表。
- **功能点修改分类**：AI 首轮评估后，围绕功能点的新增、删除、合并、拆分、改写、复杂度调整、归属调整等分类结果。
- **空画像（Blank Profile）**：仅当 `profile_data` 下 D1-D5 canonical 字段全部为空值、空数组或空对象时，判定为空画像；`field_sources`、`ai_suggestions`、Memory 记录不参与判定。

**关键口径**：
- **当前基线画像结构**：v2.6 为 5 域 12 子字段。
- **v2.7 目标画像结构**：5 域至少 20 个字段，且每域预留 `extensions`。
- **PM 导入页目标文档类型**：仅保留需求文档、设计文档、技术方案。
- **内置 Skill 范围**：v2.7 固定交付 6 个内置 Skill，但 Runtime 和 Memory 不得被设计成只能支持这 6 个。
- **服务治理导入口径**：以 D3 更新为主，对 D1/D4 的语义影响按策略产出草稿或建议，不允许无条件覆盖。
- **系统清单导入口径**：以结构化字段映射为主，仅在系统首次初始化或目标画像为空画像时自动初始化命中系统画像；非空画像一律跳过，不进入 PM 建议接受流。
- **系统清单模型口径**：v2.7 仅保留单一系统清单模板与数据模型，不再维护主系统/子系统双清单或子系统映射。

### 1.4 覆盖性检查（🔴 MUST，R5）

#### 覆盖映射表（🔴 MUST）

| Proposal 锚点 | 类型 | 对应 REQ-ID | 验收标准 | 状态 |
|---------------|------|------------|---------|------|
| P-DO-01: PM 导入页仅保留需求文档、设计文档、技术方案三种文档类型 | DO | REQ-001 | REQ-001-ACC-01 | ✅已覆盖 |
| P-DO-02: 画像数据模型重构为 5 域结构，各域字段与提案表一致 | DO | REQ-002 | REQ-002-ACC-01 | ✅已覆盖 |
| P-DO-03: 各域预留 `extensions` 扩展字段 | DO | REQ-002 | REQ-002-ACC-02 | ✅已覆盖 |
| P-DO-04: 新增管理员“服务治理”页，支持导入治理文档/模板并批量更新系统画像 | DO | REQ-003 | REQ-003-ACC-01 | ✅已覆盖 |
| P-DO-05: 服务治理导入以 D3 为主更新画像，并允许对 D1/D4 做小范围语义更新 | DO | REQ-009 | REQ-009-ACC-01 | ✅已覆盖 |
| P-DO-06: 新增系统清单导入后的画像联动能力，仅在系统首次初始化或目标画像全空时初始化命中系统画像 | DO | REQ-004 | REQ-004-ACC-02 | ✅已覆盖 |
| P-DO-07: 建立 Skill Runtime 平台，至少包含 Registry、Router、Scene Executor、Policy Gate、Memory Reader/Writer | DO | REQ-005 | REQ-005-ACC-01 | ✅已覆盖 |
| P-DO-08: 实现 6 个内置 Skill | DO | REQ-005 | REQ-005-ACC-02 | ✅已覆盖 |
| P-DO-09: 每个 Skill 显式定义元数据 | DO | REQ-005 | REQ-005-ACC-03 | ✅已覆盖 |
| P-DO-10: Runtime 支持按场景串联 Skill，而不是只做单次脚本调用 | DO | REQ-005 | REQ-005-ACC-04 | ✅已覆盖 |
| P-DO-11: 为每个系统沉淀 Memory，记录画像更新、系统识别结论、AI 评估后功能点修改，且按类型分类 | DO | REQ-007 | REQ-007-ACC-01 | ✅已覆盖 |
| P-DO-12: Memory 必须运用在系统画像完善、系统识别和功能点拆解三个工作中 | DO | REQ-008 | REQ-008-ACC-01 | ✅已覆盖 |
| P-DO-13: 系统识别结果必须直接输出 `matched / ambiguous / unknown` | DO | REQ-008 | REQ-008-ACC-04 | ✅已覆盖 |
| P-DO-14: 画像更新与功能点拆解结果的落地方式必须按场景区分 `auto_apply / draft_apply / suggestion_only / reject` | DO | REQ-009 | REQ-009-ACC-04 | ✅已覆盖 |
| P-DO-15: 存量画像数据和向量库中历史评估报告数据完成清理 | DO | REQ-012 | REQ-012-ACC-01 | ✅已覆盖 |
| P-DO-16: 画像面板（前端）适配新 5 域结构展示 | DO | REQ-002 | REQ-002-ACC-03 | ✅已覆盖 |
| P-DONT-01: 不得保留“历史评估报告”和“服务治理文档”在 PM 导入页 | DONT | REQ-C001 | REQ-C001-ACC-01 | ✅已覆盖 |
| P-DONT-02: 不得在画像数据中残留旧 schema 字段 | DONT | REQ-C002 | REQ-C002-ACC-01 | ✅已覆盖 |
| P-DONT-03: 自动导入或自动更新不得覆盖 PM 已确认的 `manual` 内容 | DONT | REQ-C003 | REQ-C003-ACC-01 | ✅已覆盖 |
| P-DONT-04: 不得把 Skill 和 Memory 设计成不可扩展结构 | DONT | REQ-C004 | REQ-C004-ACC-01 | ✅已覆盖 |
| P-DONT-05: 系统识别不得只给候选列表而不做直接判定 | DONT | REQ-C005 | REQ-C005-ACC-01 | ✅已覆盖 |
| P-DONT-06: 不得破坏现有评估流程 | DONT | REQ-C006 | REQ-C006-ACC-01 | ✅已覆盖 |
| P-DONT-07: 不得引入新的外部依赖 | DONT | REQ-C007 | REQ-C007-ACC-01 | ✅已覆盖 |
| P-DONT-08: 系统清单后续月度更新或覆盖导入不得覆盖非空画像；空画像判定仅看 `profile_data` 下 D1-D5 canonical 字段 | DONT | REQ-C008 | REQ-C008-ACC-01 | ✅已覆盖 |
| P-METRIC-01: 画像域字段数 ≥ 20（含 `extensions`） | METRIC | REQ-101 | REQ-101-ACC-01 | ✅已覆盖 |
| P-METRIC-02: PM 导入页文档类型 = 3 种 | METRIC | REQ-001 | REQ-001-ACC-02 | ✅已覆盖 |
| P-METRIC-03: 服务治理导入自动匹配更新成功率 ≥ 95% | METRIC | REQ-102 | REQ-102-ACC-01 | ✅已覆盖 |
| P-METRIC-04: 6 个内置 Skill 全部实现、正确路由，并通过独立功能测试 | METRIC | REQ-103 | REQ-103-ACC-01 | ✅已覆盖 |
| P-METRIC-05: 三类 Memory 写入覆盖率 = 100% | METRIC | REQ-104 | REQ-104-ACC-01 | ✅已覆盖 |
| P-METRIC-06: 存量旧 schema 画像数据 = 0 | METRIC | REQ-105 | REQ-105-ACC-01 | ✅已覆盖 |

**覆盖性确认**：
- Proposal 共 30 个锚点（16 个 DO + 8 个 DONT + 6 个 METRIC）。
- 当前 Requirements §1 已完成 30/30 映射，暂不引入 defer 项。
- Requirements 额外新增了对 Memory 驱动系统识别、功能点拆解应用策略和 Runtime 扩展性的明确口径，用于关闭本轮讨论中新增的关键设计决策。

## 2. 业务场景说明

### 2.1 角色与对象

**角色**：
- **产品经理（manager）**：维护本人负责系统的文档导入、画像复核与 AI 建议采纳；不承担管理员治理导入。
- **系统管理员（admin）**：维护系统清单，执行服务治理导入与系统清单导入确认，并查看全局画像与 Memory 结果。
- **专家（expert）**：只读查看画像、导入结果和相关 Memory，用于理解系统背景与评估上下文。
- **系统（Runtime）**：执行 Skill 路由、策略判断、Memory 读写和结果编排。

**核心对象**：
- **Imported Document**：需求文档、设计文档、技术方案三类 PM 可导入文档。
- **Service Governance Import**：管理员在服务治理页上传的治理文档/模板。
- **System Catalog Import**：管理员在系统清单页完成的批量导入 preview/confirm 结果。
- **Skill Execution Session**：一次 Scene 执行上下文，包含场景、输入、被调度 Skill、策略判断和结果。
- **Memory Record**：系统级资产记录，带统一元数据与分类信息。
- **Identification Result**：系统识别结果，至少含 `final_verdict`、`selected_systems`、`candidate_systems`、`questions`。
- **Function Point Adjustment**：AI 首轮评估后对功能点的修改轨迹与分类结果。
- **System Profile**：v2.7 目标 5 域结构化对象，含 D1-D5 域、`field_sources`、`ai_suggestions` 和相关 Memory 引用。

### 2.2 场景列表

| 场景分类 | 场景ID | 场景名称 | 场景说明 | 主要角色 |
|---|---|---|---|---|
| CAT-A PM知识导入 | SCN-001 | PM 导入三类文档并查看结果 | PM 上传需求/设计/技术方案，Runtime 路由对应 Skill，生成结构化建议并写入 Memory | manager |
| CAT-B 管理员治理 | SCN-002 | 管理员导入服务治理文档并更新画像 | Admin 上传治理文档/模板，更新 D3 并形成 D1/D4 语义影响结果 | admin |
| CAT-B 管理员治理 | SCN-003 | 管理员确认系统清单导入并初始化/补空画像 | Admin 在系统清单导入 confirm 后触发 `system_catalog_skill`，仅初始化命中系统中的空画像并跳过非空画像 | admin |
| CAT-C Runtime | SCN-004 | Runtime 按场景路由和串联 Skill | Runtime 根据 `scene_id` 自动选择 Skill、执行 Policy Gate 并写回 Memory | 系统 |
| CAT-D 画像维护 | SCN-005 | PM 手动编辑画像并保持 manual 优先级 | PM 保存画像后，后续自动更新不得覆盖 `manual` 内容 | manager |
| CAT-E 系统识别 | SCN-006 | Memory 驱动系统识别直接判定 | 系统识别读取系统画像和 Memory，输出 `matched / ambiguous / unknown` | 系统 |
| CAT-F 功能点拆解 | SCN-007 | Memory 驱动功能点拆解与修改沉淀 | 功能点拆解读取系统画像和 Memory，输出结构化草稿，并沉淀功能点修改 Memory | 系统, manager |
| CAT-G 错误处理 | SCN-008 | Skill / 导入 / Memory 失败时返回可判定结果 | 任意链路失败时返回明确状态和原因，不产生静默成功 | manager, admin, 系统 |
| CAT-H 数据清理 | SCN-009 | 版本切换时清理旧 schema 和历史评估数据 | v2.7 生效前清理旧 schema 画像与历史评估报告存量数据 | admin, 系统 |

### 2.3 场景明细 [包含 2.2 中所有场景]

#### SCN-001：PM 导入三类文档并查看结果

**场景分类**：CAT-A PM知识导入  
**主要角色**：manager  
**相关对象**：Imported Document、Skill Execution Session、System Profile、Memory Record  
**关联需求ID**：REQ-001、REQ-005、REQ-006、REQ-007、REQ-009

**前置条件**：
- PM 已登录且具备 manager 角色。
- PM 已进入系统画像导入页。
- 待导入文件属于需求文档、设计文档或技术方案之一。

**触发条件**：
- PM 选择其负责系统并上传文档。

**流程步骤**：
1. 系统展示三类可选文档类型。
2. PM 选择文档类型并上传文件。
3. Runtime 根据 `scene_id=pm_document_ingest` 路由对应 Skill。
4. Skill 输出结构化结果，Policy Gate 判定落地方式。
5. 系统返回提取状态、建议结果，并写入相应 Memory。

**输出产物**：
- 导入历史记录。
- Skill 执行结果。
- `ai_suggestions` 或等效建议区结果。
- 对应 Memory 记录。

**异常与边界处理**：
- 不支持的文档类型或文件格式必须被拒绝并返回明确提示。
- Skill 失败时保留失败状态和失败原因，不得伪造成功结果。

#### SCN-002：管理员导入服务治理文档并更新画像

**场景分类**：CAT-B 管理员治理  
**主要角色**：admin  
**相关对象**：Service Governance Import、System Profile、Skill Execution Session、Memory Record  
**关联需求ID**：REQ-003、REQ-005、REQ-007、REQ-009、REQ-C003

**前置条件**：
- Admin 已登录且具备 admin 角色。
- 系统清单中存在标准系统名称。
- Admin 已进入服务治理页。

**触发条件**：
- Admin 上传治理文档/模板并提交导入。

**流程步骤**：
1. Runtime 以 `scene_id=admin_service_governance_import` 执行。
2. `service_governance_skill` 解析输入，并按标准系统名匹配系统清单。
3. 对匹配成功项，系统以 D3 更新为主执行自动或草稿更新。
4. 对 D1/D4 的语义影响交由 Policy Gate 判定为草稿更新或建议。
5. 系统返回匹配成功/未匹配统计，并写入画像更新 Memory。

**输出产物**：
- D3 更新结果。
- D1/D4 语义影响结果。
- 匹配成功/未匹配统计与行级失败原因。
- 对应 Memory 记录。

**异常与边界处理**：
- 未匹配项只进入结果清单，不得误写入其他系统画像。
- 自动更新不得覆盖 `manual` 内容。

#### SCN-003：管理员确认系统清单导入并初始化/补空画像

**场景分类**：CAT-B 管理员治理  
**主要角色**：admin  
**相关对象**：System Catalog Import、System Profile、Skill Execution Session、Memory Record  
**关联需求ID**：REQ-004、REQ-005、REQ-007、REQ-009

**前置条件**：
- Admin 已完成系统清单导入 preview。
- Confirm 请求中的数据通过校验。

**触发条件**：
- Admin 提交系统清单导入 confirm。

**流程步骤**：
1. 系统先完成系统清单铺底数据写入。
2. Runtime 触发 `scene_id=admin_system_catalog_import`。
3. `system_catalog_skill` 解析高价值字段并匹配系统画像。
4. Policy Gate 按“空画像”规则筛选可更新目标：仅对首次初始化或 `profile_data` 全空的画像执行初始化写入。
5. 系统汇总已初始化系统列表、跳过项和 Memory 写入结果；非空画像不生成建议接受任务。

**输出产物**：
- 系统清单导入确认结果。
- 系统画像批量联动结果。
- 对应 Memory 记录。

**异常与边界处理**：
- Preview 阶段不允许更新系统画像。
- Confirm 阶段若存在行级错误，必须返回行级错误与受影响范围，不能静默跳过。
- `field_sources`、`ai_suggestions`、Memory 存在值但 `profile_data` D1-D5 canonical 字段全空时，仍按空画像处理。

#### SCN-004：Runtime 按场景路由和串联 Skill

**场景分类**：CAT-C Runtime  
**主要角色**：系统  
**相关对象**：Skill Execution Session、Skill Registry、Memory Record  
**关联需求ID**：REQ-005、REQ-006、REQ-007

**前置条件**：
- Skill Registry 已加载。
- Scene 配置存在。

**触发条件**：
- 任一业务入口触发 Skill Runtime。

**流程步骤**：
1. Runtime 读取 `scene_id`、输入类型和目标工件。
2. Router 从 Registry 中选择一个或多个 Skill。
3. Scene Executor 执行 Skill 并收集输出。
4. Policy Gate 判定落地方式。
5. Runtime 统一写回画像结果和 Memory。

**输出产物**：
- Skill 执行链。
- Scene 最终结果。
- 策略判定结果。

**异常与边界处理**：
- 不允许使用“默认 Skill”吞掉未知场景或未知输入。
- 对未启用的未来 Skill 必须识别其定义，但不得被误执行。

#### SCN-005：PM 手动编辑画像并保持 manual 优先级

**场景分类**：CAT-D 画像维护  
**主要角色**：manager  
**相关对象**：System Profile、Memory Record  
**关联需求ID**：REQ-002、REQ-007、REQ-009、REQ-C003

**前置条件**：
- PM 已登录并进入本人负责系统的画像面板。

**触发条件**：
- PM 手动保存画像字段。

**流程步骤**：
1. PM 修改并保存画像字段。
2. 系统为相关字段写入 `manual` 来源标记。
3. 系统生成画像更新 Memory。
4. 后续自动更新时，Policy Gate 检查 `manual` 优先级并决定跳过或建议化。

**输出产物**：
- 新的画像草稿。
- `field_sources` 更新结果。
- `profile_update` Memory。

**异常与边界处理**：
- 自动更新命中 `manual` 字段时必须给出“跳过原因”，不得静默覆盖。

#### SCN-006：Memory 驱动系统识别直接判定

**场景分类**：CAT-E 系统识别  
**主要角色**：系统  
**相关对象**：Identification Result、System Profile、Memory Record  
**关联需求ID**：REQ-007、REQ-008、REQ-C005

**前置条件**：
- 已存在需求文本或其他待识别材料。
- 系统清单、系统画像和相关 Memory 可访问。

**触发条件**：
- 系统识别链路启动或重试。

**流程步骤**：
1. 系统优先读取系统清单别名、系统画像和相关 Memory。
2. 对明确命中的稳定事实执行 Direct Decision。
3. 对剩余复杂场景再调用 LLM 做语义补强。
4. 输出 `matched / ambiguous / unknown` 之一，并写入 `identification_decision` Memory。

**输出产物**：
- 直接判定结果。
- 候选系统与澄清问题（如有）。
- `identification_decision` Memory。

**异常与边界处理**：
- 不允许只返回候选列表而没有最终判定。
- 歧义场景不得静默选择一个系统。

#### SCN-007：Memory 驱动功能点拆解与修改沉淀

**场景分类**：CAT-F 功能点拆解  
**主要角色**：系统、manager  
**相关对象**：Function Point Adjustment、System Profile、Memory Record  
**关联需求ID**：REQ-007、REQ-010

**前置条件**：
- 已完成系统识别或已有目标系统上下文。
- 系统画像与相关 Memory 可访问。

**触发条件**：
- AI 功能点拆解启动，或 PM 对 AI 首轮结果进行修改。

**流程步骤**：
1. 功能点拆解链路先读取系统画像和相关 Memory。
2. 系统生成结构化拆解草稿，并按策略决定是否自动做低风险局部归一化。
3. PM 修改 AI 首轮结果后，系统按修改类型生成 `function_point_adjustment` Memory。
4. 后续拆解再次复用这些 Memory。

**输出产物**：
- 功能点拆解草稿。
- PM 修改后的调整轨迹。
- `function_point_adjustment` Memory。

**异常与边界处理**：
- 跨系统归属和跨模块结构重排不得静默自动定稿。
- Memory 失败不得被当作“完全成功”忽略。

#### SCN-008：Skill / 导入 / Memory 失败时返回可判定结果

**场景分类**：CAT-G 错误处理  
**主要角色**：manager、admin、系统  
**相关对象**：Skill Execution Session、Memory Record、System Profile  
**关联需求ID**：REQ-011、REQ-C006

**前置条件**：
- 用户已触发导入、识别、画像更新或功能点拆解链路。

**触发条件**：
- 任一处理环节失败、部分失败或补偿失败。

**流程步骤**：
1. 系统在失败点停止当前处理或标记补偿态。
2. 记录失败状态、失败原因和失败阶段。
3. 向页面或接口返回可判定结果。
4. 阻止把不完整数据写入正式画像结构或把 Memory 失败伪装为成功。

**输出产物**：
- 明确的成功 / 失败 / 部分成功结果。
- 对应失败原因或补偿记录。

**异常与边界处理**：
- 不允许“接口返回成功但 Runtime / Memory 已失败”的静默不一致结果。

#### SCN-009：版本切换时清理旧 schema 和历史评估数据

**场景分类**：CAT-H 数据清理  
**主要角色**：admin、系统  
**相关对象**：System Profile、Imported Document、Memory Record  
**关联需求ID**：REQ-012、REQ-105、REQ-C002

**前置条件**：
- v2.7 准备生效，环境中存在旧版画像结构或历史评估报告数据。

**触发条件**：
- 管理员或部署流程执行 v2.7 清理动作。

**流程步骤**：
1. 系统识别旧 schema 画像数据和历史评估报告相关存量数据。
2. 系统执行清理，不做旧数据迁移。
3. 系统输出清理结果，供管理员核验。
4. 清理完成后，新版本仅保留 v2.7 目标结构和允许的文档类型。

**输出产物**：
- 清理执行结果。
- 清理后数据核验结果。

**异常与边界处理**：
- 清理失败时必须阻止“旧数据已清零”的误判。

## 3. 功能性需求（Functional Requirements）

> **优先级说明**：M=Must / S=Should / C=Could / W=Won't。

### 3.1 功能性需求列表

| 需求分类 | REQ-ID | 需求名称 | 优先级 | 需求说明 | 关联场景ID |
|---|---|---|---|---|---|
| PM导入页 | REQ-001 | PM 导入页文档类型收敛 | M | PM 导入页仅保留需求文档、设计文档、技术方案三类入口，并拒绝旧类型 | SCN-001 |
| 画像结构 | REQ-002 | 5 域细粒度画像结构与面板适配 | M | 系统画像、空结构、保存读取和画像面板统一切换到 v2.7 目标 5 域结构 | SCN-005 |
| 服务治理 | REQ-003 | 管理员服务治理导入与画像联动 | M | 新增 admin 专属服务治理页，导入后以 D3 为主更新画像并输出统计结果 | SCN-002 |
| 系统清单联动 | REQ-004 | 系统清单导入确认后的画像初始化与补空 | M | 在系统清单导入 confirm 后，仅初始化命中系统中的空画像并跳过非空画像 | SCN-003 |
| Runtime平台 | REQ-005 | Skill Runtime 注册、路由与场景执行 | M | 建立 Runtime 平台，支持 Registry、Router、Scene Executor、Policy Gate 与内置 Skill 调度 | SCN-004 |
| Skill兼容 | REQ-006 | 多格式输入兼容与输出 canonical 化 | M | 各 Skill 必须兼容同类文档/模板差异，并输出统一结构 | SCN-001, SCN-002, SCN-003 |
| Memory资产 | REQ-007 | Per-System Memory 记录与扩展模型 | M | 为画像更新、系统识别、功能点修改写入分类 Memory，并支持未来扩展 | SCN-001, SCN-002, SCN-003, SCN-006, SCN-007 |
| 系统识别 | REQ-008 | Memory 驱动的系统识别直接判定 | M | 系统识别必须读取画像和 Memory，并给出直接判定 | SCN-006 |
| 画像策略 | REQ-009 | 场景化的画像更新落地策略 | M | 不同场景下区分 `auto_apply / draft_apply / suggestion_only / reject` | SCN-002, SCN-003, SCN-005 |
| 拆解策略 | REQ-010 | Memory 驱动的功能点拆解与修改应用 | M | 功能点拆解必须使用画像和 Memory，且对修改结果按类型沉淀和使用 | SCN-007 |
| 错误处理 | REQ-011 | Skill / 导入 / Memory 失败的可判定结果 | M | 失败必须可判定、可追溯，且不得静默脏写或静默成功 | SCN-008 |
| 数据清理 | REQ-012 | 旧 schema 与历史评估数据清理 | M | v2.7 生效前完成旧 schema 和历史评估报告数据清理，并输出可核验结果 | SCN-009 |

### 3.2 功能性需求明细 [包含 3.1 中所有功能性需求]

#### REQ-001：PM 导入页文档类型收敛 [Integration Required]

**测试等级**：Integration Required  
**目标/价值**：让 PM 导入页回到单系统知识导入职责，去除管理员治理入口和无关文档类型。  
**入口/触发**：PM 访问系统画像导入页或调用文档导入接口。  
**前置条件**：用户具备 manager 角色，且进入 PM 系统画像导入流程。

**主流程**：
1. 系统加载 PM 导入页配置。
2. 页面仅展示需求文档、设计文档、技术方案三类导入卡片。
3. PM 上传文档后，系统按文档类型进入对应 Runtime Scene。
4. 系统记录导入历史并返回提取任务状态。

**输入/输出**：
- 输入：系统 ID、文档文件、`doc_type in {requirements, design, tech_solution}`
- 输出：导入历史记录、提取任务状态、结构化结果入口

**页面与交互**：
- 涉及页面：PM 系统画像导入页
- 关键交互：选择文档类型、上传文件、查看导入历史、查看提取状态
- 信息展示：仅展示三类文档卡片；不展示历史评估报告/服务治理文档卡片及其模板下载按钮

**业务规则**：
- PM 导入页允许的文档类型仅为 `requirements`、`design`、`tech_solution`。
- 被移除的 `history_report`、`esb`、其他治理类类型不得继续作为 PM 页面的可见入口或成功导入类型。
- PM 模板下载接口仅允许 `requirements`、`design`、`tech_solution`。

**异常与边界**：
- 不支持的 `doc_type` 或文件扩展名必须返回可判定错误。
- 旧前端缓存或手工构造请求也不得绕过 allowlist。

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-001-01: Given manager 访问 PM 导入页，When 页面渲染完成，Then 页面仅展示“需求文档”“设计文档”“技术方案”三类卡片，且页面中不出现“历史评估报告”“服务治理文档”字符串。
- [ ] GWT-REQ-001-02: Given manager 上传合法 `requirements/design/tech_solution` 文档，When 调用导入接口成功，Then 系统记录成功导入历史，且返回可查询的 Runtime/提取状态。
- [ ] GWT-REQ-001-03: Given 请求携带 `doc_type=history_report` 或 `doc_type=esb`，When 调用 PM 文档导入接口，Then 系统返回明确失败结果，且不会生成成功导入历史记录。

**关联**：SCN-001

#### REQ-002：5 域细粒度画像结构与面板适配 [Integration Required]

**测试等级**：Integration Required  
**目标/价值**：统一前后端画像结构，使 v2.7 的 5 域细粒度模型成为唯一口径。  
**入口/触发**：读取画像、保存画像、发布画像、查看画像面板。  
**前置条件**：目标系统存在画像记录或可初始化空画像。

**主流程**：
1. 系统为目标系统返回 v2.7 目标画像结构。
2. PM 在画像面板查看和编辑 5 域字段。
3. 系统按同一套字段键保存、读取和发布画像。

**输入/输出**：
- 输入：5 域画像载荷、字段值、发布动作
- 输出：标准化 5 域画像、保存结果、发布结果

**页面与交互**：
- 涉及页面：系统画像面板
- 关键交互：切换 D1-D5 域、编辑字段、保存草稿、发布画像、查看 AI 建议和来源信息
- 信息展示：每个域展示固定字段与 `extensions`

**业务规则**：
- 画像一级域固定为 `system_positioning`、`business_capabilities`、`integration_interfaces`、`technical_architecture`、`constraints_risks`。
- D1 字段固定为 `system_type`、`business_domain`、`architecture_layer`、`target_users`、`service_scope`、`system_boundary`、`extensions`。
- D2 字段固定为 `functional_modules`、`business_processes`、`data_assets`、`extensions`。
- D3 字段固定为 `provided_services`、`consumed_services`、`other_integrations`、`extensions`。
- D4 字段固定为 `architecture_style`、`tech_stack`、`network_zone`、`performance_baseline`、`extensions`；其中 `tech_stack` 按 `languages/frameworks/databases/middleware/others` 分类。
- D5 字段固定为 `technical_constraints`、`business_constraints`、`known_risks`、`extensions`。

**异常与边界**：
- 读取空画像时，系统必须返回完整空结构，而不是缺失域或缺失字段。
- 前端不得再依赖旧 schema 字段名渲染页面。

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-002-01: Given 系统首次创建或已清空画像，When 读取画像详情，Then 返回 5 个一级域，且每个域都包含本需求定义的目标字段和 `extensions` 键。
- [ ] GWT-REQ-002-02: Given 读取 D4 技术架构域，When 查看 `tech_stack` 与 `performance_baseline` 结构，Then `tech_stack` 至少包含 `languages/frameworks/databases/middleware/others` 五类键，且 `performance_baseline` 支持“联机/批量 + processing_model”结构。
- [ ] GWT-REQ-002-03: Given manager 在画像面板保存包含 D1-D5 新字段的画像，When 重新读取并渲染页面，Then 页面按新 5 域结构展示并保留已保存值。

**关联**：SCN-005

#### REQ-003：管理员服务治理导入与画像联动 [E2E Required]

**测试等级**：E2E Required  
**目标/价值**：把服务治理导入从 PM 逐系统操作改为管理员集中治理与批量画像联动。  
**入口/触发**：admin 访问服务治理页并上传治理文档/模板。  
**前置条件**：用户具备 admin 角色；系统清单存在标准系统名称；服务治理页可访问。

**主流程**：
1. Admin 进入服务治理页。
2. 上传合法治理文档/模板。
3. Runtime 执行 `scene_id=admin_service_governance_import` 和 `service_governance_skill`。
4. 对匹配成功记录，系统以 D3 更新为主批量更新画像。
5. 页面返回匹配成功/未匹配统计及未匹配项清单。

**输入/输出**：
- 输入：治理文档/模板、管理员操作
- 输出：D3 更新结果、统计结果、未匹配项、失败原因

**页面与交互**：
- 涉及页面：管理员“服务治理”页
- 关键交互：上传模板、查看导入结果、查看未匹配项、重新导入
- 信息展示：匹配成功数、未匹配数、未匹配项清单、更新摘要

**业务规则**：
- 服务治理页为 admin 专属入口，不复用 PM 导入页。
- 本期最新治理模板样例以 `data/esb-template.xlsx` 为准；该模板的提供/消费方表头口径（如 `服务方系统名称`、`消费方系统名称`）属于 v2.7 必须兼容范围。
- 历史 `data/接口申请模板.xlsx` 继续作为兼容输入保留，但不得反向定义 v2.7 的最新模板口径。
- `service_governance_skill` 负责解析治理输入、生成 D3 结构化结果，并为 D1/D4 语义影响提供输入信号。
- D3 更新至少包含服务名称、服务分类、对端系统、消费方数量、状态和域级汇总统计。
- D1/D4 的语义影响不在本需求中直接放行为无条件自动覆盖，而必须进一步走 REQ-009 的场景化策略。
- 未匹配项只进入结果清单，不得误写入其他系统画像。

**异常与边界**：
- 模板格式错误、缺失关键列或内容为空时，系统必须拒绝导入并返回明确失败原因。
- 单条记录未匹配不能阻断整批统计结果输出，但不能把未匹配记录当作已更新。

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-003-01: Given admin 在服务治理页上传包含 3 条可匹配记录和 1 条未匹配记录的治理模板，When 导入完成，Then 页面展示“匹配成功=3、未匹配=1”，且未匹配项清单包含该 1 条记录。
- [ ] GWT-REQ-003-02: Given 治理模板记录的系统名与系统清单标准名称一致，When 导入完成，Then 对应系统画像 D3 至少包含服务名称、服务分类、对端系统、消费方数量、状态字段，并可读取到域级汇总统计。
- [ ] GWT-REQ-003-03: Given 治理模板缺失必填列或文件不可解析，When admin 提交导入，Then 系统返回明确失败结果，且不更新任何系统画像。

**关联**：SCN-002

#### REQ-004：系统清单导入确认后的画像初始化与补空 [E2E Required]

**测试等级**：E2E Required  
**目标/价值**：让系统清单中的高价值台账字段只在可安全初始化的场景下回填命中系统画像，避免月度台账更新覆盖已有画像。  
**入口/触发**：admin 执行系统清单导入 preview / confirm。  
**前置条件**：系统清单导入模板合法；preview 已输出校验结果。

**主流程**：
1. Admin 上传系统清单模板，系统执行 preview。
2. Admin 确认导入内容后提交 confirm。
3. 系统完成台账写入，并以 `scene_id=admin_system_catalog_import` 触发 Runtime。
4. `system_catalog_skill` 解析高价值字段，并按空画像规则筛选可初始化目标。
5. 对满足条件的目标系统直接完成画像初始化/补空；对非空画像返回跳过原因，不生成 PM 建议接受任务。
6. 系统返回受影响系统列表、跳过项和失败原因。

**输入/输出**：
- 输入：系统清单导入文件、preview/confirm 操作
- 输出：导入结果、受影响系统列表、画像批量更新结果

**业务规则**：
- Preview 只负责校验和展示差异，不得更新系统画像。
- Confirm 后才允许触发 `system_catalog_skill`。
- `system_catalog_skill` 仅处理单一系统清单模板，不再要求额外子系统 Sheet 或主子系统映射输入。
- `system_catalog_skill` 的确定性 canonical 映射固定为：
  - `系统类型` -> `D1.system_type`
  - `应用主题域` -> `D1.business_domain`
  - `应用分层` -> `D1.architecture_layer`
  - `服务对象` -> `D1.target_users`
  - `功能描述` -> `D1.service_scope`
  - `开发语言` -> `D4.tech_stack.languages`
  - `RDBMS` -> `D4.tech_stack.databases`
  - `应用中间件` -> `D4.tech_stack.middleware`
  - `操作系统` / `芯片` / `新技术特征` -> `D4.tech_stack.others`
- `system_catalog_skill` 的弱证据映射固定进入 `extensions`：
  - `英文简称` -> `D1.extensions.aliases`
  - `业务领域` -> `D1.extensions.business_lines`
  - `状态` / `应用等级` -> `D1.extensions.*`
  - `是否云部署` / `是否有互联网出口` / `是否双活` / `集群分类` / `虚拟化分布` -> `D4.extensions.*`
  - `全栈信创` / `等保定级` / `是否是重要信息系统` -> `D5.extensions.*`
  - `系统RTO` / `系统RPO` / `灾备情况` / `灾备部署地` / `应急预案更新日期` -> `D5.extensions.*`
  - `知识产权` / `产品授权证书情况` -> `D5.extensions.*`
  - `关联系统` -> `D3.extensions.catalog_related_systems`
- 以下台账/责任字段不得进入画像：`系统编号`、`上线日期`、`下线时间`、`主管部门`、`产品经理`、`系统负责人`、`需求分析师`、`架构师`、`归属中心`、`实施厂商`、`厂商属地`、`开发模式`、`运维模式`、`备注`。
- “空画像”判定仅检查 `profile_data` 下 D1-D5 canonical 字段是否全部为空值/空数组/空对象；`field_sources`、`ai_suggestions`、Memory 记录不参与判定。
- 系统首次初始化时允许批量联动，但仅对满足空画像条件的命中系统执行初始化写入，且无须 PM 接受建议。
- 若系统清单已存在，后续月度更新或覆盖导入只允许补空画像；目标画像存在任一非空 canonical 字段时必须整份跳过，不得覆盖。
- 系统清单场景只允许对明确字段映射执行初始化写入；不通过 PM 建议流处理非空画像。
- `功能描述` 只允许初始化到 `D1.service_scope`，不得拆分写入 `D2.functional_modules` 或 `D2.business_processes`。
- `关联系统` 只允许写入 `D3.extensions.catalog_related_systems`，不得直接写入 `D3.provided_services`、`D3.consumed_services` 或 `D3.other_integrations`。

**异常与边界**：
- 行级错误必须在 preview 或 confirm 结果中返回，不允许在后台静默跳过。
- 未命中画像的系统必须在结果中标明。
- 命中非空画像不属于失败，但必须返回明确跳过原因（如 `profile_not_blank`）。

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-004-01: Given admin 上传包含合法与非法行混合的系统清单模板，When 执行 preview，Then 系统返回行级校验结果与错误行号，且不更新任何系统画像。
- [ ] GWT-REQ-004-02: Given admin 在系统清单首次初始化场景下对 100 条合法记录执行 confirm，且其中命中系统存在空画像与非空画像两类，When Runtime 完成 `system_catalog_skill`，Then 系统仅对空画像直接完成初始化写入、无需 PM 接受建议，并返回 `updated_system_ids/skipped_items` 结果。
- [ ] GWT-REQ-004-03: Given 系统清单已存在，且某命中系统的 `profile_data` 下 D1-D5 canonical 字段中任一字段非空，When admin 再次执行 confirm 覆盖导入，Then 该系统画像保持不变，并在结果中标记 `profile_not_blank` 或等效跳过原因。
- [ ] GWT-REQ-004-04: Given 某空画像命中系统的系统清单记录同时包含 canonical 字段、弱证据字段和 ignore 字段，When admin 执行 confirm，Then 系统仅按本需求定义把字段分别写入 canonical 或 `extensions`，且 ignore 字段不进入画像。
- [ ] GWT-REQ-004-05: Given 系统清单记录包含 `功能描述` 和 `关联系统` 两列，When admin 执行 confirm 初始化空画像，Then `功能描述` 只进入 `D1.service_scope`，`关联系统` 只进入 `D3.extensions.catalog_related_systems`，两者都不触发 D2 或 D3 canonical 写入。

**关联**：SCN-003

#### REQ-005：Skill Runtime 注册、路由与场景执行 [Integration Required]

**测试等级**：Integration Required  
**目标/价值**：让系统具备像 Codex 一样的 Skill 调用能力，而不是停留在脚本集合。  
**入口/触发**：PM 文档导入、服务治理导入、系统清单导入 confirm、系统识别、功能点拆解。  
**前置条件**：Skill Registry 已加载。

**主流程**：
1. 系统加载 Skill Registry。
2. 根据 `scene_id`、输入类型和目标工件选择一个或多个 Skill。
3. Scene Executor 执行 Skill。
4. Policy Gate 判定落地策略。
5. Runtime 写回结果与 Memory。

**输入/输出**：
- 输入：场景、输入载荷、上下文
- 输出：Skill 执行链、场景结果、策略判定、Memory 写回结果

**业务规则**：
- Runtime 至少包含 `Skill Registry`、`Skill Router`、`Scene Executor`、`Policy Gate`、`Memory Reader/Writer` 五个能力组件。
- v2.7 内置 Skill 固定交付 6 个：
  - `service_governance_skill`
  - `system_catalog_skill`
  - `requirements_skill`
  - `design_skill`
  - `tech_solution_skill`
  - `code_scan_skill`
- 每个 Skill 至少定义：
  - `skill_id`
  - `skill_type`
  - `supported_inputs`
  - `supported_tasks`
  - `target_artifacts`
  - `execution_mode`
  - `decision_policy`
  - `version`
- Runtime 必须支持场景化串联，例如服务治理导入场景至少串联“Skill -> Policy Gate -> Memory Writer”。
- Runtime 不得把当前 6 个内置 Skill 写死为唯一可识别集合；未来 Skill 可以通过注册表扩展并以启停状态控制。
- `code_scan_skill` 必须支持 `repo_path` 与源码压缩包两种输入源，并通过统一 skill 定义暴露给 Runtime。
- `code_scan_skill` 在 v2.7 的扫描范围固定为 Java / Spring Boot 与前端 JS / TS，中度语义扫描结果只用于 D4 建议与功能点拆解上下文，不直接覆盖正式画像。

**异常与边界**：
- 未知场景或未知输入不得落到“默认 Skill”。
- 未启用的未来 Skill 可以被 Registry 识别，但不得被误执行。

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-005-01: Given Runtime 加载 v2.7 注册表，When 查询平台组件与 Scene 配置，Then 可读取到 Registry、Router、Scene Executor、Policy Gate、Memory Reader/Writer 五类能力以及已配置的业务 Scene。
- [ ] GWT-REQ-005-02: Given 查询内置 Skill 注册表，When 检查 Skill 列表，Then 注册表中存在且仅存在 `service_governance_skill`、`system_catalog_skill`、`requirements_skill`、`design_skill`、`tech_solution_skill`、`code_scan_skill` 六项内置 Skill。
- [ ] GWT-REQ-005-03: Given 查询任一 Skill 定义，When 检查配置项，Then 每个 Skill 都明确声明 `skill_id/skill_type/supported_inputs/supported_tasks/target_artifacts/execution_mode/decision_policy/version`。
- [ ] GWT-REQ-005-04: Given `scene_id=admin_service_governance_import` 或 `scene_id=admin_system_catalog_import`，When Runtime 执行场景，Then 系统分别路由到 `service_governance_skill` 或 `system_catalog_skill`，并在 Skill 后执行 Policy Gate 与 Memory Writer，而不是仅执行单个脚本后返回。
- [ ] GWT-REQ-005-05: Given 注册表中存在一个 `enabled=false` 的未来 Skill 定义（如 `requirement_review_skill`），When Runtime 加载注册表，Then 该定义可被识别为合法配置，但不会被纳入可执行内置 Skill 集合。
- [ ] GWT-REQ-005-06: Given 查询 `code_scan_skill` 的注册定义，When 检查其输入源与扫描范围，Then 可读取到 `repo_path`、`repo_archive` 两种输入源，以及“Java / Spring Boot + JS / TS 中度语义扫描”的固定能力边界。

**关联**：SCN-004

#### REQ-006：多格式输入兼容与输出 canonical 化 [Integration Required]

**测试等级**：Integration Required  
**目标/价值**：避免同类文档或模板因格式差异导致 Skill 提取失败或输出口径分裂。  
**入口/触发**：文档导入、服务治理导入、系统清单导入 confirm。  
**前置条件**：目标 Skill 已可被调度。

**主流程**：
1. 系统接收同类但版式不同的文档或模板。
2. 对应 Skill 执行预处理与提取。
3. Skill 输出统一 canonical 结构结果。

**输入/输出**：
- 输入：同类不同格式的文档或模板
- 输出：同一结构的结构化结果或行级错误

**业务规则**：
- 同类需求/设计/技术方案文档允许存在不同标题层级、章节命名和内容分布。
- PM 文档类 skill 在 v2.7 的输入格式边界固定为可直接抽文本的 `docx`、文本型 `pdf`、`pptx`；扫描件 PDF、纯图片型 PPTX/OCR 场景不属于本期有效性目标。
- 服务治理模板允许存在受支持的列名别名，但输出的 D3 结果结构必须一致。
- 系统清单模板允许出现额外列，但核心字段缺失时必须给出行级错误；v2.7 不得再要求额外“子系统清单”Sheet。
- 缺失字段可为空，但结果结构不能缺少 canonical 键。

**异常与边界**：
- 对内容缺失的文档，Skill 可返回空值，但不能伪造字段内容。
- 对无法识别的列或内容块，系统必须返回失败原因或行级错误。

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-006-01: Given 两份“需求文档”语义相近但标题层级和章节命名不同，When `requirements_skill` 提取完成，Then 两份结果都输出同一套 D1/D2/D5 目标字段键。
- [ ] GWT-REQ-006-02: Given 两份列名别名不同但语义一致的治理模板，When `service_governance_skill` 提取完成，Then 两份结果都归一到同一套 D3 canonical 字段键，或对无法识别列返回明确行级错误。
- [ ] GWT-REQ-006-03: Given 系统清单模板包含额外非核心列，When `system_catalog_skill` 处理 confirm 数据，Then 系统仍按 canonical 字段解析可初始化字段，并对缺失核心字段的记录返回行级错误，而不是中断全部处理。
- [ ] GWT-REQ-006-04: Given 当前系统清单模板仅包含单一系统清单表，When `system_catalog_skill` 执行 preview 或 confirm，Then 系统可正常解析该模板且不会因为缺少子系统 Sheet 而失败。
- [ ] GWT-REQ-006-05: Given PM 上传 `docx`、文本型 `pdf` 或 `pptx` 的需求/设计/技术方案文档，When 文档类 skill 执行，Then 系统按统一文本解析链路处理；若上传扫描件 PDF 或纯图片型 PPTX，Then 系统明确返回“超出本期有效性范围”或等效提示，而不是伪造高置信提取结果。

**关联**：SCN-001；SCN-002；SCN-003

#### REQ-007：Per-System Memory 记录与扩展模型 [Integration Required]

**测试等级**：Integration Required  
**目标/价值**：把系统画像更新、系统识别、功能点修改沉淀为可复用系统级资产，而不是普通日志。  
**入口/触发**：画像更新、系统识别完成、AI 评估后功能点修改、未来扩展记录写入。  
**前置条件**：目标系统存在 `system_id`。

**主流程**：
1. 业务动作成功后生成对应 Memory Record。
2. Memory Writer 写入统一结构的系统级资产记录。
3. Memory Reader 按系统、类型、场景提供读取能力。

**输入/输出**：
- 输入：业务动作结果、上下文、证据引用
- 输出：Memory Record、查询结果

**业务规则**：
- v2.7 Memory 至少支持以下 `memory_type`：
  - `profile_update`
  - `identification_decision`
  - `function_point_adjustment`
- 每条 Memory 至少包含：
  - `memory_id`
  - `system_id`
  - `memory_type`
  - `memory_subtype`
  - `scene_id`
  - `source_type`
  - `source_id`
  - `evidence_refs`
  - `decision_policy`
  - `confidence`
  - `created_at`
- `profile_update` 至少记录变化字段或变化摘要。
- `identification_decision` 至少记录最终判定、理由和候选解释。
- `function_point_adjustment` 至少记录修改类型，如新增、删除、合并、拆分、改写、复杂度调整、归属调整。
- Memory 模型必须可扩展到未来 `review_issue`、`review_resolution` 等类型，而不另起一套专用结构。

**异常与边界**：
- Memory 不是普通 debug 日志，不允许缺少 `system_id` 和类型信息。
- 同一业务动作的 Memory 写入失败不得被静默忽略。

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-007-01: Given 某系统画像完成一次字段更新，When 业务动作成功，Then 系统写入一条 `memory_type=profile_update` 的 Memory，且包含字段变化摘要或等效 diff 信息。
- [ ] GWT-REQ-007-02: Given 系统识别完成一次判定，When 结果落库，Then 系统写入一条 `memory_type=identification_decision` 的 Memory，且包含最终判定和理由摘要。
- [ ] GWT-REQ-007-03: Given PM 在 AI 首轮功能点结果上执行新增、删除、合并、拆分、改写、复杂度调整或归属调整，When 保存修改，Then 系统写入 `memory_type=function_point_adjustment` 的 Memory，且记录对应调整分类。
- [ ] GWT-REQ-007-04: Given 系统尝试写入 `memory_type=review_issue` 的未来类型记录，When 校验公共元数据，Then Memory 模型接受该记录并可被查询，而不要求新增一套专用存储结构。

**关联**：SCN-001；SCN-002；SCN-003；SCN-006；SCN-007

#### REQ-008：Memory 驱动的系统识别直接判定 [Integration Required]

**测试等级**：Integration Required  
**目标/价值**：让系统识别先基于稳定事实和 Memory 做直接判断，再由 LLM 补强，而不是只给候选列表。  
**入口/触发**：系统识别链路启动、重试。  
**前置条件**：需求文本或其他待识别材料已存在；系统清单、系统画像和 Memory 可访问。

**主流程**：
1. 系统读取系统清单、系统画像和相关 Memory。
2. 对别名、标准名、已确认映射等稳定事实做 Direct Decision。
3. 对未收敛部分调用 LLM 做语义补强。
4. 系统输出 `matched / ambiguous / unknown` 之一，并附带解释信息。
5. 系统写入 `identification_decision` Memory。

**输入/输出**：
- 输入：需求文本、候选系统线索、画像与 Memory 上下文
- 输出：最终判定、候选系统、澄清问题、Memory 记录

**业务规则**：
- 精确命中别名、标准名或已确认稳定映射时，系统应直接输出 `matched`。
- 存在多个高相似候选且无法收敛到唯一系统时，系统应输出 `ambiguous`。
- 证据不足或无法稳定指向任一系统时，系统应输出 `unknown`。
- `candidate_systems` 和 `questions` 只能作为解释，不得替代最终判定。

**异常与边界**：
- 不允许只输出候选列表而没有 `final_verdict`。
- 不允许在 `ambiguous` 场景静默选中一个系统继续后续链路。

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-008-01: Given 需求文本中出现某系统的已确认别名，且该别名已存在于系统清单或 `identification_decision` Memory 的稳定映射中，When 执行系统识别，Then 最终结果直接返回 `matched` 且指向该系统。
- [ ] GWT-REQ-008-02: Given 需求文本同时命中两个高相似候选系统且证据不足以唯一收敛，When 执行系统识别，Then 最终结果返回 `ambiguous`，并列出候选系统与澄清问题，而不是静默选择其一。
- [ ] GWT-REQ-008-03: Given 需求文本无法可靠映射到任何标准系统，When 执行系统识别，Then 最终结果返回 `unknown`，且不进入“已选中系统”的后续链路。
- [ ] GWT-REQ-008-04: Given 任一系统识别响应，When 检查返回载荷，Then 其中必须存在 `final_verdict` 字段，且值只能是 `matched`、`ambiguous`、`unknown` 三者之一。

**关联**：SCN-006

#### REQ-009：场景化的画像更新落地策略 [Integration Required]

**测试等级**：Integration Required  
**目标/价值**：让不同来源和不同风险等级的画像更新按场景落地，避免“要么全自动、要么全建议”的粗糙策略。  
**入口/触发**：服务治理导入、系统清单导入、PM 文档导入、代码扫描、PM 手动保存。  
**前置条件**：Skill 输出已生成，Policy Gate 可执行。

**主流程**：
1. Runtime 收到 Skill 输出。
2. Policy Gate 根据场景、证据类型、冲突情况和 `manual` 优先级做策略判定。
3. 系统执行 `auto_apply / draft_apply / suggestion_only / reject` 之一。

**输入/输出**：
- 输入：Skill 输出、场景、字段冲突、来源信息
- 输出：策略判定结果、画像更新结果、建议结果、Memory

**业务规则**：
- 服务治理导入中的 D3 结构化事实默认 `auto_apply` 到当前画像草稿，但不得覆盖 `manual`。
- 系统清单导入中的明确字段映射仅在目标画像满足空画像条件时 `auto_apply` 到正式 `profile_data`；目标画像非空时统一 `reject/skip`。
- 系统清单导入不为非空画像生成 PM 需接受的建议任务；服务治理中的语义推断结果和存在冲突的更新默认 `suggestion_only`。
- `requirements_skill`、`design_skill`、`tech_solution_skill`、`code_scan_skill` 的输出默认 `suggestion_only`，不得直接覆盖正式画像字段。
- 任一自动更新命中 `manual` 字段时，必须以跳过或建议化处理，不得覆盖。

**异常与边界**：
- 不允许把语义推断结果静默自动覆盖到正式画像字段。
- 不允许因为一处 `manual` 冲突而阻断整个系统的其他低风险更新。
- 不允许把 `field_sources`、`ai_suggestions` 或 Memory 元数据误判为“画像已有内容”而阻断系统清单初始化。

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-009-01: Given 服务治理导入产生一条结构化 D3 集成记录，且目标字段不存在 `manual` 冲突，When Policy Gate 判定，Then 该记录直接 `auto_apply` 到当前画像草稿的 D3。
- [ ] GWT-REQ-009-02: Given 系统清单导入提供一条明确字段映射的标准信息，且目标系统画像满足空画像条件，When Policy Gate 判定，Then 该字段直接 `auto_apply` 到正式 `profile_data`，并记录 `system_catalog` 来源和对应 `profile_update` Memory。
- [ ] GWT-REQ-009-03: Given 系统清单导入命中某个已存在非空 canonical 字段的系统画像，When Policy Gate 判定，Then 结果为 `reject/skip`，且系统既不覆盖 `profile_data`，也不生成需 PM 接受的 `ai_suggestions`。
- [ ] GWT-REQ-009-04: Given `requirements_skill`、`design_skill`、`tech_solution_skill` 或 `code_scan_skill` 任一输出成功，When 用户重新读取画像详情，Then 结果进入建议区或等效 `ai_suggestions`，且正式 `profile_data` 未被自动覆盖。
- [ ] GWT-REQ-009-05: Given 某字段已被 PM 标记为 `manual`，When 任一自动导入链路命中该字段，Then 系统不覆盖该字段，并在结果中标记“manual 优先导致跳过或转建议”。

**关联**：SCN-002；SCN-003；SCN-005

#### REQ-010：Memory 驱动的功能点拆解与修改应用 [Integration Required]

**测试等级**：Integration Required  
**目标/价值**：让功能点拆解复用系统画像和 Memory 资产，并把 AI 评估后的修改沉淀为可复用经验。  
**入口/触发**：功能点拆解启动、PM 修改 AI 首轮结果。  
**前置条件**：系统识别已完成或已有目标系统上下文；系统画像与 Memory 可访问。

**主流程**：
1. 功能点拆解前读取系统画像和相关 Memory。
2. 系统生成结构化拆解草稿。
3. 对低风险局部归一化场景允许自动应用到草稿。
4. 对跨系统归属、跨模块结构重排等高风险场景只输出建议或待复核草稿。
5. PM 修改 AI 首轮结果后，系统记录 `function_point_adjustment` Memory。

**输入/输出**：
- 输入：需求文本、目标系统、系统画像、Memory、PM 修改
- 输出：功能点草稿、修改结果、Memory 记录

**业务规则**：
- 功能点拆解必须读取目标系统画像和相关 Memory，再调用 LLM。
- 已确认的局部命名归一化、重复项去重、稳定模块映射等低风险模式允许自动应用到“当前拆解草稿”。
- 跨系统归属判断、模块拆分/合并、范围变更等高风险调整默认 `suggestion_only` 或待复核草稿，不得静默自动定稿。
- AI 首轮评估后，PM 对功能点的新增、删除、合并、拆分、改写、复杂度调整、归属调整都必须写入分类 Memory。

**异常与边界**：
- 功能点拆解不得忽略目标系统画像边界。
- Memory 失败不得被伪装为完整成功。

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-010-01: Given 某系统已存在与功能点命名和模块归属相关的 `function_point_adjustment` Memory，When 对同一系统执行新一轮功能点拆解，Then 拆解草稿会读取这些 Memory 并在输出中体现同一命名或模块模式，而不是完全忽略历史调整。
- [ ] GWT-REQ-010-02: Given 某类低风险局部归一化模式已被确认可复用，When 新一轮拆解命中同类模式，Then 系统可将该调整自动应用到当前拆解草稿，并写入新的 `function_point_adjustment` Memory。
- [ ] GWT-REQ-010-03: Given 拆解结果涉及跨系统归属或跨模块结构重排，When 系统完成策略判定，Then 结果仅以建议或待复核草稿形式返回，而不是直接自动定稿。

**关联**：SCN-007

#### REQ-011：Skill / 导入 / Memory 失败的可判定结果 [Integration Required]

**测试等级**：Integration Required  
**目标/价值**：让用户和测试都能明确判断失败位置、失败原因和数据是否落库。  
**入口/触发**：Runtime 失败、Skill 失败、导入失败、Memory 写入失败。  
**前置条件**：用户或系统已触发相关链路。

**主流程**：
1. 系统在失败点停止当前处理或转入补偿态。
2. 记录失败状态、失败原因和失败阶段。
3. 向页面或接口返回可判定结果。
4. 阻止把不完整数据写入正式画像结构，或把 Memory 失败伪装为完全成功。

**输入/输出**：
- 输入：失败的请求或处理中间结果
- 输出：失败状态、失败原因、补偿记录或部分成功结果

**业务规则**：
- Skill 失败必须更新导入历史或执行状态。
- 服务治理和系统清单允许“部分成功 + 行级错误”，但不允许脏写。
- Memory 写入失败时，业务结果不得标记为“完全成功”；必须返回 `partial_success` 或等效补偿态。
- 禁止“接口返回 success，但内部 Runtime 或 Memory 已失败”的静默不一致结果。

**异常与边界**：
- 写入阶段失败时，系统不得把失败前的半成品误报为成功画像。
- Preview 阶段失败不得触发 confirm 或画像联动。

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-011-01: Given PM 导入文档后 Skill 执行失败，When 查询导入历史和提取状态，Then 导入历史或任务状态显示失败终态，并包含失败原因。
- [ ] GWT-REQ-011-02: Given 系统清单 preview 返回行级错误，When 用户未执行 confirm，Then 系统画像不发生任何更新。
- [ ] GWT-REQ-011-03: Given 画像更新业务动作已成功但 Memory 写入失败，When 接口返回结果，Then 返回状态为 `partial_success` 或等效补偿态，并包含 Memory 失败原因，而不是返回“success”。
- [ ] GWT-REQ-011-04: Given Runtime 在中途失败，When 用户重新读取画像详情或执行结果，Then 不会看到未标记来源的半成品数据被写入正式画像字段。

**关联**：SCN-008

#### REQ-012：旧 schema 与历史评估数据清理 [Integration Required]

**测试等级**：Integration Required  
**目标/价值**：避免 v2.7 上线后保留旧 schema 与无关历史评估数据，造成口径混乱。  
**入口/触发**：v2.7 数据清理任务、部署前核验。  
**前置条件**：环境中存在旧 schema 画像数据或历史评估报告相关存量数据。

**主流程**：
1. 系统识别旧 schema 画像数据。
2. 系统识别历史评估报告相关存量导入/向量数据。
3. 执行清理，不做迁移。
4. 输出清理结果，供核验。

**输入/输出**：
- 输入：待清理的画像数据、知识数据、导入记录
- 输出：清理结果、清理后核验结果

**业务规则**：
- 清理对象至少包含旧 schema 画像数据和历史评估报告相关存量数据。
- 清理后系统只保留 v2.7 允许的画像结构和导入类型。
- 清理结果必须可通过查询或脚本核验。

**异常与边界**：
- 清理失败时不得把状态标记为已完成。
- 不要求保留旧 schema 到新 schema 的迁移兼容层。

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-012-01: Given 环境中存在旧 schema 画像记录与历史评估报告相关存量数据，When 执行 v2.7 清理，Then 旧 schema 数据和历史评估报告数据都被移除。
- [ ] GWT-REQ-012-02: Given 清理完成，When 执行核验查询，Then 旧 schema 画像数据计数为 0，且历史评估报告类型存量数据计数为 0。
- [ ] GWT-REQ-012-03: Given 清理过程中发生异常，When 清理任务结束，Then 系统返回失败结果并附带失败原因，不会误报“已清理完成”。

**关联**：SCN-009

## 4. 非功能需求

### 4.1 非功能需求列表

| 需求分类 | REQ-ID | 需求名称 | 优先级 | 需求说明 | 验收/指标 |
|---|---|---|---|---|---|
| 结构完整性 | REQ-101 | 画像字段覆盖度达标 | M | v2.7 新画像结构的字段总数必须达到提案目标，并保持单一 canonical 结构口径 | 5 域字段数 ≥ 20（含 `extensions`） |
| 数据质量 | REQ-102 | 服务治理导入自动匹配成功率达标 | M | 对治理导入中系统名与系统清单标准名称一致的记录，自动匹配并完成画像更新的成功率必须达标 | 成功率 ≥ 95% |
| 测试完整性 | REQ-103 | Skill Runtime 覆盖完整并通过独立测试 | M | 6 个内置 Skill 必须全部实现，且 Runtime 路由矩阵正确 | 6/6 Skill 测试通过，核心场景路由正确 |
| 资产沉淀 | REQ-104 | 三类 Memory 写入覆盖率达标 | M | 范围内画像更新、系统识别结论、功能点修改必须全部写入 Memory | 覆盖率 = 100% |
| 清理完成度 | REQ-105 | 旧数据清理结果可核验 | M | v2.7 生效后旧 schema 画像数据和历史评估报告存量数据都必须清零 | 残留数据 = 0 |

### 4.2 非功能需求明细 [包含 4.1 中所有非功能需求]

#### REQ-101：画像字段覆盖度达标

**需求分类**：结构完整性  
**适用范围**：系统画像全局结构、前后端 canonical schema、画像读写链路  
**指标与口径**：
- 统计对象：v2.7 正式画像结构中的一级域下业务字段总数。
- 计数方式：按 D1-D5 域字段键计数，`extensions` 作为各域独立字段计入总数。
- 目标值：总字段数 ≥ 20，且每个域都包含 `extensions`。

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-101-01: Given v2.7 目标画像结构已落地，When 按 D1-D5 域字段键计数，Then 总字段数不少于 20，且 5 个域均包含 `extensions` 字段。
- [ ] GWT-REQ-101-02: Given 前端画像面板和后端空画像结构分别输出字段定义，When 对比两侧字段键，Then 两侧使用同一套 canonical 字段键，不存在仅一侧保留的旧字段名。

**验收方法/证据**：
- 代码/配置对比前后端 schema 定义。
- 读取空画像结构并核对返回载荷。

**异常与边界**：
- 不允许以“前端展示字段数满足、后端结构未对齐”的方式通过验收。

**关联**：REQ-002；REQ-C002

#### REQ-102：服务治理导入自动匹配成功率达标

**需求分类**：数据质量  
**适用范围**：管理员服务治理页、治理导入与画像更新链路  
**指标与口径**：
- 分子：治理导入中“系统名与系统清单标准名称一致”的记录里，成功匹配并完成画像更新的记录数。
- 分母：治理导入中“系统名与系统清单标准名称一致”的记录总数。
- 统计窗口：测试阶段导入样本。
- 目标值：成功率 ≥ 95%。

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-102-01: Given 测试样本中有 100 条系统名与系统清单标准名称一致的治理记录，When admin 完成服务治理导入，Then 至少 95 条记录成功匹配并完成画像更新。
- [ ] GWT-REQ-102-02: Given 导入结果同时包含“名称一致可匹配记录”和“名称不一致未匹配记录”，When 统计成功率，Then 仅以名称一致记录作为分母计算，不把未纳入口径的记录混入成功率统计。

**验收方法/证据**：
- 导入结果统计日志。
- 匹配成功/未匹配清单与系统清单对照结果。

**异常与边界**：
- 不允许把“写入失败但匹配成功”的记录算入成功分子。

**关联**：REQ-003；REQ-009

#### REQ-103：Skill Runtime 覆盖完整并通过独立测试

**需求分类**：测试完整性  
**适用范围**：Skill Registry、Runtime 路由、内置 Skill、场景矩阵  
**指标与口径**：
- 统计对象：6 个内置 Skill 与核心场景路由矩阵。
- 达标条件：
  - 6 个内置 Skill 都已实现并通过独立功能测试
  - 核心场景 `pm_document_ingest`、`admin_service_governance_import`、`admin_system_catalog_import`、`system_identification`、`feature_breakdown` 路由正确
- 目标值：6/6 Skill 测试通过，核心场景路由正确率 = 100%。

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-103-01: Given v2.7 Runtime 已加载，When 执行 Skill 功能测试集，Then 6 个内置 Skill 都存在且测试通过。
- [ ] GWT-REQ-103-02: Given 执行核心场景路由矩阵测试，When 检查 `scene_id -> skill_chain` 结果，Then `pm_document_ingest`、`admin_service_governance_import`、`admin_system_catalog_import`、`system_identification`、`feature_breakdown` 五类场景都落到预期链路，不出现错路由或空路由。

**验收方法/证据**：
- Skill 独立功能测试结果。
- Runtime 路由矩阵测试结果。

**异常与边界**：
- 不允许以“注册了但未实现核心行为”的空壳 Skill 计入完成数。

**关联**：REQ-005；REQ-006

#### REQ-104：三类 Memory 写入覆盖率达标

**需求分类**：资产沉淀  
**适用范围**：画像更新、系统识别结论、功能点修改  
**指标与口径**：
- 统计对象：范围内成功动作，包括：
  - 成功的画像更新动作
  - 成功的系统识别结论落库动作
  - 成功的 AI 评估后功能点修改动作
- 公式：`memory_write_coverage = successful_actions_with_memory / successful_actions * 100%`
- 目标值：`memory_write_coverage = 100%`

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-104-01: Given 测试样本中存在画像更新、系统识别结论落库、功能点修改三类成功动作，When 统计 Memory 记录，Then 每个成功动作都能找到对应 Memory 记录，且覆盖率为 100%。
- [ ] GWT-REQ-104-02: Given 按 `system_id + memory_type` 查询系统资产，When 查看结果，Then 能分别查到 `profile_update`、`identification_decision`、`function_point_adjustment` 三类 Memory 记录或明确的“当前无记录”结果。

**验收方法/证据**：
- Memory 写入日志。
- 按系统和类型查询 Memory 的结果。

**异常与边界**：
- 不允许以异步日志补写失败为由漏掉范围内动作。

**关联**：REQ-007；REQ-008；REQ-010

#### REQ-105：旧数据清理结果可核验

**需求分类**：清理完成度  
**适用范围**：旧 schema 画像数据、历史评估报告存量数据、部署前后核验  
**指标与口径**：
- 统计对象 1：旧 schema 画像数据记录数。
- 统计对象 2：历史评估报告类型相关存量数据记录数。
- 目标值：两类数据在 v2.7 清理后均为 0。

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-105-01: Given v2.7 清理动作已执行，When 查询画像数据存储，Then 不存在旧 schema 字段记录或旧 schema 结构残留。
- [ ] GWT-REQ-105-02: Given v2.7 清理动作已执行，When 查询历史评估报告相关导入/知识数据，Then 相关存量数据计数为 0。

**验收方法/证据**：
- 数据文件/存储查询结果。
- 清理执行日志与清理后复核结果。

**异常与边界**：
- 不允许仅删除前端入口而保留后端数据残留。

**关联**：REQ-012；REQ-C002

## 4A. 约束与禁止项（Constraints & Prohibitions）

### 4A.1 禁止项列表

| REQ-ID | 禁止项名称 | 适用范围 | 来源 | 关联GWT-ID |
|--------|-----------|---------|------|-----------|
| REQ-C001 | 禁止在 PM 导入页保留历史评估报告和服务治理文档入口 | PM 导入页、相关模板下载与旧类型导入请求 | proposal §P-DONT-01 | REQ-C001-ACC-01, REQ-C001-ACC-02 |
| REQ-C002 | 禁止保留旧 schema 字段和旧数据残留 | 画像数据结构、旧 schema 数据、历史评估报告存量数据 | proposal §P-DONT-02 | REQ-C002-ACC-01, REQ-C002-ACC-02 |
| REQ-C003 | 禁止自动更新覆盖 PM 已确认的 `manual` 内容 | 画像自动更新链路、字段来源判定、结果摘要 | proposal §P-DONT-03 | REQ-C003-ACC-01, REQ-C003-ACC-02 |
| REQ-C004 | 禁止把 Skill 与 Memory 设计成不可扩展结构 | Skill Registry、Memory 模型、未来 Skill/Memory 扩展 | proposal §P-DONT-04 | REQ-C004-ACC-01, REQ-C004-ACC-02 |
| REQ-C005 | 禁止系统识别只返回候选列表而不做直接判定 | 系统识别结果结构、任务链路输入 | proposal §P-DONT-05 | REQ-C005-ACC-01 |
| REQ-C006 | 禁止破坏现有评估主链路和报告语义 | 创建任务、分配专家、专家评估、报告查询/导出链路 | proposal §P-DONT-06 | REQ-C006-ACC-01, REQ-C006-ACC-02 |
| REQ-C007 | 禁止引入新的外部依赖 | 后端运行时依赖、前端运行时依赖 | proposal §P-DONT-07 | REQ-C007-ACC-01 |
| REQ-C008 | 禁止系统清单导入覆盖非空画像 | 系统清单 confirm 联动、空画像判定、月度更新/覆盖导入 | proposal §P-DONT-08 | REQ-C008-ACC-01, REQ-C008-ACC-02 |

### 4A.2 禁止项明细

#### REQ-C001：禁止在 PM 导入页保留历史评估报告和服务治理文档入口

**适用范围**：PM 系统画像导入页、该页面模板下载按钮、旧类型导入行为  
**来源**：proposal `P-DONT-01`

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-C001-01: Given manager 访问 PM 导入页，When 页面加载完成，Then 页面不出现“历史评估报告”“服务治理文档”卡片、上传入口或模板下载按钮。
- [ ] GWT-REQ-C001-02: Given 客户端仍尝试以 `history_report`、`esb` 或治理类旧类型调用 PM 文档导入接口或模板下载接口，When 服务端处理请求，Then 系统返回明确失败结果，且不返回成功结果或模板文件。

#### REQ-C002：禁止保留旧 schema 字段和旧数据残留

**适用范围**：画像读写结构、清理结果、历史评估报告存量数据  
**来源**：proposal `P-DONT-02`

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-C002-01: Given v2.7 画像结构已启用，When 读取画像详情或空画像结构，Then 返回结果中不包含 `system_description`、`boundaries`、`module_structure`、`integration_points`、`architecture_positioning`、`performance_profile`、`key_constraints` 等旧 schema 字段键。
- [ ] GWT-REQ-C002-02: Given 执行完 v2.7 清理动作，When 查询旧 schema 画像数据和历史评估报告存量数据，Then 两类残留计数都为 0。

#### REQ-C003：禁止自动更新覆盖 PM 已确认的 `manual` 内容

**适用范围**：服务治理、系统清单、自动画像更新链路  
**来源**：proposal `P-DONT-03`

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-C003-01: Given 某个画像字段已由 PM 手动保存并标记为 `manual`，When 自动导入链路对该字段产生不同值，Then 系统不覆盖该字段，且读取结果仍为人工值。
- [ ] GWT-REQ-C003-02: Given 自动导入命中 `manual` 冲突字段，When 导入完成，Then 结果中明确标记该字段因 `manual` 优先而被跳过或转为建议，而不是无提示覆盖。

#### REQ-C004：禁止把 Skill 与 Memory 设计成不可扩展结构

**适用范围**：Skill Registry、Memory 模型、未来扩展能力  
**来源**：proposal `P-DONT-04`

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-C004-01: Given 注册表新增一个 `enabled=false` 的未来 Skill 定义（如 `architecture_review_skill`），When Runtime 加载注册表，Then 系统识别该定义为合法配置，而不是因硬编码枚举而报错。
- [ ] GWT-REQ-C004-02: Given Memory 模型写入 `memory_type=review_resolution` 的未来类型记录，When 校验公共元数据，Then 系统接受该记录并可被查询，而不是要求新增一套专用结构。

#### REQ-C005：禁止系统识别只返回候选列表而不做直接判定

**适用范围**：系统识别结果结构、任务链路输入  
**来源**：proposal `P-DONT-05`

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-C005-01: Given 任一系统识别结果返回载荷，When 检查结果字段，Then 必须包含 `final_verdict`，且不得只返回候选列表、相似度或澄清问题而缺少直接判定。

#### REQ-C006：禁止破坏现有评估主链路和报告语义

**适用范围**：任务创建、提交管理员、分配专家、专家评估、报告查询/导出  
**来源**：proposal `P-DONT-06`

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-C006-01: Given manager/admin/expert 按现有主链路执行“创建任务 -> 提交给管理员 -> 分配专家 -> 专家评估 -> 查看报告”，When v2.7 变更生效后执行该链路，Then 该链路仍可按原有角色权限和入口完成，不因画像、Runtime 或 Memory 改造被阻断。
- [ ] GWT-REQ-C006-02: Given 系统画像导入、服务治理导入、系统清单联动或 Memory 写入发生失败，When 用户继续访问评估主链路相关页面和接口，Then 任务评估与报告链路保持可用，且现有报告查询/导出语义不被改变。

#### REQ-C007：禁止引入新的外部依赖

**适用范围**：后端 `pyproject.toml` / `requirements.txt` / `backend/requirements.txt` 运行时依赖、前端 `frontend/package.json` 运行时依赖  
**来源**：proposal `P-DONT-07`

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-C007-01: Given 对比 v2.6 与 v2.7 的 `pyproject.toml`、`requirements.txt`、`backend/requirements.txt` 和 `frontend/package.json` 运行时依赖清单，When 检查依赖差异，Then 不新增为实现 v2.7 而引入的外部运行时依赖。

#### REQ-C008：禁止系统清单导入覆盖非空画像

**适用范围**：系统清单 confirm 联动、空画像判定、月度更新/覆盖导入  
**来源**：proposal `P-DONT-08`

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-C008-01: Given 系统清单已存在，且某命中系统的 `profile_data` 下 D1-D5 canonical 字段中任一字段非空，When admin 执行 confirm 覆盖导入，Then 该系统的 `profile_data` 保持不变，不写入 `ai_suggestions`，并在结果中标记 `profile_not_blank` 或等效跳过原因。
- [ ] GWT-REQ-C008-02: Given 某命中系统的 `profile_data` 下 D1-D5 canonical 字段全部为空值/空数组/空对象，但 `field_sources`、`ai_suggestions` 或 Memory 已存在元数据，When admin 执行系统清单 confirm，Then 系统仍将该画像判定为空画像，并允许按 REQ-004 / REQ-009 执行初始化写入。

## 5. 权限与合规

### 5.1 权限矩阵

| 角色 | 操作/权限 | 资源范围 | 备注 |
|---|---|---|---|
| manager | 访问 PM 导入页；上传需求/设计/技术方案；查看导入历史、执行状态、画像事件、系统 Memory | 仅本人主责或 B 角负责系统 | 不再拥有服务治理或系统清单导入入口 |
| manager | 保存画像草稿；采纳/忽略 AI 建议；发布画像 | 仅本人主责或 B 角负责系统；发布仅主责 | 手动保存默认写入 `manual` 来源和 `profile_update` Memory |
| admin | 访问服务治理页；上传治理文档/模板；查看匹配结果与 Memory | 全局系统范围 | v2.7 新增治理入口 |
| admin | 执行系统清单导入 preview/confirm，并触发画像批量联动 | 全局系统范围 | 仅 confirm 后触发 `system_catalog_skill`；首次初始化可直写空画像，后续仅允许补空 |
| admin | 查看画像列表、画像详情、导入历史、执行状态、系统 Memory | 全局系统范围 | 用于治理、审计和复核 |
| expert | 查看画像详情、执行结果、系统 Memory | 仅已授权/可查看范围 | 只读，不得执行导入或画像写操作 |

### 5.2 客户信息与合规

- v2.7 不新增客户个人信息采集字段；新增或变更的数据对象限于系统画像结构、导入结果、Memory 记录、字段来源标记和内部审计字段。
- `operator_id`、`updated_by` 等内部账号标识仅用于审计和追溯，不作为对无关角色的公开展示字段。
- 若导入文档或模板携带与本需求无关的个人敏感信息列，系统必须忽略或拒绝该列，不得把无关个人信息写入画像或 Memory。
- 本版本不新增“同意/撤回/导出/删除”类个人信息流程；若后续引入客户级个人信息字段，必须通过新的变更单重新定义合规要求。

## 6. 数据与接口

### 6.1 数据字典

| 字段/对象 | 类型 | 必填 | 来源/去向 | 脱敏 | 留存期 | 备注 |
|---|---|---|---|---|---|---|
| `system_id` | string | 是 | 系统清单 -> 画像接口 / Runtime / Memory | 否 | 长期 | 系统主键 |
| `doc_type` | enum string | 是 | PM 导入页 -> 文档导入接口 | 否 | 随导入历史保留 | 仅允许 `requirements/design/tech_solution` |
| `scene_id` | string | 是 | 业务入口 -> Runtime | 否 | 至少覆盖版本周期 | 例如 `pm_document_ingest`、`admin_service_governance_import` |
| `skill_execution_session` | object | 是 | Runtime -> 执行状态/日志 | 否 | 至少覆盖版本周期 | 包含场景、输入、skill_chain、policy_results、status |
| `profile_data` | object | 是 | 画像读写接口 <-> 画像存储 | 否 | 长期 | v2.7 canonical 5 域结构 |
| `field_sources` | object | 否 | 画像保存/自动更新 -> 画像存储 | 否 | 长期 | 至少支持 `manual`、`ai`、`governance`、`system_catalog` |
| `ai_suggestions` | object | 否 | 非自动覆盖结果 -> 画像建议区 | 否 | 长期 | 保存建议制结果 |
| `memory_record` | object | 是 | Runtime / 画像 / 系统识别 / 功能点修改 -> Memory 存储 | 否 | 长期 | 至少包含统一元数据与类型字段 |
| `identification_result` | object | 是 | 系统识别链路 -> 任务/接口结果 | 否 | 至少覆盖任务周期 | 包含 `final_verdict/selected_systems/candidate_systems/questions` |
| `function_point_adjustment` | object | 否 | PM 修改功能点 -> Memory / diff | 否 | 长期 | 记录修改类型、修改前后摘要 |
| `governance_import_result` | object | 是 | 服务治理导入 -> 页面结果/日志 | 否 | 至少覆盖版本周期 | 包含 `matched_count/unmatched_count/unmatched_items/updated_system_ids/errors` |
| `catalog_import_result` | object | 是 | 系统清单 confirm -> 页面结果/日志 | 否 | 至少覆盖版本周期 | 包含 `preview_errors/updated_system_ids/skipped_items/errors`，且 `skipped_items.reason` 至少支持 `profile_not_blank` |
| `evidence_refs` | array | 否 | 文档导入/治理导入/系统清单/识别/拆解 -> Memory | 否 | 长期 | 不得缺失 `source_type/source_id` |
| `source_file` | string | 否 | 导入链路 -> 历史、事件、Memory | 否 | 至少覆盖版本周期 | 记录来源文件名 |

### 6.2 错误码与提示语

| 错误码 | 场景 | 提示语 | HTTP状态码 | 处理建议 |
|---|---|---|---|---|
| `AUTH_001` | 角色不符、非主责/B角、非 admin 访问治理入口 | 权限不足 | 403 | 按接口契约校验角色和系统归属 |
| `PROFILE_IMPORT_FAILED` | PM 文档导入类型非法、文件非法、初始化失败 | 文档导入失败 | 400 | 检查 `doc_type`、文件格式与失败原因 |
| `SKILL_001` | `scene_id` 或 Skill 不支持 | Skill 场景不支持 | 400 | 检查场景与输入类型 |
| `SKILL_002` | Skill 执行失败 | Skill 执行失败 | 500 | 查看执行状态、错误详情和输入上下文 |
| `PROFILE_001` | 画像保存/发布通用失败 | 保存系统画像失败 / 发布系统画像失败 | 400/500 | 查看字段格式与服务端失败原因 |
| `PROFILE_002` | 系统画像不存在 | 系统画像不存在 | 404 | 检查 `system_id/system_name` 是否存在于系统清单 |
| `PROFILE_003` | 发布缺少必填字段 | 发布失败，缺少必填字段 | 400 | 补齐发布必填字段后重试 |
| `SUGGESTION_NOT_FOUND` | 采纳/忽略不存在的 AI 建议 | AI 建议不存在 | 404 | 刷新建议区并确认 `domain + sub_field` |
| `ESB_001` | 服务治理文件格式不支持或解析失败 | 文件格式不支持，请上传治理模板 | 400/500 | 检查模板格式、文件内容与服务端日志 |
| `ESB_002` | 服务治理必填字段缺失、参数不符合批量治理口径 | 治理文件缺少必填字段 | 400 | 按模板规范补齐字段并修正参数 |
| `CATALOG_001` | 系统清单 preview/confirm 失败 | 系统清单处理失败 | 400/500 | 查看 preview/confirm 结果与错误行 |
| `CATALOG_002` | 系统清单模板不匹配 | 系统清单模板不匹配 | 400 | 请使用系统清单模板填写后重试 |
| `MEMORY_001` | Memory 写入失败 | Memory 写入失败 | 500 | 检查 Memory 存储、补偿任务与日志 |
| `TEMPLATE_TYPE_INVALID` | 模板类型非法 | 模板类型无效 | 400 | 使用需求约定的有效模板类型 |
| `TEMPLATE_NOT_FOUND` | 模板文件缺失 | 模板文件不存在 | 404 | 检查模板文件部署和路径映射 |

### 6.3 指标与计算口径

- `M1 画像域字段覆盖度`
  - 公式：`field_count = count(D1..D5 canonical 字段键，含各域 extensions)`
  - 目标：`field_count >= 20`
  - 统计范围：前后端统一后的正式 schema
- `M2 PM 导入页文档类型数`
  - 公式：`pm_doc_type_count = count(PM 导入页可见且可成功提交的文档类型)`
  - 目标：`pm_doc_type_count = 3`
  - 统计范围：PM 导入页 UI + 服务端 allowlist
- `M3 服务治理导入自动匹配更新成功率`
  - 公式：`success_rate = matched_and_updated_records / exact_name_match_records * 100%`
  - 目标：`success_rate >= 95%`
  - 统计范围：测试阶段样本；仅使用治理导入中系统名与系统清单标准名称一致的记录作为分母
- `M4 Skill Runtime 覆盖率`
  - 公式：`built_in_skill_pass_rate = passed_skill_count / 6 * 100%`
  - 目标：`built_in_skill_pass_rate = 100%`
  - 统计范围：6 个内置 Skill 的独立功能测试 + 核心场景路由矩阵测试
- `M5 Memory 写入覆盖率`
  - 公式：`memory_write_coverage = successful_actions_with_memory / successful_actions * 100%`
  - 目标：`memory_write_coverage = 100%`
  - 统计范围：画像更新、系统识别结论、功能点修改三类范围内成功动作
- `M6 存量画像清理`
  - 公式：`residual_count = old_schema_profile_count + history_report_residual_count`
  - 目标：`old_schema_profile_count = 0` 且 `history_report_residual_count = 0`
  - 统计范围：部署前后核验查询

### 6.4 核心接口契约

| 接口 | 方向 | v2.7 需求口径 |
|---|---|---|
| `GET /api/v1/system-profiles/template/{template_type}` | PM 模板下载 | 仅 manager 可调用；`template_type` 仅允许 `requirements/design/tech_solution`；治理模板下载不再留在 PM 导入页 |
| `POST /api/v1/system-profiles/{system_id}/profile/import` | PM 文档导入 | 仅系统主责/B角 manager 可调用；成功后触发 `scene_id=pm_document_ingest` 的 Runtime；仅接受 `requirements/design/tech_solution` |
| `GET /api/v1/system-profiles/{system_id}/profile/import-history` | 导入历史查询 | manager 查询本人负责系统；admin/expert 只读查询授权范围；返回按时间倒序的导入历史 |
| `GET /api/v1/system-profiles/{system_id}/profile/execution-status` | Runtime 执行状态查询 | manager/admin/expert 可按读权限查询；返回 Runtime/Skill 执行状态、错误信息与终态 |
| `GET /api/v1/system-profiles/{system_id}/profile/events` | 画像事件查询 | manager/admin/expert 可按读权限查询；返回画像变更时间线，用于追溯建议采纳、手动编辑、治理导入、系统清单联动等事件 |
| `GET /api/v1/system-profiles/{system_id}/memory` | 系统 Memory 查询 | manager/admin/expert 可按读权限查询；支持按 `memory_type/scene_id/time_range` 过滤 |
| `POST /api/v1/system-profiles/{system_id}/profile/suggestions/accept` | 建议采纳 | 仅系统主责/B角 manager 可调用；采纳指定建议并更新正式画像字段 |
| `POST /api/v1/system-profiles/{system_id}/profile/suggestions/ignore` | 建议忽略 | 仅系统主责/B角 manager 可调用；忽略指定建议并保留建议记录 |
| `POST /api/v1/system-profiles/{system_id}/profile/suggestions/rollback` | 建议回滚 | 仅系统主责/B角 manager 可调用；允许回滚到历史建议版本 |
| `PUT /api/v1/system-profiles/{system_name}` | 画像草稿保存 | 仅系统主责/B角 manager 可保存正式画像字段和 `field_sources`；手动保存默认写入 `manual` 来源和 `profile_update` Memory |
| `POST /api/v1/system-profiles/{system_name}/publish` | 画像发布 | 仅主责 PM 可发布；发布以正式画像字段为准，不自动发布未采纳建议 |
| `POST /api/v1/esb/imports` | 服务治理导入 | 仅 admin 可调用；触发 `scene_id=admin_service_governance_import`；成功返回 `matched_count/unmatched_count/unmatched_items/updated_system_ids/errors` |
| `GET /api/v1/esb/search` | 服务治理检索 | admin 治理页查询接口；用于治理页检索与复核 |
| `GET /api/v1/esb/stats` | 服务治理统计 | admin 治理页统计接口；返回活动条目数、废弃条目数、唯一服务数和系统汇总 |
| `GET /api/v1/system-list/template` | 系统清单模板下载 | 仅 admin 可调用；返回系统清单批量导入模板 |
| `POST /api/v1/system-list/batch-import/preview` | 系统清单导入预览 | 仅 admin 可调用；只做校验与预览，不更新画像 |
| `POST /api/v1/system-list/batch-import/confirm` | 系统清单导入确认 | 仅 admin 可调用；成功后触发 `scene_id=admin_system_catalog_import`，首次初始化可直接初始化空画像，后续更新仅补空画像，并返回 `updated_system_ids/skipped_items` 结果 |

## 7. 变更记录

| 版本 | 日期 | 说明 | 作者 |
|---|---|---|---|
| v0.1 | 2026-03-12 | 初始化 Requirements 第 1 段：完成概述、术语口径与 Proposal -> Requirements 覆盖映射 | Codex |
| v0.2 | 2026-03-12 | 完成 Requirements 第 2 段：补充角色/对象、场景列表与业务场景明细 | Codex |
| v0.3 | 2026-03-12 | 完成 Requirements 第 3 段：落盘旧版 9 条功能性需求 | Codex |
| v0.4 | 2026-03-12 | 完成 Requirements 第 4 段：补充旧版非功能需求与禁止项 | Codex |
| v0.5 | 2026-03-12 | 完成 Requirements 第 5-6 段：补充旧版权限矩阵、数据字典、错误码与接口契约 | Codex |
| v0.6 | 2026-03-12 | 修复旧版复核问题：补充模板下载约束与角色边界 | Codex |
| v0.7 | 2026-03-12 | 修复旧版 Requirements 复审问题：补齐旧模板下载拒绝验收与草稿/发布边界 | Codex |
| v0.8 | 2026-03-13 | 按用户纠偏重写 Requirements：将范围升级为 6 个内置 Skill + Skill Runtime + Per-System Memory，并补齐服务治理/系统清单双导入联动、系统识别直接判定、功能点拆解应用策略与可扩展性要求 | Codex |
| v0.9 | 2026-03-13 | 同步 Proposal v0.4：修正关联提案版本，并统一系统清单导入联动为“所有命中的系统画像”口径 | Codex |
| v0.10 | 2026-03-13 | 按用户确认补充系统清单月度更新规则：仅首次初始化或空画像时允许初始化写入，新增空画像判定口径与禁止覆盖非空画像约束 | Codex |
| v0.11 | 2026-03-13 | 删除子系统清单口径，补齐系统清单字段映射规则，并明确 `code_scan_skill` 双入口与扫描边界 | Codex |
| v0.12 | 2026-03-13 | 补充文档类 skill 的本期有效性边界：仅覆盖可直接抽文本的 `docx` / 文本型 `pdf` / `pptx`，扫描件/OCR 不纳入有效性目标 | Codex |
| v0.13 | 2026-03-14 | 明确服务治理最新模板口径以 `data/esb-template.xlsx` 为准，并保留 `data/接口申请模板.xlsx` 作为兼容输入 | Codex |
