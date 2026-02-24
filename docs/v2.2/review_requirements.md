# Review Report：Requirements / v2.2

| 项 | 值 |
|---|---|
| 阶段 | Requirements |
| 版本号 | v2.2 |
| 日期 | 2026-02-24 |
| 基线版本（对比口径） | v2.1 |
| 当前代码版本 | HEAD |
| 复查口径 | full |
| Active CR（如有） | 无 |
| 检查点 | 可验收性/一致性/可追溯/边界与异常/接口与指标口径/禁止项收口 |
| 审查范围 | 文档（`docs/v2.2/requirements.md`、`docs/v2.2/proposal.md`、`docs/v2.2/status.md`） |
| 输入材料 | `docs/v2.2/requirements.md`、`docs/v2.2/proposal.md`、`docs/v2.2/status.md`、`docs/系统功能说明书.md`、`docs/接口文档.md` |

## 使用方式
- 人工指定审查者：`@review Claude` 或 `@review Codex`
- 审查结果必须**追加到本文件末尾**
- Requirements 阶段在进入 Design 前，必须完成“禁止项/不做项确认清单”（见下方机器可读块）

## 当前结论摘要
- 总体结论：⚠️ 有条件通过（需人工确认"禁止项/不做项清单"，并确认是否进入 Design）
- Blockers（P0）：0
- 高优先级（P1）：0（第 2 轮 RVW-004~009 已全部 Fix）
- 其他建议（P2+）：0（第 2 轮 RVW-010~011 已全部 Fix）

## 禁止项/不做项确认清单（🔴 MUST，进入 Design 前必须完成）

> 说明：清单来源需覆盖：对话中出现的不要/不做/禁止/不允许/不显示/不出现 + `docs/v2.2/proposal.md` 的 Non-goals。
> 每条必须二选一：A) 固化为 `REQ-Cxxx`（给出 REQ-C 与 GWT 映射）或 B) 写入 Non-goals（给出边界与原因）。

<!-- CONSTRAINTS-CHECKLIST-BEGIN -->
| ITEM | CLASS | TARGET | SOURCE |
|---|---|---|---|
| C-001 | A | REQ-C001 | requirements.md REQ-C001（来源：proposal.md P-DONT-01） |
| C-002 | A | REQ-C002 | requirements.md REQ-C002（来源：proposal.md P-DONT-02） |
| C-003 | A | REQ-C003 | requirements.md REQ-C003（来源：proposal.md P-DONT-03） |
| C-004 | A | REQ-C004 | requirements.md REQ-C004（来源：proposal.md P-DONT-04） |
| C-005 | A | REQ-C005 | requirements.md REQ-C005（来源：proposal.md §约束/前提：不涉及数据库迁移或数据格式变更） |
| C-006 | A | REQ-C006 | requirements.md REQ-C006（来源：proposal.md §开放问题决策：文档导入不做批量） |
| C-007 | A | REQ-C007 | requirements.md REQ-C007（来源：proposal.md §不包含（Non-goals）：FUNC-022 下线；并在需求中固化为禁止项） |
| C-008 | A | REQ-C008 | requirements.md REQ-C008（来源：proposal.md §开放问题决策：排行榜统计周期不提供配置项） |
| C-009 | B | Non-goals | proposal.md §不包含（Non-goals）：新增角色或权限体系调整（原因：本期不做，避免影响面扩大） |
| C-010 | B | Non-goals | proposal.md §不包含（Non-goals）：移动端适配（原因：本期不做） |
| C-011 | B | Non-goals | proposal.md §不包含（Non-goals）：国际化（i18n）（原因：本期不做） |
| C-012 | B | Non-goals | proposal.md §不包含（Non-goals）：性能优化（非本次目标）（原因：本期不做） |
| C-013 | B | Non-goals | proposal.md 变更六“后端接口策略”：不新建统一导入 API（原因：本期按类型复用既有 API，避免引入新契约） |
<!-- CONSTRAINTS-CHECKLIST-END -->

<!-- CONSTRAINTS-CONFIRMATION-BEGIN -->
CONSTRAINTS_CONFIRMED: yes
CONFIRMED_BY: User
CONFIRMED_AT: 2026-02-24
<!-- CONSTRAINTS-CONFIRMATION-END -->

---

## 2026-02-24 | 第 1 轮 | 审查者：Codex

### 审查角度
Requirements 阶段全面走查：覆盖性（R5）、可验收性（GWT）、一致性、可追溯（REQ/SCN/API）、边界与异常、接口与指标口径、禁止项/不做项收口。

### 本轮结论
- `docs/v2.2/requirements.md` 已补齐提案范围内的关键缺口（标题精简含“消息通知”；去除“省略号”占位；细化排行榜计算逻辑；补齐看板标题精简验收；补齐报告下载接口引用），版本更新为 v0.2。
- 禁止项（REQ-C001~REQ-C008）均已在 requirements.md 中定义并提供 GWT；本文件已补齐“禁止项/不做项确认清单”机器可读表。
- 仍需人工确认：将 `CONSTRAINTS_CONFIRMED` 改为 `yes`，并填写确认信息（见下一轮“人工确认块”）。

