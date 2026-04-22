# spec.md

## Default Read Layer

### Intent Summary
- Problem: 需求文档内嵌附件未被解析，导致功能点拆分不完整
- Goals:
  - G1: 递归解析需求文档内部的所有附件（DOCX/XLSX/PPTX/PDF）
  - G2: 在功能点拆分中覆盖附件内容
- Non-goals:
  - NG1: 不支持图片/图表的智能识别（OCR/图像理解）
  - NG2: 不支持压缩包（ZIP/RAR）的递归解压
  - NG3: 不修改现有的功能点拆分算法
- Must-have Anchors:
  - A1: 支持 DOCX/XLSX/PPTX 格式的附件提取
  - A2: 递归深度至少支持3层
  - A3: 单个附件解析失败不影响整体流程
  - A4: 向后兼容（不影响现有功能）
- Prohibition Anchors:
  - P1: 禁止无限递归（必须有深度限制）
  - P2: 禁止解析超大附件导致系统资源耗尽
  - P3: 禁止修改已有的 Agent 核心逻辑
- Success Anchors:
  - S1: 功能点拆分覆盖率从当前的 60-70% 提升到 95% 以上（针对带附件的文档）
  - S2: 单文档解析时间控制在 5 分钟内
- Boundary Alerts:
  - B1: PDF 附件提取依赖 PyPDF2 库能力，可能存在兼容性问题
  - B2: 循环引用检测基于文件内容哈希，重命名后的相同文件会被重复解析
  - B3: 附件格式识别依赖文件扩展名，伪装格式可能导致解析失败
- Unresolved Decisions:
  - 无（用户已确认所有关键决策）

### Requirements Quick Index
- Proposal 阶段只保留最小导读；formal REQ/ACC/VO 在 Requirements phase 正式填写。
- Proposal Coverage Map: maintain in `## Requirements`
- Clarification Status: maintain in `## Requirements`
- Requirements Index:
  - REQ-001: 附件提取能力（DOCX/XLSX/PPTX）
  - REQ-002: 递归解析控制（深度、循环检测、性能保护）
  - REQ-003: 内容合并
  - REQ-004: 错误隔离与降级处理
  - REQ-005: 配置化与向后兼容

### Acceptance Index
- ACC-001 -> REQ-001: 正确提取并解析附件
- ACC-002 -> REQ-002: 递归控制机制有效
- ACC-003 -> REQ-003: 功能点覆盖附件内容
- ACC-004 -> REQ-004: 单个附件失败不影响整体
- ACC-005 -> REQ-005: 不影响现有功能

### Verification Index
- VO-001 -> ACC-001: 单元测试 + 集成测试
- VO-002 -> ACC-002: 边界场景测试
- VO-003 -> ACC-003: 端到端测试
- VO-004 -> ACC-004: 错误注入测试
- VO-005 -> ACC-005: 回归测试

### Appendix Map
- 无（Proposal 阶段暂无 appendix）

<!-- SKELETON-END -->

## Intent

### Problem / Background
项目经理在系统中上传需求文档（如《2026年管理会计集市系统中收模型优化等共计33个迭代优化需求 (1).docx》）时，该文档内部嵌入了多个附件（docx、xlsx、pptx、pdf等）。当前系统只解析了主文档的文本和表格内容，**完全忽略了内嵌附件**，导致功能点拆分不完整，工作量评估不准确。

实际估算工作中，提交的需求文档可能带有 docx、xlsx、pptx、pdf 等格式的内部附件，这些附件往往包含关键的功能描述、数据库设计、接口定义等信息，必须一并解析才能得到完整的需求全貌。

### Goals
- G1: 递归解析需求文档内部的所有附件（DOCX/XLSX/PPTX/PDF）
- G2: 在功能点拆分中覆盖附件内容，确保评估完整性

### Non-goals
- NG1: 不支持图片/图表的智能识别（OCR/图像理解），图片仅记录文件名
- NG2: 不支持压缩包（ZIP/RAR）的递归解压
- NG3: 不修改现有的功能点拆分算法（Agent 逻辑）
- NG4: 不支持 PDF 内嵌附件提取（一期暂不实现，PyPDF2 能力有限）

### Must-have Anchors
- A1: 支持 DOCX/XLSX/PPTX 格式的附件提取
- A2: 递归深度至少支持3层（主文档 → 附件 → 子附件）
- A3: 单个附件解析失败不影响整体流程（错误隔离）
- A4: 向后兼容（不影响现有功能，不带附件的文档正常解析）

### Prohibition Anchors
- P1: 禁止无限递归（必须有深度限制，默认3层）
- P2: 禁止解析超大附件导致系统资源耗尽（单附件10MB限制）
- P3: 禁止修改已有的 Agent 核心逻辑（系统识别、功能点拆分、工作量评估）

