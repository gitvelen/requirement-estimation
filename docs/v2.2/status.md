---
_baseline: v2.1
_current: HEAD
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: major
_review_round: 0
_phase: Planning
---

| 项 | 值 |
|---|---|
| 版本号 | v2.2 |
| 变更目录 | `docs/v2.2/` |
| 当前阶段 | Planning |
| 变更状态 | In Progress |
| 基线版本（对比口径） | v2.1 |
| 当前代码版本 | HEAD (dev) |
| 本次复查口径 | full |
| 负责人 | - |
| 最后更新 | 2026-02-24 |
| 完成日期 | - |

## 变更摘要
- v2.2 综合优化升级：页面精简、菜单重构、效能看板重构、任务管理优化、编辑流程管控、系统画像重设计、专家评估优化、备注自动化

## 目标与成功指标
- 简化全站页面冗余信息，提升操作效率
- 重构效能看板为排行榜+多维报表双模块
- 任务管理子菜单化，减少页面内切换
- 项目经理编辑流程增加管控（预估人天只读、实质性修改触发重评估）
- 备注字段 AI 自动生成，减少人工填写

## 关键链接
- 提案：`proposal.md`
- 需求：`requirements.md`
- 设计：`design.md`
- 计划：`plan.md`
- 变更单（CR）：`cr/CR-*.md`（如启用）
- 审查：`review_proposal.md`、`review_requirements.md`（按阶段命名）
- 测试报告：`test_report.md`
- 部署：`deployment.md`

## Active CR 列表（🔴 MUST，CR场景）

| CR-ID | 状态 | 标题 | 影响面（文档/模块/ID） | 链接 |
|---|---|---|---|---|
| （暂无） | - | - | - | - |

## 需要同步的主文档清单（如适用）
- [ ] `docs/系统功能说明书.md`
- [ ] `docs/技术方案设计.md`
- [ ] `docs/接口文档.md`
- [ ] `docs/用户手册.md`
- [ ] `docs/部署记录.md`

## 回滚要点
- 待实现阶段补充

## 备注
- 本文件用于显式标记阶段/完成状态，避免仅靠"文件存在性"推断导致误判。
- 建议为 v2.1 补打 git tag：`git tag v2.1 91ec97c`
- Requirements：`requirements.md` v0.3 已完成第 2 轮审查（见 `review_requirements.md`），已确认禁止项清单，进入 Design 阶段。
- Design：`design.md` + `review_design.md` 已收敛（P0/P1 open=0），进入 Planning 阶段。

---

## 工作流状态

> **已迁移至 YAML front matter**

**枚举说明**：
- **工作流模式**（`_workflow_mode`）：`manual`（人工介入期，Phase 00-02）/ `semi-auto`（Deployment 阶段）/ `auto`（AI 自动期，Phase 03-06）
- **运行状态**（`_run_status`）：`running`（正常运行）/ `paused`（暂停）/ `wait_confirm`（等待确认）/ `completed`（已完成）
- **变更状态**（`_change_status`）：`in_progress`（进行中）/ `done`（已完成）
- **变更分级**（`_change_level`）：`major`（完整门禁）/ `minor`（最小产物门禁）/ `hotfix`（极速修复）
- **审查轮次**（`_review_round`）：当前阶段连续审查轮次（非负整数；>5 时需切换 `wait_confirm` 请求人工确认）
- **当前阶段**（`_phase`）：`ChangeManagement` / `Proposal` / `Requirements` / `Design` / `Planning` / `Implementation` / `Testing` / `Deployment`

---

## 阶段转换记录
| 从阶段 | 到阶段 | 日期 | 原因 | 触发人 | 关键决策 |
|---|---|---|---|---|---|
| - | ChangeManagement | 2026-02-24 | 初始化 v2.2 综合优化 | User | Major 级别，走完整 8 阶段流程 |
| ChangeManagement | Proposal | 2026-02-24 | 进入提案阶段 | User | 明确总体目标、范围边界与指标口径 |
| Proposal | Requirements | 2026-02-24 | 人工确认提案已收敛 | User | 明确 FUNC-022 下线；补齐 ESB 导入合并处置；进入需求编写 |
| Requirements | Design | 2026-02-24 | 人工确认需求已收敛 | User | 确认禁止项清单；进入技术方案设计 |
| Design | Planning | 2026-02-24 | AI 自动审查已收敛（第 1 轮） | AI | 追溯覆盖通过；进入任务计划拆解 |

## 紧急中断记录
| 触发时间 | 原因 | 当前状态 | 恢复条件 |
|---|---|---|---|

## 技术债务登记（Deferred Items）
| 来源阶段 | RVW-ID / 问题描述 | 严重度 | defer 理由 | 缓解措施 | 目标处理版本 | 状态 |
|---------|-------------------|--------|-----------|---------|-------------|------|
