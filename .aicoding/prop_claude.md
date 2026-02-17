# `.aicoding/` 框架优化建议（Claude 视角）

> 来源：基于 `enhance_temp.md` 分析、`worry.md` 10 条顾虑、多轮讨论、外部走查反馈、以及脚本可移植性分析的综合建议。
> 目的：作为用户反思与后续讨论的输入材料，不直接修改现有文件。
> 日期：2026-02-15（走查反馈 + 脚本移植性分析 + Codex 走查 + 深度交叉分析 + 人工走查反馈后修订 + Codex 二次走查反馈吸收 + Codex 全面走查建议吸收）
> 引用说明：本文档中的 `文件:行号` 引用为分析时点快照，后续迭代中行号可能漂移。落地实施时应以锚点/函数名为准。

---

## 一、框架现状评估（走查校准）

> 走查纠正了初版建议中的几处事实性偏差；脚本移植性分析揭示了新的结构性缺口。以下先厘清"已有什么"和"真正缺什么"，避免重复造轮子。

### 已有且有效的机制

1. **对抗性审查已是强制项**：`review_template.md:127` 明确 REQ-C 的反向假设为强制（🔴 MUST），`SPOT_CHECK_GWTS` 也是强制字段（`:133`），缺少即门禁拦截。
2. **REQ_BASELINE_HASH 已只算 GWT 行**：`review_gate_common.sh:60` 的实现 `grep -oE 'GWT-REQ-C?[0-9]+-[0-9]+:.*'` 已忽略说明性文字，改错别字不触发全量重审。
3. **禁止项查漏已是人工确认条款**：`02-requirements.md:82-89` 已要求 `CONSTRAINTS-CHECKLIST` + `CONSTRAINTS-CONFIRMATION`，且门禁校验 A/B 分类和 REQ-C 映射完整性。
4. **增量审查机制已定义**：`review_template.md:139-143` 已支持 `REVIEW_SCOPE: incremental` + `CARRIED` 标记 + REQ-C 禁止 carry-over。
5. **证据非空/非占位已是硬门禁**：`review_gate_common.sh:455-476` 在阶段出口硬拦截证据列为空/占位的情况（`return 1`），`w22-review-evidence.sh` 是额外的 warning 层。
6. **增量 carry-over 已有严格验真**：`review_gate_common.sh:650-674` 校验 `CARRIED_FROM_COMMIT` 合法性、前次审查 pass、FAIL/WARN 为 0、REQ_BASELINE_HASH 一致性。

### 真实缺口（走查确认）

1. **Goodhart 盲区——"格式完美但内容空洞"**：证据列非空/非占位检查已是硬门禁（`review_gate_common.sh:455-476`，阶段出口触发），`w22-review-evidence.sh` 是额外的 warning 层。但硬门禁只能验证"有证据"，无法验证"证据是否真的支持 GWT 判定结论"——AI 可以写 `src/xx.ts:42` 但该行代码根本不支持 GWT 语义。这是自动化验证的天花板。
2. **"没写进 requirements 的不要 X"无法被门禁发现**：自动机制只能对"被记录的真相源"负责。对话中说过但没固化到文档的禁止项，再强的门禁也拦不住。
3. **迭代摩擦偏大**：GWT 行改了就要求重审，缺少"结构性变更 vs 澄清性变更"的可执行区分，以及"只重验受影响 GWT，其余可沿用"的门禁落地规则。
4. **人类参与是被动的**：`SPOT_CHECK_GWTS` 只是"标注"，没有强制人类真的抽检，更没有把抽检结果反馈为机器可读的门禁输入。
5. **门禁脚本的运行时错误缺少分级处理**：30 个 hook 脚本（CC-hooks 10 + Git-hooks 3 主脚本 + 17 warning 模块）已有 24 个测试文件（测试规模 proxy，非严格覆盖率），测试基础较好。但脚本自身的运行时错误（如依赖文件缺失、正则匹配异常）没有分级处理机制——关键门禁和非关键检查的错误行为一样，都是 hard block。这在脚本 bug 场景下会导致错杀，开发者被迫 `--no-verify` 绕过，进而废掉整个门禁体系。
6. **脚本无配置层，跨项目移植靠"整体复制"**：`common.sh` 用动态检测（`aicoding_detect_version_dir`）而非硬编码路径，脚本间通过 `${SCRIPT_DIR}/../lib/` 相对引用——目录结构差异不是问题。但阈值和规则（DEFERRED 上限、抽检数量公式、GWT-ID 格式正则、YAML 必填字段列表等）直接写死在脚本里，没有 `aicoding.config.yaml` 或类似的配置机制。这意味着：所有项目要么用完全相同的规则，要么 fork 脚本源码——后者会导致版本漂移，测试基线也需要跟着 fork。
7. **状态字段缺少枚举校验**：`pre-commit:290-300` 只校验 `_workflow_mode`/`_run_status`/`_change_status`/`_phase` 字段存在且非空，不做枚举校验。拼写错误（如 `_workflow_mode: manul`）会通过门禁，导致下游门禁静默跳过。`hooks.md:1091` 已定义了枚举值，但实现未跟进。需建立"单一真相源"（建议放在 `scripts/lib/common.sh` 常量或映射表），用脚本生成/校验 `hooks.md` 与 `templates/status_template.md` 中的枚举文案，避免人工漂移。
8. **脚本解析过度依赖固定中文标题**：`review_gate_common.sh:135` 用 `/^### 2\.1[[:space:]]+需求-设计追溯矩阵/` 匹配，`:196` 用 `/^##[[:space:]]+需求覆盖矩阵（GWT/` 匹配。模板标题改一个字就会导致误报或漏报。应改为按稳定锚点（如 `<!-- TRACE-MATRIX-BEGIN -->`）解析。
9. **Minor/Hotfix 流程未落地到硬门禁**：`ai_workflow.md:12` 定义了 Minor 合并阶段，但 `pre-commit:331` 的阶段出口硬门禁仍按完整产物检查，没有按 `_workflow_mode` 区分。Minor 模式名义上简化了流程，实际执行仍重，拉低效率并诱发绕过。
10. **规范文档与实现存在治理漂移**：`hooks.md` 写"软警告 13 个"，实际 `warnings/` 目录已有 17 个脚本（w06-w22）。这类漂移会持续侵蚀文档的可信度。
11. **阶段降级（backward transition）被静默允许**：`pre-commit:321` 的逻辑 `[ "$NEW_RANK" -le "$OLD_RANK" ] && continue` 在阶段回退时跳过所有出口检查。正常回退修复是合理的，但大幅降级（如 Testing→Proposal）会跳过所有中间阶段的出口检查，且 `_phase` 被意外改错时无任何告警。
12. **plan.md 验证命令检查诱发 Goodhart**：`pre-commit:410-434` 要求每个任务都有 backtick 包裹的验证命令，但"编写文档"、"配置环境变量"等任务没有自然的命令行验证方式，迫使 AI 编造无意义的验证命令来通过门禁。
13. **收敛最大轮次无门禁强制**：`ai_workflow.md:124` 规定连续 3 轮不收敛要暂停，但这只是 AI 行为规范，没有门禁脚本强制。AI 忽略规则或 prompt 被截断时可无限循环自审。
14. **commit-msg 多 CR 关联逻辑漏洞**：`commit-msg:42-45` 在有多个 Active CR 时，commit message 只需包含其中任意一个即可通过。一个 commit 可以只关联 CR-A 但实际修改了 CR-B 的文件，追溯链断裂。
15. **post-commit warning 无汇总输出**：`post-commit:26` 在子 shell 中执行 17 个 warning 模块，各自独立输出，开发者看到一堆 ⚠️ 但没有汇总（如"本次提交触发 3 个警告，其中 1 个与 REQ-C 相关"）。
16. **Phase 00 CR 影响分析仅有 warning 级校验，尚无 pre-commit 硬门禁**：CR 模板要求"二元影响分析"（是/否），当前仅有 warning 级提示，尚无 pre-commit 硬门禁。CR 可以声称"不影响 API 契约"但实际改了 API，硬门禁不会拦截。

