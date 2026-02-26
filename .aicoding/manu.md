# AI 协作框架人工操作手册（manu.md）

## 0. 这份手册怎么用
- 本手册面向“人类负责人”，不是 AI 提示词。
- 目标是两件事：让你知道哪些环节必须人工处理；让你能把本框架稳定迁移到任意业务仓库。
- 推荐阅读顺序：
1. 先读第 1-3 章，建立整体认知。
2. 日常执行时查第 4-6 章（按阶段操作）。
3. 做框架迁移时重点读第 7-9 章（迁移剧本 + 验收 + 回滚）。

## 1. 框架核心原则（人工必须掌握）

### 1.1 单一真相源
- `docs/<版本号>/status.md` 是流程状态唯一真相源。
- 任何阶段、分级、运行状态、完成状态都以 `status.md` front matter 为准。

### 1.2 人工与 AI 的边界
- AI 负责“执行与产出”：写文档、写代码、自审、按门禁推进。
- 人工负责“裁决与授权”：分级拍板、阶段确认、风险决策、生产/高风险部署授权。

### 1.3 阶段推进原则
- `ChangeManagement -> Proposal -> Requirements -> Design -> Planning -> Implementation -> Testing -> Deployment`
- 只允许相邻推进，不允许跳阶段。
- 人工介入期（00-02）必须人工确认推进。
- Deployment 采用“验收环境自动、生产人工”的策略：STAGING/TEST 默认自动部署，PROD/高风险需人工确认。

### 1.4 门禁优先级
- 文本规则 < CC 会话门禁 < Git pre-commit 硬门禁。
- 人工应默认以 pre-commit 结果为最终执行约束。

### 1.5 规则单源（必须统一口径）
- 阶段入口/出口清单单源：`scripts/lib/common.sh`
  - `aicoding_phase_entry_required`
  - `aicoding_phase_exit_required`
- Claude Code 写入期门禁统一入口：`scripts/cc-hooks/pre-write-dispatcher.sh`
  - 合并 CC-1/3/6/7/8，避免多脚本口径漂移
- commit 期硬门禁统一入口：`scripts/git-hooks/pre-commit`
  - 枚举校验、阶段推进、交付关口、结果门禁、内容级校验均在此兜底

## 2. 角色职责（仅 AI + 人类）

| 工作项 | AI | 人类 |
|---|---|---|
| 变更分级建议（major/minor/hotfix） | 负责给建议与依据 | 最终拍板 |
| 阶段产出（文档/代码/测试报告） | 负责生成与更新 | 抽查关键内容 |
| 阶段审查 | 可由不同 AI 工具执行（Claude/Codex） | 确认审查结论是否可接受 |
| 00-02 阶段推进 | 等待确认，不自行推进 | 明确回复“确认进入下一阶段” |
| 风险裁决（安全/迁移/不可逆） | 识别并举手 | 做最终决策 |
| 部署执行 | 默认可自动部署到验收环境 | 仅生产部署做最终确认 |

说明：
- “评审人”通常就是 AI 工具切换视角做审查。
- 人类的核心职责是“决策与授权”，不是逐项执行。

## 3. 关键文件与字段字典（人工速查）

### 3.1 关键文件
- 规则：`ai_workflow.md`（迁移后通常位于 `.aicoding/ai_workflow.md`）
- 阶段定义：`phases/*.md`
- 门禁索引：`hooks.md`
- 实现细节：`hooks_implementation_reference.md`
- 配置：`aicoding.config.yaml`
- 状态文件模板：`templates/status_template.md`
- 运行状态：`docs/<版本号>/status.md`

### 3.2 status.md front matter 字段（必须懂）
- `_phase`：当前阶段。
- `_change_level`：`major / minor / hotfix`。
- `_workflow_mode`：`manual / auto / semi-auto`，必须与阶段匹配。
- `_run_status`：`running / paused / wait_confirm / completed`。
- `_change_status`：`in_progress / done`。
- `_baseline`：基线版本（tag/commit）。
- `_current`：当前代码参考版本。
- `_review_round`：当前阶段审查轮次。

### 3.3 人工最常用检查命令
```bash
# 1) 看当前阶段和状态
rg -n "^_phase:|^_change_level:|^_run_status:|^_change_status:|^_workflow_mode:" docs/v*/status.md

# 2) 安装 hooks（项目初次接入）
bash scripts/install-hooks.sh

# 3) 全量门禁回归
bash scripts/tests/run-all.sh

# 4) 查看门禁告警审计
tail -n 100 .git/aicoding/gate-warnings.log
```

