---
_baseline: v2.3
_current: HEAD
_workflow_mode: semi-auto
_run_status: completed
_change_status: done
_change_level: major
_review_round: 0
_phase: Deployment
---

| 项 | 值 |
|---|---|
| 版本号 | v2.4 |
| 变更目录 | `docs/v2.4/` |
| 当前阶段 | Deployment |
| 变更状态 | Done |
| 变更分级 | major |
| 基线版本（对比口径） | v2.3 |
| 当前代码版本 | HEAD |
| 本次复查口径 | diff-only |
| 当前执行 AI | Codex |
| 人类决策人 |  |
| 最后更新 | 2026-03-02 |
| 完成日期 | 2026-03-02 |

## 变更摘要
- v2.4 系统画像增强与评估机制优化：文档导入页重构、系统画像展示增强（时间线+inline diff）、AI 结构化信息提取与字段更新、画像建议回滚机制、工作量估算机制激活、评估经验资产沉淀机制
- 增量 CR：内网部署目录属主对齐与默认账号初始化（`CR-20260302-003`）

## 目标与成功指标
| ID | 指标定义（可判定） | 基线（v2.3） | 目标（v2.4） | 统计窗口 | 数据源 |
|---|---|---|---|---|---|
| M1 | 文档导入操作效率 | 需反复切换下拉框，切换丢状态 | 各类型独立操作，零状态丢失 | 功能验收 | 手动测试 |
| M2 | 画像变更可追溯性 | 无变更历史 | 100% 变更事件可追溯 | 功能验收 | 时间线数据 |
| M3 | AI 建议可回滚性 | 无回滚能力 | 支持一级回滚 | 功能验收 | 手动测试 |
| M4 | 工作量估算准确度 | 静态映射（高=4/中=2.5/低=1.5） | LLM 参与估算，输出三点估计 | 回归对比 | 评估报告 |
| M5 | 评估经验资产沉淀 | PM 修正数据用完即弃 | AI 原始输出快照 + PM 修正 diff 落盘 + 系统画像 ai_correction_history 自动更新 | 功能验收 | API 查询 + 画像字段 |

## 关键链接
- 提案：`proposal.md`
- 需求：`requirements.md`
- 设计：`design.md`
- 计划：`plan.md`
- 变更单（CR）：`cr/CR-*.md`（如启用）
- 审查：`review_*.md`
- 测试报告：`test_report.md`
- 部署：`deployment.md`

## Active CR 列表（🔴 MUST，CR场景）
| CR-ID | 状态 | 标题 | 影响面（文档/模块/ID） | 链接 |
|---|---|---|---|---|
| - | - | 当前无 Active CR | - | - |

## Idea池（可选，非Active）
| CR-ID | 状态 | 标题 | 提出日期 | 优先级 | 链接 |
|---|---|---|---|---|---|
| v2.5-IDEA-01 | Proposed | 系统识别 prompt 注入历史修正模式 | 2026-02-27 | 高 | proposal.md v2.5 展望 #1 |
| v2.5-IDEA-02 | Proposed | 功能拆分 prompt 注入粒度偏好与常见遗漏 | 2026-02-27 | 高 | proposal.md v2.5 展望 #2 |
| v2.5-IDEA-03 | Proposed | 功能类型维度模式自动归纳 | 2026-02-27 | 中 | proposal.md v2.5 展望 #3 |
| v2.5-IDEA-04 | Proposed | 评估知识库（历史案例向量化检索） | 2026-02-27 | 中 | proposal.md v2.5 展望 #4 |
| v2.5-IDEA-05 | Proposed | 专家校准画像 | 2026-02-27 | 低 | proposal.md v2.5 展望 #5 |
| v2.5-IDEA-06 | Proposed | 前端 AI 准确率趋势图 | 2026-02-27 | 低 | proposal.md v2.5 展望 #6 |

