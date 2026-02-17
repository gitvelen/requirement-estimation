# 框架走查报告（资深开发专家视角）

> 走查日期：2026-02-16
> 走查范围：`.aicoding/` 全部规范文件、流程定义、模板、脚本、测试
> 走查方法：逐文件阅读 + 交叉引用一致性检查 + 脚本逻辑审查

---

## 总体评价

这是一个设计意图明确的 AI 协作开发框架——用程序化门禁替代纯文本约束，解决"AI 跳过规则"的核心问题。架构思路正确，双层 hooks 体系（CC hooks + Git hooks）的分层设计合理。

但当前实现存在**过度工程化**的倾向：框架自身的复杂度已接近一个独立项目的体量（400KB+ 文档/脚本、24 个测试、17 个 warning 模块），对实际业务开发形成了显著的认知和 context 开销。

以下按严重度分级列出具体发现。

---

## P0：架构层面的根本性问题

### ENR-001 status.md 双轨存储的脆弱性

**位置**：`templates/status_template.md`、`scripts/lib/common.sh:65-79`、`scripts/git-hooks/pre-commit:15-18`

**问题**：`status.md` 同时使用 YAML front matter 和 Markdown 表格存储状态，两者要求"同步"但没有程序化保证一致性。

具体表现：
- YAML front matter 用 `grep + sed + awk` 解析（`common.sh:65-79` 的 `aicoding_yaml_value`），Markdown 表格用 `awk -F'|'` 解析——两套解析逻辑独立运行，无交叉校验
- `aicoding_get_phase()`（`common.sh:88-98`）先尝试 YAML，失败后 fallback 到表格——如果两者不一致，取决于哪个先匹配，行为不可预测
- YAML 值不加引号（如 `_baseline: v1.0`），如果值包含空格（如 `v1.0 hotfix`），`awk '{print $2}'` 会截断——`pre-commit:17` 的 `yaml_value_from_block` 用 `tr -d '[:space:]'` 规避了这个问题，但也意味着值中不能有合法空格
- 框架自己的核心前提是"没有程序化强制就只是建议"，但 YAML↔表格同步恰恰没有程序化强制

**建议**：
1. 将机器可读状态拆为独立的 `status.yaml`（纯 YAML，用 `yq` 或 `python -c 'import yaml'` 解析），`status.md` 仅保留人类可读的 Markdown 展示
2. 或者彻底去掉表格展示行，只保留 YAML front matter 作为唯一数据源，Markdown 正文只放非结构化内容（决策日志、备注等）
3. 如果保留当前方案，至少在 pre-commit 中增加 YAML↔表格一致性校验

### ENR-002 框架自身的 context 开销过大

**位置**：全局

**问题**：AI 在每个阶段需要读取 5-7 个框架文件才能开始工作（CC-7 强制）。以 Design 阶段为例：

| 必读文件 | 估算大小 |
|---------|---------|
| `status.md` | ~2KB |
| `requirements.md` | ~5-15KB |
| `phases/03-design.md` | ~5KB |
| `templates/design_template.md` | ~8KB |
| `review_template.md`（自审时） | ~20KB |
| Active CR 文件（如有） | ~3KB |

仅框架文件就占用 ~40KB+ context（约 10K tokens），还没算业务代码。对于 200K context window 的模型，这意味着 ~5% 的 context 被框架规则占用；对于更小的 context window，比例更高。

**建议**：
1. 精简各阶段定义文件，去掉重复的"入口协议"表格（CC-7 已程序化强制，文档中不需要再重复列出）
2. `review_template.md` 拆分为"模板骨架"（<2KB）和"判定口径参考"（按需读取）
3. 考虑将 CC-4（SessionStart 注入）的上下文信息做得更丰富，减少 AI 需要主动读取的文件数量

### ENR-003 "先读后写"机制的根本缺陷

**位置**：`scripts/cc-hooks/read-tracker.sh`、`scripts/cc-hooks/phase-entry-gate.sh`

**问题**：CC-7 + CC-7b 通过 `/tmp/aicoding-reads-*.log` 追踪 AI 读了哪些文件，存在多个漏洞：

1. **绕过路径**：只追踪 Claude Code 的 `Read` 工具调用。AI 用 `Bash` 执行 `cat`/`head`/`grep` 读取文件不会被记录，CC-7 会误判为"未读取"
2. **Session ID 可靠性**：`read-tracker.sh:12` 使用 `${CLAUDE_SESSION_ID:-$$}` 作为日志文件名。如果 `CLAUDE_SESSION_ID` 为空，fallback 到 `$$`（进程 ID）。但每次 hook 调用是独立的 shell 进程，`$$` 每次不同——这意味着 CC-7b 写入的日志和 CC-7 读取的日志可能不是同一个文件
3. **形式主义风险**：机制只能证明"文件被 Read 工具打开过"，不能证明 AI 理解了内容。AI 可以 Read 一个文件然后完全忽略其内容
4. **竞态条件**：多个 Claude Code 实例并发时，同一个 `/tmp/aicoding-reads-*.log` 文件会被并发写入，无文件锁保护

**建议**：
1. 对于 Session ID 问题：Claude Code 的 hook 机制应该保证 `CLAUDE_SESSION_ID` 始终可用——需要验证这一点，如果不可靠则改用其他标识（如 `PPID`）
2. 对于绕过问题：接受这是一个已知限制，在 AGENTS.md 中明确要求 AI 使用 Read 工具而非 Bash 读取文件（文本层约束作为补充）
3. 对于形式主义：这是所有"过程检查"的固有局限，不建议过度投入解决——把精力放在结果检查（出口门禁）上更有效

---

## P1：流程设计问题

### ENR-004 Minor 流程仍然过重

**位置**：`ai_workflow.md:12-35`、`scripts/git-hooks/pre-commit:20-48`

**问题**：Minor 的核心原则是"简化文档，不简化理解"，但实际要求仍然很重：

- `status.md` 必须有完整 YAML front matter（`_change_level: minor`）
- 必须输出 `review_minor.md`，包含机器可读摘要块（`REVIEW-SUMMARY-BEGIN/END`）、`REQ_BASELINE_HASH`、GWT 验证表（至少 1 行）
- 测试证据必须满足 `test_report.md` 或 `status.md` 内联 `TEST-RESULT` 块
- pre-commit 的 `validate_minor_review()` 对 `review_minor.md` 做 5 项结构校验