### 3.4 当前门禁结构（人工快速定位）
- CC 写入期：
  - `scripts/cc-hooks/pre-write-dispatcher.sh`（PreToolUse 统一入口）
  - `scripts/cc-hooks/doc-structure-check.sh`（PostToolUse on Write）
  - `scripts/cc-hooks/read-tracker.sh`（PostToolUse on Read）
  - `scripts/cc-hooks/stop-gate.sh`（Stop）
- Git 提交期：
  - `scripts/git-hooks/pre-commit`（硬门禁）
  - `scripts/git-hooks/commit-msg`（提交信息门禁）
  - `scripts/git-hooks/post-commit`（软警告；21 个 warning 脚本 + W23/W24 内置检查）

## 4. 按阶段的人工作业 SOP（重点）

### 4.1 Phase 00 ChangeManagement
人工必须做：
1. 确认 `status.md` 的 `_baseline` 是否正确且可解析到有效 commit/tag。
2. 确认是否需要创建 CR（已测后新增需求必须 CR 化）。
3. 确认 CR 状态是否从 `Idea -> Accepted`（必须完成结构化澄清后才可 Accepted）。
4. 指定审查者并阅读 `review_change_management.md`（自由格式，无结构化模板强制）。
5. 明确回复“确认进入 Proposal”后再推进。

人工不应省略：
- 未确认基线就进入 Proposal。
- 未澄清范围就把 CR 设为 Accepted。

### 4.2 Phase 01 Proposal
人工必须做：
1. 检查“做什么/不做什么/成功指标”是否完整。
2. 检查开放问题是否全部关闭或明确 defer。
3. 确认 proposal 真正反映用户意图。
4. 审阅 `review_proposal.md` 并给推进确认（自由格式，无结构化模板强制）。

确认话术建议：
- `确认 Proposal，通过，进入 Requirements。`

### 4.3 Phase 02 Requirements
人工必须做：
1. 对照 proposal 检查覆盖映射（P-DO/P-DONT/P-METRIC）。
2. 强查禁止项收口：每条“不要/不做/禁止”必须二选一。
   - 固化为 `REQ-C + GWT`
   - 写入 Non-goals（有边界和原因）
3. 审查 `review_requirements.md` 机器可读块：
   - `CONSTRAINTS-CHECKLIST-BEGIN/END`
   - `CONSTRAINTS-CONFIRMATION`
4. 明确确认后才能进入 Design。

### 4.4 Phase 03 Design（默认 AI 自动）
人工通常只在以下场景介入：
- 技术方案有多解且 trade-off 取舍涉及业务成本。
- 触及兼容、迁移、权限、安全等高风险项。
- AI 明确举手请求人类决策。

介入时检查清单：
- 每条 REQ/REQ-C 是否有对应设计落点。
- 回滚路径是否可执行（不是口头“可回滚”）。

### 4.5 Phase 04 Planning（默认 AI 自动）
人工介入触发：
- 计划工时显著超出预期。
- 任务拆分不可执行或依赖关系不清。
- 关键验证命令不可复现。

人工检查：
- 每个任务有 `验证方式`。
- 高风险任务有回滚/开关策略。

### 4.6 Phase 05 Implementation（默认 AI 自动）
人工必须介入的触发条件：
- 连续失败、原因不明。
- 发现跨模块扩 scope。
- 触及禁止变更或安全风险。
- 连续 3 轮不收敛。

人工决策要点：
- 是继续修复、降级拆分，还是停止并回到上游阶段修订。

### 4.7 Phase 06 Testing（默认 AI 自动）
人工重点看：
- 是否覆盖全部 GWT。
- fail/warn 是否归零。
- 是否存在“带问题推进”。

minor 特别检查：
- `review_minor.md` 必须有 `MINOR-TESTING-ROUND` 机器可读块。
- 必须有测试证据（`test_report.md` 或 status 内联 `TEST-RESULT`）。

### 4.8 Phase 07 Deployment（推荐策略：验收环境自动，生产人工）
推荐执行策略：
1. **验收环境（staging/test）**：AI 在自测通过后自动部署，供人类验收。
2. **生产环境（prod）或高风险场景**：先由人类确认再部署。

人类仅需在以下情况介入部署决策：
1. 生产部署。
2. 变更涉及 API/迁移/权限/不可逆配置。
3. 回滚方案不完整或风险不清晰。

