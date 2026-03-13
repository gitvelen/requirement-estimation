# Hooks 方案：程序化质量门禁（实现参考）

> **说明**：本文档是 hooks 实现的精简参考。完整索引见 `hooks.md`。
> 对于实现细节，优先阅读脚本源码：`scripts/cc-hooks/` 和 `scripts/git-hooks/`

## 1. 问题背景

当前框架的所有质量规则（阶段门禁、CR 追溯、文档一致性等）完全依赖 AI 自觉执行文本指令。实际开发中 AI 会跳过规则、遗漏检查，导致交付质量不稳定。

**核心矛盾**：规则写得再详细，如果没有程序化强制执行，就只是建议。

## 2. 设计约束

| 约束 | 说明 |
|------|------|
| 双工具兼容（AI 自动期） | Phase 03-06 同时使用 Claude Code 和 Codex，Git hooks 必须对两者都生效 |
| Codex 无 hooks 机制 | Codex 仅支持 AGENTS.md 文本规则 + sandbox 隔离，不支持 Claude Code 的 PreToolUse/PostToolUse |
| 最大公约数 = Git hooks | `.git/hooks/` 是唯一对 Claude Code 和 Codex 都生效的程序化执行点 |
| Claude Code hooks 全阶段生效 | CC hooks 不再限于 Phase 00-02，CC-3/CC-4/CC-6/CC-7/CC-7b 全阶段生效，CC-8 在 Phase 02-06 生效 |
| `--no-verify` 可绕过 | Git hooks 可被 `--no-verify` 跳过，但仅影响 pre-commit 和 commit-msg，post-commit 不受影响 |
| `.git/hooks/` 不被 git 跟踪 | 需要安装脚本，每次 clone 后手动执行 |

## 3. 架构决策：双层 hooks 体系

用户指挥多个 AI 工具（多个 Claude、Codex 等）协作开发，本方案默认不依赖 CI（可选启用）。根据阶段特征采用两层互补的 hooks 体系：

```
┌─────────────────────────────────────────────────────────────────┐
│                    Claude Code Hooks 层                          │
│           （全阶段生效，Phase 00-02 + Phase 03-07）              │
│                                                                  │
│  拦截 AI 的实时工具调用（Write/Edit/Stop/SessionStart）          │
│  入口提示 + 写入守卫 + 结构反馈 + 收口校验                      │
│  只对 Claude Code 生效                                           │
├─────────────────────────────────────────────────────────────────┤
│                      Git Hooks 层                                │
│                （全阶段通用，全工具兼容）                         │
│                                                                  │
│  拦截 commit 动作                                                │
│  硬拦截 7 个（pre-commit / commit-msg，含交付关口条件拦截+出口门禁）│
│  软警告 21 个脚本 + 内置 W23/W24（post-commit）                  │
│  对 Claude Code 和 Codex 都生效                                  │
└─────────────────────────────────────────────────────────────────┘
```

两层的关系是**互补而非替代**：
- Claude Code hooks 管"AI 正在做什么"（实时行为）
- Git hooks 管"AI 提交了什么"（落盘结果）

### hooks 的定位原则

hooks 只做**流程守卫和结构校验**，不做内容质量判断：

| hooks 该管 | hooks 不该管 |
|-----------|-------------|
| 流程是否被遵守（阶段门禁、暂停机制、文件作用域） | 内容质量好不好（proposal 写得深不深、需求够不够细） |
| 结构是否完整（必填章节是否存在、GWT 是否有） | 语义是否正确（需求有没有矛盾、术语是否一致） |
| 上下文是否充分（AI 是否知道当前阶段） | 对话是否充分（AI 有没有深入追问用户） |

质量判断是人和 review 的职责。hooks 只确保"该走的流程走了、该有的东西有了"。

---

## 4. Claude Code Hooks：全阶段流程守卫（9 个）

Claude Code hooks 覆盖全部阶段（Phase 00-07），利用其 hooks 机制对 AI 的实时工具调用做程序化检查。

配置位置：`.claude/settings.json`（项目级）或 `.claude/settings.local.json`（本地不提交）。

### 4.1 设计原则

- **只管流程，不管质量**：检查结构和流程合规性，不判断内容好坏
- **确定性优先**：只做正则/文件存在性等确定性检查，避免语义判断导致误报
- **PreToolUse 拦截 vs PostToolUse 反馈**：破坏性操作（覆盖 review、推进阶段）用 PreToolUse 阻止；可修复的缺陷（缺章节）用 PostToolUse 反馈给 AI 自动补充
- **静默通过**：检查通过时 exit 0 无输出，不干扰正常工作流

### 4.2 阻断协议

不同事件类型使用不同的阻断方式，这是 Claude Code 的官方协议：

