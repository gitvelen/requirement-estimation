---
_baseline: v2.6
_current: HEAD
_workflow_mode: semi-auto
_run_status: wait_confirm
_change_status: in_progress
_change_level: major
_review_round: 0
_phase: Deployment
---

| 项 | 值 |
|---|---|
| 版本号 | v2.7 |
| 变更目录 | `docs/v2.7/` |
| 当前阶段 | Deployment |
| 变更状态 | In Progress |
| 变更分级 | major |
| 基线版本（对比口径） | `v2.6` |
| 当前代码版本 | HEAD |
| 本次复查口径 | diff-only |
| 当前执行 AI | Codex |
| 人类决策人 | User |
| 最后更新 | 2026-04-08 |
| 完成日期 | 2026-03-15 |
| 发布日期 | 2026-03-15 |

## 变更摘要
- 2026-04-08 新增补丁 `CR-20260408-001`：修复 v2.7 文档导入画像闭环，包括过滤需求/技术方案中的目录与封面噪声、补强技术方案多域建议提取与运行态重试链路、修复平铺 canonical AI 建议在信息展示页“采纳新建议 / 忽略”不生效的问题，并修复启动迁移对平铺建议的污染；当前已完成 STAGING/TEST 人工复验，进入 wait_confirm，待主分支收口
- v2.7 已完成 Implementation、Testing 与 Deployment 收口；`REQ-003/REQ-004` 的人工 E2E 已在 STAGING/TEST 完成并通过
- Proposal 范围已从旧版“5 个 Skill + 脚本式提取”升级为“6 个内置 Skill + Skill Runtime + Per-System Memory 资产层”，并形成统一 execution / Memory 记录链路
- PM 导入页已收敛为 `需求文档 / 设计文档 / 技术方案` 三类；信息展示页保持既有“系统 TAB + 5 个域 TAB”交互，只展示 D1-D5 canonical 与 AI 建议
- 管理员“服务治理”页与“系统清单”页已按最新口径完成用户可读化；治理模板以 `data/esb-template.xlsx` 为准，系统清单 confirm 仅初始化空画像并返回系统名称与用户可读跳过原因
- `proposal.md`、`requirements.md`、`design.md`、`plan.md`、`review_implementation.md`、`test_report.md`、`review_testing.md`、`deployment.md` 与 5 份主文档已同步完成
- 自动化回归、前端 smoke/build、后端 compileall、API regression 与回溯 CR `CR-20260314-001` 的证据已闭环；2026-03-14 23:42 已完成 STAGING/TEST 运行态发布，2026-03-14 23:59 User 完成 `REQ-003/REQ-004` 人工 E2E 并反馈“正常”

## 目标与成功指标
| ID | 指标定义（可判定） | 基线（v2.6） | 目标（v2.7） | 统计窗口 | 数据源 |
|---|---|---|---|---|---|
| M1 | 画像域字段覆盖度 | 5 域 12 子字段 | 5 域 ≥ 20 字段（含 `extensions`） | 上线时 | schema 对比 |
| M2 | PM 导入页文档类型数 | 5 种 | 3 种（需求/设计/技术方案） | 上线时 | 前端配置 |
| M3 | 服务治理导入 -> 画像更新成功率 | 无此功能 | 对治理导入中系统名与系统清单标准名称一致的记录，自动匹配更新成功率 ≥ 95% | 测试阶段 | 测试日志 |
| M4 | Skill Runtime 覆盖率 | 0 | 6 个内置 Skill 全部注册、正确路由，并通过独立功能测试 | 测试阶段 | 注册表 + 功能测试 |
| M5 | Memory 写入覆盖率 | 0 | 系统画像更新、系统识别结论、AI 评估后功能点修改三类范围内动作的 Memory 写入覆盖率 = 100% | 测试阶段 | Memory 日志 |
| M6 | 存量画像清理 | 旧 schema 数据残留 | 旧 schema 数据 = 0 | 上线时 | DB 查询 |

## 关键链接
- 提案：`proposal.md`
- 需求：`requirements.md`
- 设计：`design.md`
- 计划：`plan.md`
- 实现清单：`implementation_checklist.md`
- 重构对照：`refactoring_checklist.md`
- 变更单（CR）：`cr/CR-*.md`
- 审查：`review_implementation.md`
- 测试报告：`test_report.md`
- 部署：`deployment.md`

## Active CR 列表（🔴 MUST，CR场景）
| CR-ID | 状态 | 标题 | 影响面（文档/模块/ID） | 链接 |
|---|---|---|---|---|
| CR-20260408-001 | In Progress | 修复 v2.7 文档导入画像闭环与平铺 AI 建议采纳/忽略失效 | `deployment.md` / `backend/api/system_profile_routes.py` / `backend/service/document_skill_adapter.py` / `backend/service/system_profile_service.py` / `frontend/src/pages/SystemProfileBoardPage.js` / `tests/*` | `cr/CR-20260408-001.md` |

