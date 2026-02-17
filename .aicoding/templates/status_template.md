# 变更状态（`docs/<版本号>/status.md`）

```yaml
---
_baseline: v1.0
_current: HEAD
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: major
_review_round: 0
_phase: Proposal
---
```

> **YAML front matter 说明（🔴 MUST）**：
> - `_baseline`: 基线版本（tag/commit），用于代码 diff 和 CR 追溯
> - `_current`: 当前代码版本（commit/branch），用于代码 diff
> - `_workflow_mode`: 工作流模式，枚举值：`manual` / `semi-auto` / `auto`
> - `_run_status`: 运行状态，枚举值：`running` / `paused` / `wait_confirm` / `completed`
> - `_change_status`: 变更状态，枚举值：`in_progress` / `done`
> - `_change_level`: 变更分级，枚举值：`major` / `minor` / `hotfix`
> - `_review_round`: 同阶段审查轮次（非负整数；>5 时需切换 `wait_confirm` 请求人工确认）
> - `_phase`: 当前阶段，枚举值：`Proposal` / `Requirements` / `Design` / `Planning` / `Implementation` / `Testing` / `Deployment`
> - 必须使用标准 YAML front matter 格式（`---` 包裹），放在文件**第 1 行**
> - **值不加引号**：写 `_baseline: v1.0` 而非 `_baseline: "v1.0"`，确保 `awk '{print $2}'` 可直接提取
> - 解析方式：命令行可用 `grep "^_baseline:" status.md | awk '{print $2}'` 提取
> - 如缺失 `_baseline`、`_current`、`_workflow_mode`、`_run_status`、`_change_status` 或 `_phase`，门禁必须失败并提示补充
> - `_change_level` 兼容期缺失会告警并按 `major` 处理；后续可升级为硬门禁
> - Markdown 表格中的关键行（如“当前阶段”“变更状态”）保留为人类可读视图，且需与 YAML front matter 保持一致

| 项 | 值 |
|---|---|
| 版本号 | `<版本号>` |
| 变更目录 | `docs/<版本号>/` |
| 当前阶段 | Proposal / Requirements / Design / Planning / Implementation / Testing / Deployment |
| 变更状态 | In Progress / Done |
| 基线版本（对比口径） | tag / commit（例如 `v1.0`） |
| 当前代码版本 | commit / tag / branch |
| 本次复查口径 | diff-only / full |
| 负责人 |  |
| 最后更新 | YYYY-MM-DD |
| 完成日期 | YYYY-MM-DD（如 Done） |

## 变更摘要
- ...

## 目标与成功指标
- ...

## 关键链接
- 提案：`proposal.md`
- 需求：`requirements.md`
- 设计：`design.md`
- 计划：`plan.md`
- 变更单（CR）：`cr/CR-*.md`（如启用）
- 审查：`review_<stage>.md`（按阶段命名，如 `review_proposal.md`、`review_requirements.md`）
- 测试报告：`test_report.md`
- 部署：`deployment.md`
- Issue/PR/看板/监控：...

## CR状态枚举（🔴 MUST）

> **状态值说明**：

| 状态值 | 含义 | 是否可入Active CR列表 | 说明 |
|--------|------|---------------------|------|
| Idea | 想法/提议 | ❌ 否 | 未确认的初步想法，不应进入Active列表 |
| Accepted | 已接受 | ✅ 是 | 需求已澄清，计划纳入当前版本 |
| In Progress | 进行中 | ✅ 是 | 正在实现中 |
| Implemented | 已实现 | ❌ 否（已从Active移除） | 已上线部署完成 |
| Dropped | 已废弃 | ❌ 否 | 不再实施 |
| Suspended | 已暂停 | ❌ 否 | 暂停实施，保留恢复可能 |

> **状态转换规则**：
> - Idea → Accepted：AI 与用户完成需求澄清对话（范围、验收、影响面、风险），用户明确确认后转换
> - Accepted → In Progress：开始实现时
> - In Progress → Implemented：部署完成后
> - Accepted/In Progress → Dropped：需求取消时
> - In Progress → Suspended：暂停实施时
> - Suspended → In Progress：恢复实施时

## Active CR 列表（🔴 MUST，CR场景）

> **Active CR 语义说明**：
> - Active CR = 本次版本计划交付的 CR（状态为 Accepted/In Progress）
> - Idea 状态的 CR 不应放入 Active 列表，避免门禁误伤
> - 如需要管理 Idea，可在下方单独维护"Idea 池"区域