一个"修复按钮颜色"的 Bug，需要：创建 status.md → 写 review_minor.md（含 GWT 表）→ 提供测试证据。这个成本远超直接修 bug。

**建议**：
1. 增加 `hotfix` 级别（`_change_level: hotfix`）：commit message 带 `[hotfix]` 标记 + 测试通过即可，跳过所有文档门禁
2. Minor 的 `review_minor.md` 改为可选——如果 diff 文件数 ≤ 3 且无 REQ-C 涉及，允许跳过
3. 在 `aicoding.config.yaml` 中增加 `minor_skip_review: true/false` 配置项

### ENR-005 8 阶段流程对 AI 协作场景过于线性

**位置**：`phases/` 全部 8 个文件、`ai_workflow.md:45-51`

**问题**：现实中 AI 辅助开发的节奏是迭代式的，不是瀑布式的：

- 用户说"帮我加个登录功能"，AI 可能在一个会话内完成理解→设计→编码→测试
- 8 阶段流程要求每个阶段产出独立文件、经过独立审查、满足独立门禁
- 阶段之间的"推进"需要修改 `status.md` 的 `_phase` 字段，触发出口门禁检查——这些都是纯流程开销

框架在 `manu.md` 中说"阶段 3-6 AI 全自动"，但"全自动"仍然意味着 AI 要：读 5-7 个文件 → 写产出物 → 自审 → 写审查报告 → 检查收敛 → 更新 status.md → 读下一阶段的 5-7 个文件 → 重复。这不是"全自动"，这是"全自动走流程"。

**建议**：
1. 允许 AI 在单次会话中跨阶段执行（"流式模式"），只在关键节点（需求确认、部署确认）强制暂停
2. 阶段产出物可以合并——比如 Design + Planning 合并为一个 `design_plan.md`
3. 保留阶段概念作为思维框架和检查清单，但不强制每个阶段都有独立的文件和审查轮次

### ENR-006 审查机制的形式主义风险

**位置**：`templates/review_template.md`、`scripts/lib/review_gate_common.sh`

**问题**：框架要求 AI 自审并输出机器可读摘要块（`REVIEW-SUMMARY-BEGIN/END`），然后用门禁检查摘要块的格式和值。这创造了一个激励扭曲：

- AI 的目标变成了"生成 `REVIEW_RESULT=pass` + `GWT_FAIL=0` 的摘要块"，而不是"发现并修复真实问题"
- 机器可读块的值完全由 AI 自己填写——相当于让考生自己批改试卷
- `review_gate_common.sh` 检查的是"摘要块格式是否正确"和"REVIEW_RESULT 是否为 pass"，不检查审查内容是否真实

框架在 `hooks.md` §7.2 承认了这个问题（"CC-5 导致 AI 形式主义"），但标注为"低严重度"——实际上这是整个审查机制的根本性缺陷。

**建议**：
1. 区分"结构检查"和"质量审查"：结构检查（文件存在、章节完整）由门禁做；质量审查由人工抽检做
2. 降低 AI 自审的形式要求——不需要机器可读摘要块，只需要 AI 在审查报告中列出发现和结论
3. 把 `REVIEW_RESULT=pass` 的门禁权交给人工（spotcheck 机制已有雏形，应该强化）
4. 或者引入"交叉审查"：Claude 写的代码由 Codex 审查，反之亦然——至少比自审可信

### ENR-007 Codex 兼容性是名义上的

**位置**：`hooks.md:13-16`、`AGENTS.md.template`

**问题**：框架声称支持 Claude Code + Codex 双工具协作，但实际约束力严重不对称：

| 约束层 | Claude Code | Codex |
|--------|------------|-------|
| CC hooks（9 个） | ✅ 全部生效 | ❌ 不支持 |
| Git hooks（7 硬 + 17 软） | ✅ 生效 | ⚠️ sandbox 中行为可能不同 |
| AGENTS.md 文本规则 | ✅ 读取 | ✅ 读取（但无强制力） |

框架的核心前提是"文本规则不够，需要程序化强制"，但对 Codex 只有文本规则。这意味着双工具协作时，Codex 可以绕过大部分门禁（除了 Git hooks 的 pre-commit/commit-msg）。

**建议**：
1. 明确标注 Codex 的约束力等级，不要给用户"双工具同等受控"的错觉
2. 如果 Codex 是重要的协作工具，考虑将关键门禁上收到 CI（GitHub Actions），而不是依赖本地 hooks
3. 或者在 AGENTS.md 中为 Codex 增加更强的文本约束（比如要求 Codex 在每次写入前输出"已读取 XXX 文件"的声明）

---

## P1：工程实现问题

### ENR-008 Shell 脚本的健壮性边界

**位置**：多处脚本

**具体问题**：

1. **`find ... -exec ls -t {} + | head -1` 的语义问题**（`common.sh:48-49`）：当存在多个版本目录（如 `docs/v1.0/`、`docs/v2.0/`）时，取"最近修改的 status.md"。但"最近修改"不等于"当前活跃版本"——用户可能在 v1.0 的 status.md 上做了一个无关修改，导致 v2.0 的门禁读取了 v1.0 的状态

2. **`for pattern in $(echo "$ALLOWED" | tr '|' ' ')` 的空格问题**（`doc-scope-guard.sh:44`）：如果未来白名单中出现包含空格的模式，`tr '|' ' '` + unquoted `$()` 会导致 word splitting。当前白名单没有空格，但这是一个脆弱的隐式假设

3. **`aicoding_block()` 的 JSON 转义不完整**（`common.sh:119`）：只转义了 `\` 和 `"`，没有转义控制字符（`\n`、`\t`、`\r`）。如果 reason 字符串包含换行符（比如多行错误信息），生成的 JSON 会无效

4. **`aicoding_yaml_value()` 的 awk 正则注入**（`common.sh:73`）：`$0 ~ "^" k ":"` 中 `k` 来自函数参数，如果 key 包含 awk 正则特殊字符（如 `.`、`*`），会导致误匹配。当前所有 key 都以 `_` 开头，不含特殊字符，但这是一个隐式假设

**建议**：
1. `find` fallback 改为按版本号排序取最大值，而非按修改时间
2. 白名单匹配改用数组 + 循环，避免 word splitting
3. `aicoding_block()` 使用 `jq -n --arg reason "$reason" '{decision:"block",reason:$reason}'` 生成 JSON，彻底避免转义问题
4. `aicoding_yaml_value()` 的 key 参数做正则转义，或改用 `index()` 函数做精确匹配