## 需要同步的主文档清单（如适用）
- [x] `docs/系统功能说明书.md`
- [x] `docs/技术方案设计.md`
- [x] `docs/接口文档.md`
- [x] `docs/用户手册.md`
- [x] `docs/部署记录.md`

## 回滚要点
- L1（功能级回滚，优先）：已在 `design.md` §6.4 定义（AI 建议回滚 + 手动字段回滚）
- L2（版本级回滚）：`git checkout v2.3 && bash deploy-all.sh`

## 备注
- 本文件用于显式标记阶段/完成状态，避免仅靠"文件存在性"推断导致误判。
- v2.4 为 Major 级别变更（前后端多模块改动），走完整 8 阶段流程。
- 2026-03-01：T010（三点估计展示与导出联动）、T011（全量回归与覆盖矩阵）、T012（部署清单与回滚演练）均已完成，相关证据已回写 `review_implementation.md`、`review_testing.md`、`deployment.md`。
- 2026-03-01：已按 STAGING 路径执行 `printf '2\\n' | bash deploy-all.sh` 并通过健康检查，曾进入 `wait_confirm` 等待验收。
- 2026-03-01：收到用户“继续”指令后完成收口，状态切换为 `_change_status: done` + `_run_status: completed`。
- 2026-03-01：主文档同步清单已补齐（系统功能说明书/技术方案设计/接口文档/用户手册/部署记录）。
- 2026-03-01：收到用户“走CR”指令后新增 `CR-20260301-001`，状态回切为进行中（`_change_status: in_progress` + `_run_status: running`），复查口径切换为 `diff-only`。
- 2026-03-02：新增 `CR-20260302-001`（去冗余域标题 + 五域导航左对齐），继续按 `diff-only` 口径迭代。
- 2026-03-02：新增 `CR-20260302-002`（旧 `system_id` 容错与当前 ID 优先），继续按 `diff-only` 口径迭代。
- 2026-03-02：按 STAGING 路径执行 `printf '2\\n' | bash deploy-all.sh`，并通过本机/公网健康检查，状态置 `wait_confirm` 等待人工验收。
- 2026-03-02：追加修复“系统存在但画像为空时 `/profile/events` 返回404”问题，完成后端容错回归与二次发布，健康检查通过。
- 2026-03-02：人工验收通过，CR-20260301-001/CR-20260302-001/CR-20260302-002 已上线，状态切换为 `_change_status: done` + `_run_status: completed`。
- 2026-03-02：用户新增 `CR-20260302-003`（内网部署目录属主对齐与默认账号初始化），状态回切为 `_change_status: in_progress` + `_run_status: running`。
- 2026-03-02：`CR-20260302-003` 验证通过并完成收口，状态切换为 `_change_status: done` + `_run_status: completed`。

---

