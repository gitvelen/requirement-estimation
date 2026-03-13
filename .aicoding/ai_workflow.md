# AI 工作流控制规则

## 阶段入口协议（🔴 MUST，CC-7硬校验）

> **为什么需要这个规则：**
> 实战证据显示，AI经常"不通读就动手"，导致遗漏系统性需求（见 aiquant R6、requirement-estimation 2026-02-07）。
> 强制读取必读文件，可以确保AI理解完整上下文。

> **核心规则：** 进入任何阶段后、开始产出前，**必须先读取**该阶段定义的必读文件。
> **硬校验：** CC-7 hook 会在首次写入产出物时检查是否已读取，未读取时**阻止写入**。
> **如何证明已读：** AI在输出中明确说"我已读XX文件"（CC-7通过read-tracker.sh追踪）

**必读文件来源：** `phases/<NN>-<stage>.md` 的"阶段入口协议"章节

**示例：** 进入 Requirements 阶段时，必须先读：
- `docs/<版本号>/status.md`
- `docs/<版本号>/proposal.md`
- `phases/02-requirements.md`

读取后，AI应输出："我已读 status.md、proposal.md、phases/02-requirements.md，现在开始编写 requirements.md..."

---

## 变更分级与流程选择

| 级别 | 判断条件（满足任一） | 流程 |
|------|---------------------|------|
| **Major** | 新功能开发；API 契约变更；数据库 schema 变更；权限/安全变更；跨模块影响；用户明确要求 | 完整 8 阶段流程 |
| **Minor** | 单模块小功能增强；Bug 修复（非紧急）；UI 微调；配置变更；文档修正 | 简化流程（见下方） |
| **Hotfix** | 线上紧急修复；低风险单点变更；无需完整阶段文档 | 独立 Hotfix 阶段的极速流程（见下方） |

**分级决策**：用户可直接指定；AI 可建议但须用户确认；Minor/Hotfix 中发现复杂度超预期时，AI 必须暂停并建议升级为 Major（操作规程见下方）。

### Hotfix 极速流程

> 核心原则：只解决紧急问题，不引入新范围。
> 机器可读切换：如涉及 `docs/vX.Y/status.md`，必须声明 `_change_level: hotfix`。
> **与 CR/Phase 00 的关系**：Hotfix 属于"当前版本追加 CR"的一种特殊形式（见 STRUCTURE.md），但因其紧急性和低风险性，允许跳过 Phase 00 澄清流程，直接进入修复。
> **Hotfix 阶段语义**：Hotfix 使用独立的 `_phase: Hotfix` 状态，不占用其他阶段。进入 Hotfix 时，AI 应记录原阶段到 `status.md` 的"阶段转换记录"表中（如 `Implementation -> Hotfix`），完成后可选择回到原阶段或直接推进到 Deployment。阶段细则见 `phases/08-hotfix.md`。
> **Hotfix 的 review_round**：Hotfix 的 `_review_round` 独立计数，不受 5 轮限制；若退出 Hotfix 并恢复 major/minor 常规流程（即将 `_change_level` 改回 `major` 或 `minor`），按目标阶段从 `0` 重新计数，不恢复进入 Hotfix 前的旧值。

```
适用边界（任一不满足即不可走 hotfix）：
1. staged 文件数 <= hotfix_max_diff_files（默认 3）
2. 不触碰 REQ-C / 禁止项边界
3. 不涉及 API/DB schema/权限安全变更

执行路径：
1. 切换到 Hotfix 阶段：`_phase: Hotfix`，记录原阶段到"阶段转换记录"表
2. 代码修复
3. 关键验证（最小可复现测试）
4. 提交（推荐 `fix:` / `fix(scope):`；兼容 `[CR-...]` 与 `Merge/Revert/fixup!/squash!`）
5. 完成后选择：回到原阶段继续，或直接推进到 Deployment

门禁行为：
- pre-commit 保留 hotfix 边界检查（文件数 + REQ-C + API/DB schema/权限安全敏感边界）
- hotfix 使用独立阶段 `_phase: Hotfix`，允许从任意阶段切换进入
- hotfix 可修改的 status.md 字段：`_run_status`、`_change_status`、`_review_round`、`_change_level`、`_phase`
- hotfix 退出阶段或标记完成时，`status.md` 必须内联 `TEST-RESULT` 结果块作为最小交付证据
- 完成态同步是**全局规则**：`_change_status=done` ⇔ `_run_status=completed`（见 `templates/status_template.md`）；hotfix 这里只额外要求在完成态时补齐最小测试证据
- hotfix 的 `_review_round` 不受 5 轮限制（长期维护版本可能累积多轮）
```

