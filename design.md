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
    notes: 通用附件提取器负责识别并抽取 DOCX/XLSX/PPTX/PDF 附件正文。
  - spec_ref: REQ-002
    aligned: true
    notes: 递归深度、附件大小、附件数量、循环检测都在解析层集中控制。
  - spec_ref: REQ-003
    aligned: true
    notes: 主文档入口继续输出单一 `requirement_content`，附件正文在解析阶段合并。
  - spec_ref: REQ-004
    aligned: true
    notes: 单个附件失败只记录错误并继续处理剩余附件。
  - spec_ref: REQ-005
    aligned: true
    notes: 不改现有 API/Agent 契约，不带附件的文档保持现有行为。

### Architecture Boundary
- impacted_capabilities:
  - DOCX 主文档解析入口与 `requirement_content` 组装
  - 通用多格式正文解析与文本扁平化复用
  - OOXML 附件扫描、递归控制与错误隔离
- not_impacted_capabilities:
  - `backend/agent/**` 系统识别、功能点拆分、工作量评估逻辑
  - `backend/api/routes.py` 任务 API 契约与任务存储结构
  - `frontend/**` 页面、报告与编辑页展示
- impacted_shared_surfaces:
  - `backend/utils/docx_parser.py`
  - `backend/service/document_parser.py`
  - `backend/utils/embedded_attachment_extractor.py`
- not_impacted_shared_surfaces:
  - `backend/agent/**`
  - `backend/api/**`
  - `frontend/**`
- major_constraints:
  - 默认递归深度 3、单附件 10MB、附件总数 20、总解析预算 5 分钟。
  - 必须支持循环检测，禁止同一内容无限递归。
  - 失败降级只能影响当前附件，不能让整个任务解析失败。
- contract_required: false
- compatibility_constraints:
  - 主文档仍通过现有 `DocxParser.parse(file_path)` 和 `DocumentParser.parse(file_content, filename)` 入口消费。
  - Agent 侧继续只接收合并后的纯文本 `requirement_content`，不新增来源标签字段。
  - 不新增外部服务依赖，不修改任务 API、报告格式或前端交互。

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
    rationale: 附件提取、正文合并和回归测试都围绕同一组解析入口，拆分后只会增加冲突面。

#### Branch Strategy Recommendation
recommended_branch_count: 1
rationale: |
  本次改动集中在文档解析层，核心文件只有 `docx_parser.py`、`document_parser.py` 和新增附件提取工具。
  单分支串行推进可以保证解析行为、限制策略和测试样例同步收敛，避免多个 WI 在同一文本输出口径上互相覆盖。

alternative_if_parallel_needed: |
  若后续发现需要拆分，可把“附件提取器/解析器实现”和“测试样例补齐”拆成两个 WI，
  但前提是先冻结统一的附件正文合并格式并明确共享文件 owner；当前没有必要。

**Note**: The above three sections (Dependency Analysis, Parallel Recommendation, Branch Strategy Recommendation)
are suggestions only, not enforced by gates. User decides the actual execution strategy.

#### Shared Surface Analysis
potentially_conflicting_files:
  - path: backend/utils/docx_parser.py
    reason: 主文档入口在这里组装 `requirement_content`，正文拼接规则只能有一套。
    recommendation: 所有正文合并逻辑都收口到同一 helper，避免在入口里散落分支判断。
  - path: backend/service/document_parser.py
    reason: 通用多格式解析器负责把附件文件转成结构化正文，递归路径会直接复用它。
    recommendation: 只增加附件复用接口和扁平化适配，不改现有知识提取协议。

conflict_risk_assessment:
  high_risk:
    - backend/utils/docx_parser.py
  medium_risk:
    - backend/service/document_parser.py
  low_risk:
    - tests/test_docx_parser.py
    - tests/test_document_parser.py
    - tests/test_attachment_extraction.py

#### Pre-work for Parent Feature Branch
tasks:
  - task: 初始化测试账本
    content: |
      新建 `testing.md`，为后续 Implementation 阶段记录 branch-local 测试结果预留载体。
    rationale: `start-implementation` gate 要求 `testing.md` 已存在。
  - task: 冻结单 WI 边界
    content: |
      把实现范围限制在解析器和测试文件，不改 API、Agent、前端与报告展示。
    rationale: 满足 Spec 中“禁止修改已有 Agent 核心逻辑”的硬约束。

#### Notes
- 当前设计刻意把“附件来源展示”“附件清单持久化”“任务 UI 展示”排除在本次 WI 之外。
- 允许新增一个解析工具文件，但不允许横向扩散到 `backend/api/**` 或 `backend/agent/**`。