| CR-ID | 状态 | 标题 | 影响面（文档/模块/ID） | 链接 |
|---|---|---|---|---|
| CR-YYYYMMDD-001 | Accepted/In Progress | ... | requirements / API-xxx / REQ-xxx | `cr/CR-YYYYMMDD-001.md` |

## CR管理视图（可选）

> **状态统计**：
> - Idea池数量：X
> - Active CR数量：Y（Accepted + In Progress）
> - 已完成数量：Z（Implemented）
> - 已废弃/暂停：W

## Idea池（可选，非Active）
> **未确认的初步想法，暂不纳入版本交付**

| CR-ID | 状态 | 标题 | 提出日期 | 优先级 | 链接 |
|---|---|---|---|---|---|
| CR-YYYYMMDD-002 | Idea | ... | YYYY-MM-DD | P0/P1/P2 | `cr/CR-YYYYMMDD-002.md` |

## 需要同步的主文档清单（如适用）
- [ ] `docs/系统功能说明书.md`
- [ ] `docs/技术方案设计.md`
- [ ] `docs/接口文档.md`
- [ ] `docs/用户手册.md`
- [ ] `docs/部署记录.md`

## 回滚要点
- ...

## 备注
- 本文件用于显式标记阶段/完成状态，避免仅靠"文件存在性"推断导致误判。

---

## 工作流状态

> **已迁移至 YAML front matter**：`_workflow_mode`、`_run_status`、`_change_status`、`_phase` 字段现在存储在文件开头的 YAML front matter 中，
> 便于 hooks 脚本用 `grep "^_phase:" status.md | awk '{print $2}'` 直接提取单值。

**枚举说明**：
- **工作流模式**（`_workflow_mode`）：`manual`（人工介入期，Phase 00-02）/ `semi-auto`（Deployment 阶段）/ `auto`（AI 自动期，Phase 03-06）
- **运行状态**（`_run_status`）：`running`（正常运行）/ `paused`（暂停）/ `wait_confirm`（等待确认）/ `completed`（已完成）
- **变更状态**（`_change_status`）：`in_progress`（进行中）/ `done`（已完成）
- **变更分级**（`_change_level`）：`major`（完整门禁）/ `minor`（最小产物门禁）
- **审查轮次**（`_review_round`）：当前阶段连续审查轮次（超过 3 建议人工确认，超过 5 且非 wait_confirm 将被硬拦截）
- **当前阶段**（`_phase`）：`Proposal` / `Requirements` / `Design` / `Planning` / `Implementation` / `Testing` / `Deployment`

---

## 阶段转换记录
| 从阶段 | 到阶段 | 日期 | 原因 | 触发人 | 关键决策 |
|---|---|---|---|---|---|
| - | Proposal | YYYY-MM-DD | 初始化 | User | - |

## CR状态更新记录（部署后填写）

> **填写规则**：
> - 每次部署完成后，更新上线CR的状态
> - 记录从 Accepted/In Progress → Implemented 的变更

| CR-ID | 之前状态 | 之后状态 | 上线日期 | 备注 |
|-------|---------|---------|---------|------|
| CR-YYYYMMDD-001 | In Progress | Implemented | YYYY-MM-DD | 部署验证通过 |

## 紧急中断记录
| 触发时间 | 原因 | 当前状态 | 恢复条件 |
|---|---|---|---|
| YYYY-MM-DD HH:MM | P0无法自动修复 | paused | 人工确认 |

## 技术债务登记（Deferred Items）
> 说明：记录本版本中被标记为 accept/defer 的 **RVW(P1)** 问题，便于 AI 在后续版本分析和处理。  
> 注意：这不是 `DEFERRED_TO_STAGING`（后者是 REQ 模式逐条 GWT 判定中的一种结论，见 `review_implementation.md` / `review_testing.md` 摘要块字段 `GWT_DEFERRED`）。
> 建议：下一版本 Proposal 阶段强制检查此表，评估是否纳入处理。

| 来源阶段 | RVW-ID / 问题描述 | 严重度 | defer 理由 | 缓解措施 | 目标处理版本 | 状态 |
|---------|-------------------|--------|-----------|---------|-------------|------|
| Design | RVW-xxx：... | P1 | ... | 监控/告警/... | 下一版本 | Open/Resolved |