---

## 二、改造建议（按优先级排序，从高杠杆到重工程）

### P-1：门禁脚本错误分级处理（前置项——防止错杀废掉门禁体系）

> 对应缺口 5+6。所有 P0-P2 的门禁增强都依赖脚本本身的正确性；如果脚本有 bug 且一律 hard block，新增的门禁只会制造更多错杀。

#### 问题

当前 30 个 hook 脚本已有 24 个测试文件，测试基础较好。但硬门禁脚本（pre-commit 中的 gate 逻辑、CC-hooks 中的 PreToolUse 拦截）自身的运行时错误没有分级处理——无论是核心校验逻辑（如 GWT 覆盖率、证据完整性）还是辅助性硬检查（如格式校验、命名规范），出错都是同样的 hard block。注意：post-commit 的 warning 层（17 个 w*.sh 模块）本身已在子 shell 中执行且不阻断提交（`post-commit:21-27`），不属于 hard block 范畴。

同时，脚本没有配置层：阈值和规则硬编码在源码中，跨项目移植只能"整体复制"或"fork 改源码"。

#### 方案

**错误分级策略（替代一刀切 fail-open）**：

一刀切 fail-open 会把"错杀"换成"漏放"，与提升交付质量的目标冲突。正确做法是分级：

- **关键门禁 fail-closed**：核心校验逻辑（GWT 覆盖率、证据非空、REQ_BASELINE_HASH 一致性、REQ-C 外键校验）的运行时错误仍然 hard block。这些是交付质量的底线，宁可错杀不可漏放。
- **非关键检查 fail-open + 持久化告警**：辅助检查（格式建议、命名规范、warning 类脚本）的运行时错误降级为 warning，但必须写入持久化日志（`.git/aicoding/gate-warnings.log`），防止 fail-silent。当前 `warn` 函数只是 `echo >&2`，终端关闭后信息即丢失。选择 `.git/aicoding/` 而非 `.aicoding/logs/` 是为了避免日志文件污染工作区、引入 diff 噪音和提交污染。
- **统一执行包装器 `run_gate`**：当前 `pre-commit` 等单体脚本内同时包含不同重要度的检查项（阶段出口、plan 验证命令、格式检查等），且大量 inline 检查逻辑并非独立函数，仅做"函数内标记"会导致一部分检查被分级、一部分仍是硬编码 `exit 1`，行为不可预测。正确做法是引入统一执行包装器：
  - 所有门禁检查通过 `run_gate <level> <name> <fn>` 调用，禁止在新代码里直接 `exit 1`
  - `run_gate` 内部根据 level 决定 fail-closed 还是 fail-open + 日志
  - 示例：`run_gate critical "gwt-coverage" check_gwt_coverage` vs `run_gate advisory "naming-convention" check_naming_convention`
  - **渐进式推进**：第一轮只改 3 个关键路径（阶段出口、交付关口、review 摘要校验），验证分级策略可行后再扩展到其余检查项
  - 追加一个"分级一致性测试"，扫描 `pre-commit` 中裸 `exit 1` 的门禁语句，确保新增检查都走 `run_gate`

#### 价值

- 分级处理避免了一刀切 fail-open 的"漏放"风险，也避免了一刀切 fail-closed 的"错杀"风险
- 统一执行包装器 `run_gate` 确保所有检查行为可预测——不会出现"同类错误有时阻断、有时放行"的不一致
- 渐进式推进（先 3 个关键路径）降低上线风险，验证后再扩展
- 持久化日志写入 `.git/aicoding/` 私有目录，防止 fail-silent 的同时不污染工作区
- 为后续 P0-P2 的门禁增强提供可靠的错误处理基础设施
- 在两种移植场景下都有用：原样复制时保证行为一致，fork 修改时分级标记指导哪些可以调整

#### 落地定义

- **Exit Criteria**：`run_gate` 包装器已覆盖 3 个关键路径（阶段出口、交付关口、review 摘要校验）；分级一致性测试通过（无裸 `exit 1` 新增）；`.git/aicoding/gate-warnings.log` 可正常写入
- **前置依赖**：无（P-1 是所有后续 P 项的基础设施）
- **Rollback Trigger**：上线后 1 周内 advisory 级检查的 fail-open 导致生产事故（如漏放的缺陷影响到用户可见功能或数据完整性）。注意：advisory 级别的设计意图就是允许偶发漏放，因此单纯的"漏放 > 0"不构成回滚条件——只有漏放导致实际损害时才触发回滚

---

### P-0.8：状态字段枚举统一（前置项——P-0.5 和 P2 的共同依赖）

> 对应缺口 7 + 即时修复第 1 条。P-0.5（`_change_level` 字段）和 P2（变更分级重审）都依赖枚举校验机制就绪，但"枚举统一"此前只是即时修复的一部分，没有独立的 Exit Criteria 和追踪。将其升级为独立前置工作项，确保依赖链可管理。

#### 问题

`pre-commit:290-300` 只校验状态字段存在且非空，不做枚举校验。`hooks.md:1091` 已定义枚举值，但实现未跟进。拼写错误（如 `_workflow_mode: manul`）会通过门禁，导致下游门禁静默跳过。枚举定义分散在 `hooks.md`、`status_template.md`、脚本源码三处，人工维护必然漂移。

#### 方案

1. **单一真相源**：所有枚举值定义集中到 `scripts/lib/common.sh` 的关联数组或常量中
2. **校验脚本**：`pre-commit` 读取 `common.sh` 枚举定义，对 `_workflow_mode`、`_run_status`、`_change_status`、`_phase`、`_change_level` 做枚举校验
3. **一致性测试**：新增测试脚本，校验 `hooks.md` 和 `status_template.md` 中的枚举文案与 `common.sh` 一致
4. **迁移策略**：`_change_level` 按 P-0.5 的三阶段迁移执行（兼容期字段缺失仅 warning）；其余字段直接 hard block（已有字段，不存在兼容问题）

#### 落地定义

- **Exit Criteria**：`common.sh` 枚举常量已定义；`pre-commit` 枚举校验已实现；一致性测试通过；`_change_level` 兼容期 warning 逻辑就绪
- **前置依赖**：P-1（枚举校验走 `run_gate`，新字段兼容期走 `run_gate advisory`）
- **Rollback Trigger**：枚举校验误拦合法值（说明枚举定义不完整）

---