### ENR-009 hooks.md 既是设计文档又是实现规格

**位置**：`hooks.md`（82KB）

**问题**：`hooks.md` 包含：设计背景、架构决策、每个 hook 的完整代码、副作用分析、落地策略、决策记录。这导致：

1. **代码双源问题**：`hooks.md` 中的代码和 `scripts/cc-hooks/` 中的实际脚本是否一致？如果不一致，哪个是权威源？实际脚本已经引入了 `common.sh` 共享库（如 `aicoding_parse_cc_input`、`aicoding_detect_version_dir`），但 `hooks.md` 中的代码仍然是原始的内联版本
2. **维护负担**：修改一个 hook 需要同时更新脚本文件和 hooks.md 中的代码块——这恰恰是框架自己反对的"双轨维护"
3. **阅读负担**：82KB 的文件对人类和 AI 都是沉重的阅读负担

**建议**：
1. `hooks.md` 只保留架构设计和决策记录（预计 ~15KB），删除所有内联代码块
2. 每个脚本文件头部用注释说明对应的 hook 编号和设计意图
3. 代码的权威源是且仅是 `scripts/` 目录下的实际脚本文件
4. 决策记录迁移到独立的 `CHANGELOG.md` 或 `decisions.md`

### ENR-010 配置化不够彻底

**位置**：`aicoding.config.yaml`、多处脚本

**问题**：`aicoding.config.yaml` 只有 7 个配置项，但大量应该可配置的值硬编码在脚本和文档中：

| 硬编码位置 | 硬编码值 | 应配置化 |
|-----------|---------|---------|
| `doc-scope-guard.sh:21-38` | 各阶段白名单文件列表 | 允许项目自定义阶段产出物 |
| `doc-structure-check.sh` | 各文档必填章节标题 | 允许项目自定义模板结构 |
| `ai_workflow.md:133` | 3 轮不收敛阈值 | 不同项目可能需要不同阈值 |
| `ai_workflow.md:151` | 最多再给 2 轮（第 5 轮强制停止） | 同上 |
| `post-commit` | `HIGH_RISK_PATTERNS` | 不同项目的高风险路径不同 |
| `commit-msg` | commit message 格式正则 | 不同团队可能有不同的 commit 规范 |

**建议**：
1. 将上述硬编码值迁移到 `aicoding.config.yaml`，提供合理默认值
2. 脚本中通过 `aicoding_config_value` 读取，保持向后兼容
3. 特别是白名单和章节标题——这些是项目最可能需要自定义的部分

---

## P1：一致性和冗余问题

### ENR-011 CC-8 与 Git-Hook 7 的重复

**位置**：`scripts/cc-hooks/phase-exit-gate.sh`、`scripts/git-hooks/pre-commit`（阶段出口门禁部分）

**问题**：CC-8（CC hook 层）和 Git-Hook 7（Git hook 层）实现了完全相同的逻辑——检查阶段推进时必要产出物是否存在。设计文档（`hooks.md`）解释这是为了"Codex 兼容"，但：

1. 两份代码需要同步维护——如果某个阶段的出口产出物要求变了，需要改两处
2. 对于 Claude Code 用户，同一次阶段推进会被检查两次（CC-8 在 Write/Edit 时检查，Git-Hook 7 在 commit 时再检查）
3. `common.sh` 已经提供了共享函数，但出口门禁的逻辑没有抽取为共享函数

**建议**：
1. 将出口门禁的"各阶段必须存在的产出物"定义为配置（`aicoding.config.yaml` 或 `common.sh` 中的关联数组）
2. CC-8 和 Git-Hook 7 共用同一份产出物定义，避免不一致
3. 或者更激进地：CC-8 只做"提醒"（PostToolUse 反馈），Git-Hook 7 做"拦截"（pre-commit 硬门禁）——避免同一个检查在两层都做硬拦截

### ENR-012 阶段入口协议在多处重复定义

**位置**：`phases/*.md`（8 个文件）、`hooks.md`（CC-4 和 CC-7 章节）、`ai_workflow.md`、`AGENTS.md.template`

**问题**：每个阶段的"必读文件列表"在至少 4 个地方出现：

1. `phases/03-design.md` 的"阶段入口协议"表格
2. `hooks.md` CC-4 章节的 `inject-phase-context.sh` 代码
3. `hooks.md` CC-7 章节的 `phase-entry-gate.sh` 代码
4. `scripts/cc-hooks/phase-entry-gate.sh` 的实际脚本

如果要新增一个必读文件，需要改 4 处。这违反了 DRY 原则，也违反了框架自己的"单一真相源"理念。

**建议**：
1. 必读文件列表只在 `phase-entry-gate.sh`（或 `aicoding.config.yaml`）中定义一次
2. `phases/*.md` 中的入口协议表格改为"详见 CC-7 配置"的引用，不再重复列出
3. `hooks.md` 中的代码块删除（见 ENR-009）

---

## P2：文档和可用性问题

### ENR-013 语言混用增加认知负担

**位置**：全局

**问题**：文档主体是中文，但混用了大量英文：

| 类别 | 中文 | 英文 |
|------|------|------|
| 阶段名 | — | Proposal、Requirements、Design |
| 状态枚举 | — | running、wait_confirm、in_progress |
| ID 前缀 | — | REQ-、GWT-、SCN-、RVW-、CR- |
| 主文档名 | 系统功能说明书.md、技术方案设计.md | — |
| 模板名 | — | status_template.md、review_template.md |
| 配置 key | — | spotcheck_ratio_percent、minor_max_diff_files |

这不是错误，但增加了认知切换成本。特别是主文档用中文命名（`docs/系统功能说明书.md`）而模板用英文命名（`templates/master_system_function_spec_template.md`），对应关系不直观。

**建议**：
1. 统一为英文命名（推荐，避免文件名编码问题）
2. 或者在 `STRUCTURE.md` 中增加中英文对照表，方便查找

### ENR-014 模板过于详尽导致"模板驱动开发"

**位置**：`templates/` 目录

**问题**：模板设计得非常详尽（`review_template.md` 约 20KB、`requirements_template.md` 约 8KB），AI 会倾向于"填满模板的每个章节"而不是"写出有用的内容"。

典型场景：一个"加个登录功能"的需求，可能被展开成包含权限矩阵、数据字典、错误码表、合规要求、性能基准的 200 行文档——因为模板里有这些章节。