### Success Anchors
- S1: 功能点拆分覆盖率从当前的 60-70% 提升到 95% 以上（针对带附件的文档）
- S2: 单文档解析时间控制在 5 分钟内（包含所有附件）

### Boundary Alerts
- B1: PDF 附件提取依赖 PyPDF2 库能力，可能存在兼容性问题（一期暂不支持）
- B2: 循环引用检测基于文件内容哈希，重命名后的相同文件会被重复解析
- B3: 附件格式识别依赖文件扩展名，伪装格式可能导致解析失败
- B4: 某些特殊格式的 Office 文档（如加密文档）可能无法提取附件

### Unresolved Decisions
- none

### Input Intake Summary
- input_source: 用户口头描述 + 实际场景案例（qw 评估任务）
- input_quality: L2（需求明确，但缺少详细的技术规格）
- normalization_effort: 通过探索现有代码和用户确认，已完成需求澄清

### Input Intake
- input_maturity: L2
- input_refs:
  - docs/inputs/attachment-parsing-requirement.md
- input_owner: human
- approval_basis: owner approved scope and implementation approach
- normalization_status: anchored

### Testing Priority Rules
- P0: 附件提取正确性、递归控制机制、错误隔离（核心功能，必须自动化测试）
- P1: 功能点覆盖率、来源标注准确性（优先自动化，否则手动验证）
- P2: 性能测试、边界场景（可手动验证）

## Requirements

### Proposal Coverage Map
- source_ref: docs/inputs/attachment-parsing-requirement.md
  anchor_ref: G1: 递归解析需求文档内部的所有附件（DOCX/XLSX/PPTX/PDF）
  target_ref: REQ-001
  status: covered
- source_ref: docs/inputs/attachment-parsing-requirement.md
  anchor_ref: G2: 在功能点拆分中覆盖附件内容，确保评估完整性
  target_ref: REQ-003
  status: covered
- source_ref: docs/inputs/attachment-parsing-requirement.md
  anchor_ref: A1: 支持 DOCX/XLSX/PPTX 格式的附件提取
  target_ref: REQ-001
  status: covered
- source_ref: docs/inputs/attachment-parsing-requirement.md
  anchor_ref: A2: 递归深度至少支持3层（主文档 → 附件 → 子附件）
  target_ref: REQ-002
  status: covered
- source_ref: docs/inputs/attachment-parsing-requirement.md
  anchor_ref: A3: 单个附件解析失败不影响整体流程（错误隔离）
  target_ref: REQ-004
  status: covered
- source_ref: docs/inputs/attachment-parsing-requirement.md
  anchor_ref: A4: 向后兼容（不影响现有功能，不带附件的文档正常解析）
  target_ref: REQ-005
  status: covered
- source_ref: docs/inputs/attachment-parsing-requirement.md
  anchor_ref: P1: 禁止无限递归（必须有深度限制，默认3层）
  target_ref: REQ-002
  status: covered
- source_ref: docs/inputs/attachment-parsing-requirement.md
  anchor_ref: P2: 禁止解析超大附件导致系统资源耗尽（单附件10MB限制）
  target_ref: REQ-002
  status: covered
- source_ref: docs/inputs/attachment-parsing-requirement.md
  anchor_ref: P3: 禁止修改已有的 Agent 核心逻辑（系统识别、功能点拆分、工作量评估）
  target_ref: REQ-005
  status: covered
- source_ref: docs/inputs/attachment-parsing-requirement.md
  anchor_ref: S1: 功能点拆分覆盖率从当前的 60-70% 提升到 95% 以上（针对带附件的文档）
  target_ref: REQ-003
  status: covered
- source_ref: docs/inputs/attachment-parsing-requirement.md
  anchor_ref: S2: 单文档解析时间控制在 5 分钟内（包含所有附件）
  target_ref: REQ-002
  status: covered
- source_ref: docs/inputs/attachment-parsing-requirement.md
  anchor_ref: B1: PDF 附件提取依赖 PyPDF2 库能力，可能存在兼容性问题（一期暂不支持）
  target_ref: REQ-001
  status: noted
- source_ref: docs/inputs/attachment-parsing-requirement.md
  anchor_ref: B2: 循环引用检测基于文件内容哈希，重命名后的相同文件会被重复解析
  target_ref: REQ-002
  status: noted
- source_ref: docs/inputs/attachment-parsing-requirement.md
  anchor_ref: B3: 附件格式识别依赖文件扩展名，伪装格式可能导致解析失败
  target_ref: REQ-001
  status: noted
- source_ref: docs/inputs/attachment-parsing-requirement.md
  anchor_ref: B4: 某些特殊格式的 Office 文档（如加密文档）可能无法提取附件
  target_ref: REQ-004
  status: noted

### Clarification Status
- 无需澄清（所有关键决策已通过用户确认完成）