### P-0.5：Minor 门禁配置落地（效率瓶颈——决定框架日常可用性，hotfix 待规范补齐后扩展）

> 对应缺口 9+11。当前 Minor 简化流程形同虚设：`ai_workflow.md:12` 定义了 Minor 合并阶段，但 `pre-commit:331` 的阶段出口硬门禁仍按完整产物检查，没有按变更分级区分。大部分日常变更属于 Minor（具体比例待实际数据验证），但都被迫走 Major 流程，开发者会用 `--no-verify` 绕过，整个门禁体系就废了。

#### 问题

`pre-commit:331` 的 `case "$OLD_PHASE"` 对 Minor 和 Major 一视同仁——一个 CSS bug 修复也要走完整的 8 阶段产物检查（design.md、review_design.md、plan.md 等）。这不是"即时修复"级别的问题，而是框架在日常开发中的可用性瓶颈。

#### 方案

**前置澄清**：`_workflow_mode` 的枚举是 `manual/semi-auto/auto`（`status_template.md:17`），语义是"工作流自动化程度"，不应复用来承载变更分级。新增独立字段 `_change_level`，专门用于门禁规则集切换。

**`_change_level` 三阶段迁移策略**（避免新字段引入大面积拦截）：

- Phase 1（兼容期，先落 `major|minor` 两态）：
  - `status_template.md` 新增 `_change_level` 字段，枚举值 `major|minor`（默认 `major`）
  - `pre-commit`：字段缺失仅 warning，不阻断；字段存在时按值切换规则集
  - 现有项目不受影响，新项目自然采用
  - **不引入 `hotfix`**——`ai_workflow.md` 仅定义了 Major/Minor，hotfix 的触发条件、最小产物、回滚责任均未定义，贸然引入会造成语义灰区
- Phase 2（强制期）：
  - 字段缺失或非法值改为 hard block
  - 同步更新 hooks 文档、模板示例、测试基线
  - 切换时机：当所有活跃项目已自然迁移到 Phase 1 后
- Phase 3（hotfix 扩展，待规范补齐后启用）：
  - 前置条件：`ai_workflow.md` 补充 hotfix 流程定义（触发条件、允许跳过项、强制回滚字段、测试最低要求）
  - `_change_level` 枚举扩展为 `major|minor|hotfix`
  - `hooks.md` 与 `status_template.md` 同步字段定义后，才进入 hard block

1. `status_template.md` YAML front matter 新增 `_change_level` 字段，Phase 1 枚举值 `major|minor`
2. `pre-commit` 阶段出口门禁读取 `_change_level` 字段，按分级切换规则集：
   - `major`：完整产物检查（现有逻辑不变）
   - `minor`：最小必需产物——
     - `status.md`：变更摘要 + 验收标准存在
     - 测试证据：`test_report.md` 存在，或 `status.md` 中包含 `<!-- TEST-RESULT-BEGIN -->` 标记（二选一）
     - 审查记录：单文件 `review_minor.md`（不要求 `review_implementation.md` / `review_testing.md`），必须包含 `REVIEW_RESULT` 和 `REQ_BASELINE_HASH` 字段（详见下方 Minor 审查简化说明）
     - **spotcheck 豁免**：Minor 变更不要求独立的 `spotcheck_<stage>_<cr-id>.md`（P0 的 spotcheck 硬门禁仅对 Major 变更强制）。理由：Minor 的 GWT 数量少（通常 ≤ 5），review_minor.md 的证据表已覆盖全量 GWT，人类抽检的边际价值低于 Major。但如果 Minor 变更涉及 REQ-C（禁止项），仍需 spotcheck——此时误标防护（见下方）会触发告警，提示应升级为 Major
3. CC-8（阶段出口门禁）同步适配 `_change_level`
4. CC-3（文档作用域控制）的白名单按 `_change_level` 切换

**Minor 测试产物形态**：`ai_workflow.md:28` 明确允许 Minor 的"简化版测试报告可内联在 status.md 中"。因此 Minor 门禁不应要求独立的 `test_report.md` 存在，而应检查以下任一条件满足：
- `test_report.md` 存在（独立报告），或
- `status.md` 中包含测试结果章节标记（如 `<!-- TEST-RESULT-BEGIN -->`）

这需要先在 `ai_workflow.md` 的 Minor 流程中明确测试产物的机器可读标记格式，再写门禁——避免"规范与门禁互相打架"。

**Minor 审查简化说明**：Minor 变更不要求 `review_implementation.md` / `review_testing.md`（这两个只对 Major 强制），改为单文件 `review_minor.md`，保留必填机器可读块（`REVIEW_RESULT`、`REQ_BASELINE_HASH`、证据表），但不要求完整阶段文档结构。这进一步降低 Minor 的文档摩擦，避免"为了过门禁补文档"诱发 `--no-verify`。先灰度观察 Minor 平均提交耗时与绕过率，再决定是否收紧。

`review_minor.md` 最小模板结构：
```markdown
<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_RESULT: pass|fail
REQ_BASELINE_HASH: <hash>
REVIEWER: AI
REVIEW_AT: YYYY-MM-DD
<!-- REVIEW-SUMMARY-END -->

## 变更验证

| GWT-ID | RESULT | EVIDENCE_TYPE | EVIDENCE |
|--------|--------|---------------|----------|
| ... | PASS/FAIL | CODE_REF/TEST_OUTPUT/... | ... |

## 备注（可选）
```

**`_change_level` 误标防护**：`_change_level` 是自声明字段，存在 Major 变更标成 Minor 来跳过完整门禁的博弈向量——这比 `--no-verify` 更隐蔽，因为它不绕过门禁，而是让门禁降级执行。防护措施：
- post-commit warning 做"变更规模与声明级别一致性"启发式检查：
  - `_change_level: minor` 但 diff 文件数 > 10 → 告警
  - `_change_level: minor` 但新增 GWT 数 > 5 → 告警
  - `_change_level: minor` 但涉及 REQ-C 变更 → 告警
- 阈值可通过 `aicoding.config.yaml`（P3）调整，初始值硬编码
- 告警写入 `.git/aicoding/gate-warnings.log`，CI 侧可聚合统计误标率

#### 价值

- 直接决定框架在日常开发中的可用性——如果 Minor 流程不落地，开发者会绕过整个门禁体系
- 改动量中等（pre-commit case 分支 + CC-8 适配），但杠杆极高
- 与 P-1 的错误分级处理互补：P-1 防止门禁错杀，P-0.5 防止门禁过重

#### 成效 KPI

- Minor 变更的门禁绕过率（目标：< 5%）
  - **主指标（CI 侧）**：CI 重跑门禁通过率——CI 对每个 commit 重跑 pre-commit 检查，未通过即视为本地绕过。CI 是全新克隆环境，不依赖 `.git` 私有日志，采集稳定可靠
  - **⚠️ 前提条件**：此指标依赖 CI 管道已建立且具备重跑 pre-commit 检查的能力。如果当前项目无 CI，主指标从第一天起不可观测，应先以辅助指标（本地日志）过渡，同时将 CI 管道搭建列为 P-1 的并行任务
  - **辅助指标（本地可选）**：本地 `.git/aicoding/gate-pass.log` 记录正常通过门禁的 commit hash，可通过 `git log --format=%H | while read h; do ...` 脚本批量检查缺失记录。注意此指标仅限本地开发环境，不可跨环境传递
  - 统计周期：每周
