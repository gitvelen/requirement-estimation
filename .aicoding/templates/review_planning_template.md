# Review Report：Planning / <版本号>

> **共享章节**：见 `templates/review_skeleton.md`
> 本模板只包含 Planning 阶段特定的审查内容

> 轻量审查模板：聚焦任务可执行性、需求反向覆盖、验证方式可复现。
> 不含 GWT 逐条判定表（Planning 阶段无代码产出，无需 GWT 粒度判定）。

| 项 | 值 |
|---|---|
| 阶段 | Planning |
| 版本号 | <版本号> |
| 日期 | YYYY-MM-DD |
| 审查范围 | plan.md |
| 输入材料 | requirements.md, design.md, plan.md |

## §0 审查准备（REP 步骤 A+B）
> 见 `templates/review_skeleton.md` 的"§0 审查准备"章节
>
> **本阶段特定说明**：
> - A. 事实核实：从 plan.md 提取事实性声明，逐条对照 design.md 核实
> - B. 关键概念交叉引用：提取关键概念（任务 ID、REQ-ID 关联、依赖关系）

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
> 见 `templates/review_skeleton.md` 的"关键发现"章节

### RVW-001（P0/P1/P2）<标题>
- 证据：
- 风险：
- 建议修改：

## §3 覆盖率证明（REP 步骤 D）
> 见 `templates/review_skeleton.md` 的"§3 覆盖率证明"章节

| 维度 | 应检项数 | 已检 | 未检 | 未检说明 |
|------|---------|------|------|---------|
| 事实核实（步骤A） | | | | |
| 概念交叉引用（步骤B） | | | | |
| 审查清单项 | 6 | | | |
| REQ-ID 反向覆盖项 | | | | |

## 对抗性自检
> 通用检查项见 `templates/review_skeleton.md`

- [ ] 是否存在"我知道意思但文本没写清"的地方？
- [ ] 所有"可选/或者/暂不"表述是否已收敛为单一口径？
- [ ] 高风险项是否已在本阶段收敛？

## 收敛判定
> 见 `templates/review_skeleton.md` 的"收敛判定"章节

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

## 证据清单
> 见 `templates/review_skeleton.md` 的"证据清单"章节

## 多轮审查追加格式
> 见 `templates/review_skeleton.md` 的"多轮审查追加格式"章节
