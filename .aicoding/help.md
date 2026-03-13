# aicoding 框架使用说明

## 1. 这套框架在做什么

`aicoding` 不是单纯的模板集合，而是一套把“AI 协作开发流程”落到文件结构、状态机和门禁脚本上的框架。它试图解决三个问题：

1. AI 容易不读上下文就直接写。
2. 阶段推进只靠对话约定，缺少可执行约束。
3. 文档、代码、测试、部署证据之间容易失去追溯关系。

这套框架的核心做法是：

- 用 `docs/<版本号>/status.md` 作为单版本迭代的机器状态源。
- 用 `phases/*.md` 定义每个阶段该读什么、该产出什么。
- 用 Claude Code hooks 和 Git hooks 在“写入时”和“提交时”做门禁。
- 用 review / test / deployment 文档把需求、实现、测试、交付串起来。

---

## 2. 运行机制总览

### 2.1 单一真相源

真正决定框架行为的不是某一篇说明文档，而是下面几类文件：

| 范围 | 单一真相源 | 作用 |
|---|---|---|
| 工作流规则 | `ai_workflow.md` | 变更分级、阶段推进、收敛规则、债务规则 |
| 目录与版本约定 | `STRUCTURE.md` | 目录结构、版本迭代方式、CR 约定 |
| 阶段入口/出口清单 | `scripts/lib/common.sh` | 每个阶段必读文件、必需产出物 |
| 内容级校验 | `scripts/lib/validation.sh`、`scripts/lib/review_gate_common.sh` | review/test/report 的结构和追溯校验 |
| 模板 | `templates/*.md` | 产出物格式骨架 |

如果文档描述和脚本行为冲突，最终以脚本为准。

### 2.2 状态机

每个版本目录都必须有一个 `docs/<版本号>/status.md`，它包含 YAML front matter，用来表达当前运行状态：

- `_baseline`：对比基线，通常是上一个版本 tag。
- `_current`：当前代码引用。
- `_workflow_mode`：manual / semi-auto / auto。
- `_run_status`：`running` / `paused` / `wait_confirm` / `wait_feedback` / `completed`。
- `_change_status`：`in_progress` / `done`。
- `_change_level`：`major` / `minor` / `hotfix`。
- `_review_round`：当前阶段审查轮次；常规阶段切换时重置为 0，Hotfix 阶段不受 5 轮上限约束。
- `_phase`：当前阶段。

其中最关键的是：

- `_phase` 决定当前应该产出什么。
- `_change_level` 决定走完整流程、简化流程还是 hotfix 通道。
- `_run_status` 决定当前是在继续执行、等待人工确认，还是等待业务验收反馈。

### 2.3 三种流程

框架不是只有一条流程，而是三条：

| 流程 | 适用场景 | 典型路径 |
|---|---|---|
| major | 新功能、跨模块、API/schema/权限等高影响改动 | ChangeManagement/Proposal → Requirements → Design → Planning → Implementation → Testing → Deployment |
| minor | 小范围增强、非紧急修复、轻量变更 | Proposal → Requirements → Implementation → Testing → Deployment |
| hotfix | 线上紧急、低风险、单点修复 | 切到 `_phase: Hotfix`，独立执行修复与最小验证 |

约束差异：

- `minor` 跳过 Design/Planning，但不会跳过 Requirements、Testing、Deployment。
- `hotfix` 有边界限制：文件数、REQ-C 边界、API/DB schema/权限安全边界。
- `major` 必须走完整阶段，并保留完整设计、计划、测试与部署证据。

### 2.3.1 几个容易踩坑的状态细节

- Hotfix 的标准路径是切到独立 `_phase: Hotfix`，而不是停留在原阶段名里做“隐形热修”。进入后会有独立的入口门禁、文档作用域和退出门禁。
- Hotfix 退出阶段或标记完成前，`status.md` 必须内联 `TEST-RESULT` 结果块；`templates/status_template.md` 现在给了正式示例，不需要再靠测试用例猜格式。
- Minor 如果在 Requirements/Implementation 期间发现复杂度超界，不是“继续硬做”，而是暂停并升级为 Major：Implementation 已经开始时，回到 Design 补 `design.md` / `plan.md`；如果已经到了 Testing/Deployment，则先回 ChangeManagement 重新收敛范围。
- Deployment 中 `wait_feedback` 和 `wait_confirm` 不同义：前者表示“已经部署，等业务验收反馈”，后者表示“需要人工决策/多轮不收敛升级处理”。两者在同一时刻只能选一个。