### Minor 简化流程

> 核心原则：**简化文档，不简化理解**。
> 机器可读切换：`status.md` 必须声明 `_change_level: minor`（缺失按 major 处理并告警）。
> 执行语义：Minor 允许跳过 Design / Planning 阶段，直接从 Requirements 进入 Implementation。如果变更确实需要设计/计划文档，则应升级为 Major。
> 审查文件管理：`review_minor.md` **只覆盖 Implementation + Testing 两个阶段**。它在 Implementation 阶段创建并完成首轮审查，Testing 阶段继续在同一文件末尾追加测试轮次审查（必须包含 `MINOR-TESTING-ROUND` 机器可读块）。

```
1. 需求确认（Proposal + Requirements 讨论可连续进行，但文档不合并）
   - 阶段推进仍为 Proposal → Requirements（不可跳跃）
   - 与用户充分讨论，确认：做什么、不做什么、验收标准
   - 输出：`proposal.md` + `requirements.md`；并在 status.md 记录变更摘要 + 验收标准
   - 用户确认后进入下一步

2. 实现（Phase 05，跳过 Design/Planning）
   - 阶段推进：Requirements → Implementation（跳过 Design / Planning）
   - 如果 AI 判断需要设计/计划文档，必须暂停并建议升级为 Major
   - `review_minor.md` 从 **Implementation** 阶段开始创建
   - 直接编码，但必须：先读后写、遵循实现检查清单、commit 消息包含变更摘要
   - 发现复杂度超预期（如需跨模块修改）→ 暂停，建议升级为 Major
   - pre-commit 会用 `minor_max_diff_files` / `minor_max_new_gwts` 进行复杂度硬拦截（超阈值需升级 major）

3. 测试（不简化）
   - 执行完整测试（单元+集成+回归）
   - 输出测试证据：二选一即可，`test_report.md` 或在 `status.md` 内联 `TEST-RESULT` 结果块
   - 同时，必须在 `review_minor.md` 末尾追加 Testing 轮次审查（必须包含 `MINOR-TESTING-ROUND-BEGIN/END` 机器可读块，且 `ROUND_PHASE=testing`、`ROUND_RESULT=pass`）
   - Testing 阶段出口门禁会校验 `review_minor.md` 中是否存在 Testing 轮次机器可读块

4. 部署执行（不简化）
   - 若变更涉及 `REQ-C`（禁止项），必须升级为 Major 并执行人类 spotcheck（pre-commit 对 minor 触碰 `REQ-C` 进行硬拦截）
   - 高风险项与变更范围必须在 ChangeManagement/Requirements 阶段明确并收敛，Deployment 阶段仅做一致性校验
   - 标准自动流程默认部署到 STAGING/TEST；AI 自动执行部署，部署后等待业务反馈
   - 如未来纳入 PROD，必须先为项目单独定义发布审批规则
```

### Minor 升级为 Major 操作规程

1. 一旦确认 minor 已超出边界，必须暂停当前推进，将 `status.md` 设为 `_run_status: wait_confirm`，请求用户确认升级。
2. 用户确认后，若仍在 Requirements 阶段：将 `_change_level` 改为 `major`，继续按 `Requirements -> Design -> Planning` 标准路径推进。
3. 若已进入 Implementation：将 `_change_level` 改为 `major`，回到 `_phase: Design`，补齐 `design.md` / `review_design.md`，再进入 Planning 和后续阶段。
4. 若已进入 Testing / Deployment：先回到 `ChangeManagement` 重新收敛范围，再按 major 路径补齐 Requirements / Design / Planning；避免从后序阶段直接大跨度回跳到 Design。
5. 既有 `review_minor.md` 不删除，作为升级前历史记录封存；升级后不再追加，改用 major 对应的 review 文件。升级涉及阶段切换时，`_review_round` 置为 `0`。

