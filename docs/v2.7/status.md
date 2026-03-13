---
_baseline: v2.6
_current: HEAD
_workflow_mode: auto
_run_status: running
_change_status: in_progress
_change_level: major
_review_round: 0
_phase: Design
---

| 项 | 值 |
|---|---|
| 版本号 | v2.7 |
| 变更目录 | `docs/v2.7/` |
| 当前阶段 | Design |
| 变更状态 | In Progress |
| 变更分级 | major |
| 基线版本（对比口径） | `v2.6` |
| 当前代码版本 | HEAD |
| 本次复查口径 | full |
| 当前执行 AI | Codex |
| 人类决策人 | User |
| 最后更新 | 2026-03-13 |

## 变更摘要
- v2.7 已完成 Requirements 阶段基线提交，当前进入 Design 阶段；Design 阶段审查轮次已重置
- Proposal 范围已从旧版“5 个 Skill + 脚本式提取”升级为“6 个内置 Skill + Skill Runtime + Per-System Memory 资产层”
- 新增管理员“服务治理”页导入能力，要求以 D3 为主更新画像，并对 D1/D4 形成按场景受控的语义更新结果
- 新增系统清单导入后的画像联动能力，但已收敛为“仅首次初始化或空画像时初始化写入，非空画像跳过且不进入 PM 建议流”
- 明确系统识别必须输出直接判定，功能点拆解必须读取画像与 Memory，并将 AI 评估后的修改继续沉淀为 Memory
- `proposal.md` 已同步到 v0.6；`requirements.md` 已升级到 v0.12，`review_requirements.md` 已完成第 6 轮复审并收敛；`design.md` 已升级到 v0.3，`review_design.md` 已完成第 3 轮自审并通过，当前进入 Design 阶段

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
- 审查：`review_design.md`
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
- [ ] `docs/系统功能说明书.md`
- [ ] `docs/技术方案设计.md`
- [ ] `docs/接口文档.md`
- [ ] `docs/用户手册.md`
- [ ] `docs/部署记录.md`

## 回滚要点
- L1（流程级回滚）：将 v2.7 变更停留在独立分支，不合入主分支。
- L2（版本级回滚）：如已合入，回退至基线 tag `v2.6`。

## 备注
- 本文件用于显式标记阶段/完成状态，避免仅靠“文件存在性”推断导致误判。
- 第 2 轮 Requirements 复审结论已被用户新增范围正式作废；Requirements 以 2026-03-13 的第 6 轮复审结果为准，并已在同日获人工确认进入 Design。
- 当前处于 Design 阶段：设计文档已收敛，后续将进入 Planning 做任务拆解和验证口径固化。

---

## 阶段转换记录
| 从阶段 | 到阶段 | 日期 | 原因 | 触发人 | 关键决策 |
|---|---|---|---|---|---|
| - | Proposal | 2026-03-12 | 新版本启动初始化 | User | 基线锁定 v2.6，无 Active CR |
| Proposal | Requirements | 2026-03-12 | Proposal 第 4 轮复审收敛且用户确认进入下一阶段 | User + Codex | 开始按分段走查协议编写 `requirements.md` |
| Requirements | Design | 2026-03-13 | Requirements 第 6 轮复审收敛，且用户确认进入 Design | User + Codex | 系统清单联动已收敛为“首次初始化/空画像补写，非空画像跳过” |
| Proposal | Requirements | 2026-03-12 | Proposal 第 4 轮复审收敛且用户确认进入下一阶段 | User + Codex | 开始按分段走查协议编写 `requirements.md` |
| Requirements | Design | 2026-03-13 | Requirements 第 6 轮复审收敛，且用户确认进入 Design | User + Codex | 系统清单联动已收敛为“首次初始化/空画像补写，非空画像跳过” |
| Design | Planning | 2026-03-13 | Design 第 3 轮复审通过，且用户确认进入 Planning | User + Codex | 开始编写 `plan.md`，按 requirements/design 做任务反向覆盖与验证命令拆解 |

## CR状态更新记录（部署后填写）
| CR-ID | 之前状态 | 之后状态 | 上线日期 | 备注 |
|-------|---------|---------|---------|------|

## 紧急中断记录
| 触发时间 | 原因 | 当前状态 | 恢复条件 |
|---|---|---|---|

## 技术债务登记（Deferred Items）
| 来源阶段 | RVW-ID / 问题描述 | 严重度 | defer 理由 | 缓解措施 | 目标处理版本 | 状态 |
|---------|-------------------|--------|-----------|---------|-------------|------|

## 质量债务登记（🔴 MUST）
| 债务ID | 类型 | 描述 | 风险等级 | 计划偿还版本 | 状态 |
|--------|------|------|---------|-------------|------|
