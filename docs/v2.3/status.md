---
_baseline: v2.2
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
| 版本号 | v2.3 |
| 变更目录 | `docs/v2.3/` |
| 当前阶段 | Deployment |
| 变更状态 | Done |
| 变更分级 | major |
| 基线版本（对比口径） | v2.2 |
| 当前代码版本 | HEAD（d9b9284） |
| 本次复查口径 | full |
| 当前执行 AI | Codex |
| 人类决策人 |  |
| 最后更新 | 2026-02-26 |
| 完成日期 | 2026-02-26 |

## 变更摘要
- v2.3 深度代码扫描增强：接通现有扫描断路（capability_item → Agent 流水线）、AST 解析替换正则、调用链分析与服务依赖图、数据流分析、代码复杂度度量、变更影响面分析、GitLab 仓库集成

## 目标与成功指标
| ID | 指标定义（可判定） | 基线（v2.2） | 目标（v2.3） | 统计窗口 | 数据源 |
|---|---|---|---|---|---|
| M1 | `capability_item` 评估链路可达率 = 通过用例数 / 总用例数 | 0%（链路断开） | >= 95% | 每次全量回归 | `test_report.md` 中链路回归结果 |
| M2 | AST 覆盖率 = AST 成功解析文件数 / 可解析文件数 | 0%（tree-sitter 未接入） | >= 95% | 每次全量回归 | `test_report.md` + 扫描统计输出 |
| M3 | 调用图覆盖率 = 入图方法数 / 可分析方法数 | 0%（无方法级调用图） | >= 85% | 每次全量回归 | `test_report.md` + 调用图统计输出 |
| M4 | 数据流覆盖率 = 已识别读写关系实体数 / 可分析实体数 | 0%（无实体读写关系图） | >= 80% | 每次全量回归 | `test_report.md` + 数据流统计输出 |
| M5 | 复杂度覆盖率 = 具备 CC+WMC 指标的方法数 / 可分析方法数 | 0%（无统一复杂度产物） | >= 95% | 每次全量回归 | `test_report.md` + 复杂度统计输出 |
| M6 | GitLab 扫描路径通过率 = 已通过模式数 / 3（Archive/Compare/Raw） | 0/3 | 3/3（且任务成功率 >= 99%） | 每次全量回归 + 发布前一次 | `test_report.md` + 扫描任务日志 |

## 关键链接
- 提案：`proposal.md`
- 需求：`requirements.md`
- 设计：`design.md`
- 计划：`plan.md`
- 变更单（CR）：`cr/CR-*.md`（如启用）
- 审查：`review_testing.md`
- 测试报告：`test_report.md`
- 部署：`deployment.md`

## Active CR 列表（🔴 MUST，CR场景）
| CR-ID | 状态 | 标题 | 影响面（文档/模块/ID） | 链接 |
|---|---|---|---|---|

## Idea池（可选，非Active）
| CR-ID | 状态 | 标题 | 提出日期 | 优先级 | 链接 |
|---|---|---|---|---|---|

## 需要同步的主文档清单（如适用）
- [x] `docs/系统功能说明书.md`
- [x] `docs/技术方案设计.md`
- [x] `docs/接口文档.md`
- [x] `docs/用户手册.md`
- [x] `docs/部署记录.md`

## 回滚要点
- L1（功能级回滚，优先）：
  - 在 `.env.backend` 设置：`V23_DEEP_SCAN_ENABLED=false`、`V23_GITLAB_SOURCE_ENABLED=false`
  - 执行：`docker-compose restart backend`
  - 验证：`curl -fsS http://127.0.0.1/api/v1/health`；`/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_code_scan_api.py`
- L2（版本级回滚，L1 无法恢复时）：
  - 执行：`git checkout v2.2 && bash deploy-all.sh`
  - 验证：`curl -fsS http://127.0.0.1/api/v1/health`；`/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_code_scan_api.py`

## 备注
- 本文件用于显式标记阶段/完成状态，避免仅靠"文件存在性"推断导致误判。
- v2.3 为 Major 级别变更（新功能、跨模块影响），走完整 8 阶段流程。
- Phase 00-02 为人工介入期，需用户明确确认后方可推进。

---

## 阶段转换记录
| 从阶段 | 到阶段 | 日期 | 原因 | 触发人 | 关键决策 |
|---|---|---|---|---|---|
| - | ChangeManagement | 2026-02-26 | 初始化 v2.3 深度代码扫描增强 | User | Major 级别，走完整 8 阶段流程；基线 v2.2 |
| ChangeManagement | Proposal | 2026-02-26 | 审查收敛后人工确认进入下一阶段 | User+AI | `review_change_management.md` 第2轮复审 P0/P1/P2 open=0 |
| Proposal | Requirements | 2026-02-26 | Proposal 第4轮复审收敛并获人工确认推进 | User+Codex | `review_proposal.md` 第4轮复审 P0/P1/P2 open=0 |
| Requirements | Design | 2026-02-26 | Requirements 审查通过并获人工确认推进 | User+Codex | `review_requirements.md` 约束清单确认 `CONSTRAINTS_CONFIRMED=yes` |
| Design | Planning | 2026-02-26 | Design 自审收敛（P0/P1=0）自动推进 | Codex | `review_design.md` 审查通过 |
| Planning | Implementation | 2026-02-26 | Planning 自审收敛（P0/P1=0）自动推进 | Codex | `review_planning.md` 审查通过 |
| Implementation | Testing | 2026-02-26 | Implementation 自审收敛（P0/P1=0）自动推进 | Codex | `review_implementation.md` 审查通过；T001~T007 完成 |
| Testing | Deployment | 2026-02-26 | Testing 自审收敛（P0/P1=0）自动推进 | Codex | `test_report.md` + `review_testing.md` 通过；已生成 `deployment.md`，等待人工验收 |
| Deployment | Deployment | 2026-02-26 | 用户确认继续全自动推进，完成主文档同步与验收收口 | User+Codex | `deployment.md` 置 Approved；`_run_status=completed`、`_change_status=done` |
| Deployment | Deployment | 2026-02-26 | 文档收口提交触发门禁冲突，按用户授权使用 `--no-verify` 完成 `status.md` 提交并补审计说明 | User+Codex | 见 `deployment.md`「逃生通道审计说明」 |

## CR状态更新记录（部署后填写）
| CR-ID | 之前状态 | 之后状态 | 上线日期 | 备注 |
|-------|---------|---------|---------|------|

## 紧急中断记录
| 触发时间 | 原因 | 当前状态 | 恢复条件 |
|---|---|---|---|

## 技术债务登记（Deferred Items）
| 来源阶段 | RVW-ID / 问题描述 | 严重度 | defer 理由 | 缓解措施 | 目标处理版本 | 状态 |
|---------|-------------------|--------|-----------|---------|-------------|------|
