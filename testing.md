# Testing Records

## How to Use This File

`testing.md` 是测试证据账本，记录当前变更从 `Implementation` 到 `Testing` 阶段的验证证据。

**测试类型（test_type）**：
- `unit`: 单元测试，测试单个函数/类的逻辑
- `integration`: 集成测试，测试多个模块的交互
- `e2e`: 端到端测试，测试完整的用户流程
- `performance`: 性能测试，测试响应时间/吞吐量
- `security`: 安全测试，测试安全漏洞
- `manual`: 手工测试，人工验证

**测试范围（test_scope）**：
- `branch-local`: Implementation 阶段当前执行分支的局部验证
- `full-integration`: Testing 阶段 parent feature 分支的完整集成验证

**测试结果（result）**：
- `pass`: 测试通过，acceptance 得到验证
- `fail`: 测试失败，需要修复实现或重新开启 spec/design

**重新开启标记（reopen_required）**：
- `true`: 需要重新开启 spec/design
- `false`: 不需要重新开启

---

## Branch-Local Testing (Implementation Phase)

### WI-001 (Branch: feature-v2.9)

#### ACC-001: 创建页输入规则与候选项来源闭环

- acceptance_ref: ACC-001
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  test_command: cd frontend && CI=true npm test -- --runInBand --watch=false src/__tests__/uploadPage.targetSystem.test.js
  test_date: 2026-04-20
  artifact_ref: frontend/src/__tests__/uploadPage.targetSystem.test.js
  result: pass
  notes: 验证待评估系统位于任务名称前、候选项按主责+B角过滤且“不限”始终最后；无主责/B角时仅展示“不限”；未选择时阻止提交，选择具体系统后提交 multipart 字段。
  residual_risk: low
  reopen_required: false

#### ACC-002: 后端约束、持久化和详情追溯闭环

- acceptance_ref: ACC-002
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  test_command: python -m pytest tests/test_target_system_task_create.py -q
  test_date: 2026-04-20
  artifact_ref: tests/test_target_system_task_create.py
  result: pass
  notes: 验证 specific 系统越权拒绝、unlimited 空归属兼容、task 持久化 target_system_mode/name，以及详情/编辑结果基础接口回传字段。
  residual_risk: low
  reopen_required: false

### WI-002 (Branch: feature-v2.9)

#### ACC-003: 具体系统模式核心评估流程

- acceptance_ref: ACC-003
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  test_command: python -m pytest backend/tests/test_target_system_orchestrator.py -q
  test_date: 2026-04-20
  artifact_ref: backend/tests/test_target_system_orchestrator.py
  result: pass
  notes: 验证 specific 模式跳过自动系统识别、直接以全文需求和指定系统进入拆分与估算，并在零功能点场景返回明确失败。
  residual_risk: low
  reopen_required: false

#### ACC-004: 既有多系统路径兼容性

- acceptance_ref: ACC-004
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  test_command: python -m pytest backend/tests/test_target_system_orchestrator.py -q
  test_date: 2026-04-20
  artifact_ref: backend/tests/test_target_system_orchestrator.py
  result: pass
  notes: 验证 unlimited 模式仍先做系统识别并保留多系统输出；同时补充 routes 透传测试，确保任务上的目标系统选择进入编排层。
  residual_risk: low
  reopen_required: false

### WI-003 (Branch: feature-v2.9)

#### ACC-002: 详情页待评估系统展示闭环

- acceptance_ref: ACC-002
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  test_command: cd frontend && CI=true npm test -- --runInBand --watch=false src/__tests__/reportPage.targetSystem.test.js
  test_date: 2026-04-20
  artifact_ref: frontend/src/__tests__/reportPage.targetSystem.test.js
  result: pass
  notes: 验证 ReportPage 在具体系统与 unlimited 两种任务上都展示“待评估系统”结果，并与已有详情接口字段保持一致。
  residual_risk: low
  reopen_required: false

#### ACC-005: 后端系统级锁定拒绝

- acceptance_ref: ACC-005
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  test_command: python -m pytest backend/tests/test_target_system_locking.py -q
  test_date: 2026-04-20
  artifact_ref: backend/tests/test_target_system_locking.py
  result: pass
  notes: 验证具体系统任务上的新增系统、重命名系统、删除系统、重新拆分四类系统级操作全部返回锁定拒绝，同时功能点级 update 仍可执行。
  residual_risk: low
  reopen_required: false