- Minor 变更的 commit 到 done 耗时（目标：比 Major 减少 60%+）
  - 采集口径：`status.md` 阶段切换时间戳（Proposal→Done）
  - 统计周期：每个迭代

#### 落地定义

- **Exit Criteria**：`_change_level` 字段已加入 `status_template.md`；`pre-commit` 按 `major|minor` 切换规则集；Minor 使用 `review_minor.md` 单文件审查；兼容期测试通过
- **前置依赖**：P-1（`run_gate` 包装器就绪，Minor 门禁的新检查项走 `run_gate`）；P-0.8（枚举单一真相源 + `_change_level` 兼容期逻辑就绪）
- **Rollback Trigger**：Minor 绕过率 > 10%（说明门禁仍过重）；或 Minor 交付后缺陷率显著高于 Major（说明门禁过松）

---

### P0：人类抽检硬门禁化（A 档——最小改动，立刻抗 Goodhart）

> 对应缺口 1+4。这是改动量最小但杠杆最高的改造：把"标注抽检"变成"交付关口硬门禁"。

#### 问题

当前 `SPOT_CHECK_GWTS` 是强制标注（缺少即拦截），证据列非空/非占位也已是硬门禁（`review_gate_common.sh:455-476`）。但人类是否真的抽检了、结果如何，没有任何机器可读的记录。硬门禁能保证"有证据"，但无法保证"证据真的支持 GWT 判定结论"。

人类抽检是对抗 Goodhart 效应的最后一道防线——但当前这道防线是纸糊的。

#### 方案

在 `_run_status=wait_confirm` 或 `_change_status=done` 时（复用 W16/W22 的触发信号），要求存在机器可读的 `HUMAN_SPOTCHECK` 结果块。

**独立文件方案（推荐）**：抽检结果存放在独立文件 `spotcheck_<stage>_<cr-id>.md`（如 `spotcheck_implementation_CR-20260215-001.md`；无 CR 时用 `spotcheck_<stage>_main.md`），而非嵌入 review 文件。理由：
- review 文件保持 AI 自审的职责边界，不与人类填写内容混杂
- spotcheck 文件是纯人类填写的，不会被 AI 的格式生成问题污染
- 门禁脚本可以独立检查两个文件，逻辑更清晰
- review_template.md 已有 200+ 行，避免进一步膨胀
- CR-ID 后缀防止多 CR 并行时文件覆盖或混写，历史追溯清晰
- 每次基线变化必须新建 spotcheck 文件，禁止复写历史

**文件归档策略**：spotcheck 文件会随阶段和 CR 数量增殖（3 阶段 × 2 CR × 2 次基线变化 = 12 个文件）。为防止 docs 目录嘈杂：
- 项目交付（`_change_status: done`）后，将当前 CR 的所有 spotcheck 文件移入 `docs/archive/<cr-id>/` 目录
- 归档操作可由 post-commit hook 在检测到 `_change_status: done` 时自动执行（advisory 级，失败不阻断）
- `docs/archive/` 目录纳入 `.gitignore` 的可选项——如果团队需要保留审计记录则不忽略，如果只需要当前活跃文件则忽略

文件格式：

```text
<!-- HUMAN-SPOTCHECK-BEGIN -->
SPOTCHECK_FILE: spotcheck_<stage>_<cr-id>.md
SPOTCHECK_REVIEWER: <human name>
SPOTCHECK_AT: YYYY-MM-DD
SPOTCHECK_SCOPE: REQ-C:all + SPOT_CHECK_GWTS
SPOTCHECK_BASELINE: <commit-hash>
REQ_BASELINE_HASH: <hash>
| GWT-ID | RESULT | METHOD | NOTE |
|--------|--------|--------|------|
| GWT-REQ-C001-01 | PASS | UI_VISUAL | 已目视确认空/有数据两种状态 |
| GWT-REQ-001-03 | FAIL | RUN_CMD | 普通用户多了一列"内部备注" |
SPOTCHECK_RESULT: pass|fail
<!-- HUMAN-SPOTCHECK-END -->
```

门禁按 review 摘要块中的 `SPOTCHECK_FILE` 指针定位文件，而非猜测文件名。

**基线绑定**：`SPOTCHECK_BASELINE`（抽检时的 commit hash）和 `REQ_BASELINE_HASH`（抽检时的需求基线 hash）用于防止复用旧抽检结果。门禁在交付关口校验这两个字段与当前基线一致，不一致则要求重新抽检。

#### 门禁规则

- **适用范围**：`_change_level: major` 的变更强制执行；`_change_level: minor` 的变更豁免（除非涉及 REQ-C，此时误标防护会触发告警提示升级）
- 覆盖范围：所有 REQ-C 的 GWT（强制）+ `SPOT_CHECK_GWTS` 中列出的条目（强制）
- `SPOTCHECK_RESULT=fail` → 硬拦截交付
- `spotcheck_<stage>_<cr-id>.md` 不存在或覆盖不全 → 硬拦截交付
- 实现：新增一个 gate 脚本，通过 review 摘要块中的 `SPOTCHECK_FILE` 指针定位文件并解析覆盖完整性（与 review 文件的 gate 脚本独立）

#### 价值

- 改动量：1 个新脚本 + 1 个 spotcheck 模板文件 + review_template 增加抽检指南（不增加机器可读块）
- 直接堵住"AI 自审自过"的最大漏洞
- 不增加 AI 侧的工作量（AI 不生成 spotcheck 文件），只要求人类在交付前做一次有记录的抽检
- review 文件和 spotcheck 文件职责分离，降低模板复杂度累积风险

#### 成本基线

典型项目的抽检规模由公式 `min(5, max(1, ceil(GWT_TOTAL*0.1)))` 决定：
- 小项目（10-20 条 GWT）：抽检 1-2 条 + 全部 REQ-C 的 GWT
- 中型项目（30-50 条 GWT）：抽检 3-5 条 + 全部 REQ-C 的 GWT
- REQ-C 通常 1-3 个，每个含 2-4 条 GWT

实际人力成本：每次交付多填一个 `HUMAN-SPOTCHECK` 块、实际验证 3-10 条 GWT。对于有 UI 的项目，大部分验证是"打开页面目视确认"，单次抽检耗时可控。

#### 残余风险

人类抽检本身可能流于形式（"橡皮图章"）——填了 PASS 但没真的看。当前方案无法从机器层面区分"认真抽检"和"走过场"。缓解措施：
- 要求 `METHOD` 列填写具体验证手段（`UI_VISUAL` / `RUN_CMD` / `LOG_CHECK`），而非笼统的"已确认"
- 抽检结果积累后，可做"抽检有效性回溯"——如果某人的抽检从未发现问题，可能需要关注
- 这是管理问题而非工具问题，框架能做的是降低抽检门槛（验证指南）+ 留下可审计的记录

#### 对 review_template.md 的影响

仅在"建议人类抽检"章节增加抽检验证指南（帮助人类高效抽检），不增加新的机器可读块。`HUMAN-SPOTCHECK` 块定义移至独立的 `spotcheck_template.md`：