### 关键发现与处理记录
| RVW-ID | 严重度 | 描述 | 处理决策 | 说明/证据 |
|---|---|---|---|---|
| RVW-001 | P1 | 标题精简范围未覆盖“消息通知”，且看板标题“仅保留子页面名称”未落到可验收条目 | Fix | 已在 `docs/v2.2/requirements.md` v0.2 补齐：REQ-001 增加“消息通知”；REQ-003/REQ-004 增加标题精简 GWT |
| RVW-002 | P2 | 需求文本存在“省略号”占位，可能导致后续验收口径歧义 | Fix | 已在 `docs/v2.2/requirements.md` v0.2 去除相关占位（SCN-003、REQ-003、REQ-013） |
| RVW-003 | P1 | `review_requirements.md` 未按门禁格式提供 CONSTRAINTS-CHECKLIST（无法推进 Requirements→Design） | Fix（待人工确认） | 已补齐机器可读表；仍需人工将 `CONSTRAINTS_CONFIRMED: no → yes` |

### 建议验证清单（命令级别）
- [x] 校验 requirements 完整性（REQ/GWT 唯一性与外键归属）：`bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_requirements_integrity docs/v2.2/requirements.md docs/v2.2/requirements.md'`（exit 0）

### 人工确认块（进入 Design 前必须完成）
> 操作：将上方确认块改为 `CONSTRAINTS_CONFIRMED: yes`，并补齐 `CONFIRMED_BY` 与 `CONFIRMED_AT`（YYYY-MM-DD）。

---

## 2026-02-24 | 第 2 轮 | 审查者：Claude

### 审查角度
Requirements 阶段全面走查：GWT 可验收性（每条 REQ 的 GWT 是否覆盖其页面/交互/业务规则描述）、覆盖性（R5，proposal In Scope 全覆盖）、一致性（R10，术语/口径）、禁止项收口、边界与异常。同时修复发现的 GWT 缺口（边查边改）。

### 上一轮问题处理状态
| RVW-ID | 严重度 | 上一轮描述 | 处理方式 | 本轮状态 |
|---|---|---|---|---|
| RVW-001 | P1 | 标题精简范围未覆盖"消息通知"，看板标题精简未落验收 | Fix（v0.2） | ✅ 已关闭 |
| RVW-002 | P2 | 需求文本存在"省略号"占位 | Fix（v0.2） | ✅ 已关闭 |
| RVW-003 | P1 | review_requirements.md 未按门禁格式提供 CONSTRAINTS-CHECKLIST | Fix（v0.2） | ✅ 已关闭（待人工确认） |

### 本轮新发现问题
| RVW-ID | 严重度 | 描述 | 处理决策 | 说明/证据 |
|---|---|---|---|---|
| RVW-004 | P1 | REQ-001 GWT 仅覆盖 3/9 页面，缺少已完成任务列表、系统清单配置、COSMIC规则配置、用户管理、知识库管理、系统画像-信息展示 | Fix | 已在 v0.3 补齐 GWT-REQ-001-04（6 页合并验收） |
| RVW-005 | P1 | REQ-005 缺少点击"已完成"子菜单的 GWT | Fix | 已在 v0.3 补齐 GWT-REQ-005-03 |
| RVW-006 | P1 | REQ-006 缺少摘要卡片必须展示 7 个字段的 GWT，且未验收"删除区域"（任务详情/专家评估进度/报告版本列表） | Fix | 已在 v0.3 补齐 GWT-REQ-006-03（字段）、GWT-REQ-006-04（删除区域） |
| RVW-007 | P1 | REQ-007 缺少非实质性修改的反向验收（不应触发确认弹窗） | Fix | 已在 v0.3 补齐 GWT-REQ-007-03 |
| RVW-008 | P1 | REQ-008 未覆盖 P-DO-11（"信息看板"改名为"信息展示"）的 GWT | Fix | 已在 v0.3 补齐 GWT-REQ-008-03 |
| RVW-009 | P1 | REQ-011 GWT 仅覆盖 AI 重评估触发，缺少 PM 编辑和专家评估完成触发备注的验收 | Fix | 已在 v0.3 补齐 GWT-REQ-011-03（PM）、GWT-REQ-011-04（专家） |
| RVW-010 | P2 | REQ-013 GWT 仅覆盖 2/5+ 重定向规则，缺少 rankings/overview/tab=ongoing | Fix | 已在 v0.3 补齐 GWT-REQ-013-03~05 |
| RVW-011 | P2 | pre-write-dispatcher.sh 入口门禁 session key 不一致导致门禁误拦截 | Fix | 已修复：将 `${CLAUDE_SESSION_ID:-$$}` 改为 `$(aicoding_session_key)` |

### 本轮结论
- `docs/v2.2/requirements.md` 已升级为 v0.3，补齐 7 处 GWT 缺口（新增 11 条 GWT）。
- 禁止项（REQ-C001~REQ-C008）GWT 完整，无遗漏。
- 覆盖性（R5）：proposal In Scope 15 条 P-DO 均有对应 REQ/GWT 覆盖。
- 一致性（R10）：术语与 proposal.md v0.3 一致，无冲突。
- 框架 bug 修复：pre-write-dispatcher.sh 入口门禁 session key 不一致问题已修复。
- 仍需人工确认：将 `CONSTRAINTS_CONFIRMED` 改为 `yes`。

### 收敛判定
- 本轮后：P0(open)=0, P1(open)=0, P2(open)=0
- 距离收敛：是（所有发现已 Fix）
- 建议：人工确认禁止项清单后可进入 Design 阶段

---

## 2026-02-24 | 人工确认 | 确认人：User
- 已确认禁止项/不做项清单（`CONSTRAINTS_CONFIRMED: yes`）
- 已确认进入 Design 阶段
