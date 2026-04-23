# Testing Records

## How to Use This File

testing.md 是测试证据账本，记录所有测试活动。每个 acceptance 可以有多条测试记录，覆盖不同的测试类型。

**测试类型（test_type）**：
- `unit`: 单元测试
- `integration`: 集成测试
- `e2e`: 端到端测试
- `manual`: 手工测试
- `regression`: 回归测试

**测试范围（test_scope）**：
- `branch-local`: Implementation 阶段的局部测试
- `full-integration`: Testing 阶段的完整集成测试

---

## Branch-Local Testing (Implementation Phase)

执行分支在 Implementation 阶段的测试记录。

### WI-001

- acceptance_ref: ACC-001
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  test_command: npm test -- --runInBand --watch=false src/__tests__/cosmicConfigPage.render.test.js
  test_date: 2026-04-22
  artifact_ref: frontend/src/__tests__/cosmicConfigPage.render.test.js
  result: pass
  notes: 已验证 COSMIC 使用说明只保留必要配置含义，快速设置预设不再宣称直接控制现网拆分粒度。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-002
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  test_command: python -m pytest tests/test_task_reevaluate_api.py -q
  test_date: 2026-04-22
  artifact_ref: tests/test_task_reevaluate_api.py
  result: pass
  notes: 已验证 `/tasks/{task_id}/estimate` 会在缺失历史结果时按当前 COSMIC 配置主动执行分析、构建统一 rule_context，并与完整需求上下文一并注入估算 Agent；未选择规则时显式标记为 skipped。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-003
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  test_command: python -m pytest tests/test_task_reevaluate_api.py tests/test_evaluation_contract_api.py -q
  test_date: 2026-04-22
  artifact_ref: tests/test_evaluation_contract_api.py
  result: pass
  notes: 已验证 COSMIC rule_context 统一结构、点击估算时的运行时分析与历史结果复用策略、功能点级 degraded 状态以及 estimation artifact 中的后台证据字段。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-004
  test_type: regression
  test_scope: branch-local
  verification_type: automated
  test_command: python -m pytest tests/test_task_reevaluate_api.py backend/tests/test_target_system_orchestrator.py -q
  test_date: 2026-04-22
  artifact_ref: backend/agent/work_estimation_agent.py
  result: pass
  notes: 已验证估算链路在 specific/unlimited 模式兼容不回归，且估算 Agent 同时接收完整需求语义、系统画像上下文与 rule_context。
  residual_risk: low
  reopen_required: false

---

## Full Integration Testing (Testing Phase)

在 parent feature 分支的完整集成测试，作为最终验收依据。

- acceptance_ref: ACC-001
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  test_command: npm test -- --runInBand --watch=false src/__tests__/cosmicConfigPage.render.test.js
  test_date: 2026-04-22
  artifact_ref: frontend/src/__tests__/cosmicConfigPage.render.test.js
  result: pass
  notes: full-integration 复核规则管理页说明仅保留必要配置含义，快速设置文案不再暗示直接控制拆分粒度。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-002
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  test_command: python -m pytest tests/test_task_reevaluate_api.py tests/test_evaluation_contract_api.py -q
  test_date: 2026-04-22
  artifact_ref: tests/test_task_reevaluate_api.py
  result: pass
  notes: full-integration 复核 `/tasks/{task_id}/estimate` 在缺失历史结果时会按当前 COSMIC 配置主动执行分析、构建 rule_context 并注入估算 Agent；未选择规则时显式标记为 skipped。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-003
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  test_command: python -m pytest tests/test_task_reevaluate_api.py tests/test_evaluation_contract_api.py -q
  test_date: 2026-04-22
  artifact_ref: tests/test_evaluation_contract_api.py
  result: pass
  notes: full-integration 复核 COSMIC rule_context 统一结构、运行时分析与历史结果复用策略、功能点级 degraded 状态以及 artifact 后台证据字段。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-004
  test_type: regression
  test_scope: full-integration
  verification_type: automated
  test_command: python -m pytest tests/test_task_reevaluate_api.py backend/tests/test_target_system_orchestrator.py -q
  test_date: 2026-04-22
  artifact_ref: backend/agent/work_estimation_agent.py
  result: pass
  notes: full-integration 复核估算链路在 specific/unlimited 模式兼容不回归，且估算 Agent 同时接收完整需求语义、系统画像上下文与 rule_context。
  residual_risk: low
  reopen_required: false