## Idea池（可选，非Active）
| CR-ID | 状态 | 标题 | 提出日期 | 优先级 | 链接 |
|---|---|---|---|---|---|
| - | - | - | - | - | - |

## 需要同步的主文档清单（如适用）
- [x] `docs/系统功能说明书.md`
- [x] `docs/技术方案设计.md`
- [x] `docs/接口文档.md`
- [x] `docs/用户手册.md`
- [x] `docs/部署记录.md`

## 回滚要点
- L1（流程级回滚）：将 v2.7 变更停留在独立分支，不合入主分支。
- L2（版本级回滚）：如已合入，回退至基线 tag `v2.6`。

## 备注
- 本文件用于显式标记阶段/完成状态，避免仅靠“文件存在性”推断导致误判。
- 第 2 轮 Requirements 复审结论已被用户新增范围正式作废；Requirements 以 2026-03-13 的第 6 轮复审结果为准，并已在同日获人工确认进入 Design。
- `CR-20260314-001` 已以回溯记录方式收口为 Implemented；在本次补丁启动前，v2.7 曾处于“无 Active CR”状态。
- 2026-04-08 补丁 `CR-20260408-001` 已完成业务复验并确认通过：验收范围包括文档导入文本清洗、多域画像建议提取、信息展示页采纳/忽略闭环，以及支持运行态快照的“重新生成 AI 建议”链路；当前保持 `_phase=Deployment`、`_change_status=in_progress`、`_run_status=wait_confirm`，语义为“业务已验收通过，待主分支收口 / tag / 基线同步后再切 completed”。
- v2.7 的自动化回归、人工验收、Deployment 留痕与主文档同步已形成闭环，可作为 `v2.7` 发布基线。

---

## 阶段转换记录
| 从阶段 | 到阶段 | 日期 | 原因 | 触发人 | 关键决策 |
|---|---|---|---|---|---|
| - | Proposal | 2026-03-12 | 新版本启动初始化 | User | 基线锁定 v2.6，无 Active CR |
| Proposal | Requirements | 2026-03-12 | Proposal 第 4 轮复审收敛且用户确认进入下一阶段 | User + Codex | 开始按分段走查协议编写 `requirements.md` |
| Requirements | Design | 2026-03-13 | Requirements 第 6 轮复审收敛，且用户确认进入 Design | User + Codex | 系统清单联动已收敛为“首次初始化/空画像补写，非空画像跳过” |
| Design | Planning | 2026-03-13 | Design 第 3 轮复审通过，且用户确认进入 Planning | User + Codex | 开始编写 `plan.md`，按 requirements/design 做任务反向覆盖与验证命令拆解 |
| Planning | Implementation | 2026-03-13 | Planning 第 1 轮复审收敛，且用户确认进入 Implementation | User + Codex | 先执行 T001~T003，并在 T006（M1🏁）前按后端里程碑展示协议暂停汇报 |
| Implementation | Testing | 2026-03-14 | T001-T009 完成，Implementation 自审收敛，Testing 输入与自动化证据已就绪 | Codex | 已产出 `review_implementation.md` / `test_report.md` / `review_testing.md`；`REQ-003/REQ-004` 人工 E2E 待补 |
| Testing | Deployment | 2026-03-14 | `REQ-003/REQ-004` 人工 E2E 完成且 Deployment 留痕闭环 | User + Codex | 最新治理模板固定为 `data/esb-template.xlsx`；STAGING/TEST 验收通过并切换为 Deployment 完成态 |

## CR状态更新记录（部署后填写）
| CR-ID | 之前状态 | 之后状态 | 上线日期 | 备注 |
|-------|---------|---------|---------|------|
| CR-20260314-001 | Accepted | Implemented | 2026-03-14 | 回溯记录 Testing 阶段前端可读性与交互回归收敛，已纳入 v2.7 测试与部署闭环 |

## 紧急中断记录
| 触发时间 | 原因 | 当前状态 | 恢复条件 |
|---|---|---|---|

## 技术债务登记（Deferred Items）
| 来源阶段 | RVW-ID / 问题描述 | 严重度 | defer 理由 | 缓解措施 | 目标处理版本 | 状态 |
|---------|-------------------|--------|-----------|---------|-------------|------|

## 质量债务登记（🔴 MUST）
| 债务ID | 类型 | 描述 | 风险等级 | 计划偿还版本 | 状态 |
|--------|------|------|---------|-------------|------|