## 阶段转换记录
| 从阶段 | 到阶段 | 日期 | 原因 | 触发人 | 关键决策 |
|---|---|---|---|---|---|
| - | Proposal | 2026-02-27 | 初始化 v2.4 系统画像增强与评估机制优化 | User+Claude | Major 级别，走完整 8 阶段流程；基线 v2.3 |
| Proposal | Requirements | 2026-02-27 | Proposal v0.9 审查收敛（11 轮，P0/P1=0）并获人工确认推进；2026-02-28 完成 v1.1 修复复核（P0/P1=0） | User+Claude+Codex | `review_proposal.md` 第 11 轮（v0.9）全量走查通过 + v1.1 修复复核通过；D1-D20 共 20 条用户决策落盘 |
| Requirements | Design | 2026-02-28 | Requirements v1.2 审查收敛（15 轮，P0/P1=0）并获人工确认推进 | User+Claude+Codex | `review_requirements.md` 第 15 轮通过；34 条覆盖映射全闭合；7 条 REQ-C 禁止项+约束确认；3 条 P2 标注 Design 细化 |
| Design | Planning | 2026-02-28 | Design v0.5 第 2 轮审查收敛（P0/P1=0），追溯门禁+API契约门禁通过 | Codex | 统一 Requirements/Design API 契约前缀口径；补齐 API-009~012 参数与错误处理 |
| Planning | Implementation | 2026-02-28 | Planning v0.1 审查收敛（P0/P1=0），任务反向覆盖门禁通过 | Codex | 12 个任务拆解完成；REQ/REQ-C 25 项反向覆盖完整；验证命令闭环 |
| Implementation | Testing | 2026-03-01 | T010~T011 收敛并完成全量回归门禁（pytest/build/typecheck） | Codex | `test_report.md`、`review_implementation.md` 已落盘；预审门禁 130 passed |
| Testing | Deployment | 2026-03-01 | T012 收敛并完成部署清单与回滚演练证据 | Codex | `deployment.md`、`review_testing.md` 已落盘；L1 rollback 测试通过 + L2 worktree 演练通过 |
| Deployment | Done | 2026-03-01 | STAGING 部署成功且健康检查通过，进入完成态 | User+Codex | `_change_status: done` 与 `_run_status: completed` 同步成立 |
| Deployment | Deployment | 2026-03-01 | 收口后新增信息展示页交互一致性修正需求，按 CR 流程继续迭代 | User+Codex | 新增 `CR-20260301-001` 并启用 diff-only 复查口径 |
| Deployment | Deployment | 2026-03-02 | 新增视觉一致性诉求（域标题去冗余、域导航左对齐），按 CR 流程继续迭代 | User+Codex | 新增 `CR-20260302-001` 并纳入 Active CR |
| Deployment | Deployment | 2026-03-02 | 线上报错“系统不存在”，定位为旧 system_id 失配并新增容错修复 CR | User+Codex | 新增 `CR-20260302-002` 并纳入 Active CR |
| Deployment | Deployment | 2026-03-02 | CR 增量发布执行到 STAGING，自动部署完成并等待人工验收 | Codex | 执行 `printf '2\\n' | bash deploy-all.sh` + 健康检查通过，`_run_status` 置 `wait_confirm` |
| Deployment | Done | 2026-03-02 | 人工验收通过，完成本轮 CR 收口 | User+Codex | Active CR 全部置 Implemented；`_change_status=done` 且 `_run_status=completed` |
| Deployment | Deployment | 2026-03-02 | 用户新增内网部署目录属主与默认账号初始化诉求，按 CR 流程继续迭代 | User+Codex | 新增 `CR-20260302-003` 并纳入 Active CR |
| Deployment | Done | 2026-03-02 | 用户确认完成 v2.4 收口（含 CR-20260302-003） | User+Codex | `CR-20260302-003` 置 Implemented；`_change_status=done` 且 `_run_status=completed` |

## CR状态更新记录（部署后填写）
| CR-ID | 之前状态 | 之后状态 | 上线日期 | 备注 |
|-------|---------|---------|---------|------|
| CR-20260301-001 | In Progress | Implemented | 2026-03-02 | 与 CR-20260302-001/002 同批次验收通过 |
| CR-20260302-001 | In Progress | Implemented | 2026-03-02 | UI 去冗余与左对齐验收通过 |
| CR-20260302-002 | In Progress | Implemented | 2026-03-02 | stale system_id + 无画像事件容错验收通过 |
| CR-20260302-003 | In Progress | Implemented | 2026-03-02 | 内网部署目录属主对齐与默认账号初始化验证通过 |

## 紧急中断记录
| 触发时间 | 原因 | 当前状态 | 恢复条件 |
|---|---|---|---|

## 技术债务登记（Deferred Items）
| 来源阶段 | RVW-ID / 问题描述 | 严重度 | defer 理由 | 缓解措施 | 目标处理版本 | 状态 |
|---------|-------------------|--------|-----------|---------|-------------|------|