### Functional Requirements
- REQ-001
  - summary: 从 DOCX/XLSX/PPTX 文档中提取嵌入的附件对象
  - rationale: 附件包含关键需求信息，必须提取才能完整评估

- REQ-002
  - summary: 支持递归解析附件，包含深度限制、循环检测、性能保护机制
  - rationale: 附件可能嵌套，需要递归解析；同时必须防止无限递归和资源耗尽

- REQ-003
  - summary: 将附件内容合并到主文档，传递给功能点拆分 Agent
  - rationale: 确保功能点覆盖附件内容

- REQ-004
  - summary: 单个附件解析失败时继续处理其他附件，记录错误信息
  - rationale: 提高系统容错性，避免单点故障影响整体流程

- REQ-005
  - summary: 通过配置控制附件解析功能，不影响现有功能
  - rationale: 保持系统稳定性，支持灰度发布和回滚

### Constraints / Prohibitions
- 递归深度不超过3层
- 单附件大小不超过10MB
- 单文档附件数量不超过20个
- 总解析超时不超过5分钟
- 不修改现有 Agent 核心逻辑

### Non-functional Requirements
- 性能：单文档解析时间 ≤ 5分钟（包含所有附件）
- 覆盖率：功能点拆分覆盖率 ≥ 95%（针对带附件的文档）
- 可用性：单个附件失败不影响整体流程（错误隔离）

## Acceptance

- acc_id: ACC-001
  source_ref: REQ-001
  expected_outcome: 能够从 DOCX/XLSX/PPTX 文档中正确提取嵌入的附件，附件内容完整可解析
  priority: P0
  priority_rationale: 核心功能，附件提取失败将导致功能点拆分不完整
  status: pending

- acc_id: ACC-002
  source_ref: REQ-002
  expected_outcome: 递归深度限制为3层，循环引用被正确检测并跳过，性能保护机制生效（大小/数量/超时限制）
  priority: P0
  priority_rationale: 防止系统资源耗尽，保障系统稳定性
  status: pending

- acc_id: ACC-003
  source_ref: REQ-003
  expected_outcome: 功能点拆分覆盖附件内容，附件内容被正确合并到主文档并传递给 Agent
  priority: P1
  priority_rationale: 确保评估完整性
  status: pending

- acc_id: ACC-004
  source_ref: REQ-004
  expected_outcome: 单个附件解析失败时，其他附件继续处理，错误信息被记录，整体流程不中断
  priority: P0
  priority_rationale: 提高系统容错性，避免单点故障
  status: pending

- acc_id: ACC-005
  source_ref: REQ-005
  expected_outcome: 不带附件的文档解析结果与现有功能一致，通过配置可开关附件解析功能
  priority: P0
  priority_rationale: 向后兼容，保障系统稳定性
  status: pending

## Verification

- vo_id: VO-001
  acceptance_ref: ACC-001
  verification_type: automated
  verification_profile: focused
  obligations:
    - 单元测试：测试 DOCX/XLSX/PPTX 附件提取函数
    - 集成测试：测试完整解析流程（主文档 + 附件）
    - 边界测试：测试不支持格式、空附件、损坏附件
  artifact_expectation: tests/test_attachment_extraction.py 中的测试用例全部通过

- vo_id: VO-002
  acceptance_ref: ACC-002
  verification_type: automated
  verification_profile: focused
  obligations:
    - 深度限制测试：构造4层嵌套文档，验证只解析到第3层
    - 循环引用测试：构造 A→B→A 循环，验证正确检测并跳过
    - 性能保护测试：测试超大附件、大量附件、超时场景
  artifact_expectation: tests/test_attachment_extraction.py 中的边界测试用例全部通过

- vo_id: VO-003
  acceptance_ref: ACC-003
  verification_type: automated
  verification_profile: end-to-end
  obligations:
    - 端到端测试：上传带附件的需求文档，验证功能点拆分覆盖附件内容
    - 内容合并测试：验证附件内容被正确合并到主文档
  artifact_expectation: tests/test_attachment_integration.py 中的测试用例全部通过

- vo_id: VO-004
  acceptance_ref: ACC-004
  verification_type: automated
  verification_profile: focused
  obligations:
    - 错误注入测试：构造损坏的附件，验证错误被正确隔离
    - 降级测试：验证部分附件失败时，其他附件继续处理
  artifact_expectation: tests/test_attachment_extraction.py 中的错误处理测试用例全部通过

- vo_id: VO-005
  acceptance_ref: ACC-005
  verification_type: automated
  verification_profile: regression
  obligations:
    - 回归测试：使用现有测试文档（不带附件），验证解析结果一致
    - 配置测试：验证配置开关生效（开启/关闭附件解析）
  artifact_expectation: 现有测试套件全部通过，无回归问题
