# Review Report：Proposal / v2.1

| 项 | 值 |
|---|---|
| 阶段 | Proposal |
| 版本号 | v2.1 |
| 日期 | 2026-02-11 |
| 基线版本（对比口径） | v2.0 |
| 复查口径 | full |
| Active CR（如有） | 无 |
| 检查点 | 价值/范围边界/指标口径/风险与回滚/依赖与可落地性 |
| 审查范围 | 文档（`docs/v2.1/proposal.md`、`docs/v2.1/status.md`）；只读走查现有实现与数据样本用于提供证据 |
| 输入材料 | `docs/v2.1/proposal.md`、`docs/v2.1/status.md`、`backend/api/system_routes.py`、`data/knowledge_retrieval_logs.json`、`data/ai_effect_snapshots.json` |

## 结论摘要
- 总体结论：有条件通过（建议补齐 2 项 P1 后收敛 Proposal）
- Blockers（P0）：0
- 高优先级（P1）：2
- 其他建议（P2+）：2

## 关键发现（按优先级）

### RVW-001（P1）缺少“备选方案/取舍对比”章节，难以回溯关键结构性决策
- 证据：`docs/v2.1/proposal.md` 未包含“备选方案（可选）”或等价对比段落；但本次包含结构性变更 B-04（系统画像 7→4 字段）、C-01（系统清单数据源统一）等。
- 风险：后续阶段争议点无法快速回溯“为什么不选 A”；范围蔓延或返工概率上升。
- 建议修改：
  - 在 Proposal 补充至少 1 个替代方案对比（例如：保留 7 字段仅新增 `module_structure` vs 收敛为 4 字段；是否保留旧字段迁移等），并明确结论与取舍。
- 验证方式（可复现）：
  - `rg -n \"备选方案\" docs/v2.1/proposal.md`

### RVW-002（P1）“知识命中率≥30%”指标需明确达成前提，否则容易成为不可控目标
- 证据（本地样本）：检索日志存在但 0 命中（total=43、hit=0、max_similarity=0.0），且任务级快照 `knowledge_hit_rate` 平均值为 0（n=64）。
  - 复现命令（统计命中率与 max_similarity）：
    - `python - <<'PY'\nimport json, pathlib\nlogs=json.loads(pathlib.Path('data/knowledge_retrieval_logs.json').read_text(encoding='utf-8'))\nprint('total',len(logs))\nprint('hit',sum(1 for x in logs if (x.get('hit_count') or 0)>0))\nprint('max_hit',max((x.get('hit_count') or 0) for x in logs) if logs else None)\nprint('max_similarity',max((x.get('max_similarity') or 0.0) for x in logs) if logs else None)\nPY`
- 风险：
  - 没有“知识/画像数据量”与“阈值/TopK”前提时，指标不可控；上线后很难解释“为什么没达标”。
  - B-04/B-06 的闭环效果（画像增强→AI 改进）可能无法量化验证。
- 建议修改：
  - 在 Proposal（或后续 Requirements/Design）补充指标前提与口径固定项：统计窗口、TopK、阈值、知识类型范围、最小样本量（例如近 30 天且检索次数≥N 才出值）。
  - 明确“达标手段”归因：数据覆盖（导入/画像发布）+ 检索策略（阈值/召回）+ Prompt 注入位置。
- 验证方式（可复现）：
  - `python - <<'PY'\nimport json, pathlib\nsnaps=json.loads(pathlib.Path('data/ai_effect_snapshots.json').read_text(encoding='utf-8'))\nvals=[(s.get('metrics') or {}).get('knowledge_hit_rate') for s in snaps if s.get('system') is None and s.get('module') is None]\nvals=[v for v in vals if isinstance(v,(int,float))]\nprint('task_level_snapshots',len(vals),'avg',sum(vals)/len(vals) if vals else None)\nPY`

### RVW-003（P2）C-01 根因与落地一致，但建议在后续阶段明确“唯一数据源”的具体文件/接口
- 证据：`docs/v2.1/proposal.md` 已明确“废弃 legacy `system_list.csv`”；现有实现中 `backend/api/system_routes.py` 仍定义 `CSV_PATH=.../system_list.csv`（见 `backend/api/system_routes.py` 第 37 行）。
  - 复现命令：`rg -n \"system_list\\.csv\" backend/api/system_routes.py`
- 风险：实现阶段如果只修一处入口，仍可能存在“导入写 A、读取走 B”的残留路径。
- 建议修改：Requirements/Design 中把“系统清单唯一数据源”落实为：存储文件路径 + CRUD API（读取/写入的唯一入口）+ 其他模块引用方式（system_identification/knowledge_import/dashboard）。

### RVW-004（P2）Feature Flags/回滚策略已写入 Proposal，但需在 Planning/Implementation 阶段强制落地并验收
- 证据：`docs/v2.1/proposal.md` 新增了 `V21_*` 开关与回滚策略；当前尚无对应实现与验收条目（属正常阶段差异）。
- 风险：到实现阶段容易“文档有、代码无”，回滚不可用。
- 建议修改：进入 Planning 阶段时把开关落为 T 任务，并写明 DoD（默认值、读取位置、覆盖范围、验证命令）。

## 建议验证清单（命令级别）
- [ ] 指标口径一致性：`rg -n \"知识命中率|knowledge_hit_rate\" docs/v2.1/proposal.md`
- [ ] C-01 数据源残留扫描：`rg -n \"system_list\\.csv\" backend -S`
- [ ] 检索命中率基线：运行 RVW-002 的 python 统计脚本
- [ ] 文档结构完整性（标题检查）：`rg -n \"^(#|##|###|####) \" docs/v2.1/proposal.md`

## 开放问题（需产品/Owner 确认）
- [ ] 是否需要在 Proposal 即补齐“备选方案”对比（推荐：是，最少 1 条）
- [ ] “知识命中率≥30%”是否需要附带前提（最小样本量/数据准备）并作为门禁指标？

## 处理记录（建议由开发/人工填写）
| RVW-ID | 严重度 | 处理决策（Fix/Defer/Accept） | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-001 | P1 | Accept | AI | 决策链路已通过 D-06/D-07/D-13 及 v0.3→v1.5 变更记录可追溯；Proposal 阶段不强制要求独立"备选方案"章节 | proposal.md 关键决策记录 D-06/D-13 |
| RVW-002 | P1 | Fix | AI | 知识命中率从硬性目标（≥30%）降级为观测指标；补充前提条件（最小样本量/数据覆盖/参数固定）；具体目标值延至 Requirements 阶段根据数据准备情况确定 | proposal.md 成功指标表 v1.8 |
| RVW-003 | P2 | Defer | AI | 系统清单唯一数据源的具体文件/接口/CRUD 入口细节属于 Requirements/Design 阶段产出 | 待 requirements.md 落实 |
| RVW-004 | P2 | Defer | AI | Feature Flags 实现与验收条目属于 Planning/Implementation 阶段产出；Proposal 已写明开关清单与回滚策略 | 待 plan.md 落实为 T 任务 |
