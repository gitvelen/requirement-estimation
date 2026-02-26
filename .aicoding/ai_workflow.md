# AI 工作流控制规则

## 变更分级与流程选择

| 级别 | 判断条件（满足任一） | 流程 |
|------|---------------------|------|
| **Major** | 新功能开发；API 契约变更；数据库 schema 变更；权限/安全变更；跨模块影响；用户明确要求 | 完整 8 阶段流程 |
| **Minor** | 单模块小功能增强；Bug 修复（非紧急）；UI 微调；配置变更；文档修正 | 简化流程（见下方） |
| **Hotfix** | 线上紧急修复；低风险单点变更；无需完整阶段文档 | 极速流程（见下方） |

**分级决策**：用户可直接指定；AI 可建议但须用户确认；Minor/Hotfix 中发现复杂度超预期时，AI 必须暂停并建议升级为 Major。

### Hotfix 极速流程

> 核心原则：只解决紧急问题，不引入新范围。  
> 机器可读切换：如涉及 `docs/vX.Y/status.md`，必须声明 `_change_level: hotfix`。

```
适用边界（任一不满足即不可走 hotfix）：
1. staged 文件数 <= hotfix_max_diff_files（默认 3）
2. 不触碰 REQ-C / 禁止项边界
3. 不涉及 API/DB schema/权限安全变更

执行路径：
1. 代码修复
2. 关键验证（最小可复现测试）
3. 提交（推荐 `fix:` / `fix(scope):`；兼容 `[CR-...]` 与 `Merge/Revert/fixup!/squash!`）

门禁行为：
- pre-commit 保留 hotfix 边界检查（文件数 + REQ-C + API/DB schema/权限安全敏感边界）
- 如 status.md 也被修改，阶段出口门禁不触发（不推进阶段）
- `_workflow_mode` 仍按 `_phase` 映射填写（manual/auto/semi-auto），hotfix 不因分级单独改写映射
- hotfix 标记完成时（`_change_status: done` / `_run_status: completed`），`status.md` 必须内联 `TEST-RESULT` 结果块作为最小交付证据
- 完成态必须同步：`_change_status=done` ⇔ `_run_status=completed`
```

### Minor 简化流程

> 核心原则：**简化文档，不简化理解**。
> 机器可读切换：`status.md` 必须声明 `_change_level: minor`（缺失按 major 处理并告警）。
> 执行语义：Minor 的“合并阶段”仅指**产出物与审查文档合并**；`_phase` 仍按标准顺序逐阶段推进，不允许跳阶段。

```
1. 需求确认（Proposal + Requirements 讨论可连续进行，但文档不合并）
   - 阶段推进仍为 Proposal → Requirements（不可跳跃）
   - 与用户充分讨论，确认：做什么、不做什么、验收标准
   - 输出：`proposal.md` + `requirements.md`；并在 status.md 记录变更摘要 + 验收标准
   - 用户确认后进入下一步

2. 设计+计划+实现（Phase 03-05）
   - 阶段推进仍为 Design → Planning → Implementation（不可跳跃）
   - Design / Planning 产出不合并：仍需 `design.md + review_design.md`、`plan.md + review_planning.md`
   - Implementation / Testing 审查可合并使用 `review_minor.md`（单文件审查，最小机器可读块）
   - 直接编码，但必须：先读后写、遵循实现检查清单、commit 消息包含变更摘要
   - 发现复杂度超预期（如需跨模块修改）→ 暂停，建议升级为 Major
   - pre-commit 会用 `minor_max_diff_files` / `minor_max_new_gwts` 进行复杂度硬拦截（超阈值需升级 major）

3. 测试（不简化）
   - 执行完整测试（单元+集成+回归）
   - 输出测试证据：`test_report.md` 或在 `status.md` 内联 `TEST-RESULT` 结果块（二选一）
   - `review_minor.md` 必须追加 Testing 轮次机器可读块（`MINOR-TESTING-ROUND-BEGIN/END`，且 `ROUND_PHASE=testing`、`ROUND_RESULT=pass`）

4. 部署执行（不简化）
   - 若变更涉及 `REQ-C`（禁止项），必须升级为 Major 并执行人类 spotcheck（pre-commit 对 minor 触碰 `REQ-C` 进行硬拦截）
   - 目标环境为 STAGING/TEST 且不涉及高风险项 → AI 自动部署，部署后等待人类验收
   - 目标环境为 PROD，或涉及高风险项 → 先请求人工确认再部署
```

## 框架版本与发布约定（P4）

- 框架默认采用“GitHub 单版本最新”策略，不维护多版本门禁脚本并行兼容。
- 重大门禁变更必须在 GitHub Release Notes 中提供迁移说明（受影响字段、门禁变化、回滚建议）。
- `framework_ref` 当前为预留字段，尚未被门禁脚本消费；如需冻结，请在仓库层面固定框架来源 commit/tag 后再升级。

---

## 时期划分（Major 完整流程）

| 时期 | 阶段 | 人工介入 | 推进方式 |
|------|------|---------|---------|
| 人工介入期 | 00 变更管理 / 01 提案 / 02 需求 | ✅ | 人工确认 |
| AI 自动期 | 03 设计 / 04 计划 / 05 实现 / 06 测试 | ❌ | AI 自动（收敛即推进） |
| AI 自动期（特殊） | 07 部署 | ⚠️ | 验收环境可自动部署；生产/高风险需人工确认 |

> 注：上表"❌ 人工介入"指阶段推进无需人工确认；阶段内部的里程碑交互（如 AI 向用户确认设计方案）不计为人工介入。

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

