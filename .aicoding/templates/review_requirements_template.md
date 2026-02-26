# Review Report：Requirements / <版本号>

> 轻量审查模板：聚焦需求完整性、GWT 可判定性、禁止项固化。
> 不含代码级证据判定（Requirements 阶段无代码产出）。

| 项 | 值 |
|---|---|
| 阶段 | Requirements |
| 版本号 | <版本号> |
| 日期 | YYYY-MM-DD |
| 审查范围 | requirements.md |
| 输入材料 | proposal.md, requirements.md |

## 审查清单

- [ ] Proposal 覆盖：每个 P-DO/P-DONT/P-METRIC 在 §1.4 覆盖映射表中有对应 REQ-ID 或标注 defer
- [ ] 需求可验收：每条 REQ 有 GWT 格式验收标准，无"优化""提升"等模糊词
- [ ] 场景完整：正常/异常/边界场景均已覆盖
- [ ] GWT 可判定：Given/When/Then 三段均为具体可观测行为，无歧义
- [ ] 禁止项固化：对话中出现的"不要/禁止/不允许/不显示"已固化为 REQ-C + GWT
- [ ] REQ-C 完整：每条 REQ-C 有对应 GWT-ID，可被门禁校验
- [ ] ID 唯一性：REQ-ID / GWT-ID 无重复
- [ ] 术语一致：关键术语与 proposal.md 一致，无歧义别名

## 禁止项/不做项确认清单

> 来源覆盖：对话中出现的不要/不做/禁止/不允许/不显示/不出现/不需要 + proposal.md Non-goals。
> 每条必须归类为 A（已固化为 REQ-C）或 B（明确写入 Non-goals）。

| # | 禁止/不做项描述 | 归类 | 目标 | 来源 |
|---|----------------|------|------|------|
| 1 | ... | A/B | REQ-Cxxx / Non-goals | proposal.md §x / 对话 |

<!-- CONSTRAINTS-CHECKLIST-BEGIN -->
| ITEM | CLASS | TARGET | SOURCE |
|------|-------|--------|--------|
| ... | A/B | REQ-Cxxx / Non-goals / NONE | proposal.md ... |
<!-- CONSTRAINTS-CHECKLIST-END -->

## 需求覆盖判定

| REQ-ID | GWT 数量 | GWT 可判定 | 备注 |
|--------|---------|-----------|------|
| REQ-001 | N | ✅/⚠️/❌ | |

## 高风险语义审查（必做）

> 以下类型必须逐条审查语义明确性，不得仅靠覆盖表 ✅ 放行。

- [ ] REQ-C 禁止项：每条在 requirements.md 中有明确 GWT（不是"提及"而是"可验收"）
- [ ] "可选/二选一/仅提示"表述：默认按 P1 处理，必须收敛为单一口径
- [ ] 角色差异：不同角色的展示/权限规则是否无歧义
- [ ] 数据边界：空值/极值/并发场景是否有明确行为定义

## 关键发现

### RVW-001（P0/P1/P2）<标题>
- 证据：
- 风险：
- 建议修改：

## 对抗性自检
- [ ] 是否存在"我知道意思但文本没写清"的地方？
- [ ] 所有"不要/禁止"是否都已固化为 REQ-C + GWT？
- [ ] 所有"可选/或者/暂不"表述是否已收敛为单一口径？
- [ ] 高风险项是否已在本阶段收敛？

## 收敛判定
- P0(open): X
- P1(open): Y
- 结论：✅ 通过 / ⚠️ 有条件通过 / ❌ 不通过

<!-- CONSTRAINTS-CONFIRMATION-BEGIN -->
CONSTRAINTS_CONFIRMED: yes
CONFIRMED_BY: <审查者>
CONFIRMED_AT: YYYY-MM-DD
<!-- CONSTRAINTS-CONFIRMATION-END -->

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: requirements
REVIEW_RESULT: pass|fail
P0_OPEN: 0
P1_OPEN: 0
RVW_TOTAL: 0
REVIEWER: <name>
REVIEW_AT: YYYY-MM-DD
VERIFICATION_COMMANDS: rg -n "关键词" docs/<版本号>/requirements.md
<!-- REVIEW-SUMMARY-END -->

---

## 多轮审查追加格式

> 后续轮次以追加方式写入，并更新 REVIEW-SUMMARY-BEGIN 块中的字段。

```markdown
## 第 N 轮审查（YYYY-MM-DD）
### 上轮遗留问题处置
| RVW-ID | 处置 | 证据 |
|--------|------|------|
| RVW-001 | 已修复 | requirements.md §x.x 已补充 |

### 本轮新发现
（同"关键发现"格式）

<!-- 更新 REVIEW-SUMMARY-BEGIN 块中的字段 -->
<!-- 更新 CONSTRAINTS-CONFIRMATION-BEGIN 块中的字段 -->
```