```markdown
### 建议人类抽检（SPOT_CHECK）

#### GWT-REQ-C001-01（抽检理由：禁止项，证据依赖 UI 截图）
- 验证方式：以管理员角色登录 → 打开订单列表页 → 确认页面不出现「描述性卡片」
- 预期结果：页面无该卡片（空状态/有数据状态均需确认）
- 快速验证：打开浏览器 → 访问 /orders → 目视确认
- AI 给出的证据：截图链接 xxx（请对比实际页面）
```

抽检锚点选择策略：
- 优先选择 REQ-C（禁止项）——AI 最容易"用设计意图合理化"的地方
- 优先选择证据类型为 CODE_REF 的行为性 GWT——运行时行为只给代码引用说明证据可能不充分
- 避免选择纯静态/配置类 GWT——CODE_REF 通常足够可靠，抽检价值低

#### 落地定义

- **Exit Criteria**：`spotcheck_<stage>_<cr-id>.md` 模板已创建；gate 脚本可解析 `SPOTCHECK_FILE` 指针并校验覆盖完整性；交付关口硬拦截 spotcheck 缺失/FAIL 的 commit
- **前置依赖**：P-1（gate 脚本走 `run_gate critical`）
- **Rollback Trigger**：抽检流程导致交付周期增加 > 30%（说明抽检成本过高，需简化）

---
### P1：上游需求质量补强（B 档——补上游质量 + 证据升级）

> 对应缺口 2。解决"没写进 requirements 的不要 X"——把意图前移并固化为可机读、可追溯的输入。

#### 问题

自动门禁只能对"被记录的真相源"负责。当前框架在 Requirements 阶段已有 `CONSTRAINTS-CHECKLIST`（`02-requirements.md:82-89`），但其来源依赖"对话中出现的不要/不做..."——而用户实际在多个 AI 工具间多轮工作，对话回溯不现实。

#### 方案 B-1：Proposal 阶段引入结构化意图清单（Do/Don't）

在 `proposal_template.md` 的"范围界定"章节后，增加结构化的"验收锚点"。

**ID 前缀策略**：不引入 ANCHOR-DO/DONT/METRIC 三种新前缀（`STRUCTURE.md` 已定义 9 种 ID 前缀，再加 3 种会增加 AI 认知负担和出错概率）。但完全不编号的纯文本模糊匹配风险较大（措辞改写即导致误报/漏报），因此采用折中方案：Proposal 阶段使用轻量级临时 ID `P-DONT-01`、`P-DO-01` 等，仅用于 Proposal→Requirements 的对齐追溯，到 Requirements 阶段正式编号为 REQ-/REQ-C/GWT- 后临时 ID 即废弃。

```markdown
## 关键验收锚点（Proposal 阶段初步明确）

> 这些锚点将在 Requirements 阶段细化为正式的 REQ/REQ-C/GWT。
> 临时 ID（P-DO/P-DONT）仅用于 Proposal→Requirements 的追溯对齐，不进入下游。

### 必须做到（Must Have）
- [ ] P-DO-01: ...（用户可感知的关键行为/结果）

### 绝对不能出现（Prohibitions）
- [ ] P-DONT-01: ...（明确的禁止项，将固化为 REQ-C）

### 成功指标（可量化）
- [ ] P-METRIC-01: ...
```

门禁校验：Requirements 阶段推进到 Design 前，脚本验证 `proposal.md` 中每个 `P-DONT-*` 都在 `CONSTRAINTS-CHECKLIST` 中以 `CLASS=A`（映射到 REQ-C）或 `CLASS=B`（明确写入 Non-goals）出现，差集为空。匹配方式：按 `P-DONT-*` ID 精确匹配（`CONSTRAINTS-CHECKLIST` 的 `SOURCE` 列引用 `proposal.md P-DONT-01`）。

对 `phases/01-proposal.md` 的影响：
- 行为准则增加："引导用户明确'绝对不能出现'的事项，记录到验收锚点 > Prohibitions"
- 质量门禁增加："验收锚点章节已填写（至少 Must Have 和 Prohibitions 各 1 条）"

**形式化风险**：对于简单改动（如修复一个 CSS bug），强制要求 Must Have 和 Prohibitions 各至少 1 条可能诱发"凑数式填充"，反而增加 Goodhart 行为。建议：门禁仅要求"验收锚点章节存在且非空"，不强制最低条数；或对小型变更（如 GWT 总数 ≤ 5）豁免 Prohibitions 最低条数要求。

#### 方案 B-2：需求捕获从"对话回溯"转为"文档沉淀 + 人工确认"

- §7.0 的"来源覆盖"要求中，"对话中出现的不要/不做..."降级为"建议"而非"必须"（跨工具对话无法保证完整提取）
- 核心保障从"AI 提取完整性"转移到"人类确认完整性"
- `CONSTRAINTS-CHECKLIST` 的 `SOURCE` 列：文档引用（`proposal.md §X`、`requirements.md REQ-C001`）为必填，对话引用为可选补充
- Requirements → Design 推进前，人类必须回答显式问题："除了文档中已列出的 REQ-C，是否还有其他'不要做/不允许出现'的要求？"

#### 方案 B-3：证据从"非空"升级为"CODE_REF 可验证引用"

证据非空/非占位的硬拦截已在 `review_gate_common.sh:455-476` 实现。需要补强的是 CODE_REF 类证据的可验证性：
- 校验 `CODE_REF` 类证据的文件路径存在（`test -f`）
- 校验行号有效（文件行数 >= 引用行号）
- 禁止占位符模式（`<placeholder>`、`...`、`TODO`）——这部分已由现有硬门禁覆盖，无需重复

注意：代码在 review 之后还会变（commit 间行号漂移），所以验证时机应在 pre-commit 时，而非 review 生成时。

#### 价值

- B-1 把"禁止项捕获"前移到 Proposal 阶段，用户思维最活跃时捕获效率最高
- B-2 让 `CONSTRAINTS-CHECKLIST` 的来源更可靠（文档引用 > 对话引用）
- B-3 堵住"证据非空但无效"的漏洞，与 P0 的人类抽检形成双保险
- 形成完整链路：Proposal P-DONT → Requirements REQ-C → Review GWT 判定 → Human SPOTCHECK

#### 落地定义

- **Exit Criteria**：`proposal_template.md` 含验收锚点章节；`P-DONT-*` → `CONSTRAINTS-CHECKLIST` 追溯门禁通过；CODE_REF 文件路径/行号校验脚本就绪
- **前置依赖**：P-0.5（`_change_level` 就绪，B-1 的形式化风险豁免依赖变更分级）；P0（B-3 证据升级与 spotcheck 互补）
- **Rollback Trigger**：P-DONT 追溯门禁误拦截率 > 5%（说明匹配规则过严）

---
### P2：变更分级重审优化（降低迭代摩擦）

> 对应缺口 3。当前缺少"结构性变更 vs 澄清性变更"的可执行区分。

#### 现状

- `REQ_BASELINE_HASH` 已基于 GWT 行计算（`review_gate_common.sh:60`），说明性文字的修改不触发重审——Level 1（格式变更）已覆盖
- `REVIEW_SCOPE: incremental` + `CARRIED` 机制已定义（`review_template.md:139-143`）——Level 2（增量审查）的协议层已有
- GWT 行任何改动都触发 hash 变化 → 全量重审——Level 2 到 Level 3 的边界缺少可执行区分

