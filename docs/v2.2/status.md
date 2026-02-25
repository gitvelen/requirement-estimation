---
_baseline: v2.1
_current: HEAD
_workflow_mode: semi-auto
_run_status: running
_change_status: in_progress
_change_level: major
_review_round: 2
_phase: Testing
---

| 项 | 值 |
|---|---|
| 版本号 | v2.2 |
| 变更目录 | `docs/v2.2/` |
| 当前阶段 | Testing |
| 变更状态 | In Progress |
| 基线版本（对比口径） | v2.1 |
| 当前代码版本 | HEAD (dev) |
| 本次复查口径 | full |
| 负责人 | - |
| 最后更新 | 2026-02-25 |
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
| CR-20260225-001 | In Progress | 收口后可读性与紧凑布局优化补记 | plan/test_report/frontend pages/backend route | `cr/CR-20260225-001.md` |
| CR-20260225-002 | Accepted | 知识导入与信息展示页 UI 重设计 | requirements/design/test_report/SystemProfileImportPage/SystemProfileBoardPage | `cr/CR-20260225-002.md` |

## 需要同步的主文档清单（如适用）
- [x] `docs/系统功能说明书.md`
- [x] `docs/技术方案设计.md`
- [x] `docs/接口文档.md`
- [x] `docs/用户手册.md`
- [x] `docs/部署记录.md`

## 回滚要点
- 发布异常时优先回退至 v2.1 对应版本；必要时恢复 `backups/v2.2_*` 快照（`task_storage.json`、`task_modifications.json`、`system_profiles.json`、`system_list.csv`）

## 备注
- 本文件用于显式标记阶段/完成状态，避免仅靠"文件存在性"推断导致误判。
- 建议为 v2.1 补打 git tag：`git tag v2.1 91ec97c`
- Requirements：`requirements.md` v0.3 已完成第 2 轮审查（见 `review_requirements.md`），已确认禁止项清单，进入 Design 阶段。
- Design：`design.md` + `review_design.md` 已收敛（P0/P1 open=0），进入 Planning 阶段。
- Planning：`plan.md` + `review_planning.md` 已收敛（P0/P1 open=0，反向覆盖通过），进入 Implementation 阶段。
- Implementation：已完成 T001~T013（含 REQ-C 全量回归、兼容/死链校验、无 DB 迁移证明、主文档同步）；可进入 Testing 阶段。
- Testing：已完成 `test_report.md`、`review_testing.md`、`spotcheck_testing_main.md`（GWT 53/53 覆盖，P0/P1 open=0）。
- Deployment：已产出 `deployment.md`、`review_deployment.md`，并修复 result-gate 命令为可执行口径（`.venv/bin/pytest` + `compileall`）；等待人工确认上线。
- Deployment：用户确认后已执行正式部署（fallback 构建成功、backend healthy、最小回归通过），本次变更完成。
- ChangeManagement（增量）：用户在收口阶段提出多项 UI/可读性优化诉求，已登记 `CR-20260225-001` 并按 diff-only 口径回填追溯链路。

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
| Design | Planning | 2026-02-24 | 独立审查发现问题后修复并复核收敛（第 3 轮） | AI | 追溯覆盖通过；RVW-001~007 已关闭；进入任务计划拆解 |
| Planning | Implementation | 2026-02-24 | Planning 第 1 轮自检收敛（P0/P1 open=0） | AI | R6 引用自检通过；requirements ↔ plan 反向覆盖差集为空 |
| Implementation | Testing | 2026-02-24 | Testing 第 1 轮自审收敛（P0/P1 open=0，GWT 覆盖 53/53） | AI | 生成 `test_report.md`、`review_testing.md`、`spotcheck_testing_main.md`；发现并记录 result-gate 命令阻塞 |
| Testing | Deployment | 2026-02-24 | Deployment 文档与门禁命令修复完成，转入人工确认上线 | AI | 生成 `deployment.md`、`review_deployment.md`；`_run_status` 置 `wait_confirm` |
| Deployment | Deployment | 2026-02-24 | 人工确认后完成正式部署与上线验证 | AI | 备份 `backups/v2.2_20260224_223625`；`docker-compose up -d --build` fallback 成功；健康检查与最小回归通过 |
| Deployment | Deployment | 2026-02-25 | 收口后新增优化需求，按 CR 流程补记追溯并继续迭代 | User/AI | 新增 `CR-20260225-001`，复查口径维持 full（文档执行 diff-only 回填） |

## 紧急中断记录
| 触发时间 | 原因 | 当前状态 | 恢复条件 |
|---|---|---|---|

## 技术债务登记（Deferred Items）
| 来源阶段 | RVW-ID / 问题描述 | 严重度 | defer 理由 | 缓解措施 | 目标处理版本 | 状态 |
|---------|-------------------|--------|-----------|---------|-------------|------|