### 2.4 阶段是怎么被驱动的

阶段推进不是靠“AI 说完成了”，而是靠下面这条链路：

1. AI 在会话开始时接收当前阶段的入口必读提示，并按需读取相关文件。
2. AI 写入阶段产物。
3. Claude Code hook 在写入时检查：
   - 是否写到了当前阶段允许的文件。
   - 是否试图越级推进阶段。
   - 阶段出口产物是否已经齐全。
4. Git commit-msg hook 检查：
   - commit message 格式。
   - 是否一次提交触碰多个版本目录。
   - Active CR 场景下是否带了正确的 CR-ID。
5. Git pre-commit 检查：
   - `status.md` front matter 枚举是否合法。
   - 阶段推进是否合法。
   - 阶段出口产物和内容级证据是否满足。
   - `minor` / `hotfix` 是否越界。
   - `Implementation -> Testing`、`Testing -> Deployment` 时是否执行 result gate 命令。
   - 新版本启动时是否触发质量债务门禁。
6. Git post-commit 输出软警告，留审计痕迹。

### 2.5 Claude Code hooks 的职责

如果目标项目使用 Claude Code，这部分非常关键：

- `SessionStart`：`scripts/cc-hooks/inject-phase-context.sh`
  - 自动注入当前版本、阶段、运行状态、Active CR、入口必读清单。
- `PreToolUse(Edit|Write|MultiEdit)`：`scripts/cc-hooks/pre-write-dispatcher.sh`
  - 统一做 review 追加保护、hotfix 边界检查、人工介入期阶段推进拦截、文档作用域控制、阶段出口门禁。
- `Stop`：`scripts/cc-hooks/stop-gate.sh`
  - 在人工介入期阻止“没等确认就结束”。

注意：

- 入口必读清单现在是会话级提示，不再对 `Read` 行为做运行时硬校验。
- 真正的硬约束仍然在写入范围限制、阶段出口门禁和 Git `pre-commit` 结果校验。

### 2.6 Git hooks 的职责

Git hooks 是这套框架真正的硬门禁：

- `scripts/git-hooks/commit-msg`
  - 校验 commit message 格式。
  - 阻止一次提交同时触碰多个 `docs/vX.Y/`。
  - 在 Active CR 场景下强制带 CR-ID。
- `scripts/git-hooks/pre-commit`
  - 校验 `status.md` 结构与状态机。
  - 校验阶段推进、出口产物、review 证据、测试证据、Deployment 交付证据。
  - 触发 `minor` / `hotfix` 边界门禁。
  - 触发结果门禁和质量债务门禁。
- `scripts/git-hooks/post-commit`
  - 输出风险告警，不阻断提交。
  - 把告警写入日志，便于审计绕过和弱信号问题。
- `scripts/git-hooks/pre-push`
  - 默认阻止日常直接 push 到 `main/master`。
  - 对 Deployment `completed` 执行 release gate：只有主分支 + 匹配版本 tag + 同次 push 才允许通过。

### 2.7 result gate 和质量债务门禁

这两个机制决定框架能不能真正落地到具体项目：

#### result gate

配置在 `aicoding.config.yaml`：

- `result_gate_test_command`
- `result_gate_build_command`
- `result_gate_typecheck_command`

触发时机：

- `Implementation -> Testing`
- `Testing -> Deployment`

如果这些命令为空，框架只会告警，不会硬拦截。也就是说，不填这三项，框架只能约束流程，不能真正约束结果。

#### 质量债务门禁

脚本：`scripts/check_quality_debt.sh`

触发场景：

- 新版本启动。
- 当前阶段为 `Proposal`。
- 当前版本没有 Active CR。

它会检查 `_baseline` 指向版本中的质量债务和技术债务，如果高风险债务过多，会阻断新版本启动。相关阈值现在由 `aicoding_load_config()` 统一加载，后续脚本可以直接复用：

- `quality_debt_max_total`
- `quality_debt_high_risk_max`
- `tech_debt_max_total`

---