#### 真正需要补的：影响分析章节验真 + 澄清性变更的快速路径

**问题 A：增量审查缺少"影响分析章节"的门禁验真**

增量 carry-over 的核心校验已有严格实现（`review_gate_common.sh:650-674`：commit 合法性、前次 pass、FAIL/WARN 为 0、hash 一致性）。但门禁脚本还没有落地以下检查：
- 影响分析章节是否存在且完整（模板要求在 `review_template.md:145`，脚本未检查）
- carry-over 的 GWT 所关联的文件是否确实不在本次 diff 中

建议：
- 在 `design.md` 的追溯矩阵中增加"关联文件"列，使影响分析可基于文件级交集自动化
- 门禁脚本增加"影响分析完整性"检查：incremental 模式下，必须输出影响分析章节
- 如果追溯矩阵不存在或不完整，禁止使用 incremental 模式

标准化影响分析格式（建议加入 review_template.md）：
```markdown
### 影响分析（REVIEW_SCOPE: incremental 时必填）
| 变更文件 | 关联 REQ | 关联 GWT | 本次重判 |
|---------|---------|---------|---------|
| src/xx.ts | REQ-001 | GWT-REQ-001-01, -02 | ✅ |

未受影响（carry-over）：GWT-REQ-002-01, GWT-REQ-002-02（关联文件未变更）
```

**问题 B：GWT 文本澄清 vs 结构性变更缺少区分**

GWT 澄清快速路径已有定义（只改 GWT 文本不改 ID），但门禁层没有落地这个区分——hash 变了就是变了，脚本不区分"改了什么"。

**简化方案（推荐）**：门禁在检测到 `REQ_BASELINE_HASH` 变化时，输出 GWT 行的 diff 让人类一眼判断是否需要重审。具体：
- 门禁脚本提取旧/新 GWT 行，输出 diff（新增行标 `+`，删除行标 `-`，仅文本变更标 `~`）
- 如果 ID 集合变了（新增/删除 GWT）→ 硬拦截，标记为"结构性变更"，必须全量重审
- 如果 ID 集合不变（只是文本改了）→ 输出 diff + warning，提示人类确认是否需要重审
- **快速路径限定条件**（防止削弱基线强约束）：
  - "ID 不变"并不代表语义不变——一句文本改动即可改变验收边界。因此门禁不做自动语义分类（"标点修正 vs 关键动词变更"的判断超出 shell 脚本能力边界），一律输出 diff + 要求人工确认
  - 要求人工确认字段：`GWT_CHANGE_CLASS: clarification` + `CLARIFICATION_CONFIRMED_BY: <human name>` + `CLARIFICATION_CONFIRMED_AT: YYYY-MM-DD`
  - 强制 spotcheck 至少 1 条受影响 GWT（即使是澄清性变更）
  - 复杂度留给人而非脚本：脚本只负责检测 ID 集合变化和输出 diff，分类判断由人工完成
- 人类确认方式：在 review 摘要块（`REVIEW-SUMMARY-BEGIN/END`）中增加上述字段。不使用 commit message 标记（如 `[GWT-CLARIFICATION]`），因为 commit message 可审计性弱、易被误用，且与文档门禁链路割裂
- 门禁检查：`REQ_BASELINE_HASH` 变化 + ID 集合不变 + `GWT_CHANGE_CLASS: clarification` + `CLARIFICATION_CONFIRMED_BY` 非空 → 允许复用上一轮证据引用；任一字段缺失时默认按结构性变更处理（fail-safe）

这比原方案（`CHANGE_CLASS_CONFIRMED` + `HUMAN-SPOTCHECK` 块确认）简单，同时保持了机器可读的审计链路。

#### 落地定义

- **Exit Criteria**：影响分析章节门禁验真通过；GWT diff 输出功能就绪；`GWT_CHANGE_CLASS: clarification` + `CLARIFICATION_CONFIRMED_BY` 字段可被门禁解析；ID 集合不变时一律输出 diff + 人工确认（不做自动语义分类）
- **前置依赖**：P-1（`run_gate` 包装器）；P0（spotcheck 机制就绪，澄清性变更仍需 spotcheck 至少 1 条）；P-0.8（枚举单一真相源就绪）
- **Rollback Trigger**：快速路径被滥用（澄清性变更中实际含语义变更的比例 > 10%，通过 spotcheck 回溯发现）

---

### P3：框架分层与配置化（C 档——重工程，解决复用维护）

> 对应走查建议的 C 档。优先级最低，但对跨项目复用的长期健康度有价值。
>
> **注意**：prop_claude.md 本身已达 600+ 行，违反了自己"避免大而全文档"的建议。本文档应保持精简的决策记录，具体方案细节在实施时展开到对应的 phases/templates/scripts 文件中。后续迭代应优先拆分而非追加——新增内容如果超过 10 行，应考虑是否属于实施细节而非决策记录。

#### 现状认知

用户已有隐含的三层结构：
- **原则层**：`AGENTS.md`（或 `CLAUDE.md`）— 不变的行为准则
- **机制层**：`phases/` — 阶段流程定义、门禁规则
- **实现层**：`templates/` — 具体文档模板、格式规范

#### 优化建议

**原则层（AGENTS.md）应更精简、更稳定**：
- 只保留 5-7 条不变的核心原则（如"需求是唯一真相源"、"禁止项与功能需求同等地位"、"门禁计数必须可验真"等）
- 具体的 GWT-ID 格式、hash 计算方式、hook 编号等不应出现在原则层

**机制层（phases/）应成为"规则引擎"**：
- 机制与行为准则分离：phases 文件专注于"阶段流转规则"，通用 AI 行为指导提取到 AGENTS.md
- 门禁规则集中管理：当前分散在 `enhance_temp.md`、`phases/*.md`、`hooks.md` 中，建议集中到 `gates.md` 或 `ai_workflow.md`
- 跨项目适配点标注：用明确标记区分"通用规则"和"可调参数"（如 `GWT_TOTAL <= 15` 阈值、`DEFERRED_TO_STAGING` 的 10% 上限等）

**实现层（templates/）保持当前定位**：
- 模板中不应重复定义机制层的规则（引用即可）
- 考虑为模板增加"最小可用版本"标注——Minor 变更不需要完整模板，标注哪些章节必填/可选

**配置化（走查 C 档建议）**：
- 把阈值（deferred 上限、抽检数量、哪些阶段强制人审）下沉到配置文件（如 `aicoding.config.yaml`）
- 脚本只读配置，避免跨项目 fork 漂移
- 项目侧的适配通过配置覆盖，而非 fork 整个框架

**`enhance_temp.md` 拆分落地**：
- 原则性内容（§2 DoD、§3 核心思想）→ 融入 AGENTS.md
- 机制性内容（§5-§7 门禁策略、§6 @review 协议）→ 融入 phases/ 或 gates.md
- 实现性内容（§10 文件级实施规格、§11 验收命令）→ 融入 templates/ 和 scripts/
- 完成后 `enhance_temp.md` 归档为"设计决策记录"（ADR），不再作为运行时参考