部署完成后统一检查：
1. `deployment.md`、主文档同步项、回滚方案是否齐。
2. 完成态一致性：`_change_status=done` 且 `_run_status=completed`。
3. 认知对齐：CC-8 只覆盖 Phase 02-06；Phase 07 主要由 pre-commit 交付关口 + 部署流程规则兜底。

## 5. 三类变更（major/minor/hotfix）人工判定指南

### 5.1 major
适用：
- 新功能、API 契约变化、DB schema、权限安全、跨模块。

人工重点：
- 00-02 充分确认。
- 自动期异常及时裁决。
- 仅在“生产部署/高风险部署”前强审风险与回滚。

### 5.2 minor
关键原则：
- 简化审查形态，不简化理解和验证。
- `proposal.md`、`requirements.md` 仍应存在。
- 触碰 `REQ-C` 必须升级 major。

人工常见误区：
- 误以为 minor 可以省略 proposal/requirements。
- 误以为 review_minor 只写一句自然语言结论就够。

### 5.3 hotfix
边界（任一不满足都不应走 hotfix）：
1. 文件数在 `hotfix_max_diff_files` 内。
2. 不触碰 `REQ-C`。
3. 不触及 API/DB schema/权限安全。

人工操作重点：
- 先确认“是否真紧急且可控”。
- hotfix 不允许阶段推进（保持当前 `_phase`），`_workflow_mode` 仍按 `_phase` 映射填写。
- 完成态必须有 status 内联 `TEST-RESULT`。

## 6. 异常与暂停处理（人工决策矩阵）

| 触发事件 | AI 应做 | 人工必须决定 |
|---|---|---|
| 连续 3 轮不收敛 | 置 `wait_confirm` 并举手 | 继续修复/调整范围/暂停 |
| 连续失败且原因不明 | 停止盲试、上报尝试记录 | 是否回退方案或拆分任务 |
| 安全/合规风险 | 立即停 | 是否中止当前迭代 |
| 需危险 Git 操作 | 不执行，先说明必要性 | 是否授权执行 |
| 实际工作量超计划 | 暂停并建议调整 | 是否改计划或改目标 |

建议人工回复模板：
- `同意继续修复，保持当前阶段，_run_status=running。`
- `同意升级为 major，回到 Design 重新审。`
- `暂停本次变更，待业务确认后继续。`

### 6.1 分阶段确认话术模板（可直接复制）
- ChangeManagement -> Proposal：`确认变更管理阶段完成，进入 Proposal。`
- Proposal -> Requirements：`确认 Proposal 通过，进入 Requirements。`
- Requirements -> Design：`确认 Requirements（含禁止项清单）通过，进入 Design。`
- 自动期遇风险：`先暂停在当前阶段，请给出 A/B 两个可执行方案与风险。`
- 验收环境部署：`请直接部署到验收环境，完成后通知我验收入口。`
- 生产部署：`确认生产部署执行。部署后请同步主文档并更新 status 完成态。`

### 6.2 人工决策 Do/Don't
| Do | Don't |
|---|---|
| 要求 AI 明确列出已尝试方案与失败原因 | 在根因不明时让 AI 继续盲目重试 |
| 对安全/迁移/权限问题先做风险裁决再推进 | 先推进后补风险说明 |
| 对每次“升级 major”给出文字确认 | 默认 AI 可自行升级/降级 |
| 对生产部署给出明确“允许/暂缓”结论 | 把验收环境部署也当成必须人工审批 |

## 7. 框架迁移到具体项目：完整实施剧本（重点）

### 7.1 迁移目标
- 在目标业务仓库复用本框架的流程、文档、门禁能力。
- 保证“项目规则”和“框架规则”一致，避免文档与门禁漂移。

### 7.2 迁移前准备（人工必须完成）
1. 选定目标仓库和默认分支。
2. 确认目标仓库已有最小可运行测试命令。
3. 指定唯一人类决策人（避免多头确认）。
4. 确定试点范围（先 minor，再 major，最后 hotfix）。

### 7.3 落地步骤（可执行）
1. 拷贝框架目录到目标仓库（通常 `.aicoding/`）。
2. 准备 `AGENTS.md` 或 `CLAUDE.md`，声明流程入口。
3. 初始化版本目录：
   - `docs/v1.0/status.md`
   - 必要模板产出文件