**建议**：
1. 模板分为"必填"和"按需"两部分，用注释明确标注
2. 每个模板的必填部分不超过 50 行
3. 在模板头部增加"适用场景"说明——比如"权限矩阵"章节标注"仅当涉及多角色权限时填写"
4. 考虑按 `_change_level` 提供不同详细度的模板（major 用完整模板，minor 用精简模板）

### ENR-015 缺少"逃生通道"文档

**位置**：`manu.md`

**问题**：当框架阻碍了实际工作时（门禁误报、流程不适用、紧急修复），用户该怎么办？目前的选项：

- `--no-verify` 跳过 git hooks（但 AGENTS.md 禁止 AI 使用，需要用户手动执行）
- 手动编辑 `status.md` 改状态（但不知道改哪些字段、改成什么值）
- 没有"临时禁用特定 hook"的机制
- 没有"跳过特定阶段"的标准操作

**建议**：
在 `manu.md` 中增加"故障排除"章节，明确列出：
1. 如何临时禁用特定 CC hook（修改 `.claude/settings.json`）
2. 如何跳过特定阶段（手动设置 `_phase` + `--no-verify` commit）
3. 如何重置状态（`_run_status: running`、`_phase: <目标阶段>`）
4. 常见门禁误报的排查步骤
5. 紧急修复的快速通道（hotfix 流程）

### ENR-016 缺少实际项目的端到端验证

**位置**：全局

**问题**：`skills/` 目录有量化交易相关的 skills，但没有看到任何实际项目的 `docs/v1.0/` 目录。24 个测试文件覆盖了单个 hook 的行为，但没有端到端测试验证"从 Proposal 到 Deployment 的完整流程"。

一个 400KB 的流程框架如果没有在真实项目中跑过完整流程，很可能在第一次实际使用时暴露大量问题——特别是阶段间的衔接、门禁的误报/漏报、AI 的实际行为与预期的偏差。

**建议**：
1. 用一个小型真实项目（比如一个 CLI 工具）跑一轮完整的 Major 流程，记录所有摩擦点
2. 用实际体验来修剪不必要的复杂度——如果某个门禁在实际使用中从未触发过有意义的拦截，考虑降级或移除
3. 将端到端测试脚本化（模拟 AI 的文件操作序列，验证门禁行为）

---

## P2：测试覆盖问题

### ENR-017 测试只覆盖 happy path 和单点行为

**位置**：`scripts/tests/`

**问题**：24 个测试文件覆盖了各个 hook 的独立行为，但缺少：

1. **跨 hook 交互测试**：CC-7（入口门禁）和 CC-8（出口门禁）的交互——比如 CC-7 通过后 CC-8 是否正确识别已读取状态
2. **并发场景测试**：多个 Claude Code 实例同时操作同一个项目
3. **状态恢复测试**：`status.md` 被手动修改后，门禁是否能正确恢复
4. **边界值测试**：YAML front matter 中的特殊字符、超长值、空值
5. **回归测试**：`common.sh` 的共享函数被修改后，所有依赖它的 hook 是否仍然正确

**建议**：
1. 增加集成测试：模拟一个完整的阶段推进流程（创建 status.md → 写产出物 → 自审 → 推进阶段）
2. 增加 `common.sh` 的单元测试（特别是 `aicoding_yaml_value`、`aicoding_detect_version_dir`、`aicoding_block`）
3. 在 `run-all.sh` 中增加测试覆盖率统计

---

## 总结建议（按优先级）

### 短期（立即可做）

1. **ENR-008**：修复 `aicoding_block()` 的 JSON 生成，改用 `jq`
2. **ENR-009**：从 `hooks.md` 中删除内联代码块，只保留设计文档
3. **ENR-012**：必读文件列表收敛到单一定义点
4. **ENR-015**：在 `manu.md` 中增加"故障排除"章节

### 中期（需要设计）

5. **ENR-001**：将 status.md 的机器可读部分拆为 `status.yaml`
6. **ENR-004**：增加 `hotfix` 级别，真正的快速通道
7. **ENR-010**：将硬编码值迁移到 `aicoding.config.yaml`
8. **ENR-011**：CC-8 和 Git-Hook 7 共用产出物定义

### 长期（需要验证）

9. **ENR-005**：设计"流式模式"，允许跨阶段执行
10. **ENR-002**：精简框架文件的 context 开销
11. **ENR-016**：用真实项目跑完整流程，用体验驱动优化
12. **ENR-006**：重新设计审查机制，区分结构检查和质量审查

---

## 专题分析：质量保障 vs 上下文开销

> 本节聚焦框架的核心矛盾：**规范不够细 → 质量不稳定** vs **规范太繁琐 → 上下文爆炸**。
> 以下从"质量实际在哪里泄漏"和"上下文实际在哪里膨胀"两个维度做系统分析，并给出同时改善两端的具体建议。

### 一、质量泄漏点分析

当前框架在质量保障上投入了大量机制（CC hooks 9 个、Git hooks 24 个、8 阶段审查），但质量仍可能从以下缝隙泄漏：

#### Q-001 门禁检查形式而非实质

| 门禁 | 检查了什么 | 没检查什么 |
|------|-----------|-----------|
| CC-7（入口门禁） | 文件是否被 Read 工具打开过 | AI 是否理解了文件内容 |
| CC-8（出口门禁） | 产出物文件是否存在 | 产出物内容是否有意义 |
| Git-Hook 7（出口） | `review_*.md` 是否存在 | 审查是否发现了真实问题 |
| 摘要块门禁 | `REVIEW_RESULT=pass`、`GWT_FAIL=0` | 这些值是否真实反映了代码状态 |
| GWT 覆盖门禁 | 每个 GWT-ID 是否出现在判定表中 | 判定结论（✅/❌）是否正确 |

**核心问题**：所有门禁都在检查"过程痕迹"，没有一个门禁在检查"结果正确性"。AI 完全可以生成格式完美但内容空洞的审查报告，所有门禁都会通过。

#### Q-002 需求→代码的追溯链有断点

框架设计了 `REQ-ID → GWT-ID → 代码 → 测试` 的追溯链，但链条在以下环节可能断裂：