### Design Slice Index
- DS-001:
  - appendix_ref: none
  - scope: 在解析层补齐 OOXML 附件扫描、支持格式识别、递归控制、错误隔离与正文合并。
  - requirement_refs: [REQ-001, REQ-002, REQ-003, REQ-004, REQ-005]
  - acceptance_refs: [ACC-001, ACC-002, ACC-003, ACC-004, ACC-005]
  - verification_refs: [VO-001, VO-002, VO-003, VO-004, VO-005]

### Work Item Derivation
- wi_id: WI-001
  input_refs:
    - docs/inputs/attachment-parsing-requirement.md
  requirement_refs:
    - REQ-001
    - REQ-002
    - REQ-003
    - REQ-004
    - REQ-005
  goal: 在不改 Agent 和 API 契约的前提下，为主文档及其嵌套附件补齐递归正文解析和 `requirement_content` 合并。
  covered_acceptance_refs: [ACC-001, ACC-002, ACC-003, ACC-004, ACC-005]
  verification_refs:
    - VO-001
    - VO-002
    - VO-003
    - VO-004
    - VO-005
  dependency_refs: []
  contract_needed: false
  notes_on_boundary: 实现仅允许修改解析器和测试文件；任何对 Agent、API、前端、报告格式的需求都必须回到 design 重新开边界。
  work_item_alignment: keep equal to work-items/WI-001.yaml acceptance_refs

### Contract Needs
- no additional contract required; the change stays within parser internals and existing return shapes.

### Failure Paths / Reopen Triggers
- 如果附件真实载荷无法通过当前已锁定的 `olefile` + 现有解析依赖稳定解出，需要重新评估是否继续引入新的解析依赖或缩小支持边界。
- 如果正文合并后会破坏现有无附件文档的解析结果或任务编辑页语义，需要先回写 spec/design 再继续。
- 如果为了暴露附件来源、附件清单或 UI 展示必须修改 API/前端契约，需要重新开 WI，不在本次实现中追加。

### Appendix Map
- none

## Goal / Scope Link

### Scope Summary
- 主文档入口仍由 `backend/utils/docx_parser.py` 负责提取需求名称、摘要与正文，但正文来源不再只看主文档段落/表格，而是合并“主文档正文 + 支持格式附件正文”。
- 通用正文解析继续由 `backend/service/document_parser.py` 负责：`docx/xlsx/pptx/pdf` 附件都先转成已有结构化形态，再复用 `parsed_to_text` 风格扁平化为纯文本。
- 附件递归控制、大小限制、数量限制、循环检测、失败降级全部放在解析层统一处理，不让 Agent、API 或任务编排层感知附件细节。
- 本次实现不新增新的对外数据结构；最终交付物仍然是更完整的 `requirement_content` 字符串和与现有兼容的解析结果。

### spec_alignment_check
- spec_ref: REQ-001
  aligned: true
  notes: 设计以通用 OOXML 附件扫描器覆盖 DOCX/XLSX/PPTX 嵌入对象，并对 PDF 载荷复用现有 `PyPDF2` 解析链路。
- spec_ref: REQ-002
  aligned: true
  notes: 所有递归参数都通过统一配置对象管理，默认值与 spec 约束一致。
- spec_ref: REQ-003
  aligned: true
  notes: 附件文本在解析阶段直接拼接进 `requirement_content`，因此功能点拆分无需改协议。
- spec_ref: REQ-004
  aligned: true
  notes: 附件解析错误只产生日志/元信息，不抛出中断主流程的异常。
- spec_ref: REQ-005
  aligned: true
  notes: 不带附件的路径保持原逻辑，回归测试验证文本结果不退化。

## Architecture Boundary
- system_context: 需求评估主链路在 `process_task_sync -> DocxParser.parse -> AgentOrchestrator.process_requirement` 上串联；本次只允许变更 `DocxParser` 与其复用的通用 `DocumentParser`。
- impacted_capabilities:
  - 主文档附件扫描与递归抽取
  - 多格式附件正文解析与文本扁平化
  - `requirement_content` 完整性提升
- not_impacted_capabilities:
  - 系统识别 Prompt、功能点拆分 Prompt 与估算逻辑
  - 任务详情 API、编辑页修改接口与报表导出
  - 知识库导入、服务治理导入、系统画像导入链路
- impacted_shared_surfaces:
  - `backend/utils/docx_parser.py`
  - `backend/service/document_parser.py`
  - `backend/utils/embedded_attachment_extractor.py`
- not_impacted_shared_surfaces:
  - `backend/api/routes.py`
  - `backend/agent/agent_orchestrator.py`
  - `frontend/src/**`
