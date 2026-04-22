# Testing Records

## How to Use This File

testing.md 是测试证据账本，记录所有测试活动。每个 acceptance 可以有多条测试记录，覆盖不同的测试类型。

**测试类型（test_type）**：
- `unit`: 单元测试，测试单个函数/类的逻辑
- `integration`: 集成测试，测试多个模块的交互
- `e2e`: 端到端测试，测试完整的用户流程
- `performance`: 性能测试，测试响应时间/吞吐量
- `security`: 安全测试，测试安全漏洞
- `manual`: 手工测试，人工验证

**测试范围（test_scope）**：
- `branch-local`: 执行分支的局部测试（Implementation 阶段）
- `full-integration`: 完整集成测试（Testing Phase，parent feature 分支）

**测试结果（result）**：
- `pass`: 测试通过，acceptance 得到验证
- `fail`: 测试失败，需要修复实现或重新开启 spec/design

**残留风险（residual_risk）**：
- `none`: 无残留风险
- `low`: 低风险，可接受的小问题
- `medium`: 中等风险，需要监控
- `high`: 高风险，需要立即处理或重新开启 spec/design

**重新开启标记（reopen_required）**：
- `true`: 需要重新开启 spec/design 进行调整
- `false`: 不需要重新开启

## Acceptance 到 Testing 的映射

每个 spec.md 中的 acceptance（ACC-ID）可以在 testing.md 中有多条测试记录：
- 同一个 ACC-ID 可以有多个 test_type（unit, integration, e2e, performance, security, manual）
- 同一个 ACC-ID 可以有多个 test_scope（branch-local, full-integration）
- 最终验收要求：每个 ACC-ID 至少有一条 test_scope=full-integration 且 result=pass 的记录

---

## Branch-Local Testing (Implementation Phase)

执行分支在 Implementation 阶段的测试记录。

### WI-001

- acceptance_ref: ACC-001
  test_type: unit
  test_scope: branch-local
  verification_type: automated
  test_command: python -m pytest tests/test_attachment_extraction.py -q
  test_date: 2026-04-21
  artifact_ref: tests/test_attachment_extraction.py
  result: pass
  notes: 覆盖原生嵌入 DOCX/XLSX，以及真实 OLE 样本中的 package 流与 Workbook BIFF 流恢复。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-002
  test_type: unit
  test_scope: branch-local
  verification_type: automated
  test_command: python -m pytest tests/test_attachment_extraction.py -q
  test_date: 2026-04-21
  artifact_ref: tests/test_attachment_extraction.py
  result: pass
  notes: 覆盖递归嵌套样例、附件数量限制、附件大小限制与失败降级路径。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-003
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  test_command: python -m pytest tests/test_docx_parser.py tests/test_document_parser.py -q
  test_date: 2026-04-21
  artifact_ref: tests/test_docx_parser.py
  result: pass
  notes: 验证主文档正文和附件正文被统一并入 requirement_content。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-004
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  test_command: python -m pytest tests/test_attachment_extraction.py tests/test_docx_parser.py -q
  test_date: 2026-04-21
  artifact_ref: tests/test_attachment_extraction.py
  result: pass
  notes: 验证单个损坏附件或未支持的 WPS-like OLE 对象不会中断整体解析，其他附件正文仍可保留。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-005
  test_type: regression
  test_scope: branch-local
  verification_type: automated
  test_command: python -m pytest tests/test_attachment_extraction.py tests/test_docx_parser.py tests/test_document_parser.py -q
  test_date: 2026-04-21
  artifact_ref: tests/test_document_parser.py
  result: pass
  notes: 组合回归通过，现有多格式解析行为未被附件能力破坏。
  residual_risk: low
  reopen_required: false

---

## Full Integration Testing (Testing Phase)

在 parent feature 分支的完整集成测试，作为最终验收依据。

- acceptance_ref: ACC-001
  test_type: unit
  test_scope: full-integration
  verification_type: automated
  test_command: python -m pytest tests/test_attachment_extraction.py -q
  test_date: 2026-04-21
  artifact_ref: tests/test_attachment_extraction.py
  result: pass
  notes: full-integration 复核原生嵌入、OLE package 流与 Workbook BIFF 流都能恢复为附件正文。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-002
  test_type: unit
  test_scope: full-integration
  verification_type: automated
  test_command: python -m pytest tests/test_attachment_extraction.py -q
  test_date: 2026-04-21
  artifact_ref: tests/test_attachment_extraction.py
  result: pass
  notes: full-integration 复核递归深度、附件数量限制、附件大小限制与失败降级路径。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-003
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  test_command: python -m pytest tests/test_docx_parser.py tests/test_document_parser.py -q
  test_date: 2026-04-21
  artifact_ref: tests/test_docx_parser.py
  result: pass
  notes: full-integration 复核主文档正文与附件正文统一并入 requirement_content。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-004
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  test_command: python -m pytest tests/test_attachment_extraction.py tests/test_docx_parser.py -q
  test_date: 2026-04-21
  artifact_ref: tests/test_attachment_extraction.py
  result: pass
  notes: full-integration 复核损坏附件和未支持的 WPS-like OLE 对象只记录错误，不中断整体解析。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-005
  test_type: regression
  test_scope: full-integration
  verification_type: automated
  test_command: python -m pytest tests/test_attachment_extraction.py tests/test_docx_parser.py tests/test_document_parser.py -q
  test_date: 2026-04-21
  artifact_ref: tests/test_document_parser.py
  result: pass
  notes: full-integration 组合回归通过，现有多格式解析行为未被附件能力破坏。
  residual_risk: low
  reopen_required: false

---

## Summary

**Final Acceptance Status**:
- ACC-001: PASS
- ACC-002: PASS
- ACC-003: PASS
- ACC-004: PASS
- ACC-005: PASS

**Residual Risks**:
- low: 部分 WPS-like OLE 容器仍走降级记录路径，不恢复正文，但不会中断整体解析。