1. **Requirements → Design**：`design.md` 要求"需求-设计追溯矩阵"覆盖全部 REQ-ID，但只检查 REQ-ID 是否出现，不检查设计是否真正覆盖了需求语义
2. **Design → Implementation**：没有程序化机制验证代码是否实现了 design.md 中的设计——这完全依赖 AI 自觉
3. **Implementation → Testing**：GWT 判定表要求逐条判定，但证据类型 `CODE_REF`（`文件:行号`）只能证明"代码存在"，不能证明"代码正确"
4. **REQ-C（禁止项）的特殊风险**：要求 `UI_PROOF` 或 `RUN_OUTPUT`，这是唯一要求运行时证据的地方——但仅限于禁止项，正向功能允许仅凭 `CODE_REF` 通过

#### Q-003 自审机制的激励扭曲

`review_template.md` 要求 AI 自审并输出机器可读摘要块，门禁检查摘要块的值。这创造了一个闭环：

```
AI 写代码 → AI 审查自己的代码 → AI 填写 REVIEW_RESULT=pass → 门禁通过
```

Implementation 和 Testing 阶段禁止 accept/defer，意味着 AI 必须让 `GWT_FAIL=0`。当 AI 发现自己的代码有问题时，它面临两个选择：(1) 修复代码，(2) 在判定表中写 ✅。选项 2 的成本远低于选项 1，且没有外部校验。

#### Q-004 Minor 流程的质量风险

Minor 流程合并了 Proposal+Requirements 和 Design+Planning+Implementation，但测试"不简化"。问题在于：

- 需求确认被压缩为"在 status.md 中记录变更摘要 + 验收标准"——没有独立的 requirements.md，GWT 粒度的追溯链不存在
- `review_minor.md` 只要求"最小机器可读块"——审查深度大幅降低
- 如果一个 Minor 变更实际影响了多个模块（但开发者低估了复杂度），升级为 Major 的触发依赖 AI 自觉（`minor_max_diff_files: 10` 只是 warning，不是硬门禁）

#### Q-005 测试阶段缺少独立验证

Testing 阶段的完成条件要求 `GWT_FAIL=0`，但：

- 测试代码由 AI 编写，测试由 AI 执行，测试结果由 AI 判定——全链路无外部校验
- `test_report.md` 的"需求覆盖矩阵"只检查 GWT-ID 是否出现，不检查测试是否真正执行了 GWT 描述的场景
- 全量回归（AC-04）只是"建议"执行 `pytest -q` 等命令，没有门禁检查回归测试是否实际通过

### 二、上下文膨胀点分析

#### C-001 每个阶段的固定 context 开销

以 Implementation 阶段（最重的阶段）为例，CC-7 强制读取的文件：

| 文件 | 估算大小 | 必要性评估 |
|------|---------|-----------|
| `status.md` | ~2KB | ✅ 必要（获取状态） |
| `plan.md` | ~5-10KB | ✅ 必要（任务清单） |
| `design.md` | ~8-15KB | ✅ 必要（技术方案） |
| `requirements.md` | ~5-15KB | ⚠️ 部分必要（GWT 追溯需要，但全文读取浪费） |
| `phases/05-implementation.md` | ~6KB | ⚠️ 大部分是 CR 场景规则，非 CR 时不需要 |
| `implementation_checklist_template.md` | ~3KB | ⚠️ 每次都读，但内容固定不变 |

**单阶段固定开销**：~30-60KB（约 7.5K-15K tokens），还没算业务代码。

**全流程累计**：Design(~40KB) + Planning(~35KB) + Implementation(~60KB) + Testing(~50KB) = ~185KB 纯框架文件读取。在 200K context window 中，框架文件占比可达 25-30%。

#### C-002 review_template.md 的重复读取

`review_template.md`（425 行，~20KB）在每个阶段都要读取（Design/Planning/Implementation/Testing 各一次）。但每次 AI 只需要其中一个阶段的清单（约 10-15 行）+ 机器可读摘要块格式（约 25 行）+ REQ 模式协议（约 80 行）。

**浪费比**：每次读取 425 行，实际需要 ~120 行，浪费率 ~72%。四个阶段累计浪费 ~60KB context。

#### C-003 阶段定义文件的冗余内容

8 个 `phases/*.md` 文件中，以下内容在每个文件中重复出现：

1. **入口协议表格**（~15 行/文件）：CC-7 已程序化强制，文档中的表格只是"文档化"，AI 不需要读这个表格来知道该读什么文件——CC-7 会告诉它
2. **出口门禁清单**（~10 行/文件）：CC-8 已程序化强制，同上
3. **"完成后"章节**（~3 行/文件）：每个文件都是"AI 自动推进到 X 阶段"
4. **CR 场景条件性规则**（~30-60 行/文件）：非 CR 场景完全不需要

**冗余估算**：每个阶段文件中 ~40-60% 的内容是重复或条件性不需要的。

#### C-004 模板驱动的产出物膨胀

模板越详尽，AI 产出的文档越长，后续阶段读取这些文档的 context 开销越大。这是一个正反馈循环：

```
详尽模板 → AI 生成详尽文档 → 后续阶段读取详尽文档 → context 膨胀
                                                    ↓
                                              留给业务代码的 context 减少
                                                    ↓
                                              AI 对业务代码的理解变浅
                                                    ↓
                                              质量下降（与初衷相悖）
```

`requirements_template.md`（207 行）鼓励 AI 为每个需求写完整的 GWT、数据字典、错误码表。一个 10 条需求的项目，`requirements.md` 可能膨胀到 300-500 行（~15-25KB）。这个文件在 Design、Planning、Implementation、Testing 四个阶段都要全文读取。

### 三、同时改善质量和 context 的建议

以下建议的设计原则是：**用更少的 context 实现更强的质量保障**。

#### 建议 S-001：从"过程门禁"转向"结果门禁"

**现状**：门禁检查"文件是否存在"、"摘要块格式是否正确"、"GWT-ID 是否出现"。
**建议**：增加结果级别的门禁，减少过程级别的门禁。

具体措施：
1. **在 pre-commit 中增加测试执行门禁**：`pytest`/`npm test` 必须通过才能 commit（这比检查 `test_report.md` 是否存在有效 100 倍）
2. **在 pre-commit 中增加编译/类型检查门禁**：`tsc --noEmit`/`go vet`/`mypy` 必须通过
3. **降低 CC-7（先读后写）的强制级别**：从"阻止写入"降为"warning"——读文件是手段不是目的，真正的目的是产出物质量，而产出物质量由出口门禁保证
4. **简化摘要块**：去掉 `GWT_CARRIED`、`CARRIED_FROM_COMMIT`、`GWT_CHANGE_CLASS` 等增量审查字段（这些增加了复杂度但不增加质量保障），只保留核心字段：`GWT_TOTAL`、`GWT_FAIL`、`GWT_WARN`、`REVIEW_RESULT`