| 事件 | 阻断方式 | 说明 |
|------|---------|------|
| **PreToolUse** | `exit 0` + JSON `{"decision":"block","reason":"..."}` | 通过 `aicoding_block()` 统一输出阻断原因并阻止工具调用 |
| **PostToolUse** | `exit 0` + JSON `{"decision":"block","reason":"..."}` | 工具已执行完毕，reason 反馈给 AI 做自我修正 |
| **Stop** | `exit 0` + JSON `{"decision":"block","reason":"..."}` | 阻止 AI 停止，reason 告知 AI 继续工作的原因 |
| **SessionStart** | 仅注入上下文，不阻断 | `exit 0` + JSON `{"hookSpecificOutput":{"additionalContext":"..."}}` |

> 说明：本仓库当前实现统一通过 `scripts/lib/common.sh` 的 `aicoding_block()` 输出 JSON block，避免多脚本间阻断协议漂移。

### 4.3 Hooks 清单

#### CC-Hook 1：阶段推进拦截（PreToolUse）

**解决的问题**：AI 在人工介入期自行修改 status.md 的"当前阶段"字段推进到下一阶段。

**设计决策**：
- 只拦截 status.md 的 `_phase` 字段修改
- 只在人工介入期（Proposal/Requirements/ChangeManagement）生效
- 使用正则匹配检测阶段推进意图

**边界条件**：
- 非人工介入期放行
- AI 仍可编辑 status.md 的其他字段（如 `_run_status: wait_confirm`）

**实现位置**：`scripts/cc-hooks/phase-transition-guard.sh`

---

#### CC-Hook 2：Stop 门禁（Stop）

**解决的问题**：AI 完成阶段产出后直接停止，没有设 `wait_confirm`，或未经过审查流程。

**设计决策**：
- 检查 `_run_status` 是否为 `wait_confirm`
- 检查对应阶段的 review 文件是否存在
- 只在人工介入期生效

**边界条件**：
- 使用 `stop_hook_active` 标志防止无限循环
- 非人工介入期放行

**实现位置**：`scripts/cc-hooks/stop-gate.sh`

---

#### CC-Hook 3：文档作用域控制（PreToolUse）

**解决的问题**：AI 在当前阶段写入不属于该阶段的文档（如在 Requirements 阶段写 design.md）。

**设计决策**：
- 维护每个阶段允许写入的文档白名单
- 使用正则匹配文件路径
- 全阶段生效

**边界条件**：
- review/status/cr 文件在所有阶段都允许
- Implementation/Testing 阶段允许回溯修改 design/requirements/plan

**实现位置**：`scripts/cc-hooks/doc-scope-guard.sh`

---

#### CC-Hook 4：会话上下文注入（SessionStart）

**解决的问题**：AI 不知道当前处于哪个阶段，导致行为不符合阶段规范。

**设计决策**：
- 读取 status.md 的 `_phase` 字段
- 通过 `additionalContext` 注入当前阶段信息
- 不阻断，仅注入上下文

**实现位置**：`scripts/cc-hooks/inject-phase-context.sh`

---

#### CC-Hook 5：产出物结构校验（PostToolUse）

**解决的问题**：AI 创建的文档缺少必要章节（如 proposal 缺少 GWT）。

**设计决策**：
- 按文件类型检查必要章节
- 使用 PostToolUse 反馈给 AI 自动补充
- 不阻断写入，让 AI 自我修正

**边界条件**：
- 只检查新创建的文件（Write 工具）
- Edit 工具不触发

**实现位置**：`scripts/cc-hooks/post-write-validator.sh`

---

#### CC-Hook 6：review 文件追加保护（PreToolUse）

**解决的问题**：AI 用 Write 覆盖已有的 review 文件，导致历史审查记录丢失。

**设计决策**：
- 检测 review 文件是否已有审查轮次
- 如果有，阻止 Write 工具，要求使用 Edit 追加
- 使用 PreToolUse 阻断（覆盖后不可恢复）

**实现位置**：`scripts/cc-hooks/review-append-guard.sh`

---

#### CC-Hook 7：阶段入口提示（SessionStart）

**解决的问题**：让 AI 在会话开始时拿到当前阶段的入口必读清单，减少遗漏关键上下文的概率。

**设计决策**：
- 必读清单来自 `aicoding_phase_entry_required()` 函数
- 通过 `SessionStart` 的 `additionalContext` 注入提示
- 写入期不再维护读取历史，不再阻断 `Read` 顺序

**边界条件**：
- 只提供提示，不做运行时硬校验
- 阶段范围限制和阶段出口完整性仍由其他 gate 负责

**实现位置**：`scripts/cc-hooks/inject-phase-context.sh`，`scripts/cc-hooks/phase-entry-gate.sh`（兼容 shim）

---