## 框架版本与发布约定（P4）

- 框架默认采用”GitHub 单版本最新”策略，不维护多版本门禁脚本并行兼容。
- 重大门禁变更必须在 GitHub Release Notes 中提供迁移说明（受影响字段、门禁变化、回滚建议）。

---

## 时期划分（Major 完整流程）

| 时期 | 阶段 | 人工介入 | 推进方式 |
|------|------|---------|---------|
| 人工介入期 | 00 变更管理 / 01 提案 / 02 需求 | ✅ | 人工确认 |
| AI 自动期 | 03 设计 / 04 计划 / 05 实现 / 06 测试 | ❌ | AI 自动（收敛即推进） |
| AI 自动期（特殊） | 07 部署 | ⚠️ | 自动部署到验收环境；部署后等待业务反馈 |

> 注：上表"❌ 人工介入"指阶段推进无需人工确认；阶段内部的里程碑交互（如 AI 向用户确认设计方案）不计为人工介入。

## 版本内变更 / 新版本启动 决策树（🔴 MUST）

当用户提出"再改一点"、"修一个 bug"、"补一个遗漏"之类的新意图时，AI 必须先依据当前 `status.md` 的运行态判断入口：

1. **若 `_run_status=completed`（版本已完成）**：
   - 不得直接假定走 Phase 00 或直接开新版本。
   - 必须先询问用户：这是**当前版本补丁/Hotfix**，还是**启动新版本**。
   - 用户确认"当前版本补丁" → 进入同版本追加 CR / hotfix 判定。
   - 用户确认"新版本" → 直接创建新版本目录，从 `Proposal` 开始。

2. **若 `_run_status!=completed`（当前版本仍在进行中）**：
   - 属于当前既有范围内的正常澄清/推进 → 继续当前版本流程，不额外创建 CR。
   - 属于对**已冻结范围**的追加/改向（例如已评审通过、已测试通过后又新增范围）→ 回到 Phase 00，创建 CR 做范围澄清。
  - 属于紧急、低风险、单点修复，且满足 hotfix 边界 → 可声明 `_change_level: hotfix`，跳过 Phase 00，并进入独立 `_phase: Hotfix` 执行。

> 判断原则：**是否新版本**取决于用户意图与范围性质；**是否需要 Phase 00**取决于是不是"版本内已冻结范围上的追加变更"；**是否可走 hotfix**取决于风险/范围边界，而不是取决于某个固定阶段名。

---

## 人工介入期规则（Phase 00-02）

### 阶段入口协议（🔴 MUST，CC-7 程序化强制）

> 人工介入期同样适用阶段入口协议。AI 进入阶段后、开始产出前，必须先读取该阶段定义的必读文件。CC-7 hook 在 AI 首次写入产出物时检查是否已读取。

**必读文件来源**：各阶段定义文件（`phases/<NN>-<stage>.md`）中的"阶段入口协议"章节。

### 审查流程
1. AI 完成阶段产出
2. 人工指定审查者：`@review Claude` 或 `@review Codex`
3. 审查者执行审查，结果**追加到文件末尾**（格式见 `review_template.md` 索引的对应阶段模板）
4. 可多次指定不同审查者，直至收敛
5. 人工确认后进入下一阶段