## 3. 迁移到具体项目之前，必须先做的事

这一部分是移植前清单。没有完成这些准备，不建议把框架直接接到真实项目里。

### 3.1 确认目标项目的版本与文档策略

至少要先定清楚：

1. 版本目录是否采用 `docs/vMAJOR.MINOR/` 命名。
2. Git tag 是否和版本目录一一对应。
3. 新版本启动时 `_baseline` 指向哪个 tag。
4. 是否接受“一个提交只绑定一个版本目录”的限制。

如果你的项目版本目录不是 `v1.0`、`v1.1` 这种形式，必须先改 `version_dir_pattern`。

### 3.2 准备项目级 result gate 命令

这是最容易漏掉、但最关键的配置项。你需要先确定项目真实可执行的三条命令：

- 测试命令
- 构建命令
- 类型检查命令

建议直接复用 CI 命令，不要再造一套本地口径。常见例子：

```yaml
result_gate_test_command: "uv run pytest -q --tb=short"
result_gate_build_command: "cd web && npm run build"
result_gate_typecheck_command: "cd web && npm run typecheck"
```

### 3.3 校准 minor / hotfix / 债务阈值

默认值只能作为起点，不能直接当成生产值。需要结合项目真实体量校准：

- `minor_max_diff_files`
- `minor_max_new_gwts`
- `hotfix_max_diff_files`
- `spotcheck_ratio_percent`
- `spotcheck_min`
- `spotcheck_max`
- `deferred_limit_percent`
- `quality_debt_max_total`
- `quality_debt_high_risk_max`
- `tech_debt_max_total`
- `high_risk_review_patterns`

如果不校准，轻则误拦截，重则把本应升级为 major/hotfix 的改动放过去。

### 3.4 准备项目文档底座

至少要准备：

- `docs/` 根目录
- 第一个版本目录，如 `docs/v1.0/`
- `status.md`

如果是存量系统，建议同时补齐主文档：

- `docs/系统功能说明书.md`
- `docs/技术方案设计.md`
- `docs/接口文档.md`
- `docs/用户手册.md`
- `docs/部署记录.md`

这些主文档不是每次迭代都新建，但 Deployment 阶段通常需要同步。

### 3.5 确认工具链依赖

最少依赖：

- `bash`
- `git`
- `awk`
- `grep`
- `sed`

如果使用 Claude Code hooks，还需要：

- `jq`

补充说明：

- `rg` 现在已经有回退逻辑，没有 `ripgrep` 也能运行，但有 `rg` 时体验更好。

### 3.6 决定是否启用 Claude Code hooks

如果目标项目只使用 Git hooks，不使用 Claude Code，也能运行，但会失去“会话入口提示”和“写入期引导”能力。

也就是说：

- 只装 Git hooks：有提交期硬门禁。
- 再配 Claude Code hooks：多出会话开始提醒、写入时拦截、停止时收口。

### 3.7 明确哪些规则仍然是软规则

目前仍无法完全程序化强制的规则包括：

- 不在主分支直接开发
- CR 澄清对话本身是否真的发生
- 用户确认事件本身是否真实发生
- 频繁提交是否执行到位

所以落地前要和团队说清楚：这套框架不是“所有规则都自动化”，而是“关键结构和关键结果自动化”。

---

## 4. 移植到具体项目的推荐步骤

下面是一套最小可执行步骤，适合把当前框架接到一个真实项目。

### 第 1 步：复制框架到目标项目

推荐目录结构：

```text
<your-project>/
├── .aicoding/
│   ├── ai_workflow.md
│   ├── STRUCTURE.md
│   ├── hooks.md
│   ├── aicoding.config.yaml
│   ├── phases/
│   ├── templates/
│   └── scripts/
└── docs/
```

框架仓库自身为了自举，配置文件在根目录也能被读取；真正移植到业务项目时，建议使用规范位置：

```text
.aicoding/aicoding.config.yaml
```

### 第 2 步：填写项目配置

先修改 `.aicoding/aicoding.config.yaml`，至少填这几项：

1. `result_gate_test_command`
2. `result_gate_build_command`
3. `result_gate_typecheck_command`
4. `version_dir_pattern`（如果版本目录命名不兼容默认值）
5. `minor` / `hotfix` / 债务阈值