#### CC-Hook 8：阶段出口门禁（PreToolUse）

**解决的问题**：AI 推进阶段时，当前阶段的必要产出物尚未完成。

**设计决策**：
- 检测 status.md 的 `_phase` 字段变更
- 检查当前阶段的必要产出物是否存在
- 使用 `aicoding_phase_exit_required()` 函数获取清单
- 生效范围：Requirements + AI 自动期（Phase 02-06）

**边界条件**：
- minor Testing 需要额外检查测试证据
- hotfix 不推进阶段，不触发

**实现位置**：`scripts/cc-hooks/pre-write-dispatcher.sh` (Gate 5)

---

## 5. Git Hooks：硬拦截（7 个）

Git hooks 在 commit 时执行，对所有 AI 工具（Claude Code、Codex）都生效。

**实现位置**：`scripts/git-hooks/pre-commit`

### 5.1 硬拦截清单

| Hook | 触发条件 | 检查内容 |
|------|---------|---------|
| **Git-Hook 1** | status.md 变更 | YAML front matter 字段完整性、枚举值合法性 |
| **Git-Hook 2** | status.md 阶段推进 | 阶段跳跃检测、相邻阶段校验 |
| **Git-Hook 3** | 文档作用域 | 当前阶段是否允许提交该文档 |
| **Git-Hook 4** | CR 文件变更 | CR 必填字段完整性 |
| **Git-Hook 5** | git 配置文件 | 防止 .gitconfig/.gitmodules 被篡改 |
| **Git-Hook 6** | 交付关口 | _run_status=wait_confirm 或 _change_status=done 时的交付条件 |
| **Git-Hook 7** | 阶段推进 | 阶段出口门禁：必要产出物存在性、证据清单完整性 |

### 5.2 关键设计决策

#### Git-Hook 7：阶段出口门禁 + 证据清单检查

**设计决策**：
- 检测 status.md 的 `_phase` 字段从 OLD_PHASE → NEW_PHASE
- 检查 OLD_PHASE 的必要产出物是否存在
- **新增**：检查 review 文件是否包含"## 证据清单"段落
- 使用正则匹配：`^## 证据清单|^### 证据清单|^## §证据清单|^### §证据清单`

**边界条件**：
- minor 场景不要求 review_minor.md 有证据清单（在 Implementation 阶段）
- minor Testing 场景要求 review_minor.md 有证据清单
- hotfix 不推进阶段，不触发

**实现位置**：`scripts/git-hooks/pre-commit:1006-1063`

---

#### CR 遗漏智能提示

**设计决策**：
- 检测代码变更涉及核心文件（frontend/src/pages/、backend/app/api/ 等）
- 检查 status.md 中是否有 Active CR
- 如果没有，提示用户确认是否需要创建 CR
- 排除 refactor/test/chore/docs 类型的 commit

**边界条件**：
- 不阻断提交，仅提示
- 用户可以选择继续或取消

**实现位置**：`scripts/git-hooks/pre-commit:1244-1283`

---

## 6. Git Hooks：软警告（21 个脚本 + 2 个内置检查）

post-commit 在 commit 完成后执行，不阻断工作流。输出警告信息，AI 看到后可自行修复并追加 commit。

> **`--no-verify` 与 post-commit**：`--no-verify` 只跳过 pre-commit 和 commit-msg，**不跳过 post-commit**。

**实现位置**：`scripts/git-hooks/warnings/W*.sh` + `scripts/git-hooks/post-commit`

### 6.1 Warning 清单

| Warning | 检查内容 | 实现位置 |
|---------|---------|---------|
| **W6** | 文档阶段出现代码文件变更 | `warnings/w06-code-in-doc-phase.sh` |
| **W7** | CR 必填字段完整性 | `warnings/w07-cr-required-fields.sh` |
| **W8** | 阶段产出文件存在性 | `warnings/w08-phase-artifacts.sh` |
| **W9** | REQ 引用存在性 | `warnings/w09-req-references.sh` |
| **W10** | 基线版本 tag 可达性 | `warnings/w10-baseline-reachable.sh` |
| **W11** | 文档变更日志同步 | `warnings/w11-doc-changelog.sh` |
| **W12** | CR 影响面与 diff 一致性 | `warnings/w12-cr-scope-consistency.sh` |
| **W13** | Deployment 阶段 Active CR 提交证据提醒 | `warnings/w13-deployment-cr-evidence.sh` |
| **W14** | 设计文档决策记录非空 | `warnings/w14-design-decisions.sh` |
| **W15** | 测试报告覆盖 CR 验收标准 | `warnings/w15-test-coverage-cr.sh` |
| **W16** | test_report 证据与结论完整性 | `warnings/w16-test-report-completeness.sh` |
| **W17** | plan.md 任务缺少验证命令 | `warnings/w17-plan-verification.sh` |
| **W18** | 高风险变更缺少 CR 声明 | `warnings/w18-high-risk-cr.sh` |
| **W19-W22** | （其他检查） | `warnings/w19-w22.sh` |
| **W23** | 审查轮次告警（内置） | `post-commit:内置` |
| **W24** | 逃生通道审计（内置） | `post-commit:内置` |
| **W25-W28** | （其他检查） | `warnings/w25-w28.sh` |