### 强制等待机制（🟡 SHOULD，软门禁 — 仅 Claude Code hook 可执行）
- AI 完成阶段产出后，**必须**将 `status.md` 的 `_run_status` 设为 `wait_confirm`
- 🚫 **禁止** AI 自行更新 `status.md` 的 `_phase`（以及表格展示行"当前阶段"）
- 仅当用户**明确确认**（如"确认"、"进入下一阶段"）后，AI 才可更新 `_phase` 并恢复 `_run_status` 为 `running`
- 新建 `status.md` 时：**版本内 CR 流**必须从 `ChangeManagement` 开始；**新版本启动**允许在“`Proposal` + 无 Active CR”时直接开始（pre-commit 硬校验）

> **软门禁说明**：pre-write-dispatcher 只检查 `_run_status=wait_confirm` 状态，未校验"用户确认事件"本身。此规则依赖 AI 自觉执行，无法程序化保证所有工具（Codex/手动 commit）都遵守。

### 执行边界说明
> `wait_confirm` 是软门禁：CC-1 hook 会拦截 Claude Code 的阶段推进写入，但 Codex 或手动 git commit 可绕过。
> 真正的硬门禁是 Git pre-commit 层的阶段出口检查（含 ChangeManagement/Proposal 的 review 文件存在性）和 `_review_round > 5` 硬拦截。
> 本框架诚实承认：人工介入期的"强制等待"对非 Claude Code 工具仅为文本规则约束，无法程序化保证。

### 收敛判定
- 触发：人工指定审查者
- 判定：人工判定
- 信号：审查者输出"建议人工确认进入下一阶段"

---

## AI 自动期规则（Phase 03-06）

### 阶段入口协议（🔴 MUST，CC-7 程序化辅助）

> AI 进入任何阶段后、开始产出前，**必须先读取**该阶段定义的必读文件列表。CC-7 hook 会在 AI 首次写入产出物时检查是否已读取，未读取时根据配置告警（默认 warn）或阻止写入（block）。

**必读文件来源**：各阶段定义文件（`phases/<NN>-<stage>.md`）中的"阶段入口协议"章节列出了该阶段的必读文件。

**通用必读文件**（所有阶段）：
- `docs/<版本号>/status.md` — 获取当前状态、Active CR、基线版本
- `phases/<NN>-<stage>.md` — 本阶段规则

**阶段特定必读文件**：各阶段定义文件（`phases/<NN>-<stage>.md`）中的"阶段入口协议"章节明确列出该阶段的必读文件范围（如 Implementation 阶段要求完整阅读 `plan.md`、`design.md`、`requirements.md`）

**追踪机制**：CC-7b（read-tracker.sh）在每次 Read 工具调用后记录已读文件路径到会话临时日志，CC-7（phase-entry-gate.sh）在写入产出物时校验日志。

**约束强度**：
- 默认 `entry_gate_mode: block`：首次写入时检查，未读取时阻断写入，直到读取后才允许继续（持续约束）
- 可配置 `entry_gate_mode: warn`：首次写入时检查，未读取时告警并标记已通过，后续同阶段不再检查（一次性提醒，非持续约束）
- 建议生产环境使用 block 确保流程合规，开发环境可用 warn 观测 AI 行为

### 预审门禁（🟡 MUST-WHEN-CONFIGURED，审查前执行）

> 来源：lessons_learned — 测试/构建不过就进入 REP 审查，审查轮次白费；修复后又要重新走查，是多轮不收敛的主要原因之一。

**适用阶段**：Implementation、Testing

**通用检查项**（所有适用阶段）：
1. 运行 `aicoding.config.yaml` 中配置的 `result_gate_test_command` → 测试全部通过
2. 运行 `result_gate_build_command` → 构建成功
3. 运行 `result_gate_typecheck_command` → 类型检查通过

> **未配置时的行为**：若某条命令为空，pre-commit 会输出 `⚠️ 未配置，已跳过` 并记录到 `gate-warnings.log`（W24 可审计），不阻断推进。建议在项目初始化时填写 CI 同款命令以启用硬门禁。

**阶段特有检查项**：
- **Implementation**：
  - 确认本阶段非 review 产出物已存在（代码改动已完成）
  - 运行契约一致性检查（如有前后端交互）：扫描前端所有 API 调用，提取端点路径，对比后端路由定义和 design.md 中定义的契约，发现不匹配时阻断