如果你在这一步偷懒，后面的门禁大概率会形同虚设。

### 第 3 步：初始化版本目录和状态文件

最少动作：

1. 创建 `docs/v1.0/`
2. 用 `.aicoding/templates/status_template.md` 初始化 `docs/v1.0/status.md`
3. 填好 `_baseline`、`_current`、`_workflow_mode`、`_change_level`、`_phase`

新版本通常从：

- `_phase: Proposal`
- `_change_level: major` 或 `minor`

开始。

如果是同版本补丁或变更单场景，再走 `ChangeManagement` 或 `Hotfix`。

### 第 4 步：安装 Git hooks

在目标项目根目录执行：

```bash
bash .aicoding/scripts/install-hooks.sh
```

这个脚本会把以下 hooks 安装到 `.git/hooks/`：

- `pre-commit`
- `commit-msg`
- `post-commit`
- `pre-push`

它会备份原有非框架 hooks。

### 第 5 步：接入 Claude Code hooks

如果项目使用 Claude Code，需要在项目的 `.claude/settings.local.json` 中注册 hooks。移植到目标项目后，建议直接按下面的路径挂载：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|MultiEdit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash $CLAUDE_PROJECT_DIR/.aicoding/scripts/cc-hooks/pre-write-dispatcher.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash $CLAUDE_PROJECT_DIR/.aicoding/scripts/cc-hooks/doc-structure-check.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash $CLAUDE_PROJECT_DIR/.aicoding/scripts/cc-hooks/stop-gate.sh"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash $CLAUDE_PROJECT_DIR/.aicoding/scripts/cc-hooks/inject-phase-context.sh"
          }
        ]
      }
    ]
  }
}
```

如果路径还是写成当前仓库的自举形式 `scripts/...`，移植后 hooks 会失效。

### 第 6 步：准备基线和版本标签

框架默认假设：

- 版本目录和 Git tag 对齐。
- `_baseline` 指向一个真实存在的 tag。
- 新版本启动时，会拿 `_baseline` 去检查上一版本债务。

因此在业务项目里，至少要保证：

1. 已有基线 tag 存在，如 `v1.0`
2. `docs/v1.0/status.md` 存在
3. 新版本如 `v1.1` 的 `_baseline` 能指回 `v1.0`

### 第 7 步：做一次冒烟验证

建议至少验证以下内容：

1. Git hooks 是否成功安装。
2. Claude Code hooks 是否被触发。
3. 新建 `docs/v1.0/status.md` 后，能否被正确识别当前阶段。
4. 故意提交一个缺少必要产物的阶段推进，确认 `pre-commit` 会拦截。
5. 故意省略 `result_gate_*_command`，确认出现的是告警而不是误以为门禁已生效。

### 第 8 步：再跑一遍框架自检

如果目标项目保留了 `.aicoding/scripts/tests`，建议执行：

```bash
bash .aicoding/scripts/tests/run-all.sh
```

至少能确认框架脚本本身在目标环境下还能跑通。

---

## 5. 迁移后的日常使用方式

一旦落地完成，日常协作的最小节奏通常是：

1. 用户提出需求或修改。
2. AI 根据 `status.md` 判断是新版本、同版本 CR，还是 hotfix。
3. AI 读取当前阶段必读文件。
4. AI 产出本阶段文档或代码。
5. 人工或 AI 追加对应 review。
6. 修改 `status.md` 推进到下一阶段。
7. 提交时由 Git hooks 做最终硬校验。
8. Deployment 完成后，把主文档同步到最新截面。
9. 在主分支用 `scripts/release-complete.sh <版本tag> [remote]` 完成 tag + push 收口；只有这一步完成后，`completed` 才算成立。

---

## 6. 建议的最小上线标准

如果你要把这套框架真正用到业务项目，至少满足这四条再开始：

1. `result_gate_test_command`、`build`、`typecheck` 都已经填成项目真实命令。
2. Git hooks 已安装，Claude Code hooks 已接通。
3. 版本目录、tag、`_baseline` 规则已经跑通过一次。
4. 团队知道哪些是硬门禁，哪些仍然是流程纪律。
5. 团队知道业务验收通过不等于基线已形成；`completed` 只在主分支 + tag + 远端同步后成立。

只满足“模板复制过去了”，不算真正落地。