---

## 7. 副作用分析与应对

### 7.1 误报风险

**问题**：正则匹配可能误判，导致合法操作被拦截。

**应对**：
- 优先使用确定性检查（文件存在性、YAML 字段）
- 正则匹配尽量精确，避免过度匹配
- 提供清晰的错误信息，帮助用户理解拦截原因
- 关键门禁提供逃生通道（如 `[skip-cr-check]`）

### 7.2 开发体验

**问题**：频繁拦截可能影响开发流畅度。

**应对**：
- PreToolUse 只拦截破坏性操作
- PostToolUse 用于可修复的缺陷，让 AI 自我修正
- 软警告不阻断工作流
- 静默通过，检查通过时无输出

### 7.3 维护成本

**问题**：hooks 脚本分散，维护困难。

**应对**：
- 提取共享函数库（`scripts/lib/common.sh`、`scripts/lib/validation.sh`）
- 统一阻断协议（`aicoding_block()`）
- 文档索引（`hooks.md`）+ 实现参考（本文档）

---

## 8. 落地策略

### 8.1 安装

```bash
# 安装 git hooks
bash scripts/install-hooks.sh

# 验证安装
ls -la .git/hooks/
```

### 8.2 配置

**Claude Code hooks**：编辑 `.claude/settings.json`，参考 `hooks.md` 的配置示例。

**Git hooks**：无需额外配置，安装后自动生效。

**框架配置**：编辑 `aicoding.config.yaml`，调整门禁阈值和模式。

### 8.3 CI 集成（推荐）

将门禁最终裁决上收到 CI（如 GitHub Actions）：

```yaml
# .github/workflows/quality-gates.yml
name: Quality Gates
on: [pull_request]
jobs:
  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run quality gates
        run: bash scripts/git-hooks/pre-commit
```

**GitHub 配置**：
- 对 `main`/`master` 启用 Branch protection
- Require PR + Require status checks
- Required check 选择：`Quality Gates / quality-gates`

---

## 9. 与现有框架的关系

| 组件 | 职责 | 与 hooks 的关系 |
|------|------|---------------|
| `ai_workflow.md` | 定义工作流规则 | hooks 强制执行这些规则 |
| `phases/*.md` | 定义阶段流程 | hooks 检查阶段门禁 |
| `templates/*.md` | 提供文档模板 | hooks 检查文档结构 |
| `scripts/lib/common.sh` | 提供共享函数 | hooks 调用这些函数 |
| `aicoding.config.yaml` | 配置门禁阈值 | hooks 读取配置 |

---

## 10. 决策记录

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-02 | 采用双层 hooks 体系 | Claude Code hooks 管实时行为，Git hooks 管落盘结果，互补而非替代 |
| 2026-02 | CC hooks 全阶段生效 | Phase 03-06 也需要流程守卫，不再限于 Phase 00-02 |
| 2026-02 | 证据清单硬校验 | 收敛判定需要验证证据，pre-commit 强制检查 |
| 2026-03 | CR 遗漏智能提示 | 核心文件变更时提示创建 CR，避免遗漏 |
| 2026-03 | 提取共享验证函数库 | 避免 pre-commit 和 pre-write-dispatcher 重复实现 |

---

## 附录：快速参考

### 常用命令

```bash
# 查看 hooks 状态
bash scripts/check-hooks.sh

# 重新安装 hooks
bash scripts/install-hooks.sh

# 查看 gate 告警日志
cat .git/aicoding/gate-warnings.log
```

### 常见问题

**Q: hooks 拦截了我的合法操作，怎么办？**
A: 检查错误信息，确认是否符合规则。如果确实是误报，可以临时使用 `git commit --no-verify`（仅限 pre-commit），但建议修复根本问题。

**Q: 如何禁用某个 hook？**
A: Claude Code hooks：编辑 `.claude/settings.json`，删除对应 hook 配置。Git hooks：删除 `.git/hooks/` 中的对应文件。

**Q: hooks 性能如何？**
A: 大部分 hooks 在 100ms 内完成。阶段推进时的门禁检查可能需要 1-2 秒。

**Q: 如何调试 hooks？**
A: 在 hook 脚本开头加 `set -x` 启用调试输出，或查看 `.git/aicoding/gate-warnings.log`。