- **Testing**：
  - 确认 `test_report.md`（major）或测试证据（minor）已产出

**执行流程**：
1. AI 在**每次启动或追加** REP 审查（即每次写入 `review_implementation.md`、`review_testing.md` 或 `review_minor.md` 之前，包括多轮复审）之前，必须先执行上述检查并确认全部通过
2. 预审全部通过后，将结果记录到本次审查产物再继续 REP 流程：
   - major：填写审查模板的「§-1 预审结果」段落
   - minor：在 `review_minor.md` 中记录同等检查结果
3. 如有失败项，先修复代码再重新预审，不进入 REP
4. **多轮审查时同样适用**：每轮修复完成后，先重新跑预审门禁确认无回归，再启动下一轮审查

### 阶段出口门禁（🔴 MUST，CC-8 程序化强制）

> AI 推进阶段（修改 `_phase` 字段）时，CC-8 hook 自动检查当前阶段的必要产出物是否存在。CC-8（Claude Code 写入期）覆盖 Requirements + AI 自动期（Phase 02-06）；pre-commit 在提交期执行同等/更严校验并兜底。
>
> **实现分层说明**：`scripts/lib/common.sh` 的 `aicoding_phase_exit_required` 只维护"文件存在性清单"；minor Testing 场景下的"测试证据存在"与 `MINOR-TESTING-ROUND` 机器可读块属于**内容级门禁**，由 CC-8 / pre-commit 的补充校验负责。

**各阶段出口必须存在的产出物**：

| 当前阶段 | 必须存在的文件 |
|---------|--------------|
| Requirements | `review_requirements.md`（并执行 constraints/proposal 覆盖校验） |
| Design | `design.md`、`review_design.md` |
| Planning | `plan.md`、`review_planning.md` |
| Implementation | major: `review_implementation.md`；minor: `review_minor.md`（不要求测试证据） |
| Testing | major: `test_report.md`、`review_testing.md`；minor: `review_minor.md` + 测试证据（`test_report.md` 或 status 内联 `TEST-RESULT`），且 `review_minor.md` 必须追加 Testing 轮次机器可读结论（`MINOR-TESTING-ROUND`） |

**行为**：如产出物缺失，CC-8 通过 JSON block 阻止 `_phase` 字段写入并提示缺失项，AI 需补充完整后再推进。

### 收敛判定（🔴 MUST）

**收敛条件（缺一不可）：**

1. **问题收敛**：P0(open) = 0 且 P1(open) = 0
2. **证据完整**：review文档必须包含”## 证据清单”段落，列出：
   - 执行的验证命令（完整命令行）
   - 关键输出（截取前10行或关键行）
   - 定位信息（文件路径:行号）

**硬校验：** pre-commit 在阶段推进时会检查 review 文件是否包含”## 证据清单”段落且内容非空（不允许仅包含占位符如 `...`、`<待补充>`、`TBD`），缺失或为空时阻断提交。

**示例：合格的证据清单**

```markdown
## 证据清单

### 1. REQ追溯覆盖

**命令：**
```bash
bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && \
  review_gate_validate_design_trace_coverage requirements \
  docs/v2.0/requirements.md design docs/v2.0/design.md'
```

**输出：**
```
✓ All 23 REQ items traced in design.md
✓ All 5 REQ-C items traced in design.md
Coverage: 28/28 (100%)
```

**定位：**
- REQ-001 → design.md:45-67
- REQ-002 → design.md:89-112
```

**其他规则：**
- **Design/Planning**：允许将少量 P1 标记为 accept/defer（必须在 RVW 记录中写清理由 + 缓解，并登记到 `status.md` 的”技术债务登记”）
- **Implementation/Testing**：不允许 accept/defer（此处指审查发现的处置动作；与 GWT 判定中的 `DEFERRED_TO_STAGING` 是不同概念——后者表示”功能延期到后续迭代”，受 `deferred_limit_percent` 门禁约束，属受限允许）（必须 Fix；且必须通过”需求符合性审查（REQ 模式）”的逐条 GWT 判定与摘要块门禁，见 `phases/05-implementation.md`、`phases/06-testing.md`）
- **单轮满足即收敛**

