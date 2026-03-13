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
_phase: Proposal
---
```
<!-- YAML front matter 枚举值:
  _baseline: 版本 tag（例如 `v1.0`）
  _workflow_mode: manual / semi-auto / auto
  _run_status: running / paused / wait_confirm / wait_feedback / completed
  _change_status: in_progress / done
  _change_level: major / minor / hotfix
  _review_round: 非负整数；同一阶段审查轮次，阶段切换时重置为 0；Hotfix 阶段不受 5 轮限制，若退出 Hotfix 并恢复 major/minor 常规流程，按新阶段从 0 重新计数
  _phase: ChangeManagement / Proposal / Requirements / Design / Planning / Implementation / Testing / Deployment / Hotfix
  完成态同步: done↔completed 必须配对；值不加引号；解析: grep "^_field:" status.md | awk '{print $2}' -->

<!-- 状态语义说明：
  - wait_confirm: 等待人工确认/决策（Phase 00-02 人工介入期，或 AI 自动期连续 3 轮不收敛时）
  - wait_feedback: 等待业务验收反馈（仅 Deployment 阶段，表示已部署到验收环境，等待业务方反馈）
  - Deployment 中若进入人工决策/多轮不收敛升级态，或已验收通过但尚未完成主分支收口 / tag / 远端 push，应从 wait_feedback 切换为 wait_confirm；处理完成后再回到 wait_feedback、继续收口，或回退上游阶段
  - completed 仅表示“主分支基线已形成”：业务验收通过 + 已合入 `main/master` + 匹配版本 tag 已创建并 push
  - hotfix 的 _review_round 不受 5 轮限制；退出 Hotfix 时不恢复进入前旧值 -->

| 项 | 值 |
|---|---|
| 版本号 | `<版本号>` |
| 变更目录 | `docs/<版本号>/` |
| 当前阶段 | ChangeManagement / Proposal / Requirements / Design / Planning / Implementation / Testing / Deployment / Hotfix |
| 变更状态 | In Progress / Done |
| 变更分级 | major |
| 基线版本（对比口径） | 版本 tag（例如 `v1.0`） |
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
<!-- Active CR 列表仅跟踪 Accepted / In Progress；Idea 进入下方 Idea池；Implemented / Dropped / Suspended 不进入 Active 列表。 -->

## Active CR 列表（🔴 MUST，CR场景）
| CR-ID | 状态（仅 Accepted/In Progress） | 标题 | 影响面（文档/模块/ID） | 链接 |
|---|---|---|---|---|
| CR-YYYYMMDD-001 | Accepted/In Progress | ... | requirements / API-xxx / REQ-xxx | `cr/CR-YYYYMMDD-001.md` |
## Idea池（可选，非Active）
| CR-ID | 状态（仅 Idea） | 标题 | 提出日期 | 优先级 | 链接 |
|---|---|---|---|---|---|
| CR-YYYYMMDD-002 | Idea | ... | YYYY-MM-DD | P0/P1/P2 | `cr/CR-YYYYMMDD-002.md` |
## 需要同步的主文档清单（如适用）
- [ ] `docs/lessons_learned.md`
- [ ] `docs/系统功能说明书.md`
- [ ] `docs/技术方案设计.md`
- [ ] `docs/接口文档.md`
- [ ] `docs/用户手册.md`
- [ ] `docs/部署记录.md`
## 回滚要点
- ...
## 备注
- 本文件用于显式标记阶段/完成状态，避免仅靠"文件存在性"推断导致误判。
- Deployment 阶段如已部署到 `STAGING/TEST`，`_run_status: wait_feedback` 表示等待业务反馈，不表示部署前批准。
- Deployment 阶段若业务已验收通过但主分支基线尚未形成，继续保持 `_change_status: in_progress`，并将 `_run_status` 切到 `wait_confirm`；只有基线发布完成后才改为 `done + completed`。

## 内联测试证据（TEST-RESULT）

> 适用场景：
> - minor 的 Testing / Deployment，可用本块替代 `test_report.md`
> - hotfix 退出阶段或标记完成前，必须内联本块作为最小测试证据

```markdown
<!-- TEST-RESULT-BEGIN -->
TEST_AT: 2026-03-12
TEST_SCOPE: hotfix-smoke
TEST_RESULT: pass
TEST_COMMANDS: echo hotfix-smoke
<!-- TEST-RESULT-END -->
```

字段约束：
- `TEST_AT`：`YYYY-MM-DD`
- `TEST_SCOPE`：本次验证范围（如 `hotfix-smoke`、`minor-regression`）
- `TEST_RESULT`：`pass` / `fail`
- `TEST_COMMANDS`：实际执行命令；多条命令可用 `;` 串联或拆多行追加说明
---
## 阶段转换记录
| 从阶段 | 到阶段 | 日期 | 原因 | 触发人 | 关键决策 |
|---|---|---|---|---|---|
| - | Proposal | YYYY-MM-DD | 新版本启动初始化 | User | 无 Active CR |
## CR状态更新记录（部署后填写）
| CR-ID | 之前状态 | 之后状态 | 上线日期 | 备注 |
|-------|---------|---------|---------|------|
| CR-YYYYMMDD-001 | In Progress | Implemented | YYYY-MM-DD | 部署验证通过 |
## 紧急中断记录
| 触发时间 | 原因 | 当前状态 | 恢复条件 |
|---|---|---|---|
| YYYY-MM-DD HH:MM | P0无法自动修复 | paused | 人工确认 |
## 技术债务登记（Deferred Items）

> 完整规则见 `ai_workflow.md` 的"质量债务管理规则"章节，此处只保留表结构

**规则摘要：**
- 来源：Design / Planning 阶段审查中，被明确 accept/defer 的设计/计划类问题
- 登记时机：问题被允许延期处理时
- 生命周期：Open / In Progress / Resolved

| 来源阶段 | RVW-ID / 问题描述 | 严重度 | defer理由 | 缓解措施 | 目标处理版本 | 状态 |
|---------|-------------------|--------|-----------|---------|-------------|------|
| Design | RVW-xxx：... | P1 | ... | 监控/告警/... | 下一版本 | Open/Resolved |

---

## 质量债务登记（🔴 MUST）

> 完整规则见 `ai_workflow.md` 的"质量债务管理规则"章节，此处只保留表结构

**规则摘要：**
- 来源：Testing / Deployment 阶段发现、但未在当前版本立即修复的质量问题
- 登记时机：问题决定延期到后续版本修复时
- 门禁影响：新版本启动时，检查 `_baseline` 指向版本的高风险质量债务数量和总量

| 债务ID | 类型 | 描述 | 风险等级 | 计划偿还版本 | 状态 |
|--------|------|------|---------|-------------|------|
| QD-001 | 测试覆盖 | [具体描述缺失的测试] | 高/中/低 | v2.5 | Open/Resolved |
| QD-002 | 契约验证 | [具体描述契约问题] | 高/中/低 | v2.5 | Open/Resolved |
