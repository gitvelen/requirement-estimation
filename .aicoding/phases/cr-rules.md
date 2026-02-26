# CR 规则汇总

## 目的
- 集中维护跨阶段通用的 CR 规则，避免在各阶段文档重复。

## 通用要求
1. Active CR 以 `status.md` 为真相源。
2. CR-ID 格式必须为 `CR-YYYYMMDD-NNN`。
3. CR 影响范围需覆盖文档、代码路径、验收与回滚。
4. 上线前需验证“本次上线 CR 列表 ⊆ Active CR 列表”。

## 阶段落地要点
1. 设计/计划：记录 CR 影响映射与任务覆盖。
2. 实现/测试：按 diff-only 审查补充 CR 影响验证证据。
3. 部署：完成 CR 闭环（状态更新、主文档同步、部署记录）。

## CR 状态枚举（规范定义）

> 此为 CR 状态的唯一规范定义。其他文件（如 status_template.md）中的状态表为内联副本，以此处为准。

| 状态值 | 含义 | 是否可入 Active CR 列表 | 说明 |
|--------|------|------------------------|------|
| Idea | 想法/提议 | ❌ 否 | 未确认的初步想法，不应进入 Active 列表 |
| Accepted | 已接受 | ✅ 是 | 需求已澄清，计划纳入当前版本 |
| In Progress | 进行中 | ✅ 是 | 正在实现中 |
| Implemented | 已实现 | ❌ 否（已从 Active 移除） | 已上线部署完成 |
| Dropped | 已废弃 | ❌ 否 | 不再实施 |
| Suspended | 已暂停 | ❌ 否 | 暂停实施，保留恢复可能 |

## CR 状态转换规则

- Idea → Accepted：AI 与用户完成需求澄清对话（范围、验收、影响面、风险），用户明确确认后转换
- Accepted → In Progress：开始实现时
- In Progress → Implemented：部署完成后
- Accepted/In Progress → Dropped：需求取消时
- In Progress → Suspended：暂停实施时
- Suspended → In Progress：恢复实施时