### 轮次定义（🔴 MUST）
- **一轮** = 通过预审门禁 → 自我审查 → 输出审查报告（含 P0/P1 列表）
- **预审门禁失败不计入轮次**：预审失败 → 修复 → 重新预审，这个循环不增加 `_review_round`
- 只有通过预审并完成审查报告后才计为一轮
- 修复审查问题后再次审查 = 新一轮（轮次 +1）
- 人工中断/人工修改文件 = 不计入轮次
- 发生阶段切换时，`_review_round` 必须重置为 `0`（pre-commit 硬拦截）
- hotfix 例外：Hotfix 阶段内 `_review_round` 不受 5 轮限制；退出 Hotfix 并恢复 major/minor 常规流程（`_change_level` 改回 `major`/`minor`）时，按目标阶段从 `0` 重新计数
- 轮次记录在 `status.md` 的”阶段转换记录”表中

### AI 行为
1. 完成阶段产出
2. 执行自我审查（按 `review_template.md` 索引的对应阶段审查模板）
3. P0(open)=0 且 P1(open)=0 → 收敛，自动更新 status.md，进入下一阶段
4. 收敛后输出：
   ```
   ✅ [阶段] AI 自动审查已收敛（第 N 轮）
   ▶️ 自动进入下一阶段：[阶段名]
   ```

### `_workflow_mode` 同步规则（🔴 MUST）

AI 推进 `_phase` 时必须同步更新 `_workflow_mode`：
- Phase 00-02（ChangeManagement / Proposal / Requirements）→ `manual`
- Phase 03-06（Design / Planning / Implementation / Testing）→ `auto`
- Phase 07（Deployment）→ `semi-auto`
- Hotfix 阶段 → `auto`（紧急修复，自动推进）

> 说明：当前 `pre-commit` 已硬校验 `_phase -> _workflow_mode` 的映射关系；若阶段已切换但 `_workflow_mode` 未同步，提交会直接失败。

### 连续 3 轮不收敛：文本规则 + 第 5 轮脚本硬拦截（🔴 MUST）

**触发条件**：同一阶段连续 3 轮仍不收敛（AI 行为规则，由 AI 自觉执行）

**触发动作**：
1. 暂停，输出：
   ```
   ⚠️⚠️⚠️ 连续3轮自我审查未收敛，请求人工确认 ⚠️⚠️⚠️
   当前阶段：[阶段名] | 轮次：3
   未收敛：P0(open)=X, P1(open)=Y

   请选择：
   1. 将部分 P1 标记为 accept/defer，AI 继续验证（仅 Design/Planning；Implementation/Testing 禁止）
   2. 给出反馈，AI 继续修复
   3. 跳过当前阶段（需确认风险）
   ```
2. 更新 `status.md`：运行状态=wait_confirm，记录"3 轮未收敛"

**重置规则**：人工确认后若仍在同一阶段继续修复，`_review_round` 不重置、继续递增；若切换到新阶段，必须重置为 `0`。同一阶段最多再给 2 轮（即第 5 轮）；第 5 轮仍不收敛则强制停止，`_review_round > 5` 时 pre-commit 硬拦截（hotfix 例外：不受此限制）

> **pre-commit 硬拦截**：当 `_review_round > 5` 且 `_run_status != wait_confirm` 且 `_change_level != hotfix` 时，pre-commit 会硬拦截提交，强制要求切换为 `wait_confirm` 并请求人工确认。此为脚本级强制，不依赖 AI 自觉。

### 失败处置协议（🔴 MUST）

适用于 AI 自动期（Phase 03-06）遇到执行失败的场景。

**失败分级与处置**：

