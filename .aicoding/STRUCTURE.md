# `.aicoding/` 目录结构与约定

> **快速导航：** 本文档包含目录结构、版本迭代规则、ID前缀约定、Git管理规范

## 规范索引（单一真相源）

当你需要查阅某个规则时，只读以下唯一真相源，不要读其他副本：

| 领域 | 唯一真相源 | 包含内容 |
|------|-----------|---------|
| 工作流规则 | `ai_workflow.md` | 变更分级、阶段推进、收敛判定、债务管理 |
| 状态机语义 | `ai_workflow.md` | Major/Minor/Hotfix、wait_confirm语义 |
| 阶段入口/出口 | `scripts/lib/common.sh` | 每个阶段的必读文件、必须产出文件 |
| CR状态枚举 | `phases/cr-rules.md` | CR状态定义、转换规则 |
| 主文档清单 | 本文档"两类文档"章节 | 6个主文档的定义 |

---

## 目录结构
```
.
├── AGENTS.md（或 CLAUDE.md）
├── .aicoding/
│   ├── STRUCTURE.md          ← 本文件
│   ├── aicoding.config.yaml  ← 框架配置（门禁阈值/模式）
│   ├── ai_workflow.md        ← 工作流控制规则
│   ├── hooks.md              ← Hook 设计索引（精简）
│   ├── hooks_implementation_reference.md ← Hook 实现参考（详版）
│   ├── phases/               ← 阶段流程定义
│   │   └── cr-rules.md       ← CR 通用规则（跨阶段）
│   └── templates/            ← 文档模板
└── docs/
    ├── lessons_learned.md    ← 经验教训（跨版本追加）
    ├── 系统功能说明书.md      ← 截面式：当前系统全貌
    ├── 技术方案设计.md        ← 截面式：当前架构全貌
    ├── 接口文档.md            ← 截面式：当前 API 全貌
    ├── 用户手册.md            ← 截面式：当前操作指南
    ├── 部署记录.md            ← 追加式：每次部署日志
    └── <版本号>/              ← 本次迭代的过程文档
        ├── status.md          ← 单一真相源
        ├── proposal.md、requirements.md、design.md
        ├── plan.md、test_report.md、deployment.md
        ├── cr/                ← 变更单（可选）
        └── review_*.md        ← 审查报告（可选）
```

**两类文档**：
- **主文档**（`docs/*.md`）：描述系统当前状态，每次部署后同步更新
- **版本文档**（`docs/<版本号>/`）：记录本次迭代的过程与结论

## 版本号
- 格式：`vMAJOR.MINOR`（如 `v1.0`、`v1.1`、`v2.0`）
- MAJOR：大版本迭代（新功能、架构变更）；MINOR：小版本迭代（增强、修复）
- 版本目录与 Git tag 保持一致：`docs/v1.0/` 对应 Git tag `v1.0`
- 首次开发从 `v1.0` 开始

## 版本迭代规则

### 部署完成后的变更决策

当项目处于 `completed` 状态时，用户提出新变更需求，AI 必须：
1. 分析变更描述，给出建议（参考下表）
2. 询问用户确认："这是 v1.0 的补丁修复，还是要开始 v1.1 新版本？"
3. 用户明确指定后，执行对应流程
4. 版本内变更默认创建 CR，进入 Phase 00 澄清流程；新版本启动直接从 Proposal 开始

> 补充：Hotfix 是"当前版本补丁"中的紧急特例。它仍属于同版本变更，但满足 hotfix 边界时可跳过 Phase 00，并切换到独立 `_phase: Hotfix` 执行。

| 变更性质 | AI 建议参考（关键词） | 操作方式 |
|---------|---------------------|---------|
| 遗漏/Bug/Hotfix | "修复"、"Bug"、"遗漏"、"缺陷" | 在当前版本处理（通常追加 CR；满足 hotfix 边界时走 hotfix 特例） |
| 新功能/重构/增强 | "新功能"、"新版本"、"重构"、"架构" | 创建新版本目录 |

### 何时创建新版本目录

- 新功能开发（不在原需求范围内）
- 架构升级或重构
- 大规模功能增强
- 用户明确指定"新版本"

### 何时在当前版本追加 CR

- 部署后发现的遗漏功能（原需求范围内）
- 部署后发现的 Bug 或缺陷
- 原需求的小幅调整
- 紧急 Hotfix（满足 hotfix 边界时可不创建 CR 文档）
- 用户明确指定"补丁"

### 基线管理

- 每次部署完成后，在主分支打 tag（如 `v1.0`）
- 新版本的 `_baseline` 指向前一版本的 tag
- 同版本追加 CR 时，`_baseline` 保持不变

### CR 创建规则