- major_constraints:
  - 附件提取器必须优先通过文件扩展名和文件签名识别支持格式，不能对不明格式做冒进解析。
  - 对 OOXML 里的 `.bin` 包装对象，需要先尝试 OLE 解包；无法识别时记为失败并继续，不允许阻断主文档。
  - 递归链路必须对已见内容做哈希去重，避免 A -> B -> A 环路。
  - 最终合并文本不能暴露内部实现噪声（如 zip entry 路径、OLE stream 名称）。
- contract_required: false
- compatibility_constraints:
  - `DocxParser.parse()` 返回字段名保持不变：`requirement_name`、`requirement_summary`、`requirement_content`、`basic_info`、`all_paragraphs`。
  - `DocumentParser.parse()` 对无附件输入保持原输出结构；附件能力以附加字段或内部 helper 复用方式接入，不破坏现有调用方。
  - 不对 API、任务表单、报告导出、前端页面新增字段。

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
    rationale: 解析输出口径只有一份，拆成多个 WI 容易在正文合并规则和测试样本上互相踩踏。

### Branch Strategy Recommendation
recommended_branch_count: 1
rationale: |
  实现范围小而耦合度高：主文档解析、通用附件解析和测试样例需要一起收敛。
  单分支推进更适合持续验证“无附件不回归 + 有附件能递归 + 单附件失败不影响整体”这三类核心行为。

alternative_if_parallel_needed: |
  若后续要继续扩展附件来源展示或非 DOCX 主文档入口，可在下一轮把“解析器实现”和“展示/任务链路扩展”拆成独立 WI。
  当前不建议提前拆分。

**Note**: The above three sections (Dependency Analysis, Parallel Recommendation, Branch Strategy Recommendation)
are suggestions only, not enforced by gates. User decides the actual execution strategy.

### Shared Surface Analysis
potentially_conflicting_files:
  - path: backend/utils/docx_parser.py
    reason: 该文件直接决定任务主链路消费的 `requirement_content` 内容。
    recommendation: 只在这里做入口编排，把复杂解析细节下沉到独立 helper。
  - path: backend/service/document_parser.py
    reason: 这是所有附件正文解析的通用入口，任何 return shape 变化都会影响其他调用方。
    recommendation: 复用现有 parse 结果结构，不随意重命名字段或改变无附件输出。
  - path: tests/test_document_parser.py
    reason: 这里已有 XLSX/PDF/PPTX 解析行为回归，新增附件能力后必须同步守住原断言。
    recommendation: 在原测试旁边补新增场景，不覆盖已有回归用例。

conflict_risk_assessment:
  high_risk:
    - backend/utils/docx_parser.py
  medium_risk:
    - backend/service/document_parser.py
    - backend/utils/embedded_attachment_extractor.py
  low_risk:
    - tests/test_docx_parser.py
    - tests/test_document_parser.py
    - tests/test_attachment_extraction.py

### Pre-work for Parent Feature Branch
tasks:
  - task: 落地 branch-local 测试账本载体
    content: |
      在仓库根目录创建 `testing.md`，后续 Implementation 直接往 WI-001 下面追加测试记录。
    rationale: `implementation-start` gate 硬要求 `testing.md` 存在。
  - task: 确认实现边界不触碰 Agent/API
    content: |
      通过 `work-items/WI-001.yaml` 的 `allowed_paths` 和 `out_of_scope` 把实现固定在解析器与测试文件。
    rationale: 避免设计阶段 scope 漂移。

### Notes
- 本设计推荐新增 `backend/utils/embedded_attachment_extractor.py` 作为唯一附件递归入口，避免把 zip/OLE 细节散落到多个解析器中。
- 附件正文合并顺序采用“主文档正文在前，附件正文按发现顺序追加”，保证当前系统识别与拆分仍然优先看到主文档上下文。
- 对于无法识别的附件，只记录错误并继续，不把文件名或二进制摘要写进最终正文。

## Design Slice Index
- DS-001:
  - appendix_ref: none
  - scope: 在文档解析层增加通用附件扫描、O​​OXML/OLE 解包、递归控制、文本扁平化与正文合并。
  - requirement_refs: [REQ-001, REQ-002, REQ-003, REQ-004, REQ-005]
  - acceptance_refs: [ACC-001, ACC-002, ACC-003, ACC-004, ACC-005]
  - verification_refs: [VO-001, VO-002, VO-003, VO-004, VO-005]

