---
_baseline: v2.4
_current: HEAD
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: major
_review_round: 0
_phase: ChangeManagement
---

| 项 | 值 |
|---|---|
| 版本号 | v2.5 |
| 变更目录 | `docs/v2.5/` |
| 当前阶段 | ChangeManagement |
| 变更状态 | In Progress |
| 变更分级 | major |
| 基线版本（对比口径） | v2.4 |
| 当前代码版本 | HEAD |
| 本次复查口径 | diff-only |
| 当前执行 AI | Codex |
| 人类决策人 | User |
| 最后更新 | 2026-03-05 |
| 完成日期 |  |

## 变更摘要
- 启动 v2.5 新版本迭代。
- 已创建首个 CR（`CR-20260305-001`），进入 Phase 00 需求澄清流程。

## 目标与成功指标
| ID | 指标定义（可判定） | 基线（v2.4） | 目标（v2.5） | 统计窗口 | 数据源 |
|---|---|---|---|---|---|
| M1 | Phase 00 完成度 | 无 v2.5 变更单 | 完成 CR 澄清并进入 Proposal | 版本启动期 | `status.md` + `review_change_management.md` |
| M2 | 需求可追溯完整度 | 无 v2.5 REQ | v2.5 需求与 CR 建立双向追溯 | 需求阶段 | `requirements.md` + `plan.md` |

## 关键链接
- 提案：`proposal.md`
- 需求：`requirements.md`
- 设计：`design.md`
- 计划：`plan.md`
- 变更单（CR）：`cr/CR-*.md`
- 审查：`review_change_management.md` / `review_*.md`
- 测试报告：`test_report.md`
- 部署：`deployment.md`

## Active CR 列表（🔴 MUST，CR场景）
| CR-ID | 状态 | 标题 | 影响面（文档/模块/ID） | 链接 |
|---|---|---|---|---|
| CR-20260305-001 | Idea | v2.5 版本启动与范围澄清 | proposal / requirements / design / plan / test_report / deployment | `cr/CR-20260305-001.md` |

## Idea池（可选，非Active）
| CR-ID | 状态 | 标题 | 提出日期 | 优先级 | 链接 |
|---|---|---|---|---|---|
| - | - | - | - | - | - |

## 需要同步的主文档清单（如适用）
- [ ] `docs/系统功能说明书.md`
- [ ] `docs/技术方案设计.md`
- [ ] `docs/接口文档.md`
- [ ] `docs/用户手册.md`
- [ ] `docs/部署记录.md`

## 回滚要点
- L1（流程级回滚）：将 v2.5 变更停留在独立分支，不合入主分支。
- L2（版本级回滚）：如已合入，回退至基线 tag `v2.4`。

## 备注
- 本文件用于显式标记阶段/完成状态，避免仅靠"文件存在性"推断导致误判。
- 当前为版本启动状态，待完成 CR 澄清后推进 Proposal。

---

## 阶段转换记录
| 从阶段 | 到阶段 | 日期 | 原因 | 触发人 | 关键决策 |
|---|---|---|---|---|---|
| - | ChangeManagement | 2026-03-05 | 初始化 v2.5 新版本迭代 | User+Codex | 基线锁定 `v2.4`，启动 `CR-20260305-001` |

## CR状态更新记录（部署后填写）
| CR-ID | 之前状态 | 之后状态 | 上线日期 | 备注 |
|-------|---------|---------|---------|------|

## 紧急中断记录
| 触发时间 | 原因 | 当前状态 | 恢复条件 |
|---|---|---|---|

## 技术债务登记（Deferred Items）
| 来源阶段 | RVW-ID / 问题描述 | 严重度 | defer 理由 | 缓解措施 | 目标处理版本 | 状态 |
|---------|-------------------|--------|-----------|---------|-------------|------|