4. 安装 hooks：
   - `bash scripts/install-hooks.sh`（若迁移后目录为 `.aicoding/`，则用 `bash .aicoding/scripts/install-hooks.sh`）
5. 调整 `aicoding.config.yaml`（见 7.4）。
6. 运行全量脚本测试：
   - `bash scripts/tests/run-all.sh`
7. 进行一次演练迭代并复盘。

### 7.4 迁移后的个性化配置（最小人工介入版）

#### 7.4.1 拷贝后“必改 5 项”（先改这 5 个就能跑）
```yaml
result_gate_test_command: "<你的测试命令>"
result_gate_build_command: "<你的构建命令; 无构建则填 true>"
result_gate_typecheck_command: "<你的类型检查命令; 无则填 true>"
minor_max_diff_files: <建议 6-15，按项目粒度>
hotfix_max_diff_files: <建议 1-3>
```

为什么只要这 5 项：
1. 前 3 项决定阶段推进时能否真实验证。
2. 后 2 项决定 minor/hotfix 是否经常被误拦截。

#### 7.4.2 建议改 4 项（第二优先级）
```yaml
minor_max_new_gwts: 3-8
entry_gate_mode: warn   # 稳定后可改 block
gwt_id_regex: ^GWT-REQ-C?[0-9]+-[0-9]+$
high_risk_review_patterns: "兼容,回滚,权限,REQ-C,迁移,越权,鉴权,安全"
```

#### 7.4.3 可保持默认（通常先不动）
- `spotcheck_ratio_percent`
- `spotcheck_min`
- `spotcheck_max`
- `deferred_limit_percent`
- `framework_ref`（当前预留字段，门禁未消费）

#### 7.4.4 三种项目模板（直接抄）

后端服务（无前端）：
```yaml
result_gate_test_command: "pytest -q"
result_gate_build_command: "true"
result_gate_typecheck_command: "mypy ."
```

前端项目：
```yaml
result_gate_test_command: "npm test -- --runInBand"
result_gate_build_command: "npm run build"
result_gate_typecheck_command: "npm run typecheck"
```

全栈项目：
```yaml
result_gate_test_command: "npm run test && pytest -q"
result_gate_build_command: "npm run build"
result_gate_typecheck_command: "npm run typecheck && mypy ."
```

#### 7.4.5 最小人工输入模板（填空后直接执行）
先填 5 个值：
1. `TEST_CMD`（测试命令）
2. `BUILD_CMD`（构建命令；无则 `true`）
3. `TYPECHECK_CMD`（类型检查命令；无则 `true`）
4. `MINOR_MAX_FILES`
5. `HOTFIX_MAX_FILES`

执行：
```bash
TEST_CMD='pytest -q'
BUILD_CMD='true'
TYPECHECK_CMD='mypy .'
MINOR_MAX_FILES='10'
HOTFIX_MAX_FILES='3'

sed -i "s#^result_gate_test_command:.*#result_gate_test_command: \"${TEST_CMD}\"#" aicoding.config.yaml
sed -i "s#^result_gate_build_command:.*#result_gate_build_command: \"${BUILD_CMD}\"#" aicoding.config.yaml
sed -i "s#^result_gate_typecheck_command:.*#result_gate_typecheck_command: \"${TYPECHECK_CMD}\"#" aicoding.config.yaml
sed -i "s#^minor_max_diff_files:.*#minor_max_diff_files: ${MINOR_MAX_FILES}#" aicoding.config.yaml
sed -i "s#^hotfix_max_diff_files:.*#hotfix_max_diff_files: ${HOTFIX_MAX_FILES}#" aicoding.config.yaml
```

最后验证：
```bash
bash scripts/tests/run-all.sh
```

### 7.5 迁移演练建议（至少 2 条）

#### 演练 A：minor 正常路径
目标：
- 验证 proposal->requirements->design->planning->implementation->testing->deployment 可走通。

必查点：
- Testing->Deployment 时 `review_minor.md` 含 `MINOR-TESTING-ROUND`。
- commit-msg 对 Active CR-ID 映射生效。

#### 演练 B：hotfix 边界拦截
目标：
- 故意制造越界（文件数超限或触碰 REQ-C）并确认 pre-commit 能拦截。