| 失败类型 | 示例 | 处置策略 |
|---------|------|---------|
| 可自动恢复 | 测试偶发失败、网络超时、依赖暂时不可用 | 重试，上限 2 次，间隔递增 |
| 需分析后修复 | 测试稳定失败、编译错误、类型不匹配 | 分析根因 → 修复 → 重新验证（计入轮次） |
| 需降级/拆分 | 性能不达标、方案不可行、依赖缺失 | 记录问题 → 提出降级/拆分方案 → 暂停等待确认 |
| 需人类决策 | 需求不明确、多方案无法取舍、安全/合规风险 | 立即暂停 → 列出选项与代价 → 等待用户决策 |

**强制规则**：
- 同一问题重试超过 2 次仍失败 → 禁止继续重试，必须升级到"需分析后修复"
- 同一问题修复超过 3 次仍失败 → 禁止继续修复，必须升级到"需人类决策"
- 升级时必须输出：问题描述、已尝试的方案、失败原因、建议的下一步选项

### 举手阈值（🔴 MUST）

以下情况 AI 必须立即暂停并征询用户，不得默默推进：

| 触发条件 | 处置 |
|---------|------|
| 需求不清且影响范围/验收标准 | 暂停，列出 1-3 个具体问题 |
| 发现需要"禁止的变更"（见 05-implementation.md） | 暂停，建议走 CR 修订 |
| 连续 2 次验证失败且原因不明 | 暂停，列出已尝试方案和失败原因 |
| 需要危险 Git 操作（`--no-verify`/`--force`/`reset --hard`） | 暂停，说明必要性 |
| 发现安全/合规风险（密钥泄露、权限越界） | 立即停止，报告风险 |
| 实际工作量显著超出 plan.md 预估 | 暂停，建议调整计划 |

---

## Deployment 阶段规则（Phase 07）

### AI 行为
1. 完成阶段产出，并在 `deployment.md` 明确目标环境（STAGING / TEST / PROD）
2. 执行自我审查，确认前序阶段已明确高风险项与变更范围，并校验本次实际交付与前序声明一致。
3. 按标准自动流程执行部署：
   - 默认目标环境为 STAGING/TEST → AI 自动部署到验收环境
   - 高风险项不在本阶段首次决策；若发现前序未收敛或交付与声明不一致，应暂停并回退上游阶段补齐
   - 如未来纳入 PROD，需先为该项目单独定义发布审批规则后再执行
4. 状态约定：
   - 自动部署到验收环境后，将 `status.md` 设为 `_phase: Deployment`、`_change_status: in_progress`、`_run_status: wait_feedback`
   - `wait_feedback` 专用于 Deployment 阶段，表示”已部署，等待业务验收反馈”
   - `wait_confirm` 专用于人工介入期（Phase 00-02）或 AI 自动期连续 3 轮不收敛时；Deployment 阶段若进入人工决策/多轮不收敛升级态，或已验收通过但尚未完成主分支收口/打 tag，也应从 `wait_feedback` 切换为 `wait_confirm`
5. 人类验收反馈：
   - 验收通过 → 先记录 `deployment.md` 验收结论；若尚未完成主分支合入、版本 tag 与远端 push，则保持 `_change_status: in_progress`，并将 `_run_status` 切到 `wait_confirm`
   - 基线发布完成（已合入 `main/master`、匹配版本 tag 已创建并 push） → `status.md` 才能置完成态（`_change_status: done` + `_run_status: completed`）
   - 验收不通过 → 回到对应上游阶段继续修复（通常 Testing/Implementation）
   - 若仍在 Deployment 阶段内等待人工判断，保持 `_phase: Deployment`，以 `wait_confirm` 表示“等待决策”而非“等待业务反馈”

> 说明：以上为流程规范；`pre-commit` 仍只校验 Deployment 文档和完成态一致性，不校验 Git 基线是否已形成。`completed` 的主分支/tag/远端同步约束由 `pre-push`、CI push 事件的 release gate 和 `scripts/release-complete.sh` 共同保证。CI 的 PR 事件对 completed 仅做告警，不阻断——因为通过 PR 合入主分支是推荐流程，completed 会自然出现在 PR diff 中。

---

## 紧急中断机制