#### ACC-005: 前端系统级入口隐藏

- acceptance_ref: ACC-005
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  test_command: cd frontend && CI=true npm test -- --runInBand --watch=false src/__tests__/editPage.targetSystemLock.test.js
  test_date: 2026-04-20
  artifact_ref: frontend/src/__tests__/editPage.targetSystemLock.test.js
  result: pass
  notes: 验证 EditPage 在 specific 任务隐藏“系统操作”入口并展示锁定说明，在 unlimited 任务保留系统级入口；功能点级“添加功能点”入口持续可用。
  residual_risk: low
  reopen_required: false

---

## Full Integration Testing (Testing Phase)

### WI-001 / WI-002 / WI-003 (Branch: feature-v2.9)

#### ACC-001: 创建页输入规则与候选项来源闭环

- acceptance_ref: ACC-001
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  test_command: cd frontend && CI=true npm test -- --runInBand --watch=false src/__tests__/uploadPage.targetSystem.test.js
  test_date: 2026-04-20
  artifact_ref: frontend/src/__tests__/uploadPage.targetSystem.test.js
  result: pass
  notes: parent feature 分支复核创建页字段顺序、候选项顺序、only-不限 场景与 multipart 提交字段；存在 React Router future flag warning，但不影响结果。
  residual_risk: low
  reopen_required: false

#### ACC-002: 后端约束、持久化与详情追溯闭环

- acceptance_ref: ACC-002
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  test_command: python -m pytest tests/test_target_system_task_create.py -q
  test_date: 2026-04-20
  artifact_ref: tests/test_target_system_task_create.py
  result: pass
  notes: parent feature 分支复核 specific 越权拒绝、unlimited 空归属兼容、task 持久化字段与详情/编辑结果接口返回。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-002
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  test_command: cd frontend && CI=true npm test -- --runInBand --watch=false src/__tests__/reportPage.targetSystem.test.js
  test_date: 2026-04-20
  artifact_ref: frontend/src/__tests__/reportPage.targetSystem.test.js
  result: pass
  notes: parent feature 分支复核 ReportPage 在 specific 与 unlimited 任务上都展示“待评估系统”；存在 React Router future flag warning，但不影响结果。
  residual_risk: low
  reopen_required: false

#### ACC-003: 具体系统模式核心评估流程

- acceptance_ref: ACC-003
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  test_command: python -m pytest backend/tests/test_target_system_orchestrator.py tests/test_agent_orchestrator.py -q
  test_date: 2026-04-20
  artifact_ref: backend/tests/test_target_system_orchestrator.py
  result: pass
  notes: parent feature 分支复核 specific 模式跳过自动系统识别、单系统输出、零功能点失败，并保留既有 orchestrator 基线行为。
  residual_risk: low
  reopen_required: false

#### ACC-004: 既有多系统路径兼容性

- acceptance_ref: ACC-004
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  test_command: python -m pytest backend/tests/test_target_system_orchestrator.py tests/test_agent_orchestrator.py -q
  test_date: 2026-04-20
  artifact_ref: backend/tests/test_target_system_orchestrator.py
  result: pass
  notes: parent feature 分支复核 unlimited 模式仍先做系统识别、保留多系统结果结构，且未回归既有 orchestrator 输入聚合逻辑。
  residual_risk: low
  reopen_required: false

#### ACC-005: 单系统任务编辑边界约束

- acceptance_ref: ACC-005
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  test_command: python -m pytest backend/tests/test_target_system_locking.py -q
  test_date: 2026-04-20
  artifact_ref: backend/tests/test_target_system_locking.py
  result: pass
  notes: parent feature 分支复核具体系统任务上的新增系统、重命名、删除、重新拆分四类系统级操作全部被后端拒绝，功能点级 update 仍可执行。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-005
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  test_command: cd frontend && CI=true npm test -- --runInBand --watch=false src/__tests__/editPage.targetSystemLock.test.js
  test_date: 2026-04-20
  artifact_ref: frontend/src/__tests__/editPage.targetSystemLock.test.js
  result: pass
  notes: parent feature 分支复核 EditPage 在 specific 任务隐藏“系统操作”入口并展示锁定说明，在 unlimited 任务保留系统级入口；存在 React Router future flag 与 antd Table warning，但不影响结果。
  residual_risk: low
  reopen_required: false