## Work Item Derivation
- wi_id: WI-001
  input_refs:
    - docs/inputs/attachment-parsing-requirement.md
  requirement_refs:
    - REQ-001
    - REQ-002
    - REQ-003
    - REQ-004
    - REQ-005
  goal: 在解析器内部补齐附件递归解析与正文合并，使现有任务主链路自动获得更完整的 `requirement_content`。
  covered_acceptance_refs: [ACC-001, ACC-002, ACC-003, ACC-004, ACC-005]
  verification_refs:
    - VO-001
    - VO-002
    - VO-003
    - VO-004
    - VO-005
  dependency_refs: []
  contract_needed: false
  notes_on_boundary: 仅允许修改 `docx_parser`、`document_parser`、新增附件提取 helper 和相关测试；任何 Agent/API/UI 变化都必须停下并回到 design 对齐。
  work_item_alignment: keep equal to work-items/WI-001.yaml acceptance_refs

## Contract Needs
- no additional contract required; implementation stays inside parser internals and existing return structures.

## Implementation Readiness Baseline

### Environment Configuration Matrix
- 运行时沿用当前 Python 后端环境；附件递归解析新增并显式锁定 `olefile` 运行依赖，其余继续复用仓库已存在的 `python-docx`、`openpyxl`、`PyPDF2`、`xlrd` 能力。
- 主文档入口仍在 `backend/api/routes.py` 的 `process_task_sync()` 中调用 `DocxParser.parse(file_path)`，不新增环境变量或部署参数。
- 测试执行使用现有 `pytest` 环境；新增样例优先通过内存构造 zip/OLE fixture，避免依赖真实上传文件。

### Security Baseline
- 附件解析只处理内嵌二进制内容，不落盘外部可执行文件，不调用 shell，不扩展上传文件权限。
- 附件类型识别以扩展名和文件签名双重校验为主，对未知/伪装格式直接降级失败，不做不受控解析。
- 递归限制、数量限制、大小限制和总预算是默认开启的资源保护措施，不能在实现中绕开。

### Data / Migration Strategy
- 本次不引入新的持久化 schema，不需要数据迁移或回填脚本。
- 已有任务数据结构保持不变；改善只体现在新解析出的 `requirement_content` 更完整。
- 对历史无附件或未重新评估的任务不做离线重算，保持按需重新上传/重新评估的现有流程。

### Operability / Health Checks
- 关键健康信号是“无附件文档回归通过”“递归附件样例解析通过”“损坏附件样例不会中断主流程”。
- 解析失败必须通过日志带出附件文件名和失败原因，便于排查具体嵌入对象，但不污染最终正文。
- 若附件总量或单附件过大触发限制，应输出明确日志而不是静默丢失。

### Backup / Restore
- 代码级改动没有持久化迁移，回滚只需恢复解析器和测试文件变更即可。
- 若上线后发现正文合并影响现有拆分结果，可直接回退本 WI 对解析器的修改，不涉及数据恢复。

## Verification Design
- ACC-001:
  - approach: 为通用附件提取器和 `DocumentParser` 增加 `docx/xlsx/pptx/pdf` 嵌入载荷解析测试，覆盖原生嵌入 entry 与 OLE 包装 entry。
  - evidence: `pytest tests/test_attachment_extraction.py tests/test_document_parser.py -q`
- ACC-002:
  - approach: 构造三层嵌套、循环引用、超大附件和超过数量上限的样例，验证深度/去重/保护策略都生效。
  - evidence: `pytest tests/test_attachment_extraction.py -q`
- ACC-003:
  - approach: 在 `DocxParser` 测试中验证最终 `requirement_content` 同时包含主文档正文和附件正文，且顺序稳定。
  - evidence: `pytest tests/test_docx_parser.py -q`
- ACC-004:
  - approach: 注入损坏附件和无法识别的伪装格式，验证其被记录并跳过，其他附件正文仍可进入结果。
  - evidence: `pytest tests/test_attachment_extraction.py tests/test_docx_parser.py -q`
- ACC-005:
  - approach: 保留现有 `tests/test_docx_parser.py`、`tests/test_document_parser.py` 回归，并新增无附件样例断言确保结果不变。
  - evidence: `pytest tests/test_docx_parser.py tests/test_document_parser.py -q`

## Failure Paths / Reopen Triggers
- 如果真实样例表明主流附件都以当前无法稳定解包的专有容器存在，需要重新评估支持边界或依赖策略。
- 如果为了表达附件来源、层级或错误详情必须修改任务返回结构或前端 UI，需要 reopen design，而不是在当前 WI 内偷偷扩 scope。
- 如果附件正文拼接显著降低现有系统识别/拆分质量，需要先回到 spec/design 重新定义合并规则和过滤策略。

## Appendix Map
- none