**context 节省**：CC-7 降级后，AI 不需要在每个阶段开始时读取阶段定义文件中的入口协议表格（~15 行 × 4 阶段 = ~60 行）。摘要块简化后，`review_template.md` 的 REQ 模式协议可以从 ~80 行压缩到 ~30 行。

#### 建议 S-002：分层模板体系（按 context 预算设计）

**现状**：所有模板都是"完整版"，无论项目大小都读取同样的模板。
**建议**：每个模板拆为"骨架"和"参考"两层。

```
templates/
├── review_skeleton.md          # ~50 行，必读：报告格式 + 摘要块格式 + 核心判定规则
├── review_reference.md         # ~375 行，按需读：详细判定口径、证据类型、diff-only 协议
├── requirements_skeleton.md    # ~30 行，必读：REQ-ID + GWT 格式 + 最小必填项
├── requirements_reference.md   # ~177 行，按需读：数据字典、错误码表、权限矩阵模板
├── test_report_skeleton.md     # ~30 行，必读：覆盖矩阵格式 + 结论格式
└── test_report_reference.md    # 按需读：详细测试策略、回归范围分析模板
```

**规则**：
- CC-7 只强制读取 `*_skeleton.md`
- `*_reference.md` 仅在 AI 判断需要时读取（如需求涉及权限矩阵时才读 `requirements_reference.md` 的权限矩阵章节）
- 骨架文件总大小控制在 ~150 行（~4KB），替代当前的 ~850 行（~40KB）

**context 节省**：每个阶段减少 ~8-15KB 模板读取，四个阶段累计减少 ~40-60KB。

#### 建议 S-003：阶段定义文件瘦身

**现状**：每个 `phases/*.md` 包含入口协议、行为准则、质量门禁、完成条件、出口门禁、CR 条件性规则。
**建议**：

1. **删除入口协议表格**：CC-7 脚本已经是权威定义，文档中的表格是冗余的。在文件头部只写一行：`> 入口必读文件由 CC-7 程序化强制，详见 phase-entry-gate.sh`
2. **删除出口门禁清单**：同理，CC-8 脚本是权威定义
3. **CR 条件性规则抽取为独立文件**：`phases/cr-rules.md`（~80 行），仅在有 Active CR 时由 CC-4 注入，非 CR 场景不读取
4. **"完成后"章节删除**：这是 CC-8 的行为描述，不需要在每个文件中重复

**预期效果**：每个阶段定义文件从 ~100-180 行压缩到 ~40-60 行。AI 在每个阶段读取的框架文件减少 ~50%。

#### 建议 S-004：requirements.md 的按需读取

**现状**：`requirements.md` 在 Design、Planning、Implementation、Testing 四个阶段都全文读取。
**建议**：

1. **Design/Planning 阶段**：全文读取（需要理解全部需求）
2. **Implementation 阶段**：只读取当前任务关联的 REQ-ID 对应的 GWT 条目（通过 `plan.md` 的任务→REQ-ID 映射定位）
3. **Testing 阶段**：全文读取（需要全量 GWT 追溯）

**实现方式**：在 `plan.md` 的任务定义中增加 `related_reqs: [REQ-001, REQ-003]` 字段。Implementation 阶段 AI 按任务逐个执行时，只读取关联的 REQ 条目。

**context 节省**：Implementation 阶段减少 ~60-80% 的 requirements.md 读取量。

#### 建议 S-005：引入真正的外部质量校验

**现状**：所有质量检查都是 AI 自检（写代码的人审查自己的代码）。
**建议**：增加不依赖 AI 自觉的质量校验点。

1. **测试必须实际执行并通过**（最高优先级）：
   - 在 `pre-commit` 中增加：如果 `_phase` 从 Testing 推进到 Deployment，必须检查最近一次测试命令的退出码（可通过 `test_report.md` 中的命令输出或 CI 结果验证）
   - 或者更简单：在 Testing 阶段的出口门禁中，要求 AI 执行 `pytest`/`npm test` 并将 stdout 写入 `test_report.md` 的"执行日志"章节，门禁检查该章节是否包含"passed"/"0 failed"等关键词

2. **Spotcheck 机制强化**：
   - 当前 `spotcheck_ratio_percent: 10` 只是配置，没有看到实际的 spotcheck 执行逻辑
   - 建议：在 Deployment 阶段门禁中，随机抽取 N 个 GWT-ID，要求 AI 重新执行对应测试并展示实时输出（不是引用之前的结果）
   - 这比检查 `SPOT_CHECK_GWTS` 字段是否非空有效得多

3. **人工 spotcheck 的最小化设计**：
   - 不要求人工审查全部产出物（这不现实）
   - 在 `status.md` 中自动生成"建议人工抽检项"（基于变更复杂度和风险等级），人工只需检查 2-3 个关键点
   - 人工确认后在 `status.md` 中记录 `_human_spotcheck: done`，作为 Deployment 的前置条件

#### 建议 S-006：context 预算机制

**现状**：框架没有 context 预算概念，所有文件都是"能读就读"。
**建议**：在 `aicoding.config.yaml` 中增加 context 预算配置。

```yaml
# Context budget (estimated tokens)
context_budget:
  framework_files_max: 8000    # 框架文件（phases + templates）上限
  project_docs_max: 12000      # 项目文档（requirements + design + plan）上限
  business_code_min: 80000     # 业务代码最低保障
```

**执行方式**：
- CC-4（SessionStart）注入时，计算当前阶段需要读取的框架文件总量
- 如果超过 `framework_files_max`，自动切换到 skeleton 模板
- 在 AI 自动期开始前，输出 context 预算分配提示：
  ```
  📊 Context 预算：框架 ~6K tokens | 项目文档 ~10K tokens | 业务代码 ~84K tokens
  ```

这不需要精确计算，只需要一个粗略的指导，防止框架文件吃掉过多 context。

### 四、优先级排序

