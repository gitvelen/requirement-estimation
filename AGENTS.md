# AGENTS.md

尽量用简体中文交流（除非涉及专业术语），禁止用 worktree。

---

## 一、当前阶段要读什么

**每次启动必读**：
1. `../lessons_learned.md` - 只读取硬规则部分
2. `./meta.yaml` - 获取当前 phase、focus_work_item、active_work_items

**按当前 phase 读取**（从 meta.yaml 的 phase 字段获取）：

**Proposal**：
- `spec.md` - 首次浏览读 Default Read Layer（到 `<!-- SKELETON-END -->`）；工作时填充 Intent、Proposal Coverage Map、Clarification Status（替换模板占位和示例）
- `spec-appendices/*` - 按需深入，但不能在 appendix 中定义正式 REQ/ACC/VO

**Requirements**：
- `spec.md` - 完整读取，填充 REQ-*、ACC-*、VO-*（替换模板占位）
- `spec-appendices/*` - 按需深入

**Design**：
- `spec.md` - 读取 approved requirements、acceptance、verification
- `design.md` - 首次浏览读 Default Read Layer（Goal/Scope Link、Architecture Boundary、Work Item Derivation、Design Slice Index）；工作时填充 Goal/Scope Link、Architecture Boundary、Work Item Derivation、Verification Design、Implementation Readiness Baseline（替换模板占位）
- `design-appendices/*` - 按需深入（通过 Design Slice Index）

**Implementation**：
- `work-items/<focus_work_item>.yaml` - 读取当前 WI 的 goal、allowed_paths、requirement_refs、acceptance_refs、verification_refs
- `design.md` - 读取当前 WI 对应的 design slice（通过 Design Slice Index）
- `spec.md` - 验证 REQ/ACC/VO 引用是否存在
- `contracts/*.md` - 如果当前 WI 的 contract_refs 非空，读取对应合约
- `testing.md` - 添加 branch-local 测试记录

**Testing**：
- `testing.md` - 添加 full-integration 测试记录
- `work-items/*.yaml` - 读取所有 work-items（Testing 阶段 verification gate 会检查 active_work_items 中所有 WI 的 approved acceptance）
- `spec.md` - 读取 approved acceptance 和 verification obligations
- `design.md` - 参考 Verification Design

**Deployment**：
- `deployment.md` - 填充 Deployment Plan、Verification Results、Acceptance Conclusion、Rollback Plan、Monitoring（替换模板占位）
- `testing.md` - 验证所有 approved acceptance 都有 test_scope=full-integration 且 result=pass 的记录

**Deployment 交接规则**：
- 先判断 `restart_required`；不能在未判断的情况下直接让用户验证
- 若需要重启，先完成重启；不得跳过
- 在提示人工验证前，先确认运行态已就绪，并记录 `runtime_ready: pass` 与 `runtime_ready_evidence`
- 只有 smoke / runtime readiness / restart decision 都闭环后，才能标记 `manual_verification_ready: pass` 并通知用户人工验证

**说明**：
- 文档可能是模板内容（阶段刚开始）或已填充内容（阶段进行中），都要读取
- Default Read Layer 是快速索引，首次浏览时读取；工作时需要读取完整章节
- `focus_work_item` 为 null 时跳过 work-items 读取
- `contract_refs` 为空时跳过 contracts 读取
- appendices 按需深入，不是每次必读
- 项目文档（`../project-docs/<base_version>/`）不在 readset 中，只在用户明确要求时读取
- 第一个版本（v1.0）的 base_version 为 null，无项目文档可读

---

## 二、什么时候必须停下

**范围越界**：
- 需要修改不在当前 WI 的 `allowed_paths` 中的文件 → 停止
- 需要修改 `forbidden_paths` 中的文件 → 停止
- 需要实现 `out_of_scope` 中的功能 → 停止
- 需要修改 frozen contract → 停止

**目标不清**：
- 目标/边界/验收不清楚 → 先问用户
- `spec.md` / `design.md` / `work-items/*.yaml` 之间描述不一致 → 先对齐
- 需要做产品判断（非纯工程判断）→ 先问用户
- `Clarification Status` 中有 open decision 影响当前动作 → 先澄清

