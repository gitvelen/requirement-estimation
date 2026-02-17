---
_baseline: v2.0
_current: HEAD
_workflow_mode: semi-auto
_run_status: completed
_change_status: done
_phase: Deployment
---

# 变更状态（`docs/v2.1/status.md`）

| 项 | 值 |
|---|---|
| 版本号 | v2.1 |
| 变更目录 | `docs/v2.1/` |
| 变更主题 | v2.1 多模块 UI/UX 优化与功能增强 |
| 基线说明 | 基于 v2.0 版本进行升级优化 |
| 当前阶段 | Deployment |
| 变更状态 | Done |
| 基线版本（对比口径） | v2.0 |
| 当前代码版本 | HEAD |
| 本次复查口径 | full（涉及多模块调整、API 变更、数据库字段变更） |
| 负责人 | AI |
| 最后更新 | 2026-02-12 |
| 提案版本 | v1.8 |
| 需求版本 | v0.3 |
| 设计版本 | v0.1 |
| 计划版本 | v0.3 |
| 实现检查清单版本 | v0.1 |
| 测试报告版本 | v0.1 |
| 部署文档版本 | v0.1 |
| 审查状态 | Proposal Review 完成（RVW-001~004 已处理）；Requirements Review 第 3 轮完成（P0/P1 open=0）；Design Review 第 5 轮完成（P0/P1 open=0，P2 defer=2，见 `review_design.md`）；Planning Review 第 1 轮完成（P0/P1 open=0，见 `review_planning.md`）；Implementation Review 第 3 轮完成（P0/P1 open=0，见 `review_implementation.md`）；Testing Review 第 3 轮完成（P0/P1 open=0，见 `review_testing.md`）；Deployment Review 第 1 轮完成（P0/P1 open=0，见 `review_deployment.md`） |
| 完成日期 | 2026-02-12 |

## 变更摘要
本次变更为 v2.1 版本的多模块 UI/UX 优化与功能增强，涉及：
1. 系统清单页面布局优化
2. 规则管理页面简化
3. 效能看板布局调整与权限优化
4. 任务管理页面简化
5. 功能点编辑页面优化
6. 功能点编辑流程增强（AI 重新评估、备注自动生成）
7. 知识导入/信息看板系统列表修复（统一系统清单数据源，废弃 legacy system_list.csv）
8. 信息看板页面简化
9. 专家评估页面布局优化
10. 系统画像重构：从 7 字段收敛为 4 字段（system_scope、module_structure、integration_points、key_constraints）
11. 修改记录增强：补充操作人字段（actor_id/actor_role）
12. 效能看板升级：管理驱动型指标体系（6 项指标 + AI 学习趋势）

## 目标与成功指标
见 `docs/v2.1/proposal.md` 的“目标与成功指标”章节

## 关键决策记录
见 `docs/v2.1/proposal.md` 的"关键决策记录（D-01~D-13）"章节

## 关键链接
- 提案：`proposal.md`
- 需求：`requirements.md`
- 设计：`design.md`
- 计划：`plan.md`
- 实现检查清单：`implementation_checklist.md`
- 测试报告：`test_report.md`
- 部署：`deployment.md`

## Active CR 列表
暂无

## 需要同步的主文档清单
- [x] `docs/系统功能说明书.md`
- [x] `docs/技术方案设计.md`
- [x] `docs/接口文档.md`
- [x] `docs/用户手册.md`
- [x] `docs/部署记录.md`

## 回滚要点
- 关键行为变更采用 Feature Flag（B-01/B-02/B-06），可快速关闭回退到 v2.0 行为
- B-04 画像字段重构为结构性变更，不做灰度开关；回滚依赖部署前对 `data/system_profiles.json` 的快照备份与恢复
- 部署前对 `data/` 关键存储做快照备份（至少包含任务存储、系统画像、系统清单、知识库/检索日志相关文件）

## 备注
- 本次变更为 Major 级别，需走完整 8 阶段流程
- 涉及 API 接口和数据库字段变更
- Deployment 阶段门禁与主文档同步已完成，版本状态设为 Done；详细见 `review_deployment.md` 与 `docs/部署记录.md`

---

## 工作流状态

**枚举说明**：
- **工作流模式**（`_workflow_mode`）：`manual`（人工介入期，Phase 00-02）/ `semi-auto`（Deployment 阶段）/ `auto`（AI 自动期，Phase 03-06）
- **运行状态**（`_run_status`）：`running`（正常运行）/ `paused`（暂停）/ `wait_confirm`（等待确认）/ `completed`（已完成）
- **变更状态**（`_change_status`）：`in_progress`（进行中）/ `done`（已完成）
- **当前阶段**（`_phase`）：`Proposal` / `Requirements` / `Design` / `Planning` / `Implementation` / `Testing` / `Deployment`

---

## 阶段转换记录
| 从阶段 | 到阶段 | 日期 | 原因 | 触发人 | 关键决策 |
|---|---|---|---|---|---|
| - | Proposal | 2026-02-11 | 初始化 v2.1 版本 | User | - |
| Proposal | Requirements | 2026-02-11 | Proposal Review 通过（0 P0、2 P1 已处理、2 P2 Defer），用户确认进入 Requirements | User | RVW-002 知识命中率降级为观测指标 |
| Requirements | Design | 2026-02-11 | Requirements 阶段完成，进入 Design 阶段 | User | - |
| Design | Planning | 2026-02-12 | 用户确认进入 Planning 阶段 | User | - |
| Planning | Implementation | 2026-02-12 | Planning 文档完成并通过 R6 引用自检，按自动阶段推进 | AI | R6 差集为空 |
| Implementation | Testing | 2026-02-12 | Implementation 第 3 轮自检收敛（P0/P1 open=0） | AI | RVW-001（P1）已 Fix（兼容性测试补齐） |
| Testing | Deployment | 2026-02-12 | Testing 第 3 轮自检收敛（后端86通过、前端测试/构建通过、备份回滚演练通过） | AI | 进入 Deployment 文档化发布准备 |
| Deployment | Deployment | 2026-02-12 | Deployment 第 1 轮审查收敛，主文档同步完成，状态收口为 Done | AI | run_status=completed, change_status=done |

## 紧急中断记录
暂无

## 技术债务登记（Deferred Items）
暂无
