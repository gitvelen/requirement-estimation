# Review Report：Planning / <版本号>

> 轻量审查模板：聚焦任务可执行性、需求反向覆盖、验证方式可复现。
> 不含 GWT 逐条判定表（Planning 阶段无代码产出，无需 GWT 粒度判定）。

| 项 | 值 |
|---|---|
| 阶段 | Planning |
| 版本号 | <版本号> |
| 日期 | YYYY-MM-DD |
| 审查范围 | plan.md |
| 输入材料 | requirements.md, design.md, plan.md |

## 审查清单

- [ ] 任务可追踪：Txxx ID 完整，每条有清晰 DoD
- [ ] 粒度合适：可独立实现与验证，依赖关系清晰
- [ ] 追溯完整：任务关联 REQ/SCN/API
- [ ] 验证可复现：每个任务有命令级别验证方式
- [ ] 风险与回滚：涉及线上行为变化的任务有开关/回滚思路
- [ ] 内容完整：覆盖需求和设计阶段产出的成果

## 需求反向覆盖

| REQ-ID | 关联任务 | 覆盖判定 | 备注 |
|--------|---------|---------|------|
| REQ-001 | T001, T003 | ✅/⚠️/❌ | |

## 关键发现

### RVW-001（P0/P1/P2）<标题>
- 证据：
- 风险：
- 建议修改：

## 对抗性自检
- [ ] 是否存在"我知道意思但文本没写清"的地方？
- [ ] 所有"可选/或者/暂不"表述是否已收敛为单一口径？
- [ ] 高风险项是否已在本阶段收敛？

## 收敛判定
- P0(open): X
- P1(open): Y
- 结论：✅ 通过 / ⚠️ 有条件通过 / ❌ 不通过

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: planning
REVIEW_RESULT: pass|fail
P0_OPEN: 0
P1_OPEN: 0
RVW_TOTAL: 0
REVIEWER: <name>
REVIEW_AT: YYYY-MM-DD
VERIFICATION_COMMANDS: rg -n "REQ-" docs/<版本号>/plan.md
<!-- REVIEW-SUMMARY-END -->

---

## 多轮审查追加格式

> 后续轮次以追加方式写入，并更新 REVIEW-SUMMARY-BEGIN 块中的字段。

```markdown
## 第 N 轮审查（YYYY-MM-DD）
### 上轮遗留问题处置
| RVW-ID | 处置 | 证据 |
|--------|------|------|
| RVW-001 | 已修复 | plan.md §x.x 已补充 |

### 本轮新发现
（同"关键发现"格式）

<!-- 更新 REVIEW-SUMMARY-BEGIN 块中的字段 -->
```