### 触发条件
- P0 Blockers 无法自动修复
- 连续 3 轮不收敛（自动触发，见上方）
- 发现安全/合规重大风险

### AI 行为
1. 立即停止
2. 更新 `status.md`：运行状态=paused 或 wait_confirm
   - `wait_confirm`：需要人工做出决策（Phase 00-02 人工介入期，或 AI 自动期连续 3 轮不收敛时）
   - `wait_feedback`：仅用于 Deployment 阶段，表示已部署到验收环境，等待业务方验收反馈
   - `paused`：因故障/风险被动停止，人工排查后设为 `running` 即可恢复（无需决策）
3. 输出：
   ```
   ⚠️⚠️⚠️ 工作已暂停 ⚠️⚠️⚠️
   原因：[原因描述]
   当前阶段：[阶段名]
   请人工确认后恢复
   ```

### 恢复
- 人工设置 `status.md` 运行状态=running，或直接说"继续"
- 工作流模式保持不变（由人工决定是否修改）

---

## 债务管理规则（🔴 MUST）

### A. 技术债务（Technical Debt）

**来源**：Design / Planning 阶段审查中，被明确 `accept/defer` 的设计/计划类问题。

**登记规则**：
1. 仅当问题来自 **Design / Planning** 审查，且被允许延期处理时，才登记到 `status.md` 的"技术债务登记"表。
2. 必填字段：来源阶段、RVW-ID / 问题描述、严重度（通常为 P1）、defer 理由、缓解措施、目标处理版本、状态。

**生命周期**：
1. 状态：`Open / In Progress / Resolved`
2. 每次部署完成后，如已偿还，必须更新为 `Resolved`
3. 新版本启动时，建议在 Proposal 中列出计划偿还的技术债务清单

**门禁影响**：
1. 技术债务总量过高时仅触发**告警**，不直接阻断当前版本推进
2. 当前实现中，pre-commit 对基线版本技术债务总量只做建议性提示，不作为硬阻断条件

### B. 质量债务（Quality Debt）

**来源**：Testing / Deployment 阶段发现、但未在当前版本立即修复的质量问题。

**登记规则**：
1. Testing 阶段发现的测试覆盖不足、契约不一致、性能/稳定性问题等，若不在本版本修复，必须登记到"质量债务登记"表。
2. Deployment 阶段人类验收发现的问题，若决定延期到后续版本修复，也必须登记到"质量债务登记"表。
3. 必填字段：债务 ID、类型、描述、风险等级（高/中/低）、计划偿还版本、状态。

**生命周期**：
1. 状态：`Open / In Progress / Resolved`
2. 每次部署完成后，必须回看质量债务表并更新状态
3. 债务标记为 `Resolved` 时，必须在对应的 `test_report.md` 或 `review_*.md` 中留下验证证据（债务 ID、修复方案、验证方法、验证结果）

**门禁影响**：
1. **高风险质量债务阈值门禁**：新版本启动时（进入 `Proposal` 且当前新建的 `status.md` 无 Active CR，以此区分"新版本启动"与"版本内 CR 流"），pre-commit 检查 **`_baseline` 指向版本** 的高风险质量债务；如果数量达到阈值，则阻断新版本启动。
2. **质量债务总量门禁**：新版本启动时，pre-commit 也会检查 **`_baseline` 指向版本** 的质量债务总量；超过阈值时阻断。

### C. 执行机制

- **硬门禁**（pre-commit 脚本）：在"新版本启动进入 `Proposal` 且无 Active CR"时，检查 **`_baseline` 指向版本** 的 `status.md` 中的质量债务总量与高风险质量债务数量；超过阈值则阻断提交。
- **软提醒**（AI 可选）：AI 在 Proposal 阶段可参考 **`_baseline` 指向版本** 的技术债务 / 质量债务清单，在 proposal 中列出本版本计划偿还范围。
- **追踪机制**：通过 `status.md` 的两张债务登记表分别追踪，避免把"设计延期"与"测试/验收遗留"混为一类。