#### 落地定义

- **Exit Criteria**：`aicoding.config.yaml` 配置机制就绪；至少 3 个阈值（deferred 上限、抽检数量、GWT-ID 格式正则）已从脚本提取到配置；`enhance_temp.md` 内容已拆分落地并归档
- **前置依赖**：P-1（`run_gate` 包装器，配置化会改变测试对象结构）；P-0.5（`_change_level` 字段，配置化需覆盖变更分级规则）
- **Rollback Trigger**：配置化引入的间接层导致门禁执行时间增加 > 50%（说明配置读取开销过大）

---

### P4：单版本管理（GitHub 统一最新版）

`.aicoding/` 目录已托管在 GitHub 上，所有项目使用最新版本。

1. 不需要框架版本管理机制，不维护多版本兼容
2. `SPEC_VERSION` 仅用于标识规格文档的修订历史
3. 重大变更通过 GitHub release notes 说明迁移注意事项
4. 项目侧定制通过 `aicoding.config.yaml`（P3 配置化）或 `ai_workflow.md` 中标注项目特定参数

**可选扩展**：如果允许项目"冻结版本"（即某个项目锁定在特定 commit 不跟随最新），P4 的风险大幅降低——项目可以选择稳定的时间窗口再升级。实现方式：项目侧在 `aicoding.config.yaml` 中标注 `framework_ref: <commit-hash>`，升级时对比 diff 决定是否跟进。这依赖 P3 配置化先落地。

#### 落地定义

- **Exit Criteria**：GitHub release notes 流程建立；重大变更有迁移说明
- **前置依赖**：P3（配置化，`aicoding.config.yaml` 支持 `framework_ref`）
- **Rollback Trigger**：N/A（P4 是管理流程，无技术回滚）

---

## 三、改造路线图总览

| 优先级 | 改造项 | 对应缺口 | 前置依赖 | 改动量 | 核心产出 | 成效 KPI |
|--------|--------|---------|---------|--------|---------|---------|
| P-1 | 门禁脚本错误分级处理 | 缺口 5+6 | 无 | 小 | 统一执行包装器 `run_gate` + 检查项级 `GATE_LEVEL` 标记 + `.git/aicoding/` 持久化日志 + critical/advisory 分流 | 门禁绕过率↓（CI 重跑采集）；gate-warnings.log 非空告警数 |
| P-0.8 | 状态字段枚举统一 | 缺口 7 | P-1 | 小 | `common.sh` 枚举单一真相源 + `pre-commit` 枚举校验 + 一致性测试 + `_change_level` 兼容期 warning | 枚举校验拦截率；规范-实现一致性测试通过率 |
| P-0.5 | Minor 门禁配置落地 | 缺口 9+11 | P-1, P-0.8 | 中 | `_change_level` 三阶段迁移（先 major/minor，hotfix 待规范补齐）+ 精确最小产物集 + Minor 单文件审查 | Minor 门禁绕过率（< 5%，CI 重跑采集）；Minor lead time（比 Major 减少 60%+） |
| P0 | 人类抽检硬门禁化 | 缺口 1+4 | P-1 | 小（1 脚本 + 1 spotcheck 模板） | `spotcheck_<stage>_<cr-id>.md` 独立文件（含基线绑定 + SPOTCHECK_FILE 指针）+ gate 脚本 | 抽检发现率（FAIL 占比）；漏检回溯率（交付后发现的应拦截项） |
| P1 | 上游需求质量补强 | 缺口 2 | P-0.5, P0 | 中（模板 + 门禁 + 证据升级） | Proposal 验收锚点（P-DONT 轻量 ID）+ 意图清单门禁 | Requirements 阶段 REQ-C 遗漏率；下游补充需求次数 |
| P2 | 变更分级重审优化 | 缺口 3 | P-1, P0, P-0.8 | 中（门禁脚本增强） | 影响分析章节验真 + GWT diff 输出 + 澄清快速路径（diff + 人工确认，不做自动语义分类） | 重审触发次数中"澄清性"占比；交付 lead time 变化 |
| P3 | 框架分层与配置化 | 缺口 6 + 维护性 | P-1, P-0.5 | 大（架构重组） | 分层落地 + `aicoding.config.yaml` + enhance_temp 拆分归档 | 跨项目部署成本（fork 改动行数）；配置项覆盖率 |
| P4 | 单版本管理 | 复用性 | P3 | 小（约定） | GitHub 统一最新版 + 可选冻结版本 | 项目间版本漂移度 |

**即时修复项**（不属于 P-1~P4，见第五节）：模板锚点、hooks.md 对齐、阶段降级告警、plan.md 验证命令放宽、收敛轮次门禁、commit-msg 多 CR 修复、post-commit 汇总、CR 影响分析校验。（注：状态枚举校验已升级为 P-0.8 独立工作项）

**回滚阈值建议**：任一 P 项上线后，如果门禁绕过率上升超过 20%（CI 重跑门禁未通过率）或交付 lead time 增加超过 30%，应暂停该项并回滚，分析原因后再重新上线。门禁绕过率的主指标通过 CI 侧重跑 pre-commit 检查采集（稳定可靠），辅助指标通过本地 `.git/aicoding/gate-pass.log` 采集（仅限本地环境）。**前提**：CI 管道搭建是采集基础设施的一部分，需在 P-1 落地时同步确认 CI 可用性；无 CI 时以本地辅助指标过渡。

**关键路径风险与并行化机会**：所有 P 项都直接或间接依赖 P-1（`run_gate` 包装器），P-1 需要重构现有 inline 检查逻辑，改动量不小。如果 P-1 延期，整条路线图停摆。以下子任务不依赖 `run_gate`，可在 P-1 开发期间并行启动：
- P0 的 `spotcheck_template.md` 模板设计 + review_template.md 抽检指南编写（纯文档，不涉及门禁脚本）
- P-0.8 的 `common.sh` 枚举常量定义（数据准备，不涉及 `run_gate` 集成）
- P1 的 `proposal_template.md` 验收锚点章节设计（纯模板，不涉及门禁脚本）
- P-0.5 的 `review_minor.md` 模板设计 + `status_template.md` 字段定义（纯模板）
- 即时修复中的模板锚点添加（纯模板改动）

这些并行子任务完成后，P-1 就绪时可快速集成门禁脚本部分，缩短整体交付周期。

---

## 四、深层洞察（讨论与走查中形成的共识）

1. **Goodhart 效应是结构性盲区，不是 bug**：硬门禁只能校验覆盖/计数/外键一致性和证据非空，无法判断"文件:行号 是否真的满足 GWT"。这不是门禁设计的缺陷，而是自动化验证的天花板。唯一的兜底是人类抽检——所以 P0 的价值最高。

2. **复杂度投资方向应前移**：当前框架在"追踪/验真"层（下游）投入很重，但在"需求捕获质量"层（上游）投入不足。最高杠杆的改进点是 Proposal/Requirements 阶段的需求完整性——上游多花 1 分力，下游少花 10 分力。

3. **8 阶段流水线与迭代开发的张力**：严格的阶段门禁适合"一次性交付"，但实际开发中经常需要"实现中发现需求遗漏 → 补充需求 → 继续实现"。GWT 澄清快速路径是好的缓解，但门禁层还没有落地"澄清性变更 vs 结构性变更"的区分（P2 要解决的问题）。