### 7.6 迁移验收清单（人工签字版）
- [ ] hooks 安装完成，`.git/hooks/pre-commit` 含 `aicoding-hooks-managed`
- [ ] `bash scripts/tests/run-all.sh` 全绿
- [ ] `status.md` front matter 能被正确解析
- [ ] 结果门禁命令在目标项目真实可执行
- [ ] Claude 配置指向 `pre-write-dispatcher.sh`（而非拆分旧脚本）
- [ ] 演练 A 通过（minor）
- [ ] 演练 B 通过（hotfix 越界被拦截）
- [ ] 团队确认“唯一人类决策人”与响应时效
- [ ] 团队明确禁止绕过门禁（制度层）

### 7.7 迁移失败回滚 SOP（人工主导）
触发条件（任一满足建议回滚）：
1. 门禁在目标仓库误拦率过高，影响正常提交流程。
2. 关键命令（test/build/typecheck）短期无法稳定接入。
3. 团队对人工职责边界尚未达成一致。

回滚步骤：
1. 暂时禁用 hooks（保留文件，不删除）：
```bash
mv .git/hooks/pre-commit .git/hooks/pre-commit.aicoding.bak
mv .git/hooks/commit-msg .git/hooks/commit-msg.aicoding.bak
mv .git/hooks/post-commit .git/hooks/post-commit.aicoding.bak
```
2. 保留 `.aicoding/` 文档与脚本，冻结为“仅文档流程”模式。
3. 列出阻塞项（命令适配、阈值校准、组织职责）并明确责任人。
4. 修复后重新执行：
```bash
bash scripts/install-hooks.sh
bash scripts/tests/run-all.sh
```

## 8. 迁移失败高频问题与修复建议

### 问题 1：结果门禁命令不能运行
- 现象：阶段推进时 pre-commit 报 `result gate ... 执行失败`。
- 原因：沿用模板命令，不适配项目栈。
- 处理：用 CI 命令替换，手工验证通过后再提交。

### 问题 2：minor 被频繁误拦截
- 现象：`minor_max_diff_files` / `minor_max_new_gwts` 触发太频繁。
- 原因：阈值过低或项目迭代粒度偏大。
- 处理：基于最近 20 次小改动数据重标定阈值。

### 问题 3：人工确认链断裂
- 现象：00-02 阶段 AI 卡在 `wait_confirm`。
- 原因：协作中没人明确回复“确认推进”。
- 处理：在团队流程中引入固定确认话术和责任人。

### 问题 4：hotfix 滥用
- 现象：明明跨模块/高风险变更仍走 hotfix。
- 原因：把“紧急”当成“可以越过流程”。
- 处理：超边界一律升级 major，保留审计链。

### 问题 5：入口门禁切到 block 后频繁卡住
- 现象：AI 在首次写入阶段产出物时被持续阻断。
- 原因：未先 Read 阶段入口必读，或会话缓存被核心文档变更触发重置。
- 处理：先按 `aicoding_phase_entry_required` 清单补读；稳定后再决定是否把 `entry_gate_mode` 从 `warn` 收紧到 `block`。

## 9. 建议的治理节奏（长期运行）
- 每周：
1. 抽查最近 10 次提交是否遵守门禁。
2. 看一次 `.git/aicoding/gate-warnings.log`。
- 每月：
1. 回顾 minor/hotfix 阈值误拦率。
2. 回顾不收敛案例并同步更新 `ai_workflow.md` / `hooks_implementation_reference.md` 对应规则。
- 每次发版后：
1. 更新主文档（系统功能、技术方案、接口、用户手册、部署记录）。
2. 核对 CR 状态闭环与 tag 对齐。

## 10. 一页式人工值班清单（可复制）
1. 看 `status.md`：确认 `_phase/_change_level/_run_status`。
2. 看审查结论：P0/P1 是否已收敛。
3. 看风险触发：是否命中安全/迁移/权限/不可逆。
4. 看部署条件：`deployment.md`、测试证据、回滚方案是否齐。
5. 给出明确裁决：
   - `确认进入下一阶段`
   - `同意部署`
   - `暂停并回到某阶段修订`

## 11. 手册维护规则（建议）
- 本手册应与以下文件同步维护：
  - `ai_workflow.md`（迁移后通常 `.aicoding/ai_workflow.md`）
  - `hooks.md`
  - `aicoding.config.yaml`
- 发生以下变更时必须更新本手册：
1. 增减硬门禁项。
2. 状态字段、枚举值或阶段推进规则变化。
3. minor/hotfix 边界变化。
4. 迁移流程新增强制步骤。
- 建议每次框架发布前执行一次“文档一致性走查”，确保“文档说法 = 脚本行为”。