**执行偏离**：
- 连续失败或复杂度超预期 → 停下重新规划
- 发现需要先回写权威文件（spec/design/testing/deployment）→ 停止当前任务，先更新文档
- 依赖 Work Item 尚未完成，但当前任务需要其结果 → 停止，等待依赖
- 测试失败且无法在当前 scope 内修复 → 回看 work-item.yaml，可能需要扩大 allowed_paths
- Proposal 阶段在 appendix 中定义正式 REQ/ACC/VO → 停止，只能在主文档中定义

---

## 三、核心原则

**取舍说明**：以下规则默认偏向谨慎而不是速度。

### 1. 先想清楚再动手

**不要想当然，不要掩盖困惑，要把假设和权衡说清楚。**

 - 明确说明你的假设。不确定时就提问。
 - 如果存在多种理解方式，把它们列出来，不要默默自行选择。
 - 如果有更简单的做法，直接指出来；必要时应当提出异议。
 - 如果有任何地方不清楚，就先停下。说清楚困惑点，然后提问。

### 2. 简单优先

**只写解决当前问题所需的最少代码，不预埋未来需求。**

- 不做未被请求的功能
- 不为一次性代码提前抽象
- 不引入未被要求的“灵活性”或“可配置性”
- 不为事实上不可能发生的场景补错误处理
- 如果 200 行能压到 50 行且不损失可读性，就重写到足够简单

问问自己：“一位资深工程师会不会认为这实现过于复杂？”如果会，就继续简化。

### 3. 手术式改动

**只改必须改的地方，只清理自己引入的问题。**

编辑既有代码时：
- 不顺手“改进”相邻代码、注释或格式
- 不重构没有坏掉的部分
- 尽量贴合现有风格，即使你的做法不同
- 发现无关的死代码时可以提示，但不要擅自删除

如果你的改动产生了遗留物：
- 删除因你的修改而不再使用的导入项、变量、函数
- 不要顺带清理既有的死代码，除非用户明确要求

判断标准：每一行修改后的代码都应当能直接追溯到用户的请求。

### 4. 以目标驱动执行

**先定义可验证的成功标准，再循环执行直到验证通过。**

- “加校验”应落实为：编写针对非法输入的测试案例，确保程序能高质量地通过测试
- “修 bug”应落实为：先写能复现问题的测试，再修到通过
- “重构 X”应落实为：改前改后都验证相关测试通过

多步骤任务先给出一个简短计划，并把每一步的验证方式写出来，例如：

```text
1. [步骤] -> verify: [检查项]
2. [步骤] -> verify: [检查项]
3. [步骤] -> verify: [检查项]
```

成功标准越强，越能独立闭环推进；像“把它弄好”这种弱目标会导致反复澄清和返工。

**这些规则生效的表现**：diff 中无关改动更少、因过度设计导致的返工更少、澄清问题发生在实现之前而不是出错之后。

---

## 四、阶段切换前检查

**命令与 gate 映射**（runtime 会自动检查）：
- `../.codespec/codespec start-requirements` → 检查 `proposal-maturity`
- `../.codespec/codespec start-design` → 检查 `requirements-approval`
- `../.codespec/codespec start-implementation <WI-ID>` → 检查 `implementation-ready`
- `../.codespec/codespec start-testing` → 检查 `metadata-consistency` + `scope` + `contract-boundary` + `verification`
- `../.codespec/codespec start-deployment` → 检查 `trace-consistency` + `verification`
- `../.codespec/codespec complete-change` → 检查 `promotion-criteria`
- `../.codespec/codespec promote-version` → 检查 `promotion`

**说明**：
- gate 检查由 runtime 自动执行，失败会阻止阶段切换
- 手动检查：`../.codespec/codespec check-gate <gate-name>`
- 详细检查项：`../.codespec/codespec check-gate <gate-name> --verbose`

---

## 五、Compact Instructions 保留优先级

1. 架构决策，不得摘要
2. 已修改文件和关键变更
3. 验证状态，pass/fail
4. 未解决的 TODO 和回滚笔记
5. 工具输出，可删，只保留 pass/fail 结论

---

