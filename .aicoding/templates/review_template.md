# 阶段化审查模板索引（`review_template.md`）

> 本文件为审查模板索引。各阶段已拆分为独立模板，请按阶段选用对应模板。

## 模板总览

| 模板 | 适用阶段 | 复杂度 | 需要 GWT 判定表 | 路径 |
|------|---------|--------|----------------|------|
| （自由格式） | ChangeManagement | — | ❌ | 人工介入期，无结构化模板要求；审查结果追加到 `review_change_management.md` |
| （自由格式） | Proposal | — | ❌ | 人工介入期，无结构化模板要求；审查结果追加到 `review_proposal.md` |
| `review_requirements_template.md` | Requirements | 中 | ❌（用 CONSTRAINTS-CHECKLIST 替代） | `templates/review_requirements_template.md` |
| `review_design_template.md` | Design | 轻 | ❌ | `templates/review_design_template.md` |
| `review_planning_template.md` | Planning | 轻 | ❌ | `templates/review_planning_template.md` |
| `review_implementation_template.md` | Implementation (major) | 重 | ✅ | `templates/review_implementation_template.md` |
| `review_testing_template.md` | Testing (major) | 重 | ✅ | `templates/review_testing_template.md` |
| `review_minor_template.md` | Minor（任意阶段） | 轻 | ✅（精简） | `templates/review_minor_template.md` |

## 选用规则

1. **ChangeManagement 阶段**：自由格式审查（人工介入期），结果追加到 `review_change_management.md`；建议参照 REP 协议执行事实核实
2. **Proposal 阶段**：自由格式审查（人工介入期），结果追加到 `review_proposal.md`；建议参照 REP 协议执行事实核实和概念交叉引用
3. **Requirements 阶段**：使用 `review_requirements_template.md`（已有独立验证逻辑：CONSTRAINTS-CHECKLIST + CONSTRAINTS-CONFIRMATION）
4. **Design 阶段**：使用 `review_design_template.md`（轻量，聚焦需求覆盖、架构合理性、API 契约）
5. **Planning 阶段**：使用 `review_planning_template.md`（轻量，聚焦任务可执行性、需求反向覆盖）
6. **Implementation 阶段**：
   - major → `review_implementation_template.md`（完整 GWT 判定 + 摘要块 + spotcheck）
   - minor → `review_minor_template.md`
7. **Testing 阶段**：
   - major → `review_testing_template.md`（完整 GWT 判定 + 摘要块 + spotcheck + test_report 交叉校验）
   - minor → `review_minor_template.md`（Testing→Deployment 前必须包含 `MINOR-TESTING-ROUND` 机器可读结论块）

## 通用原则

- **严重度判定**：P0（Blocker）/ P1（Major）/ P2（Minor），详见各模板内说明
- **证据驱动**：列出"你验证了什么、怎么验证、关键输出是什么"；避免仅凭推断
- **对抗性自检**：自审时必填，缓解"自己写自己审"的盲区
- **机器可读摘要块**：门禁只认最后一次摘要块，计数必须可验真
- **审查执行协议（REP）**：所有审查必须按 A→B→C→D 四步执行（详见 cr-rules.md §审查执行协议）；第 2+ 轮追加步骤 E

## 落盘路径约定

- `docs/<版本号>/review_<stage>.md`（阶段名用小写英文）
- 审查口径：优先读取 `docs/<版本号>/status.md` 中的"基线版本/本次复查口径/Active CR 列表"

---

*模板版本: v3.0 | 分级审查体系，按阶段选用对应模板*