- **版本内的范围调整**必须创建 CR（已测试/已完成后的新需求）
- **新版本启动**不需要 CR，直接从 Proposal 开始
- CR 必须经过 Phase 00 澄清流程（范围、验收、影响面、风险）
- CR 状态从 Idea → Accepted → In Progress → Implemented
- `status.md` 中的 **Active CR 列表**只跟踪 `Accepted / In Progress`；`Idea` 状态应记录在 `Idea池`，不进入 Active 列表

## Git 管理（AI 自动执行）

> 用户无需手动操作 Git。AI 按以下原则自动管理，确保可追溯、可回滚。

**AI 行为规范**（依赖 AI 自觉执行，部分规则无硬校验）：
1. **不在主分支直接开发**：开始工作前从主分支（`main`/`master`）切出工作分支（命名：`feat/<描述>` 或 `cr/<CR-ID>`）
2. **频繁提交**：每完成一个有意义的步骤就提交，消息格式 `<type>: <描述>`（type：feat/fix/docs/test/refactor/chore），有 CR 时加前缀 `[CR-ID]`
3. **完成后打 tag**：部署完成后在主分支（`main`/`master`）上打版本 tag（如 `v1.0`），作为下次迭代的基线
4. **合入主分支**：通过 PR 合入主分支（`main`/`master`），推荐 Squash and merge
   - **Squash merge 时的 CR-ID 规则**：Squash 后的单条 commit 消息必须包含本次涉及的所有 CR-ID，格式：`feat: <描述> [CR-YYYYMMDD-001, CR-YYYYMMDD-002]`
   - PR 标题/描述中也应列出所有 CR-ID，便于追溯
5. **禁止危险操作**：`push --force`、`reset --hard`、`branch -D` 等必须经用户授权
6. **远端同步**：非 PR 的主分支操作（打 tag、hotfix 合入等）完成后，须将 commit 和 tag 一并 push 到远端，确认 `ahead_by=0`
7. **completed 只在基线形成后出现**：`docs/<版本号>/status.md` 的 `done + completed` 只能出现在主分支收口场景；`pre-push` / CI 会拦截“未随主分支和 tag 一起发布的 completed”
8. **Commit message 自动生成**：AI 根据 diff 按现有格式规范（`<type>: <描述>`，有 CR 时加 `[CR-ID]`）自动生成，无需询问用户

> **注意**：规则 1 仍主要依赖 AI/团队纪律；规则 3/4/6/7 现在由 `pre-push`、CI release gate 和 `scripts/release-complete.sh` 部分程序化约束，但仍不替代 PR 审核与发布审批。

## 变更单（CR）
- 适用：已完成/已测试后出现新需求或范围调整
- 路径：`docs/<版本号>/cr/CR-YYYYMMDD-NNN.md`
- 详细流程：见 `.aicoding/phases/00-change-management.md`
- 跨阶段规则：见 `.aicoding/phases/cr-rules.md`

## 模板索引

| 文档 | 模板路径 |
|------|---------|
| **版本文档** | |
| status.md | `templates/status_template.md` |
| proposal.md | `templates/proposal_template.md` |
| requirements.md | `templates/requirements_template.md` |
| design.md | `templates/design_template.md` |
| plan.md | `templates/plan_template.md` |
| test_report.md | `templates/test_report_template.md` |
| deployment.md | `templates/deployment_template.md` |
| **主文档** | |
| lessons_learned.md | `templates/lessons_learned_template.md` |
| 系统功能说明书.md | `templates/master_system_function_spec_template.md` |
| 技术方案设计.md | `templates/master_design_template.md` |
| 接口文档.md | `templates/master_api_doc_template.md` |
| 用户手册.md | `templates/master_user_manual_template.md` |
| 部署记录.md | `templates/master_deployment_log_template.md` |
| **辅助** | |
| 实现检查清单 | `templates/implementation_checklist_template.md` |
| 审查模板 | `templates/review_template.md` |
| Minor 审查模板 | `templates/review_minor_template.md` |
| 变更单（CR） | `templates/cr_template.md` |

## ID 前缀约定

| 前缀 | 含义 | 示例 |
|------|------|------|
| `SCN-` | 业务场景 | SCN-001 |
| `REQ-` | 需求项（功能性/非功能） | REQ-001 |
| `REQ-C` | 约束与禁止项（负向需求，与 REQ 同等地位） | REQ-C001 |
| `GWT-` | 验收标准外键（Given/When/Then，门禁最小单位） | GWT-REQ-001-01 |
| `FUNC-` | 系统功能项（系统功能说明书用） | FUNC-001 |
| `API-` | 接口/契约 | API-001 |
| `TEST-` | 测试用例 | TEST-001 |
| `T` | 开发任务 | T001 |
| `BUG-` | 缺陷 | BUG-001 |

## 代码风格（AI 自动管理）

- AI 实现时遵循项目已有的 lint/format 配置
- 如项目无配置文件，AI 按语言社区主流规范创建（如 Python 用 ruff、JS/TS 用 ESLint+Prettier、Go 用 golangci-lint）