### 强制等待机制（🔴 MUST）
- AI 完成阶段产出后，**必须**将 `status.md` 的 `_run_status` 设为 `wait_confirm`
- 🚫 **禁止** AI 自行更新 `status.md` 的 `_phase`（以及表格展示行"当前阶段"）
- 仅当用户**明确确认**（如"确认"、"进入下一阶段"）后，AI 才可更新 `_phase` 并恢复 `_run_status` 为 `running`
- 新建 `status.md` 的 `_phase` 必须从 `ChangeManagement` 开始（pre-commit 硬拦截）

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

### 阶段入口协议（🔴 MUST，CC-7 程序化强制）

> AI 进入任何阶段后、开始产出前，**必须先读取**该阶段定义的必读文件列表。CC-7 hook 会在 AI 首次写入产出物时检查是否已读取，未读取则告警（默认 warn）或阻止写入（block），可在 aicoding.config.yaml 配置。

**必读文件来源**：各阶段定义文件（`phases/<NN>-<stage>.md`）中的"阶段入口协议"章节列出了该阶段的必读文件。

**通用必读文件**（所有阶段）：
- `docs/<版本号>/status.md` — 获取当前状态、Active CR、基线版本
- `phases/<NN>-<stage>.md` — 本阶段规则

**追踪机制**：CC-7b（read-tracker.sh）在每次 Read 工具调用后记录已读文件路径到会话临时日志，CC-7（phase-entry-gate.sh）在写入产出物时校验日志。

### 阶段出口门禁（🔴 MUST，CC-8 程序化强制）

> AI 推进阶段（修改 `_phase` 字段）时，CC-8 hook 自动检查当前阶段的必要产出物是否存在。CC-8（Claude Code 写入期）覆盖 Requirements + AI 自动期（Phase 02-06）；pre-commit 在提交期执行同等/更严校验并兜底。

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
- **收敛条件**：P0(open) = 0 且 P1(open) = 0
- **Design/Planning**：允许将少量 P1 标记为 accept/defer（必须在 RVW 记录中写清理由 + 缓解，并登记到 `status.md` 的“技术债务登记”）
- **Implementation/Testing**：不允许 accept/defer（此处指审查发现的处置动作；与 GWT 判定中的 `DEFERRED_TO_STAGING` 是不同概念——后者表示"功能延期到后续迭代"，受 `deferred_limit_percent` 门禁约束，属受限允许）（必须 Fix；且必须通过"需求符合性审查（REQ 模式）"的逐条 GWT 判定与摘要块门禁，见 `phases/05-implementation.md`、`phases/06-testing.md`）
- **单轮满足即收敛**

### 轮次定义（🔴 MUST）
- **一轮** = 完成阶段工作 → 自我审查 → 输出审查报告（含 P0/P1 列表）
- 修复后再次审查 = 新一轮（轮次 +1）
- 人工中断/人工修改文件 = 不计入轮次
- 发生阶段切换时，`_review_round` 必须重置为 `0`（pre-commit 硬拦截）
- hotfix 不允许阶段推进，因此不触发“阶段切换重置”；hotfix 的 `_review_round` 语义仍为“当前阶段内的审查轮次”
- 轮次记录在 `status.md` 的"阶段转换记录"表中

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

补充：hotfix 仍使用同一映射规则；是否 hotfix 由 `_change_level` 表达，不改变 `_phase → _workflow_mode` 的对应关系。

此为已有 pre-commit 表格一致性校验的前置要求。

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

**重置规则**：人工确认后若仍在同一阶段继续修复，`_review_round` 不重置、继续递增；若切换到新阶段，必须重置为 `0`。同一阶段最多再给 2 轮（即第 5 轮）；第 5 轮仍不收敛则强制停止，`_review_round > 5` 时 pre-commit 硬拦截

> **pre-commit 硬拦截**：当 `_review_round > 5` 且 `_run_status != wait_confirm` 时，pre-commit 会硬拦截提交，强制要求切换为 `wait_confirm` 并请求人工确认。此为脚本级强制，不依赖 AI 自觉。

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
1. 完成阶段产出，并在 `deployment.md` 明确目标环境（STAGING / PROD）
2. 执行自我审查，满足收敛条件后：
   - 检查是否涉及高风险例外（API 契约变更 / 数据迁移 / 权限安全 / 不可逆配置）
   - 目标环境为 PROD，或涉及高风险例外 → 先暂停并请求人工确认后再部署
   - 目标环境为 STAGING/TEST，且不涉及高风险例外 → AI 自动部署到验收环境
3. 状态约定：
   - 需人工确认后部署的场景：部署前设置 `status.md` 为 `wait_confirm`
   - 自动部署到验收环境的场景：部署后设置 `status.md` 为 `wait_confirm`，等待人类验收反馈
4. 人类验收反馈：
   - 验收通过 → `status.md` 置完成态（`_change_status: done` + `_run_status: completed`）
   - 验收不通过 → 回到对应上游阶段继续修复（通常 Testing/Implementation）

> 说明：以上为流程规范；当前门禁脚本不会解析 `deployment.md` 的“目标环境”字段做硬分支。

---

## 紧急中断机制

### 触发条件
- P0 Blockers 无法自动修复
- 连续 3 轮不收敛（自动触发，见上方）
- 发现安全/合规重大风险

### AI 行为
1. 立即停止
2. 更新 `status.md`：运行状态=paused 或 wait_confirm
   - `wait_confirm`：需要人工做出决策后才能继续（如选择方案、确认风险、审批推进）
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