| 优先级 | 建议 | 质量提升 | context 节省 | 实施难度 |
|--------|------|---------|-------------|---------|
| 🔴 P0 | S-005.1 测试必须实际执行并通过 | ★★★★★ | — | 低（改 pre-commit） |
| 🔴 P0 | S-001.1 pre-commit 增加编译/类型检查 | ★★★★ | — | 低（改 pre-commit） |
| 🟡 P1 | S-002 分层模板体系 | ★★ | ★★★★★ | 中（拆分模板文件） |
| 🟡 P1 | S-003 阶段定义文件瘦身 | — | ★★★★ | 低（删除冗余内容） |
| 🟡 P1 | S-005.2 Spotcheck 机制强化 | ★★★★ | — | 中（实现抽检逻辑） |
| 🟢 P2 | S-004 requirements.md 按需读取 | — | ★★★ | 中（需要 plan.md 格式配合） |
| 🟢 P2 | S-006 context 预算机制 | ★ | ★★★ | 中（需要 token 估算） |
| 🟢 P2 | S-001.3 CC-7 降级为 warning | — | ★★ | 低（改脚本 exit code） |

### 五、总结

当前框架的核心矛盾可以用一句话概括：**用大量 context 来检查过程痕迹，但没有用少量 context 来检查结果正确性**。

最有效的改进方向是：
1. **增加结果门禁**（测试必须通过、编译必须通过）——这几乎不消耗额外 context，但质量保障效果远超所有过程门禁之和
2. **减少过程门禁的 context 开销**（分层模板、阶段文件瘦身、按需读取）——释放 context 给业务代码，间接提升质量
3. **引入外部校验点**（spotcheck 强化、人工最小化抽检）——打破"AI 自审自批"的闭环

## 附录：质量优先改版建议（执行版）

> 本节由 `er_claude.md` 合并而来，用于落地执行。
> 如需进一步精简，可在此节基础上裁剪。
> 合并后载体：`enr_claude.md`

> 走查日期：2026-02-16  
> 目标：在“交付质量稳定”与“避免上下文爆炸”之间取得可执行平衡  
> 落点文件（合并后）：`enr_claude.md`

---

### 1. 走查范围与方法

#### 1.1 走查范围
- 工作流总控：`ai_workflow.md`
- 阶段定义：`phases/00-change-management.md` ~ `phases/07-deployment.md`
- 门禁设计与实现说明：`hooks.md`
- 模板体系：`templates/*.md`
- 用户操作手册：`manu.md`
- 结构约定：`STRUCTURE.md`
- 关键配置：`aicoding.config.yaml`
- 规则入口模板：`AGENTS.md.template`

#### 1.2 快速体量数据（用于判断上下文开销）
- `hooks.md`: 1949 行
- `review_template.md`: 424 行
- `design_template.md`: 360 行
- `requirements_template.md`: 206 行
- `phases/07-deployment.md`: 304 行
- 阶段文件中“阶段入口协议”高频重复：7 次
- 阶段文件中“阶段开始时检查”高频重复：7 次
- 阶段文件中“读取模板”高频重复：7 次

#### 1.3 走查结论先行
当前体系的方向是对的（把规则落到程序化门禁），但存在两个关键矛盾：
1. 对“过程痕迹”的检查很重，对“结果正确性”的强校验仍不够硬。
2. 为了防止 AI 漏读/漏写，堆叠了大量重复规范，造成上下文占用高、执行成本高、维护成本高。

---

### 2. 总体评价

#### 2.1 做得好的地方
- 已形成“文档规范 + CC hooks + Git hooks + 模板 + 测试脚本”的完整治理链路。
- 对阶段推进、审查文件存在性、结构完整性有明确门禁，降低了“裸奔开发”概率。
- 对 CR 场景、diff-only 审查、审查轮次等有机制约束，方向正确。

#### 2.2 当前最主要风险
- 风险 A（质量不稳）：门禁偏“结构/格式”而非“结果/正确性”。
- 风险 B（上下文爆炸）：规范重复定义过多，AI 每阶段固定阅读负担偏高。
- 风险 C（可维护性）：同一规则在多处重复定义，后续演进容易漂移。

---

### 3. 问题清单（按优先级）

### P0：直接影响质量稳定性的点

#### P0-1 结果门禁不足，过程门禁过重
- 现状：大量检查聚焦“是否有文件/有摘要块/有 ID”，但无法直接证明“代码真的正确”。
- 风险：可以出现“文档完美、实现有误”的假通过。
- 建议：把硬门禁重心从过程迁到结果。

#### P0-2 自审闭环缺少外部校验
- 现状：AI 写代码、AI 自审、AI 出结论，门禁更多在校验格式。
- 风险：自证式通过，问题可能后移到上线前或上线后。
- 建议：引入最小外部校验点（自动抽检 + 人工最小抽检）。

#### P0-3 Minor 流程在小变更场景仍偏重
- 现状：即使小改动仍需较完整审查结构，实际摩擦较大。
- 风险：团队为了赶进度绕过规范，反而破坏治理可信度。
- 建议：新增 `hotfix` 通道，Minor 再轻量化，保障“遵守成本”足够低。

### P1：导致上下文爆炸与维护成本上升的点

#### P1-1 入口/出口协议多处重复定义
- 现状：相同规则分散在 `phases/*.md`、`ai_workflow.md`、`hooks.md`、脚本实现中。
- 风险：改一处漏三处，文档与脚本容易漂移。
- 建议：建立“单一真相源”，其余位置只做引用。

#### P1-2 模板体量过大且常态全量读取
- 现状：`review_template.md`、`design_template.md` 等内容详尽但并非每次都需要。
- 风险：挤占模型上下文，降低业务代码理解深度。
- 建议：模板分层（Skeleton 必读 + Reference 按需）。

#### P1-3 阶段文档存在高比例重复章节
- 现状：7 个阶段文档重复“目标/输入/输出/入口协议/读取模板/完成后”等结构。
- 风险：阅读成本高、真正差异信息被稀释。
- 建议：把共性规则上收总控文件，阶段文件仅保留“本阶段差异规则”。

### P2：工程可维护性问题

#### P2-1 `hooks.md` 承载过重
- 现状：设计、代码片段、决策记录混在一个大文件。
- 风险：文档易过时，阅读和维护双高成本。
- 建议：拆分“设计说明/实现索引/变更记录”。

#### P2-2 配置化不足
- 现状：`aicoding.config.yaml` 配置项较少，许多阈值和白名单仍硬编码。
- 风险：不同项目定制成本高，容易走到“改脚本而非改配置”。
- 建议：把阈值、阶段读取策略、审查抽检参数、模板策略上收配置。

