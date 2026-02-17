# `.aicoding/` 目录结构与约定

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

## Git 管理（AI 自动执行）

> 用户无需手动操作 Git。AI 按以下原则自动管理，确保可追溯、可回滚。

**AI 必须遵循的规则**：
1. **不在主分支直接开发**：开始工作前从主分支（`main`/`master`）切出工作分支（命名：`feat/<描述>` 或 `cr/<CR-ID>`）
2. **频繁提交**：每完成一个有意义的步骤就提交，消息格式 `<type>: <描述>`（type：feat/fix/docs/test/refactor/chore），有 CR 时加前缀 `[CR-ID]`
3. **完成后打 tag**：部署完成后在主分支（`main`/`master`）上打版本 tag（如 `v1.0`），作为下次迭代的基线
4. **合入主分支**：通过 PR 合入主分支（`main`/`master`），推荐 Squash and merge
   - **Squash merge 时的 CR-ID 规则**：Squash 后的单条 commit 消息必须包含本次涉及的所有 CR-ID，格式：`feat: <描述> [CR-YYYYMMDD-001, CR-YYYYMMDD-002]`
   - PR 标题/描述中也应列出所有 CR-ID，便于追溯
5. **禁止危险操作**：`push --force`、`reset --hard`、`branch -D` 等必须经用户授权

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
| 人类抽检模板 | `templates/spotcheck_template.md` |
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
