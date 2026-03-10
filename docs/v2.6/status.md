---
_baseline: v2.5
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
| 版本号 | v2.6 |
| 变更目录 | `docs/v2.6/` |
| 当前阶段 | Deployment |
| 变更状态 | Done |
| 变更分级 | major |
| 基线版本（对比口径） | `v2.5` |
| 当前代码版本 | HEAD |
| 本次复查口径 | full |
| 当前执行 AI | Claude |
| 人类决策人 | User |
| 最后更新 | 2026-03-10 |
| 完成日期 | 2026-03-10 |
| 发布日期 | 2026-03-10 |

## 变更摘要
- v2.6 版本已完成并发布到 GitHub master 分支
- 核心功能：文档分块处理以适配内网 LLM Token 限制（Qwen3-32B / Qwen3-Embedding-8B，最大上下文 32,000 tokens）
- CR-20260309-001 已完成实施并上线（状态：Implemented）
- 新增 ESB 导入 HTTP 400 错误修复（可配置 embedding 批次大小）
- 所有测试通过：后端 210 passed，前端编译成功，覆盖率 92%
- STAGING 环境验收通过，代码已推送到 GitHub master 分支
- 版本状态：Released（已发布）

## 目标与成功指标
| ID | 指标定义（可判定） | 基线（v2.5） | 目标（v2.6） | 统计窗口 | 数据源 |
|---|---|---|---|---|---|
| M1 | Phase 00 完成度 | 无 v2.6 变更单 | 完成 CR 澄清并进入 Proposal | 版本启动期 | `status.md` + `review_change_management.md` |
| M2 | Token 超限错误率 | 按目标内网模型口径导入大文档时 token 超限失败 | 0 次 token 超限错误 | 测试阶段 | 测试日志 |

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
| - | - | 无 Active CR | - | - |

## Idea池（可选，非Active）
| CR-ID | 状态 | 标题 | 提出日期 | 优先级 | 链接 |
|---|---|---|---|---|---|
| - | - | - | - | - | - |

## 需要同步的主文档清单（如适用）
- [ ] `docs/系统功能说明书.md`（不适用：本次无新增前台功能或菜单）
- [x] `docs/技术方案设计.md`
- [x] `docs/接口文档.md`
- [ ] `docs/用户手册.md`（不适用：本次无用户操作变化）
- [x] `docs/部署记录.md`

## 回滚要点
- L1（流程级回滚）：将 v2.6 变更停留在独立分支，不合入主分支。
- L2（版本级回滚）：如已合入，回退至基线 tag `v2.5`。

## 备注
- 本文件用于显式标记阶段/完成状态，避免仅靠"文件存在性"推断导致误判。
- v2.6 版本已完成所有阶段并发布到 GitHub master 分支。
- 版本状态：Closed（已关闭），所有 CR 已实施完成。
- 下一版本：v2.7（如有新需求）

---

## 阶段转换记录
| 从阶段 | 到阶段 | 日期 | 原因 | 触发人 | 关键决策 |
|---|---|---|---|---|---|
| - | ChangeManagement | 2026-03-09 | 初始化 v2.6 新版本迭代 | User+Claude | 基线锁定 v2.5，启动 CR-20260309-001 |
| ChangeManagement | Proposal | 2026-03-09 | 完成 CR 范围澄清，通过第 1 轮审查 | User+Claude | 确认 token 分块方案、本地环境配置、时间估算 |
| Proposal | Requirements | 2026-03-09 | Proposal 审查收敛后开始需求编写与审查 | User+Codex | 收敛测试口径、降级语义与 chunk 上限规则，并产出 requirements.md / review_requirements.md |
| Requirements | Design | 2026-03-09 | Requirements 审查通过（P0=0, P1=0），人工确认进入 Design | User+Codex | 需求文档覆盖性 100%，20 个 GWT 验收标准全部可判定 |
| Design | Planning | 2026-03-09 | Design 第 1 轮自审通过（P0=0, P1=0），追溯与 API 契约门禁通过 | Codex | 采用“原文内存透传 + Token 预算 + 段落级分块 + 两阶段合并”方案，保持外部 API 契约不变 |
| Planning | Implementation | 2026-03-09 | Planning 第 1 轮自审通过（P0=0, P1=0），计划反向覆盖校验通过 | Codex | 形成 `plan.md` v0.1 / `review_planning.md`，将实现拆分为 T001~T006，覆盖 REQ 11/11 |
| Implementation | Testing | 2026-03-09 | 完成 T001~T006 与 Implementation 自审收敛，Testing 输入已就绪 | Codex | 形成 `implementation_checklist.md` / `review_implementation.md` / `test_report.md` / `deployment.md`，v2.6 定向回归 61 passed，覆盖率 92% |
| Testing | Deployment | 2026-03-09 | Testing 第 1 轮审查收敛并通过项目级结果门禁 | Codex | 新增 `review_testing.md` / `spotcheck_testing_cr-20260309-001.md`，修复 4 条 ESB 兼容性阻断后恢复 full pytest `210 passed`，前端 build 与 backend compileall 均通过 |
| Deployment | Closed | 2026-03-10 | v2.6 版本完成验收并发布到 GitHub master | User+Claude | ESB 导入修复已验证通过，代码已推送远端，版本正式关闭 |

## CR状态更新记录（部署后填写）
| CR-ID | 之前状态 | 之后状态 | 上线日期 | 备注 |
|-------|---------|---------|---------|------|
| CR-20260309-001 | Accepted | Implemented | 2026-03-10 | STAGING 验收通过，按用户要求提交并推送远端 master |

## 紧急中断记录
| 触发时间 | 原因 | 当前状态 | 恢复条件 |
|---|---|---|---|

## 技术债务登记（Deferred Items）
| 来源阶段 | RVW-ID / 问题描述 | 严重度 | defer 理由 | 缓解措施 | 目标处理版本 | 状态 |
|---------|-------------------|--------|-----------|---------|-------------|------|