---

### 4. 改版目标与原则

#### 4.1 改版目标
- 目标 1：交付质量更稳定（先保证正确，再保证完备）。
- 目标 2：规范更轻量（减少不必要文本和重复读取）。
- 目标 3：规则可演进（配置优先，单源定义，避免漂移）。

#### 4.2 三条执行原则
1. 结果优先：硬门禁优先检查“测试/构建/关键场景”结果。  
2. 分层治理：核心规则短小强制，详细规则按需展开。  
3. 单一真相源：同一规则只在一个地方定义，其余文件引用。

---

### 5. 建议的新规范架构（核心建议）

### 5.1 三层规范模型

#### Layer A：核心硬规则（短、小、硬）
建议放在 `ai_workflow.md`，控制在 1-2 屏内，明确不可协商规则：
- 必须有可执行验证命令并保留证据。
- 关键阶段推进必须满足结果门禁（测试/构建/类型检查）。
- 高风险变更触发人工最小抽检。
- 禁止无证据完成声明。

#### Layer B：阶段操作卡（差异化、低重复）
建议保留 `phases/*.md`，但每个阶段只包含：
- 本阶段输入/输出的“差异项”。
- 本阶段独有风险与校验动作。
- 与其他阶段不同的例外规则。

去掉重复性强的全局内容：
- 统一入口协议大表。
- 重复的“完成后自动推进”描述。
- 多处重复的通用审查说明。

#### Layer C：参考附录（按需读）
把重文本模板和长说明拆成 Reference：
- `review_reference.md`
- `requirements_reference.md`
- `design_reference.md`

默认只要求读 Skeleton，Reference 在触发条件下读取。

---

### 6. 流程改版建议（质量与成本平衡）

### 6.1 变更等级三轨制

#### `hotfix`（新增，最快路径）
适用：线上紧急修复、极小范围、低设计变更。  
最小要求：
- 代码修改 + 关键测试通过证据。
- 一条简版审查结论（可内联到 `status.md`）。
- 明确回滚点。

#### `minor`（轻流程）
适用：局部功能优化、小范围缺陷修复。  
要求：
- 可追溯到 REQ/GWT（可子集）。
- 必要测试和结论。
- 可选精简审查文件（不强制完整大模板）。

#### `major`（全流程）
适用：跨模块、架构调整、高风险变更。  
要求：
- 保留完整阶段化治理。
- 强制抽检比例提高。

### 6.2 阶段结构建议（兼容现有体系）
在不立即推翻 8 阶段编号的前提下，可逻辑合并为 5 个工作簇：
1. 需求确认（00-02）
2. 方案与计划（03-04）
3. 实施（05）
4. 验证（06）
5. 交付（07）

这样既保持现有脚本兼容，也降低认知分段负担。

---

### 7. 门禁重排建议（从过程门禁转向结果门禁）

### 7.1 建议保留为“硬门禁”的项
- 阶段推进前测试命令通过（与语言栈匹配）。
- 编译/类型检查通过（适用时）。
- 高风险路径改动触发强制抽检。
- 交付前关键文档同步一致性检查。

### 7.2 建议降级为“软门禁/提示”的项
- 纯“是否读过文件”的入口检查。
- 过细的摘要块字段一致性检查。
- 对低风险 minor 的过严结构检查。

### 7.3 审查机制建议
- 保留结构化审查模板，但“摘要字段”减少到最小集。  
- 强化抽检证据，不只看 `pass/fail` 自报值。  
- 对 Implementation/Testing 阶段要求至少 1 条可复现实证输出。

---

### 8. 上下文预算机制（防止规范反噬开发）

建议在 `aicoding.config.yaml` 新增：

```yaml
context_budget:
  framework_files_max_tokens: 8000
  project_docs_max_tokens: 12000
  reserved_for_code_tokens: 80000

template_policy:
  default_mode: skeleton
  auto_fallback_to_reference: true

review_policy:
  summary_fields_minimal: true
  require_runtime_evidence_in_testing: true
```

执行策略：
- 进入阶段时先计算“必读成本估算”，超预算自动切 Skeleton。
- 仅在触发条件下读取 Reference（例如涉及权限、性能、合规场景）。

---

### 9. 文档与脚本更新清单（建议落地）

### P0（1-3 天）
1. `ai_workflow.md`：新增“结果门禁优先”总则。  
2. `scripts/git-hooks/pre-commit`：强化测试/构建/类型检查门禁（按项目栈可配置）。  
3. `templates/review_template.md`：裁剪摘要字段到最小集。  
4. `manu.md`：新增故障处理与应急通道（hotfix/误报处理/恢复步骤）。

### P1（3-7 天）
1. `phases/*.md`：删除重复全局章节，仅保留阶段差异规则。  
2. `templates/`：拆分 Skeleton/Reference。  
3. `hooks.md`：改成设计索引文档，移除大段实现细节。

### P2（1-2 周）
1. `aicoding.config.yaml`：补齐预算、阈值、模板策略、抽检策略。  
2. `scripts/cc-hooks/*`：读取策略与预算联动。  
3. `scripts/tests/*`：新增跨阶段集成测试与抽检逻辑测试。

---

### 10. 验收指标（判断改版是否成功）

### 10.1 质量稳定性指标
- 阶段回退率（phase rollback rate）下降。
- 交付后缺陷率（7/14 天）下降。
- “文档通过但测试失败”类拦截比例下降。

### 10.2 规范成本指标
- 单次任务平均必读规范 tokens 降低 30% 以上。
- `phases/*.md` 总行数降低 35% 以上。
- 模板总必读行数降低 40% 以上（Reference 不计入必读）。

### 10.3 执行体验指标
- Minor/hotfix 平均交付时长下降。
- 因门禁误报导致的中断次数下降。
- 开发者主动绕过规则（如 `--no-verify`）频次下降。

---

### 11. 最终建议（给当前阶段的决策）

建议采用“先稳质量、再减负担”的顺序：
1. 先做 P0，把结果门禁补强，确保质量底线。  
2. 再做 P1，压缩重复规范和模板体量，降低上下文负担。  
3. 最后做 P2，让策略配置化，支持不同项目弹性治理。

这条路径能同时回答你的两个核心担忧：
- 规范不细导致质量不稳：通过结果门禁和外部抽检补齐。  
- 规范过重导致上下文爆炸：通过分层文档和预算机制系统降载。