4. **人类参与应是"高效抽检"而非"最小化参与"**：框架的目标不应是"让人类尽量少参与"，而是"让人类的每次参与都高效、有价值"。P0 的抽检硬门禁 + 验证指南是这个方向的具体落地。

5. **框架可维护性是跨项目复用的前提**：1100+ 行的 enhance_temp.md 本身就是维护负担。但这是 P3 的事——先把 P-1/P0/P1 落地，再考虑架构重组。

6. **"谁来看守看守者"是分级问题而非二元问题**：门禁脚本的错误处理不应一刀切。关键校验（GWT 覆盖率、证据完整性）的运行时错误应 fail-closed（宁可错杀），辅助检查（格式建议、命名规范）应 fail-open + 持久化日志到 `.git/aicoding/gate-warnings.log`（防止 fail-silent）。分级粒度应在检查项/函数级而非脚本级——`pre-commit` 等单体脚本内混合了不同重要度的检查，脚本级分级会导致"要么都放，要么都拦"。当前 24 个测试文件（测试规模 proxy，非严格覆盖率）提供了较好的回归基础，但缺少检查项级分级标记机制。

7. **P-1 与 P3 存在时序耦合**：脚本配置化（P3）会改变测试对象的结构。如果 P3 很快要做，先提取配置再调整测试，避免测试因配置化重构而大面积重写。如果 P3 短期不做，现有测试基线已足够支撑 P-1 的分级处理落地。

8. **规范与实现的漂移是持续性风险**：`hooks.md` 写"软警告 13 个"但实际已有 17 个；`pre-commit` 未实现 `hooks.md` 已定义的枚举校验。这类漂移会侵蚀文档可信度，建议增加"规范-实现一致性测试"自动校验。

9. **Minor 流程是框架可用性的生死线**：如果大部分日常变更属于 Minor（具体比例待实际数据验证）但都被迫走 Major 流程，开发者会用 `--no-verify` 绕过，整个门禁体系就废了。Minor 门禁配置不是"即时修复"级别的问题，而是决定框架日常可用性的核心改造项。建议 P-0.5 上线后首月统计实际 Minor/Major 比例，作为后续优先级调整的数据基线。

10. **阶段降级是隐蔽的门禁绕过路径**：`pre-commit:321` 的 backward transition 静默跳过设计在正常回退修复场景下合理，但也意味着 AI 可以通过"先推进→发现过不了→回退→再推进"来绕过某些检查，或 `_phase` 被意外改错时所有中间阶段的出口检查被跳过。

11. **模板复杂度的累积效应需要警惕**：review_template.md 已有 200+ 行，每次增加新的机器可读块都会降低可读性、增加 AI 生成错误的概率、增加人类的认知负担。新增的结构化块应优先考虑独立文件（如 spotcheck），而非嵌入已有模板。

---

## 五、现有代码的即时修复建议（Codex 走查 + 人工走查发现）

以下问题不属于 P0-P4 的改造范畴，但属于现有代码的 bug 或缺陷，建议尽快修复：

1. **~~`pre-commit` 补状态枚举硬校验~~**（已升级为 P-0.8 独立工作项，详见第二节）

2. **模板关键区块加稳定锚点**：`review_gate_common.sh:135` 和 `:196` 依赖固定中文标题匹配（如 `需求-设计追溯矩阵`、`需求覆盖矩阵（GWT`）。应在模板中加 `<!-- TRACE-MATRIX-BEGIN -->` 等稳定锚点，脚本改为按锚点解析，降低文案耦合。

3. **`hooks.md` 与实际 warning 数量对齐**：`hooks.md` 写"软警告 13 个"，实际 `warnings/` 目录已有 17 个脚本（w06-w22）。应更新文档，或增加"规范-实现一致性测试"自动校验 hooks 数量、规则编号。

4. **阶段降级（backward transition）增加告警**：`pre-commit:321` 的 `[ "$NEW_RANK" -le "$OLD_RANK" ] && continue` 在阶段回退时静默跳过所有出口检查。建议：
   - 阶段降级至少记录 warning（写入 `.git/aicoding/gate-warnings.log`），输出旧阶段→新阶段信息
   - 大幅降级（跨 2 个以上阶段，如 Testing→Proposal）应 hard block 或要求人工确认
   - 实现：在 `continue` 前增加降级幅度判断，`(OLD_RANK - NEW_RANK) > 2` 时 `exit 1` + 提示

5. **plan.md 验证命令检查放宽非代码任务**：`pre-commit:410-434` 要求每个任务都有 backtick 包裹的验证命令，但"编写文档"、"配置环境变量"等任务没有自然的命令行验证方式，迫使 AI 编造无意义的验证命令来通过门禁（Goodhart）。建议：
   - 允许任务标记 `验证方式: 人工确认` 或 `验证方式: N/A（文档类任务）` 来豁免命令检查
   - 门禁只对标记了 `命令:` 的任务检查 backtick 格式

6. **收敛最大轮次增加门禁强制**：`ai_workflow.md:124` 规定连续 3 轮不收敛要暂停，但这只是 AI 行为规范，没有门禁脚本强制。建议：
   - `status.md` 的 `_phase_log` 中记录每轮审查的轮次号
   - post-commit warning 检查同一阶段的连续轮次数，超过 3 轮输出 hard warning
   - 超过 5 轮时升级为 pre-commit hard block（需人工 `_run_status: wait_confirm` 解锁）

7. **commit-msg 多 CR 关联逻辑修复**：`commit-msg:42-45` 在有多个 Active CR 时，commit message 只需包含其中任意一个即可通过。建议：
   - **优先方案**：按暂存文件映射 CR 影响范围——如果暂存区文件属于某个 CR 的影响范围（通过 CR 文件中的"影响文件"字段判断），commit message 必须包含该 CR 的 ID
   - **回退方案**：无法映射时（如 CR 未声明影响文件），回退到"至少一个 Active CR"保守规则
   - **不采用"全包含所有 Active CR"**——这会误伤独立提交（一次提交只改 CR-A 文件，却被迫带 CR-B/C），仅作为临时应急开关而非默认行为

8. **post-commit warning 增加汇总输出**：`post-commit:26` 在子 shell 中执行 17 个 warning 模块，各自独立输出。建议在 dispatcher 末尾增加汇总：
   - 每个 warning 模块的退出码写入临时文件
   - dispatcher 末尾统计触发数量，输出一行汇总（如"本次提交触发 3 个警告，其中 1 个与 REQ-C 相关"）

9. **Phase 00 CR 影响分析升级为硬门禁**：CR 模板要求"二元影响分析"（是/否），当前仅有 warning 级校验，尚无 pre-commit 硬门禁。建议：
   - pre-commit 在检测到 `cr/` 目录下文件变更时，校验影响分析表的必填字段非空
   - post-commit warning 对比 CR 声称的影响范围与实际 diff 文件列表，输出差异提示

---

*本文档由 Claude 基于多轮讨论、外部走查反馈（人工 + Codex）、脚本移植性分析及人工走查反馈生成，供用户反思与后续讨论使用。*
