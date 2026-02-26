# 变更状态（`docs/<版本号>/status.md`）

```yaml
---
_baseline: v1.0
_current: HEAD
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: major
_review_round: 0
_phase: ChangeManagement
---
```
<!-- YAML front matter 枚举值:
  _workflow_mode: manual / semi-auto / auto
  _run_status: running / paused / wait_confirm / completed
  _change_status: in_progress / done
  _change_level: major / minor / hotfix
  _phase: ChangeManagement / Proposal / Requirements / Design / Planning / Implementation / Testing / Deployment
  完成态同步: done↔completed 必须配对；值不加引号；解析: grep "^_field:" status.md | awk '{print $2}' -->

| 项 | 值 |
|---|---|
| 版本号 | `<版本号>` |
| 变更目录 | `docs/<版本号>/` |
| 当前阶段 | ChangeManagement / Proposal / Requirements / Design / Planning / Implementation / Testing / Deployment |
| 变更状态 | In Progress / Done |
| 变更分级 | major |
| 基线版本（对比口径） | tag / commit（例如 `v1.0`） |
| 当前代码版本 | commit / tag / branch |
| 本次复查口径 | diff-only / full |
| 当前执行 AI | Claude / Codex / 其他 |
| 人类决策人 |  |
| 最后更新 | YYYY-MM-DD |
| 完成日期 | YYYY-MM-DD（如 Done） |

## 变更摘要
- ...
## 目标与成功指标
- ...
## 关键链接
- 提案：`proposal.md` / 需求：`requirements.md` / 设计：`design.md` / 计划：`plan.md`
- 变更单（CR）：`cr/CR-*.md`（如启用） / 审查：`review_<stage>.md`
- 测试报告：`test_report.md` / 部署：`deployment.md` / Issue/PR/看板/监控：...
<!-- CR状态枚举与转换规则见 phases/cr-rules.md -->

## Active CR 列表（🔴 MUST，CR场景）
| CR-ID | 状态 | 标题 | 影响面（文档/模块/ID） | 链接 |
|---|---|---|---|---|
| CR-YYYYMMDD-001 | Accepted/In Progress | ... | requirements / API-xxx / REQ-xxx | `cr/CR-YYYYMMDD-001.md` |
## Idea池（可选，非Active）
| CR-ID | 状态 | 标题 | 提出日期 | 优先级 | 链接 |
|---|---|---|---|---|---|
| CR-YYYYMMDD-002 | Idea | ... | YYYY-MM-DD | P0/P1/P2 | `cr/CR-YYYYMMDD-002.md` |
## 需要同步的主文档清单（如适用）
- [ ] `docs/系统功能说明书.md`
- [ ] `docs/技术方案设计.md`
- [ ] `docs/接口文档.md`
- [ ] `docs/用户手册.md`
- [ ] `docs/部署记录.md`
## 回滚要点
- ...
## 备注
- 本文件用于显式标记阶段/完成状态，避免仅靠"文件存在性"推断导致误判。
---
## 阶段转换记录
| 从阶段 | 到阶段 | 日期 | 原因 | 触发人 | 关键决策 |
|---|---|---|---|---|---|
| - | ChangeManagement | YYYY-MM-DD | 初始化 | User | - |
## CR状态更新记录（部署后填写）
| CR-ID | 之前状态 | 之后状态 | 上线日期 | 备注 |
|-------|---------|---------|---------|------|
| CR-YYYYMMDD-001 | In Progress | Implemented | YYYY-MM-DD | 部署验证通过 |
## 紧急中断记录
| 触发时间 | 原因 | 当前状态 | 恢复条件 |
|---|---|---|---|
| YYYY-MM-DD HH:MM | P0无法自动修复 | paused | 人工确认 |
## 技术债务登记（Deferred Items）
<!-- 记录本版本accept/defer的RVW(P1)问题；非DEFERRED_TO_STAGING（后者见review摘要块GWT_DEFERRED） -->
| 来源阶段 | RVW-ID / 问题描述 | 严重度 | defer 理由 | 缓解措施 | 目标处理版本 | 状态 |
|---------|-------------------|--------|-----------|---------|-------------|------|
| Design | RVW-xxx：... | P1 | ... | 监控/告警/... | 下一版本 | Open/Resolved |
